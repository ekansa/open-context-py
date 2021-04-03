
import copy
import hashlib


import numpy as np
from numpy import vstack, array
from scipy.cluster.vq import kmeans, vq
from math import radians, cos, sin, asin, sqrt

from django.db.models import Avg, Max, Min
from django.db.models import Q

from django.core.cache import caches
from django.db.models import OuterRef, Subquery

from opencontext_py.libs.globalmaptiles import GlobalMercator

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
)



MAX_CLUSTERS = 15
MIN_CLUSTER_SIZE_KM = 5  # diagonal length in KM between min(lat/lon) and max(lat/lon)
LENGTH_CENTROID_FACTOR = 0.75  # for comparing cluster diagonal length with centroid distances



def get_centroid_clusters(lon_lat_array, act_cluster_count=MAX_CLUSTERS)
    """Makes clusters from an array of lon lat centroid coordinates

    :param np.array lon_lat_array: A numpy array of lon_lat (in that 
        order) coordinate pairs to cluster into regions. Note! This
        can also be a two column dataframe, provided the longitude
        is column index 0, and latitude is column index 1
    :param int act_cluster_count: The max number of clusters we will
        attempt to make
    """
    make_new_clusters = True
    lon_lat_clusters = None
    while make_new_clusters and act_cluster_count > 0:
        try:
            lon_lat_clusters, _ = kmeans(lon_lat_array, act_cluster_count)
            make_new_clusters = False
        except:
            make_new_clusters = True
        if make_new_clusters:
            act_cluster_count -= 1
    return lon_lat_clusters, act_cluster_count


def make_geojson_coord_box(min_lon, min_lat, max_lon, max_lat):
    """ Makes geojson coordinates list for a bounding feature """
    coords = []
    outer_coords = []
    # Right hand rule, counter clockwise outside
    outer_coords.append([min_lon, min_lat])
    outer_coords.append([max_lon, min_lat])
    outer_coords.append([max_lon, max_lat])
    outer_coords.append([min_lon, max_lat])
    outer_coords.append([min_lon, min_lat])
    coords.append(outer_coords)
    return coords


def make_min_size_region(region_dict, min_distance=MIN_CLUSTER_SIZE_KM):
    """ Widens a coordinate pair based on maximum distance
        between points
        
        this makes a square (on a mercator projection) bounding box
        region. it will have different real-world distances in the
        east west direction between the northern and southern sides
    """
    gm = GlobalMercator()
    # Measure the north south distance
    mid_lat = (region_dict['min_lat'] + region_dict['max_lat']) / 2
    mid_lon = (region_dict['min_lon'] + region_dict['max_lon']) / 2
    ns_diag_dist = gm.distance_on_unit_sphere(
        region_dict['min_lat'],
        mid_lon,
        region_dict['max_lat'],
        mid_lon,
    )
    ew_diag_dist = gm.distance_on_unit_sphere(
        mid_lat,
        region_dict['min_lon'],
        mid_lat,
        region_dict['max_lon']
    )
    if ns_diag_dist < min_distance:
        # the north-south distance is too small, so widen it.
        # first, find a point south of the mid lat, at the right distance
        new_lat_s = gm.get_point_by_distance_from_point(
            mid_lat,
            mid_lon,
            (min_distance / 2),
            180
        )
        # second, find a point north of the mid lat, at the right distance
        new_lat_n = gm.get_point_by_distance_from_point(
            mid_lat,
            mid_lon,
            (min_distance / 2),
            0
        )
        region_dict['min_lat'] = new_lat_s['lat']
        region_dict['max_lat'] = new_lat_n['lat']
    if ew_diag_dist < min_distance:
        # the east-west distance is too small, so widen it.
        # first, find a point south of the mid lat, at the right distance
        new_lon_w = gm.get_point_by_distance_from_point(
            mid_lat,
            mid_lon,
            (min_distance / 2),
            270
        )
        # second, find a point north of the mid lat, at the right distance
        new_lon_e = gm.get_point_by_distance_from_point(
            mid_lat,
            mid_lon,
            (min_distance / 2),
            90
        )
        region_dict['min_lon'] = new_lon_w['lon']
        region_dict['max_lon'] = new_lon_e['lon']
    return region_dict


def check_region_overlaps(region_dicts):
    """Checks if regions overlap with other regions"""
    overlapping_regions = []
    for region_dict in region_dicts:
        region_overlap_ids = []
        for comp_dict in region_dicts:
            if region_dict.get('id') == comp_dict.get('id'):
                # Same region, skip
                continue
            if region_dict['max_lon'] < comp_dict['min_lon']:
                continue
            if region_dict['min_lon'] > comp_dict['max_lon']:
                continue
            if region_dict['max_lat'] < comp_dict['min_lat']:
                continue
            if region_dict['min_lat'] > comp_dict['max_lat']:
                continue
            region_overlap_ids += [
                region_dict.get('id'), 
                comp_dict.get('id')
            ]
        if not region_overlap_ids:
            continue
        region_overlap_ids = set(region_overlap_ids)
        if region_overlap_ids in overlapping_regions:
            continue
        overlapping_regions.append(region_overlap_ids)
    return overlapping_regions


