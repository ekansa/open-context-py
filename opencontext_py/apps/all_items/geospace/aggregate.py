


import json
import numpy as np
import pandas as pd

from sklearn.cluster import KMeans, AffinityPropagation, SpectralClustering
from shapely.geometry import mapping, shape, JOIN_STYLE
from shapely.ops import unary_union
from shapely import get_precision, set_precision, to_geojson

from django.db.models import Q


from opencontext_py.libs.globalmaptiles import GlobalMercator

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
    AllAssertion,
)

from opencontext_py.apps.all_items import permissions
from opencontext_py.apps.all_items.editorial.item import updater_spacetime

from opencontext_py.apps.etl.importer.utilities import validate_transform_data_type_value

from opencontext_py.apps.all_items.geospace import utilities as geo_utils
from opencontext_py.apps.all_items.geospace import geo_quality

"""
# testing

import importlib
import pandas as pd
import random
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
)
from opencontext_py.apps.all_items.geospace import aggregate as geo_agg
importlib.reload(geo_agg)


data = {
    'longitude': (
        [(random.randint(30, 50) + random.random()) for _ in range(50) ]
        + [(random.randint(55, 65) + random.random()) for _ in range(20)]
        + [(random.randint(20, 25) + random.random()) for _ in range(50)]
    ),
    'latitude': (
        [(random.randint(30, 50) + random.random()) for _ in range(50)]
        + [(random.randint(20, 25) + random.random()) for _ in range(20)]
        + [(random.randint(20, 25) + random.random()) for _ in range(50)]
    ),
}
df = pd.DataFrame(data=data)
r_l = geo_agg.cluster_geo_centroids(df)

"""


MAX_CLUSTERS = 15
MIN_CLUSTER_SIZE_KM = 5  # diagonal length in KM between min(lat/lon) and max(lat/lon)


DEFAULT_CLUSTER_METHOD = 'KMeans'
CLUSTER_METHODS = [
    DEFAULT_CLUSTER_METHOD,
    'AffinityPropagation',
    'SpectralClustering',
    'unary_union',
]

DEFAULT_SOURCE_ID = 'geospace-aggregate'


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
        context__in=spt_qs
    ).count()
    if count_contexts > 1:
        return True

    # There's just not much in this, it should not be
    # an acceptable region.
    return False


