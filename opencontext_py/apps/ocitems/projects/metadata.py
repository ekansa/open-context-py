import json
import numpy as np
from numpy import vstack, array
from scipy.cluster.vq import kmeans,vq
from math import radians, cos, sin, asin, sqrt
from django.db import models
from django.db.models import Avg, Max, Min

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator

from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.projects.models import Project

from opencontext_py.apps.entities.entity.models import Entity


class ProjectRels():
    """
    Checks on project relationships with subprojects
    """

    def __init__(self):
        self.sub_projects = False
        self.parent_projects = []
        self.child_entities = LastUpdatedOrderedDict()
    
    def get_sub_projects(self, uuid):
        """
        Gets (child) sub-projects from the current project uuid
        """
        sub_projs = Project.objects.filter(project_uuid=uuid).exclude(uuid=uuid)
        if len(sub_projs) > 0:
            self.sub_projects = sub_projs
        else:
            self.sub_projects = False
        return self.sub_projects

    def get_jsonldish_parents(self, uuid, add_original=True):
        """Gets parent projects for a project.
        Returns a list of dictionary objects similar to JSON-LD expectations
        This is useful for faceted search
        """
        m_cache = MemoryCache()
        cache_key = m_cache.make_cache_key(
            'proj-par-jsonldish_{}'.format(add_original),
            uuid
        )
        output = m_cache.get_cache_object(cache_key)
        if output is None:
            output = self._db_get_jsonldish_parents(
                uuid, add_original=add_original
            )
            m_cache.save_cache_object(cache_key, output)
        return output
        
    def _db_get_jsonldish_parents(self, uuid, add_original=True):
        """
        Uses the DB to gets parent projects for a project.
        Returns a list of dictionary objects similar to JSON-LD expectations
        This is useful for faceted search

        If add_original is true, add the original UUID for the entity
        that's the childmost item, at the bottom of the hierarchy
        """
        output = False
        raw_parents = self.get_parents(uuid)
        if add_original:
            # add the original identifer to the list of parents, at lowest rank
            raw_parents.insert(0, uuid)
        if len(raw_parents) < 1:
            # Skip the rest.
            return output
        # Reverse the order of the list, to make top most concept
        # first
        output = []
        parents = raw_parents[::-1]
        for par_id in parents:
            ent = Entity()
            found = ent.dereference(par_id)
            if not found:
                continue
            p_item = LastUpdatedOrderedDict()
            p_item['id'] = ent.uri
            p_item['slug'] = ent.slug
            p_item['label'] = ent.label
            if isinstance(ent.data_type, str):
                p_item['type'] = ent.data_type
            else:
                p_item['type'] = '@id'
            output.append(p_item)
        return output

    def get_parents(self, uuid):
        """ gets the project parents , recursively"""
        par_proj = Project.objects.filter(uuid=uuid).exclude(project_uuid=uuid)[:1]
        if len(par_proj) > 0:
            self.parent_projects.append(par_proj[0].project_uuid)
            self.get_parents(par_proj[0].project_uuid) # recursively look for the parent of the parent
        return self.parent_projects


