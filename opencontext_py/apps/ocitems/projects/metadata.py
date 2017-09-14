import json
import numpy as np
from numpy import vstack, array
from scipy.cluster.vq import kmeans,vq
from math import radians, cos, sin, asin, sqrt
from django.db import models
from django.db.models import Avg, Max, Min
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator
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
        if(len(sub_projs) > 0):
            self.sub_projects = sub_projs
        else:
            self.sub_projects = False
        return self.sub_projects

    def get_jsonldish_parents(self, uuid, add_original=True):
        """
        Gets parent projects for a project.
        Returns a list of dictionary objects similar to JSON-LD expectations
        This is useful for faceted search

        If add_original is true, add the original UUID for the entity
        that's the childmost item, at the bottom of the hierarchy
        """
        output = False
        raw_parents = self.get_parents(uuid)
        if(add_original):
            # add the original identifer to the list of parents, at lowest rank
            raw_parents.insert(0, uuid)
        if len(raw_parents) > 0:
            # reverse the order of the list, to make top most concept
            # first
            output = []
            parents = raw_parents[::-1]
            for par_id in parents:
                ent = Entity()
                found = ent.dereference(par_id)
                if(found):
                    p_item = LastUpdatedOrderedDict()
                    p_item['id'] = ent.uri
                    p_item['slug'] = ent.slug
                    p_item['label'] = ent.label
                    if(ent.data_type is not False):
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
            self.max_geo_range = self.get_point_distance(min_point[0],
                                                         min_point[1],
                                                         max_point[0],
                                                         max_point[1])
            if self.print_progress:
                print('Max geo range: ' + str(self.max_geo_range))
            if self.max_geo_range == 0:
                # only 1 geopoint known for the project
                lon_lat = [self.geo_range['longitude__min'],
                           self.geo_range['latitude__max']]
                clusts = {'centroids': [lon_lat],
                          'boxes': []}
            else:
                # need to cluster geo data
                clusts = self.cluster_geo(uuids)
                if self.print_progress:
                    print('finished clusters: ' + str(clusts))
            self.make_geo_objs(clusts)
            output = True
        return output

    def make_geo_objs(self, clusts):
        geo_objs = []
        if len(clusts['boxes']) == 0:
            # no bounding box polygons, just a simple point to add
            if self.print_progress:
                print(str(clusts))
            geo_obj = self.make_geo_obj(1,
                                        clusts['centroids'][0][0],
                                        clusts['centroids'][0][1]
                                        )
            geo_objs.append(geo_obj)
        else:
            # has 1 or more bounding box polygons
            i = 0
            for box in clusts['boxes']:
                act_cent = clusts['centroids'][i]
                i += 1
                geo_obj = self.make_geo_obj(i,
                                            act_cent[0],
                                            act_cent[1],
                                            box
                                            )
                if(box[0][0][0] != box[0][2][0] and box[0][0][1] != box[0][2][1]):
                    # only add a box if the cluster has more than 1 item
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
        while resonable_clusters is False:
            ch_boxes = []
            boxes = []
            resonable_clusters = True
            centroids, _ = kmeans(data, number_clusters)
            idx, _ = vq(data, centroids)
            i = 0
            for centroid in centroids:
                cent_lon = centroid[0]
                cent_lat = centroid[1]
                max_lon = max(data[idx == i, 0])
                max_lat = max(data[idx == i, 1])
                min_lon = min(data[idx == i, 0])
                min_lat = min(data[idx == i, 1])
                ch_box = {'max_lon': max_lon,
                          'max_lat': max_lat,
                          'min_lon': min_lon,
                          'min_lat': min_lat}
                ch_boxes.append(ch_box)
                i += 1
            i = 0
            for centroid in centroids:
                cent_lon = centroid[0]
                cent_lat = centroid[1]
                max_lon = max(data[idx == i, 0])
                max_lat = max(data[idx == i, 1])
                min_lon = min(data[idx == i, 0])
                min_lat = min(data[idx == i, 1])
                if(len(data[idx == i]) < 2):
                    # the cluster has only 1 point, meaning it may be too small
                    cluster_ok = self.check_ok_cluster_for_lone_point(uuids,
                                                                      max_lon,
                                                                      max_lat)
                    if cluster_ok is False:
                        resonable_clusters = False
                        if self.print_progress:
                            print('Loop (' + str(number_clusters) + '), cluster '
                                           + str(i)
                                           + ' has too few members')
                box = self.make_box(min_lon, min_lat, max_lon, max_lat)
                boxes.append(box)
                jj = 0
                for ch_box in ch_boxes:
                    if jj != i:
                        # different box then
                        overlap = self.check_overlap(min_lon,
                                                     min_lat,
                                                     max_lon,
                                                     max_lat,
                                                     ch_box)
                        if overlap:
                            resonable_clusters = False
                            if self.print_progress:
                                print('Loop (' + str(number_clusters) + '), cluster '
                                      + str(i)
                                      + ' overlaps with ' + str(jj))
                    jj += 1
                i += 1
                for o_centroid in centroids:
                    o_lon = o_centroid[0]
                    o_lat = o_centroid[1]
                    if o_lon != cent_lon and o_lat != cent_lat:
                        # not the same centroid, so check distance
                        cent_dist = self.get_point_distance(o_lon,
                                                            o_lat,
                                                            cent_lon,
                                                            cent_lat)
                        if cent_dist < self.MIN_CLUSTER_SIZE_KM \
                           or cent_dist < (self.max_geo_range * .05):
                            resonable_clusters = False
                            if self.print_progress:
                                print('Loop (' + str(number_clusters) + ') cluster size: ' \
                                      + str(cent_dist) + ' too small to ' + str(self.max_geo_range))
            if resonable_clusters is False:
                number_clusters = number_clusters - 1
            if number_clusters < 1:
                resonable_clusters = True
        return {'centroids': centroids,
                'boxes': boxes}

    def check_overlap(self, min_lon, min_lat, max_lon, max_lat, ch_box):
        """ Checkes to see if a box is inside the coordinates of another box """
        overlap = False
        overlap_lon = False
        overlap_lat = False
        if (min_lon >= ch_box['min_lon'] and min_lon <= ch_box['max_lon'])\
           or (max_lon >= ch_box['min_lon'] and max_lon <= ch_box['max_lon']):
            overlap_lon = True
        if (min_lat >= ch_box['min_lat'] and min_lat <= ch_box['max_lat'])\
           or (max_lat >= ch_box['min_lat'] and max_lat <= ch_box['max_lat']):
            overlap_lat = True
        if overlap_lon and overlap_lat:
            overlap = True
        else:
            ave_lon = (min_lon + max_lon) * .5
            ave_lat = (min_lat + max_lat) * .5
        return overlap

    def get_point_distance(self, lon1, lat1, lon2, lat2):
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        """
        # convert decimal degrees to radians 
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        # haversine formula 
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        km = 6367 * c
        return km

    def make_box(self, min_lon, min_lat, max_lon, max_lat):
        """ Makes geojson coordinates list for a bounding feature """
        coordinates = [[[min_lon, min_lat],
                       [min_lon, max_lat],
                       [max_lon, max_lat],
                       [max_lon, min_lat],
                       [min_lon, min_lat]]]
        return coordinates

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