def cluster_geo_centroids(
    df,
    max_clusters=MAX_CLUSTERS,
    min_cluster_size_km=MIN_CLUSTER_SIZE_KM,
    cluster_method=DEFAULT_CLUSTER_METHOD,
    lone_point_check_uuid=None,
):
    """Clusters centroids of items in a space_time_qs

    :param DataFrame df: A Pandas DataFrame with longitude and
        latitude columns and values.
    :param int max_clusters: The maximum number of clusters
        to return
    :param float min_cluster_size_km: The minimum diagonal
        length in KM between min(lat/lon) and max(lat/lon)
    :param str cluster_method: A string that names the sklearn
        clustering method to use on these data.
    :param UUID lone_point_check_uuid: A UUID or string UUID that
        needs to be checked to see if this point is representative
        of enough items to be its own cluster.
    """
    if cluster_method not in CLUSTER_METHODS:
        raise ValueError(f'Unsupported cluster method {cluster_method}')

    if df.empty:
        return None

    if not set(['longitude', 'latitude']).issubset(set(df.columns)):
        # We're missing the required columns
        return None

    # Remove null values, including "null island"
    ok_index = (
        ~df['longitude'].isnull()
        & ~df['latitude'].isnull()
        & ~((df['longitude'] == 0) & (df['latitude'] == 0))
    )
    if df[ok_index].empty:
        # We don't have any coordinates, despite having the columns
        return None

    df_g = df[ok_index][['latitude', 'longitude']].groupby(
        ['latitude', 'longitude'],
        as_index=False,
    ).first()
    if len(df_g.index) == 1:
        return [
            {
                'point': True,
                'id': 'point',
                'count_points': 1,
                'cent_lat': df_g['latitude'].iloc[0],
                'cent_lon': df_g['longitude'].iloc[0],
                'coordinates': [
                    df_g['longitude'].iloc[0],
                    df_g['latitude'].iloc[0],
                ],
            },
        ]
    
    # Throw out everything missing coordinates.
    df = df[ok_index].copy()

    if max_clusters == 1:
        # Nothing fancy to do, we just want 1 polygon
        region_dict = {}
        region_dict['id'] = 1
        region_dict['count_points'] = len(df.index)
        region_dict['max_lon'] = df['longitude'].max()
        region_dict['max_lat'] = df['latitude'].max()
        region_dict['min_lon'] = df['longitude'].min()
        region_dict['min_lat'] = df['latitude'].min()
        # ensure a minimum sized region
        region_dict = make_min_size_region(
            region_dict,
            min_distance=min_cluster_size_km
        )
        region_dict['coordinates'] = geo_utils.make_geojson_coord_box(
            region_dict['min_lon'],
            region_dict['min_lat'],
            region_dict['max_lon'],
            region_dict['max_lat'],
        )
        region_dict['cent_lon'], region_dict['cent_lat'] = (
            geo_utils.get_centroid_of_coord_box(region_dict['coordinates'])
        )
        return [region_dict]

    gm = GlobalMercator()
    max_dataset_distance = gm.distance_on_unit_sphere(
        df['latitude'].max(),
        df['longitude'].min(),
        df['latitude'].min(),
        df['longitude'].max(),
    )
    if min_cluster_size_km > max_dataset_distance * 0.05:
        min_cluster_size_km = max_dataset_distance * 0.05

    region_dicts = []
    reasonable_clusters = False
    act_cluster_count = max_clusters
    while not reasonable_clusters:

        if cluster_method == 'AffinityPropagation':
            # NOTE: We can't pass an argument to ask for a certain number of
            # starting clusters.
            aff_p = AffinityPropagation(random_state=None)
            cluster_ids = aff_p.fit_predict(df[['longitude', 'latitude']])
        elif cluster_method == 'SpectralClustering':
            # NOTE: This may be more error prone and weird.
            spectral = SpectralClustering(
                n_clusters=act_cluster_count,
                random_state=None
            )
            cluster_ids = spectral.fit_predict(df[['longitude', 'latitude']])
        else:
            if len(df.index) >= act_cluster_count:
                kmeans = KMeans(n_clusters=act_cluster_count)
                cluster_ids = kmeans.fit_predict(df[['longitude', 'latitude']])
            else:
                cluster_ids = 0
        df['geo_cluster'] = cluster_ids

        # Assume we made reasonable clusters.
        reasonable_clusters = True

        region_dicts = []
        for cluster_id in df['geo_cluster'].unique():
            cluster_index = df['geo_cluster'] == cluster_id
            region_dict = {}
            region_dict['id'] = cluster_id
            region_dict['count_points'] = len(df[cluster_index].index)
            region_dict['max_lon'] = df[cluster_index]['longitude'].max()
            region_dict['max_lat'] = df[cluster_index]['latitude'].max()
            region_dict['min_lon'] = df[cluster_index]['longitude'].min()
            region_dict['min_lat'] = df[cluster_index]['latitude'].min()
            # ensure a minimum sized region
            region_dict = make_min_size_region(
                region_dict,
                min_distance=min_cluster_size_km
            )
            region_dict['coordinates'] = geo_utils.make_geojson_coord_box(
                region_dict['min_lon'],
                region_dict['min_lat'],
                region_dict['max_lon'],
                region_dict['max_lat'],
            )
            region_dict['cent_lon'], region_dict['cent_lat'] = (
                geo_utils.get_centroid_of_coord_box(region_dict['coordinates'])
            )
            contains_enough = check_cluster_contains_enough(
                region_dict,
                lone_point_check_uuid=lone_point_check_uuid
            )
            if not contains_enough:
                reasonable_clusters = False
            region_dicts.append(region_dict)

        # Now check if we did in face make reasonable clusters.
        overlapping_regions = check_region_overlaps(region_dicts)
        if len(overlapping_regions):
            reasonable_clusters = False

        # OK done with looping through centroids to check on them.
        if not reasonable_clusters:
            act_cluster_count = act_cluster_count - 1
        if act_cluster_count < 1:
            reasonable_clusters = True
        if cluster_method == 'AffinityPropagation':
            reasonable_clusters = True

    return region_dicts