class ProjectMeta():
    """
    Generates geospatial and chronological summaries for project metadata
    """

    MAX_CLUSTERS = 15
    MIN_CLUSTER_SIZE_KM = 5  # diagonal length in KM between min(lat/lon) and max(lat/lon)
    LENGTH_CENTOID_FACTOR = .75  # for comparing cluster diagonal length with centoid distances

    def __init__(self):
        self.project_uuid = False
        self.geo_objs = False  # geospace objects of proj. metadata
        self.max_geo_range = False  # max distance (Euclidean coordinates)
                                    # of rectangular region with all project points
        self.event_ents = False
        self.geo_range = False  # dict object of min, max longitude, latitudes
        self.print_progress = False
        self.project_specificity = 0
    
    def get_project_geo_from_db(self, project_uuid):
        """ gets project geospatial information from the database
        """
        self.geo_objs = Geospace.objects\
                                .filter(uuid=project_uuid)\
                                .order_by('feature_id')
        if len(self.geo_objs) < 1:
            self.geo_objs = False
        return self.geo_objs

    def make_geo_meta(self, project_uuid, sub_projs=False):
        output = False
        self.project_uuid = project_uuid
        if sub_projs is False:
            # check if there are subjects in this project
            pr = ProjectRels()
            sub_projs = pr.get_sub_projects(project_uuid)
        if sub_projs is False:
            uuids = [project_uuid]
        else:
            uuids = []
            for sub_proj in sub_projs:
                uuids.append(sub_proj.uuid)
            uuids.append(project_uuid)
        self.get_geo_range(uuids)
        if self.geo_range is False:
            pass
            if self.print_progress:
                print('Range fail: ' + str(self.geo_range) )
        else:
            if self.print_progress:
                print('Working on range: ' + str(self.geo_range) )
            min_lon_lat = [self.geo_range['longitude__min'],
                           self.geo_range['latitude__min']]
            max_lon_lat = [self.geo_range['longitude__max'],
                           self.geo_range['latitude__max']]
            min_point = np.fromiter(min_lon_lat, np.dtype('float'))
            max_point = np.fromiter(max_lon_lat, np.dtype('float'))
            gm = GlobalMercator()
            self.max_geo_range = gm.distance_on_unit_sphere(min_point[1],
                                                            min_point[0],
                                                            max_point[1],
                                                            max_point[0])
            if self.print_progress:
                print('Max geo range: ' + str(self.max_geo_range))
            if self.max_geo_range == 0:
                # only 1 geopoint known for the project
                proc_centroids = []
                proc_centroid = {}
                proc_centroid['index'] = 0
                proc_centroid['id'] = 1
                proc_centroid['num_points'] = 1
                proc_centroid['cent_lon'] = self.geo_range['longitude__min']
                proc_centroid['cent_lat'] = self.geo_range['latitude__max']
                proc_centroid['box'] = False
                proc_centroids.append(proc_centroid)
            else:
                # need to cluster geo data
                proc_centroids = self.cluster_geo(uuids)
            self.make_geo_objs(proc_centroids)
            output = True
        return output

    def make_geo_objs(self, proc_centroids):
        geo_objs = []
        if self.print_progress:
            print('number centroids: ' + str(len(proc_centroids)))
        for proc_centroid in proc_centroids:
            if self.print_progress and 'cluster_loop' in proc_centroid:
                message = 'Cluster Loop: ' + str(proc_centroid['cluster_loop']) + ', cluster: ' + str(proc_centroid['index']) +  ' '
                message += ' geospace object creation.'
                print(message)
            geo_obj = self.make_geo_obj(proc_centroid['id'],
                                        proc_centroid['cent_lon'],
                                        proc_centroid['cent_lat'],
                                        proc_centroid['box'])
            geo_objs.append(geo_obj)
        self.geo_objs = geo_objs
        return geo_objs

    def make_geo_obj(self, feature_id, lon, lat, coords=False):
        geo_obj = Geospace()
        geo_obj.uuid = self.project_uuid
        geo_obj.project_uuid = self.project_uuid
        geo_obj.source_id = 'Project metadata summary'
        geo_obj.item_type = 'projects'
        geo_obj.feature_id = feature_id
        geo_obj.meta_type = 'oc-gen:geo-coverage'
        if coords is False:
            geo_obj.ftype = 'Point'
            geo_obj.coordinates = ''
        else:
            geo_obj.ftype = 'Polygon'
            geo_obj.coordinates = json.dumps(coords, ensure_ascii=False)
        geo_obj.latitude = lat
        geo_obj.longitude = lon
        geo_obj.specificity = self.project_specificity
        geo_obj.note = 'Project geographic coverage \
                        summarized from geospatial data \
                        describing subjects published \
                        with this project.'
        return geo_obj

    def cluster_geo(self, uuids):
        """ Puts geo points into clusters """
        dist_geo = self.get_distinct_geo(uuids)
        lon_lats = []
        for geo in dist_geo:
            # using geojson order of lon / lat
            lon_lat = [geo['longitude'], geo['latitude']]
            # makes it a numpy float
            dpoint = np.fromiter(lon_lat, np.dtype('float'))
            lon_lats.append(dpoint)
        # create a numpy array object from my list of float coordinates
        data = array(lon_lats)
        resonable_clusters = False
        number_clusters = self.MAX_CLUSTERS
        # check to make sure we don't have too many clusters
        centroid_problem = True
        while centroid_problem is True:
            try:
                centroids, _ = kmeans(data, number_clusters)
                centroid_problem = False
            except:
                centroid_problem = True
            if centroid_problem:
                number_clusters -= 1
        proc_centroids = []
        cluster_loop = 0
        while resonable_clusters is False:
            cluster_loop += 1
            print('check loop: ' + str(cluster_loop))
            resonable_clusters = True
            centroids, _ = kmeans(data, number_clusters)
            idx, _ = vq(data, centroids)
            # first make check boxes, which will be used to
            # see if there is an overlap with another cluster
            check_boxes = []
            i = 0
            for centroid in centroids:
                check_box = {}
                check_box['index'] = i
                check_box['id'] = i + 1
                check_box['cent_lon'] = centroid[0]
                check_box['cent_lat'] = centroid[1]
                check_box['max_lon'] = max(data[idx == i, 0])
                check_box['max_lat'] = max(data[idx == i, 1])
                check_box['min_lon'] = min(data[idx == i, 0])
                check_box['min_lat'] = min(data[idx == i, 1])
                # ensure a minimum sized region
                check_box = self.make_min_size_region(check_box)
                check_boxes.append(check_box)
                i += 1
            # now make a list of the "processed" centroids
            # that have useful data about them.
            i = 0
            proc_centroids = []
            for centroid in centroids:
                proc_centroid = {}
                proc_centroid['index'] = i
                proc_centroid['id'] = i + 1
                proc_centroid['cluster_loop'] = cluster_loop
                proc_centroid['num_points'] = len(data[idx == i])
                proc_centroid['cent_lon'] = centroid[0]
                proc_centroid['cent_lat'] = centroid[1]
                proc_centroid['max_lon'] = max(data[idx == i, 0])
                proc_centroid['max_lat'] = max(data[idx == i, 1])
                proc_centroid['min_lon'] = min(data[idx == i, 0])
                proc_centroid['min_lat'] = min(data[idx == i, 1])
                # ensure a minimum sized region
                proc_centroid = self.make_min_size_region(proc_centroid)
                proc_centroid['box'] = self.make_box(proc_centroid['min_lon'],
                                                     proc_centroid['min_lat'],
                                                     proc_centroid['max_lon'],
                                                     proc_centroid['max_lat'])
                proc_centroid['ok_cluster'] = self.check_ok_cluster(proc_centroid,
                                                                    centroids,
                                                                    uuids)
                proc_centroid['overlaps'] = self.check_overlaps(proc_centroid,
                                                                check_boxes)
                if proc_centroid['ok_cluster'] is False \
                   or proc_centroid['overlaps']:
                    resonable_clusters = False
                proc_centroids.append(proc_centroid)
                i += 1
            # OK done with looping through centroids to check on them.
            if resonable_clusters is False:
                number_clusters = number_clusters - 1
            if number_clusters < 1:
                resonable_clusters = True
        return proc_centroids

    def check_ok_cluster(self, proc_centroid, centroids, uuids):
        """ checks to see if the proc_centroid is an OK
            cluster, based on the number of items it
            contains or if it is far from all other centroids
        """
        ok_cluster = True  # default to this being a good cluster
        if proc_centroid['num_points'] < 2:
            # the cluster has only 1 point, meaning it may be too small
            db_multiple = self.check_ok_cluster_for_lone_point(uuids,
                                                               proc_centroid['max_lon'],
                                                               proc_centroid['max_lat'])
            if db_multiple is False:
                # not many records, 
                # OK now check if it is far from other points
                single_far = True
                for o_centroid in centroids:
                    o_lon = o_centroid[0]
                    o_lat = o_centroid[1]
                    if o_lon != proc_centroid['cent_lon'] \
                       and o_lat != proc_centroid['cent_lat']:
                        # not the same centroid, so check distance
                        gm = GlobalMercator()
                        cent_dist = gm.distance_on_unit_sphere(o_lat,
                                                               o_lon,
                                                               proc_centroid['cent_lat'],
                                                               proc_centroid['cent_lon'])
                        if cent_dist < 1000:
                            if cent_dist < self.MIN_CLUSTER_SIZE_KM \
                               or cent_dist < (self.max_geo_range * .1):
                                # we found a case where this point is close
                                # to another centroid
                                single_far = False
                if single_far is False:
                    ok_cluster = False
        if self.print_progress and ok_cluster is False:
            message = 'Cluster Loop: ' + str(proc_centroid['cluster_loop']) + ', cluster: ' + str(proc_centroid['index']) +  ' '
            message += ' has few items, too close with other centroids.'
            print(message)
        return ok_cluster

    def check_overlaps(self, proc_centroid, check_boxes):
        """ Checkes to see if a box is inside the coordinates of another box """
        overlap = False
        for check_box in check_boxes:
            overlap_lon = False
            overlap_lat = False
            if proc_centroid['index'] != check_box['index']:
                # only do this check if we are not looking in same cluster
                if (proc_centroid['min_lon'] >= check_box['min_lon'] \
                    and proc_centroid['min_lon'] <= check_box['max_lon'])\
                   or ( proc_centroid['max_lon'] >= check_box['min_lon'] \
                    and proc_centroid['max_lon'] <= check_box['max_lon']):
                    overlap_lon = True
                if (proc_centroid['min_lat'] >= check_box['min_lat'] \
                    and proc_centroid['min_lat'] <= check_box['max_lat'])\
                   or ( proc_centroid['max_lat'] >= check_box['min_lat'] \
                    and proc_centroid['max_lat'] <= check_box['max_lat']):
                    overlap_lat = True
                if overlap_lon and overlap_lat:
                    overlap = True
                    break
        if self.print_progress and overlap:
            message = 'Cluster Loop: ' + str(proc_centroid['cluster_loop']) + ', cluster: ' + str(proc_centroid['index']) +  ' '
            message += ' has overlaps with other clusters.'
            print(message)
        return overlap
    
    def make_min_size_region(self, region_dict):
        """ widens a coordinate pair based on maximum distance
            between points
            
            this makes a square (on a mercator projection) bounding box
            region. it will have different real-world distances in the
            east west direction between the northern and southern sides
        """
        min_distance = self.max_geo_range * 0.05
        gm = GlobalMercator()
        # measure the north south distance
        mid_lat = (region_dict['min_lat'] + region_dict['max_lat']) / 2
        mid_lon = (region_dict['min_lon'] + region_dict['max_lon']) / 2
        ns_diag_dist = gm.distance_on_unit_sphere(region_dict['min_lat'],
                                                  mid_lon,
                                                  region_dict['max_lat'],
                                                  mid_lon)
        ew_diag_dist = gm.distance_on_unit_sphere(mid_lat,
                                                  region_dict['min_lon'],
                                                  mid_lat,
                                                  region_dict['max_lon'])
        if ns_diag_dist < min_distance:
            # the north-south distance is too small, so widen it.
            # first, find a point south of the mid lat, at the right distance
            new_lat_s = gm.get_point_by_distance_from_point(mid_lat,
                                                            mid_lon,
                                                            (min_distance / 2),
                                                            180)
            # second, find a point north of the mid lat, at the right distance
            new_lat_n = gm.get_point_by_distance_from_point(mid_lat,
                                                            mid_lon,
                                                            (min_distance / 2),
                                                            0)
            region_dict['min_lat'] = new_lat_s['lat']
            region_dict['max_lat'] = new_lat_n['lat']
        if ew_diag_dist < min_distance:
            # the east-west distance is too small, so widen it.
            # first, find a point south of the mid lat, at the right distance
            new_lon_w = gm.get_point_by_distance_from_point(mid_lat,
                                                            mid_lon,
                                                            (min_distance / 2),
                                                            270)
            # second, find a point north of the mid lat, at the right distance
            new_lon_e = gm.get_point_by_distance_from_point(mid_lat,
                                                            mid_lon,
                                                            (min_distance / 2),
                                                            90)
            region_dict['min_lon'] = new_lon_w['lon']
            region_dict['max_lon'] = new_lon_e['lon']
        return region_dict

    def make_box(self, min_lon, min_lat, max_lon, max_lat):
        """ Makes geojson coordinates list for a bounding feature """
        coords = []
        outer_coords = []
        # right hand rule, counter clockwise outside
        outer_coords.append([min_lon, min_lat])
        outer_coords.append([max_lon, min_lat])
        outer_coords.append([max_lon, max_lat])
        outer_coords.append([min_lon, max_lat])
        outer_coords.append([min_lon, min_lat])
        coords.append(outer_coords)
        return coords

    def check_ok_cluster_for_lone_point(self, uuids, lon, lat):
        """ Checks to see if a lone point has enough items
           items in it to be considered a good cluster """
        cluster_ok = False
        uuids = self.make_uuids_list(uuids)
        p_geo = Geospace.objects.filter(project_uuid__in=uuids,
                                        latitude=lat,
                                        longitude=lon)[:1]
        if len(p_geo) == 1:
            subj_uuid = p_geo[0].uuid
            cont = Containment()
            children = cont.get_children_by_parent_uuid(subj_uuid, True)
            if len(children) > 2:
                cluster_ok = True
        return cluster_ok

    def get_distinct_geo(self, uuids):
        """ Gets distinct geo lat/lons """
        uuids = self.make_uuids_list(uuids)
        dist_geo = Geospace.objects.filter(project_uuid__in=uuids)\
                           .exclude(latitude=0, longitude=0)\
                           .values('latitude', 'longitude')\
                           .distinct()
        return dist_geo

    def get_geo_range(self, uuids):
        """
        Gets summary geospatial information for a string or a list
        of project uuids. Accepts a list to get sub-projects
        """
        uuids = self.make_uuids_list(uuids)
        if self.print_progress:
            print('Get geo range for ' + str(uuids))
        proj_geo = Geospace.objects.filter(project_uuid__in=uuids)\
                           .exclude(latitude=0, longitude=0)\
                           .aggregate(Max('latitude'),
                                      Max('longitude'),
                                      Min('latitude'),
                                      Min('longitude'),
                                      Avg('specificity'))
        if proj_geo['latitude__max'] is not None:
            self.geo_range = proj_geo
            act_specificity = round(float(proj_geo['specificity__avg']), 0)
            if self.project_specificity == 0:
                try:
                    self.project_specificity = int(act_specificity)
                except:
                    pass
        elif self.print_progress:
            print('Problem with: ' + str(proj_geo))
        return self.geo_range

    def make_uuids_list(self, uuids):
        """ Makes a list of UUIDS if only passed a string """
        if not isinstance(uuids, list):
            uuids = [uuids]  # make a list
        return uuids