def check_cluster_contains_enough(region_dict, lone_point_check_uuid=None):
    """Checks to see if a cluster with a lone point is reasonable

    :param dict region_dict: A region dict generated from clustering
        an array of lon lan points
    :param UUID lone_point_check_uuid: A UUID or string UUID that 
        needs to be checked to see if this point is representative
        of enough items to be its own cluster.
    """
    if region_dict['count_points'] > 1:
        # Nothing to check, their are more than 1 points
        # in this cluster.
        return True
    if not lone_point_check_uuid:
        # We're not doing a query to look up nearby related
        # points to this item.
        return False
    man_obj = AllManifest.objects.filter(
        uuid=lone_point_check_uuid
    ).first()
    if not man_obj:
        # We can't find anything to check!
        return False
    
    item_project_uuids = []
    if man_obj.item_type == 'projects':
        # This item itself is a project, which means that we want
        # to use it as the editing_project in the user interface.
        item_project_uuids.append(str(man_obj.uuid))

    item_project = man_obj.project
    at_root_proj = False
    while not at_root_proj:
        project_uuid = str(item_project.uuid)
        if not project_uuid in item_project_uuids:
            item_project_uuids.append(project_uuid)
        else:
            at_root_proj = True
        if project_uuid == str(configs.OPEN_CONTEXT_PROJ_UUID):
            at_root_proj = True
        if not at_root_proj:
            # Now go up a level in the item hierarchy
            item_project = item_project.project
    
    spt_qs = AllSpaceTime.objects.filter(
        Q(project_id__in=item_project_uuids)
        |Q(item__project_id__in=item_project_uuids)
    ).filter(
        item__item_type='subjects',
        latitude__gte=region_dict['min_lat'],
        latitude__lte=region_dict['max_lat'],
        longitude__gte=region_dict['min_lon'],
        longitude__lte=region_dict['max_lon'],
    ).distinct(
        'item'
    ).values('item')

    count_contexts = AllManifest.objects.filter(
        project_id__in=item_project_uuids,
        context_in=spt_qs
    ).count()
    if count_contexts > 1:
        return True

    # There's just not much in this, it should not be
    # an acceptable region.
    return False


def cluster_geo_centroids(
    lon_lat_array, 
    max_clusters=MAX_CLUSTERS,
    min_cluster_size_km=MIN_CLUSTER_SIZE_KM,
    length_centroid_factor=LENGTH_CENTROID_FACTOR,
    lone_point_check_uuid=None,
):
    """Clusters centroids of items in a space_time_qs

    :param np.array lon_lat_array: A numpy array of lon_lat (in that 
        order) coordinate pairs to cluster into regions. Note! This
        can also be a two column dataframe, provided the longitude
        is column index 0, and latitude is column index 1
    :param int max_clusters: The maximum number of clusters
        to return
    :param float min_cluster_size_km: The minimum diagonal 
        length in KM between min(lat/lon) and max(lat/lon)
    :param float length_centroid_factor: for comparing cluster diagonal
        length with centroid distances
    """
    
    region_dicts = []
    reasonable_clusters = False
    act_cluster_count = max_clusters
    while not reasonable_clusters:
        lon_lat_clusters, act_cluster_count = get_centroid_clusters(
            lon_lat_array, 
            act_cluster_count=act_cluster_count,
        )
        if not lon_lat_clusters:
            return None
        
        # Assume we made reasonable clusters.
        reasonable_clusters = True
        
        # Make an index to lookup coordinate ranges in the
        # clusters.
        idx, _ = vq(lon_lat_array, lon_lat_clusters)
        # first make check boxes, which will be used to
        # see if there is an overlap with another cluster
        i = 0
        region_dicts = []
        for lon_lat_cluster in lon_lat_clusters:
            region_dict = {}
            region_dict['index'] = i
            region_dict['id'] = i + 1
            region_dict['cent_lon'] = lon_lat_cluster[0]
            region_dict['cent_lat'] = lon_lat_cluster[1]
            region_dict['count_points'] = len(lon_lat_array[idx == i])
            region_dict['max_lon'] = max(lon_lat_array[idx == i, 0])
            region_dict['max_lat'] = max(lon_lat_array[idx == i, 1])
            region_dict['min_lon'] = min(lon_lat_array[idx == i, 0])
            region_dict['min_lat'] = min(lon_lat_array[idx == i, 1])
            # ensure a minimum sized region
            region_dict = make_min_size_region(
                region_dict, 
                min_distance=min_cluster_size_km
            )
            region_dict['box'] = make_geojson_coord_box(
                region_dict['min_lon'],
                region_dict['min_lat'],
                region_dict['max_lon'],
                region_dict['max_lat'],
            )
            contains_enough = check_cluster_contains_enough(
                region_dict, 
                lone_point_check_uuid=lone_point_check_uuid
            )
            if not contains_enough:
                reasonable_clusters = False
            region_dicts.append(region_dict)
            i += 1

        # Now check if we did in face make reasonable clusters.
        overlapping_regions = check_region_overlaps(region_dicts)
        if len(overlapping_regions):
            reasonable_clusters = False

        # OK done with looping through centroids to check on them.
        if not reasonable_clusters:
            number_clusters = number_clusters - 1
        if number_clusters < 1:
            resonable_clusters = True
    
    return region_dicts


def make_lon_lat_array_from_qs(space_time_qs):
    """Make a Numpy array from Space-time queryset lon, lat coordinates
    
    :param queryset space_time_qs: The query set of
        space-time instances that we want to cluster
    
    return Numpy array of [lon, lat] coordinate pairs
    """
    lon_lats = []
    for space_time_obj in space_time_qs:
        if not space_time_obj.longitude or not space_time_obj.latitude:
            continue
        dpoint = np.fromiter(
            [float(space_time_obj.longitude), float(space_time_obj.latitude)], 
            np.dtype('float')
        )
        lon_lats.append(dpoint)
    
    if not lon_lats:
        # We have no geospatial lon_lat_array to cluster.
        return None
    
    # Create a Numpy array object from my list of float coordinates
    lon_lat_array = array(lon_lats)
    return lon_lat_array