def make_geo_json_geometry_from_region_dicts(region_dicts):
    """Make a geo_json geometry object from a list of region_dicts

    :param list region_dicts: List of region_dicts generated from
        a clustering method
    """
    if not region_dicts:
        return None
    if len(region_dicts) == 1 and region_dicts[0].get('point'):
        # We have a simple point as the aggregation output.
        geometry = {
            'type': 'Point',
            'coordinates': region_dicts[0].get('coordinates'),
        }
        return geometry
    elif len(region_dicts) == 1:
        geometry = {
            'type': 'Polygon',
            'coordinates': region_dicts[0].get('coordinates'),
        }
        return geometry

    geometry = {
        'type': 'MultiPolygon',
        'coordinates': [r.get('coordinates') for r in region_dicts],
    }
    return geometry


def make_df_from_space_time_qs(
        space_time_qs,
        cols=['longitude', 'latitude'],
        add_item_cols=False
    ):
    """Make a latitude, longitude dataframe a spacetime query string

    :param queryset space_time_qs: The query set of
        space-time instances that we want to cluster

    return DataFrame
    """
    if add_item_cols:
        cols += [
            'item_id',
            'item__label',
            'item__path',
            'item__item_class__slug',
        ]
    space_time_qs = space_time_qs.values(*cols)
    df = pd.DataFrame.from_records(space_time_qs)
    if not set(['longitude', 'latitude']).issubset(set(df.columns)):
        # We're missing the required columns
        return None
    df['longitude'] = df['longitude'].astype(float)
    df['latitude'] = df['latitude'].astype(float)
    if 'item_id' in df.columns:
        df['item_id'] = df['item_id'].astype(str)
    return df


def make_project_space_time_qs(man_obj):
    """Make a project space_time_qs

   :param AllManifest man_obj: The AllManifest object project
        instance for which we will generate aggregate spatial
        regions

    return space_time_qs
    """
    # First check to see if we have geo data for this
    # project
    space_time_qs = AllSpaceTime.objects.filter(
        Q(project=man_obj)
        |Q(item__project=man_obj)
    ).filter(
        latitude__isnull=False,
        longitude__isnull=False
    ).exclude(
        item=man_obj,
    )
    if space_time_qs.count() > 0:
        # The very best and happiest scenario,
        return space_time_qs
    # Do this to look for geo data up a context hierarchy.
    # NOTE: this may mean looking outside the project if context
    # records are associated with another project
    done = False
    subj_uuids = AllManifest.objects.filter(
        item_type='subjects',
        project=man_obj
    ).values_list('uuid', flat=True)
    print(f'Initial subjects count {subj_uuids.count()} for {man_obj.slug}')
    i = 0
    while not done:
        i += 1
        space_time_qs = AllSpaceTime.objects.filter(
            Q(project=man_obj)
            |Q(item__project=man_obj)
            |Q(item_id__in=subj_uuids)
        ).filter(
            latitude__isnull=False,
            longitude__isnull=False
        )
        if space_time_qs.count() > 0:
            done = True
            return space_time_qs
        # Get the parents of the subj_uuids to if they
        # have spatial coordinates.
        count_old_subs = len(subj_uuids)
        subj_uuids = AllManifest.objects.filter(
            item_type='subjects',
            uuid__in=subj_uuids,
        ).distinct('context').order_by('context').values_list(
            'context_id', flat=True
        )
        count_new_subs = len(subj_uuids)
        print(f'No lat/lon for {count_old_subs} project items, looking at {count_new_subs} parent items')
        if i >= 5:
            done = True
    return space_time_qs


