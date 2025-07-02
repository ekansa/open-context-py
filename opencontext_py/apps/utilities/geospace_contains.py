
import json
from shapely.geometry import shape
from shapely import contains_xy, contains, Point

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
)

from opencontext_py.apps.all_items.editorial import api as editorial_api
from opencontext_py.apps.all_items.geospace import aggregate as geo_agg
from opencontext_py.apps.all_items.geospace import geo_quality



def check_lat_lon_within_item_geometries(
    latitude,
    longitude,
    item_id=None,
    item_obj=None,
):
    if not item_obj and not item_id:
        raise ValueError('Must provide an item_obj or an item_id')
    if not item_obj:
        item_obj = AllManifest.objects.get(uuid=item_id)
    latitude = float(latitude)
    longitude = float(longitude)
    item_sp_qs = AllSpaceTime.objects.filter(
        item=item_obj,
        geometry_type__in=['Polygon', 'MultiPolygon',]
    ).exclude(
        latitude__isnull=True,
    ).exclude(
        longitude__isnull=True,
    )
    report_dict = {
        'big_item_uuid': str(item_obj.uuid),
        'big_item_label': item_obj.label,
        'big_item_path': item_obj.path,
        'big_item_geonames_id': item_obj.meta_json.get('geonames_id'),
        'big_item_pleiades_id': item_obj.meta_json.get('pleiades_id'),
        'big_item_wikidata_id': item_obj.meta_json.get('wikidata_id'),
        'latitude': latitude,
        'longitude': longitude,
        'contains': [],
        'not_contains': [],
    }
    for sp_obj in item_sp_qs:
        area = shape(sp_obj.geometry)
        is_contained = contains_xy(area, x=longitude, y=latitude)
        area_dict = {
            'big_sp_uuid': str(sp_obj.uuid),
            'big_geometry_type': sp_obj.geometry_type,
        }
        if is_contained:
            report_dict['contains'].append(area_dict)
        else:
            report_dict['not_contains'].append(area_dict)
    report_dict['all_contains'] = len(report_dict['not_contains']) == 0
    return report_dict


def check_item_geometries_within_other_item_geometries(
    small_item_id,
    big_item_id,
    centroid=False,
):
    errors = []
    small_item_obj = AllManifest.objects.filter(uuid=small_item_id).first()
    if not small_item_obj:
        errors.append(f'Cannot find small_item_id: {small_item_id}')
    if big_item_id:
        big_item_obj = AllManifest.objects.filter(uuid=big_item_id).first()
    else:
        big_item_obj = small_item_obj.context
    if not big_item_obj:
        errors.append(f'Cannot find big_item_id: {big_item_id}')
    if errors:
        # skip out, we have errors
        return {'errors': errors,}
    small_sp_qs = AllSpaceTime.objects.filter(
        item=small_item_obj,
    ).exclude(
        latitude__isnull=True,
    ).exclude(
        longitude__isnull=True,
    ).exclude(
        geometry_type__isnull=True,
    )
    if not small_sp_qs.count():
        errors.append(f'Cannot find {small_item_obj.label} ({small_item_obj.uuid}) geometries')
    big_sp_qs = AllSpaceTime.objects.filter(
        item=big_item_obj,
        geometry_type__in=['Polygon', 'MultiPolygon',]
    ).exclude(
        latitude__isnull=True,
    ).exclude(
        longitude__isnull=True,
    )
    if not big_sp_qs.count():
        errors.append(f'Cannot find {big_item_obj.label} ({big_item_obj.uuid}) geometries')
    if errors:
        # skip out, we have errors
        return {'errors': errors,}
    report_dict = {
        'big_item_uuid': str(big_item_obj.uuid),
        'big_item_label': big_item_obj.label,
        'big_item_path': big_item_obj.path,
        'big_item_geonames_id': big_item_obj.meta_json.get('geonames_id'),
        'big_item_pleiades_id': big_item_obj.meta_json.get('pleiades_id'),
        'big_item_wikidata_id': big_item_obj.meta_json.get('wikidata_id'),
        'small_item_uuid': str(small_item_obj.uuid),
        'small_item_label': small_item_obj.label,
        'small_item_path': small_item_obj.path,
        'small_item_geonames_id': small_item_obj.meta_json.get('geonames_id'),
        'small_item_pleiades_id': small_item_obj.meta_json.get('pleiades_id'),
        'small_item_wikidata_id': small_item_obj.meta_json.get('wikidata_id'),
        'centroid_only': centroid,
        'contains': [],
        'not_contains': [],
    }
    for small_sp_obj in small_sp_qs:
        if centroid:
            small_geom = Point(
                (float(small_sp_obj.longitude), float(small_sp_obj.latitude))
            )
        else:
            small_geom = shape(small_sp_obj.geometry)
        for big_sp_obj in big_sp_qs:
            big_geom = shape(big_sp_obj.geometry)
            area_dict = {
                'big_sp_uuid': str(big_sp_obj.uuid),
                'big_geometry_type': big_sp_obj.geometry_type,
                'small_sp_uuid': str(small_sp_obj.uuid),
                'small_geometry_type': small_sp_obj.geometry_type,
            }
            is_contained = contains(big_geom, small_geom)
            if is_contained:
                report_dict['contains'].append(area_dict)
            else:
                report_dict['not_contains'].append(area_dict)
    report_dict['all_contains'] = len(report_dict['not_contains']) == 0
    return report_dict


def report_child_coordinate_outliers(item_id=None, path=None):
    """Reports outlier coordinates for children of a given item"""
    if item_id:
        parent_man_obj = AllManifest.objects.filter(uuid=item_id).first()
    if path:
        parent_man_obj = AllManifest.objects.filter(path=path).first()
    if not parent_man_obj:
        return None
    space_time_qs = geo_agg.make_subjects_space_time_qs(parent_man_obj)
    df_geo = geo_agg.make_df_from_space_time_qs(space_time_qs, add_item_cols=True)
    df = geo_quality.flag_outlier_points_in_df(df_geo)
    if df is None or df.empty:
        return None
    flag_index = (
        (df['flag__longitude'] == True)
        | (df['flag__latitude'] == True)
    )
    df_flag = df[flag_index].copy()
    df_flag['uri'] = ''
    for i, row in df_flag.iterrows():
        bad_obj = AllManifest.objects.get(uuid=row['item_id'])
        df_flag.at[i, 'uri'] = f'https://{bad_obj.uri}'
    bad_json = df_flag.to_json(orient='records')
    bad_list = json.loads(bad_json)
    output = editorial_api.manifest_obj_to_json_safe_dict(
        parent_man_obj ,
        do_minimal=True,
    )
    output['uri'] = 'https://' + output.get('uri')
    output['child_geo_outliers'] = bad_list
    return output