
import json
import numpy as np
import re
from scipy.spatial.distance import cosine

import warnings

from django.db.models import Max, Min
from django.db.models import OuterRef, Subquery

from opencontext_py.apps.indexer.embeddings import (
    embed_with_chunk_pooling
)

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    ManifestCachedSpacetime,
)

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items import hierarchy


def get_world_regions_two_levels_deep_qs():
    # Returns main country regions
    m_qs = AllManifest.objects.filter(
        item_type='subjects',
        item_class_id=configs.CLASS_OC_REGION_UUID,
        context__in=configs.LIST_SUBJECTS_WORLD_REGIONS_UUIDS
    )
    return m_qs


def get_distinct_project_item_type_item_classes():
    """Gets projects, their short descriptions, and
    unique item types and item classes
    """
    proj_short_qs = AllAssertion.objects.filter(
        subject=OuterRef('project'),
        predicate_id=configs.PREDICATE_DCTERMS_DESCRIPTION_UUID,
        visible=True,
    ).order_by().values('obj_string')[:1]

    m_qs = AllManifest.objects.filter(
        item_type__in=['subjects', 'media', 'documents',],
        meta_json__flag_do_not_index__isnull=True,
        project__meta_json__flag_do_not_index__isnull=True,
    ).distinct(
        'item_type',
        'item_class',
        'project',
    ).order_by(
        'item_type',
        'item_class',
        'project',
    ).select_related(
        'project'
    ).select_related(
        'item_class'
    ).exclude(
        project_id=configs.OPEN_CONTEXT_PROJ_UUID,
    ).annotate(
        proj_short_desc=Subquery(proj_short_qs)
    ).values(
        'item_type',
        'item_class_id',
        'item_class__label',
        'item_class__slug',
        'project__slug',
        'proj_short_desc',
    )
    return m_qs


def get_project_space_time(
    project_slug,
    item_type=None,
    item_class_id=None,
):
    proj_qs = ManifestCachedSpacetime.objects.filter(
        item__project__slug=project_slug,
    ).exclude(
        latitude=0,
        longitude=0,
    ).exclude(
        latitude=None,
        longitude=None,
    ).exclude(
        earliest=None,
        latest=None,
    )
    if item_type:
        proj_qs = proj_qs.filter(item__item_type=item_type)
    if item_class_id:
        proj_qs = proj_qs.filter(item__item_class_id=item_class_id)
    raw_dict = proj_qs.aggregate(
        Min('latitude'),
        Min('longitude'),
        Max('latitude'),
        Max('longitude'),
        Min('earliest'),
        Max('latest'),
    )
    output = {}
    for k, v in raw_dict.items():
        value = None
        try:
            value = float(v)
        except:
            value = None
        output[k] = value
    return output



def get_general_project_space_time(project_slug, proj_dict):
    if project_slug in proj_dict:
        return proj_dict.get(project_slug), proj_dict
    sp_time = get_project_space_time(
        project_slug=project_slug,
    )
    proj_dict[project_slug] = sp_time
    return sp_time, proj_dict


def get_distinct_project_item_type_item_classes_with_geo_chrono():
    """Gets projects, their short descriptions, and
    unique item types and item classes
    """
    m_qs = get_distinct_project_item_type_item_classes()
    proj_dict = {}
    output = []
    for m_dict in m_qs:
        if m_dict.get('item_type') == 'subjects':
            sp_time = get_project_space_time(
                project_slug=m_dict.get('project__slug'),
                item_type=m_dict.get('item_type'),
                item_class_id=m_dict.get('item_class_id'),
            )
        else:
            sp_time, proj_dict = get_general_project_space_time(
                project_slug=m_dict.get('project__slug'), 
                proj_dict=proj_dict,
            )
        if sp_time:
            for k, v in sp_time.items():
                m_dict[k] = v
        output.append(m_dict)
    return output    


def generate_bbox_from_m_dict(m_dict):
    """Makes a bounding box query value for an m_dict"""
    sw_keys = [
        'min__latitude',
        'min__longitude',
    ]
    ne_keys = [
        'max__latitude',
        'max__longitude',
    ]
    for k in (sw_keys + ne_keys):
        if not k.get(m_dict):
            return None
    lat_diff_factor = abs(m_dict['max__latitude'] - m_dict['min__latitude']) * 0.075
    lon_diff_factor = abs(m_dict['max__longitude'] - m_dict['min__longitude']) * 0.075
    sw_lat = round(
        (m_dict['min__latitude'] - lat_diff_factor), 4
    )
    sw_lon = round(
        (m_dict['min__longitude'] - lon_diff_factor), 4
    )
    ne_lat = round(
        (m_dict['max__latitude'] + lat_diff_factor), 4
    )
    ne_lon = round(
        (m_dict['max__longitude'] + lon_diff_factor), 4
    )
    return f'{sw_lon},{sw_lat},{ne_lon},{ne_lat}'
        