def make_table_geo_df(man_obj):
    """Makes a dataframe with geospatial data from a table
    :param AllManifest man_obj: An all manifest instance object
    :param dict act_dict: The acting representation dict for the item

    returns act_dict
    """
    csv_url = man_obj.table_full_csv_url
    if not csv_url:
        return None
    try:
        df = pd.read_csv(csv_url, low_memory=False)
    except:
        df = None
    use_cols = {'Latitude (WGS-84)': 'latitude', 'Longitude (WGS-84)': 'longitude'}
    cols = [orig_c for orig_c, _ in use_cols.items() if orig_c in df.columns]
    if len(cols) < len(use_cols):
        # We're missing the columns we need
        return None
    df = df[cols]
    df.rename(columns=use_cols, inplace=True)
    df['longitude'] = df['longitude'].astype(float)
    df['latitude'] = df['latitude'].astype(float)
    return df


def make_subjects_space_time_qs(man_obj):
    """Makes a space_time_qs for subjects items that has logic to limit by paths
    that are actually children of the man_obj.
    """
    child_man_objs_qs = AllManifest.objects.filter(
        context=man_obj,
        item_type='subjects',
    )
    if child_man_objs_qs.count() < 1:
        return None
    q_term = Q(item__path__startswith=child_man_objs_qs[0].path)
    if child_man_objs_qs.count() > 1:
        for child_man_obj in child_man_objs_qs[1:]:
            q_term |= Q(item__path__startswith=child_man_obj.path)
    space_time_qs = AllSpaceTime.objects.filter(
        q_term
    ).filter(
        geometry__isnull=False,
    ).exclude(
        item=man_obj,
    )
    return space_time_qs


def make_unary_union_polygon_for_contained_geo(man_obj, eps=0.0000001):
    space_time_qs = make_subjects_space_time_qs(man_obj)
    sptime_count = space_time_qs.count()
    if not sptime_count:
        return None, None
    raw_shapes = [shape(sp_obj.geometry) for sp_obj in space_time_qs]
    shapes = []
    for shp in raw_shapes:
        if shp.is_valid:
            shapes.append(shp)
            continue
        shp_2 = shp.buffer(eps)
        if not shp_2.is_valid:
            # We skip it.
            continue
        shapes.append(shp_2)
    raw_boundary = unary_union(shapes)
    boundary = raw_boundary.convex_hull
    boundary = boundary.buffer(eps, 1, join_style=JOIN_STYLE.mitre).buffer(-eps, 1, join_style=JOIN_STYLE.mitre)
    geo_json = to_geojson(boundary)
    geometry = json.loads(geo_json)
    return geometry, sptime_count


def make_geo_json_of_regions_for_man_obj(
    man_obj,
    max_clusters=MAX_CLUSTERS,
    min_cluster_size_km=MIN_CLUSTER_SIZE_KM,
    cluster_method=DEFAULT_CLUSTER_METHOD,
    exclude_outliers=False,
):
    """Make aggregate geospatial regions for an entity

    :param AllManifest man_obj: The AllManifest object instance that
        for which we will generate aggregate spatial regions
    :param int max_clusters: The maximum number of clusters
        to return
    :param float min_cluster_size_km: The minimum diagonal
        length in KM between min(lat/lon) and max(lat/lon)
    :param str cluster_method: A string that names the sklearn
        clustering method to use on these data.
    :param bool exclude_outliers: A boolean value, if true to a
        spatial aggregation that excludes outlier values.
    """
    if man_obj.item_type == 'subjects' and cluster_method == 'unary_union':
        # A somewhat different approach to making a geometry by combining
        # multiple geometries together.
        geometry, sptime_count = make_unary_union_polygon_for_contained_geo(man_obj)
        return geometry, sptime_count
    df = None
    space_time_qs = None
    if man_obj.item_type == 'projects':
        space_time_qs = make_project_space_time_qs(man_obj)
    elif man_obj.item_type == 'subjects':
        space_time_qs = make_subjects_space_time_qs(man_obj)
    elif man_obj.item_type == 'tables':
        df = make_table_geo_df(man_obj)
    elif man_obj.item_type == 'predicates':
        assert_qs = AllAssertion.objects.filter(
            predicate=man_obj,
        ).distinct(
            'subject'
        ).order_by(
            'subject'
        ).values(
            'subject'
        )
        space_time_qs = AllSpaceTime.objects.filter(
           item__in=assert_qs,
        )
    elif man_obj.item_type in [
            'types',
            'media',
            'documents',
            'persons',
        ]:
        assert_qs = AllAssertion.objects.filter(
            object=man_obj,
        ).distinct(
            'subject'
        ).order_by(
            'subject'
        ).values(
            'subject'
        )
        space_time_qs = AllSpaceTime.objects.filter(
           item__in=assert_qs,
        )
    else:
        return None, None

    # Now make a longitude, latitude dataframe.
    if df is None and man_obj.item_type != 'tables':
        df = make_df_from_space_time_qs(space_time_qs)

    if df is None:
        return None, None
    
    if exclude_outliers:
        # we want to exclude outlier values.
        df = geo_quality.remove_outlier_points_in_df_geo(df)

    if df is None or df.empty:
        return None, None
    # Do the fancy math of clustering.
    region_dicts = cluster_geo_centroids(
        df,
        max_clusters=max_clusters,
        min_cluster_size_km=min_cluster_size_km,
        cluster_method=cluster_method,
        lone_point_check_uuid=man_obj.uuid,
    )
    if region_dicts is None:
        return None, None

    # OK Process all of these different regions into a
    # single GeoJSON geometry (Polygon or MultiPolygon)
    geometry = make_geo_json_geometry_from_region_dicts(
        region_dicts
    )
    return geometry, len(df.index)


def add_agg_spacetime_objs(request_list, request=None, source_id=DEFAULT_SOURCE_ID):
    """Add AllSpaceTime and from a client request JSON"""
    errors = []

    if not isinstance(request_list, list):
        errors.append('Request json must be a list of dictionaries to update')
        return [], errors

    add_list = []
    for item_add in request_list:
        man_obj = None
        if item_add.get('item_id'):
            man_obj = AllManifest.objects.filter(
                uuid=item_add.get('item_id')
            ).first()

        if not man_obj:
            errors.append(f'Cannot find manifest object for location/chronology {str(item_add)}')
            continue

        _, ok_edit = permissions.get_request_user_permissions(
            request,
            man_obj,
            null_request_ok=True
        )
        if not ok_edit:
            errors.append(f'Need permission to edit manifest object {man_obj}')
            continue

        max_clusters = item_add.get('max_clusters', MAX_CLUSTERS)
        if isinstance(max_clusters, str):
            max_clusters = validate_transform_data_type_value(
                max_clusters,
                'xsd:integer'
            )
        if not max_clusters:
            errors.append(f'Max clusters must be an integer, not {max_clusters}')
            continue

        min_cluster_size_km = item_add.get('min_cluster_size_km', MIN_CLUSTER_SIZE_KM)
        if isinstance(min_cluster_size_km, str):
            min_cluster_size_km = validate_transform_data_type_value(
                min_cluster_size_km,
                'xsd:double'
            )
        if not min_cluster_size_km:
            errors.append(f'Min cluster size must be a number, not {min_cluster_size_km}')
            continue

        exclude_outliers = item_add.get('exclude_outliers', False)
        if exclude_outliers:
            exclude_outliers = True

        geometry, count_points = make_geo_json_of_regions_for_man_obj(
            man_obj,
            max_clusters=max_clusters,
            min_cluster_size_km=min_cluster_size_km,
            cluster_method=item_add.get('cluster_method', DEFAULT_CLUSTER_METHOD),
            exclude_outliers=exclude_outliers,
        )
        if geometry is None:
            errors.append(f'Could not make aggregate geometry for manifest object {man_obj}')
            continue

        item_add['geometry_type'] = geometry.get('type')
        item_add['geometry'] = geometry
        item_add['meta_json'] = {
            'function': 'geo_agg.make_geo_json_of_regions_for_man_obj',
            'max_clusters': max_clusters,
            'min_cluster_size_km': min_cluster_size_km,
            'cluster_method': item_add.get('cluster_method', DEFAULT_CLUSTER_METHOD),
            'count_points': count_points,
        }
        add_list.append(item_add)

    # Now add all of these results to the database!
    added, new_errors = updater_spacetime.add_spacetime_objs(
        add_list,
        request=None,
        source_id=source_id,
    )
    return added, (errors + new_errors)