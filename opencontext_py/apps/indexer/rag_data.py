import duckdb
from duckdb.typing import *

import os
import json
import numpy as np
import pandas as pd
import re

from django.db.models import Max, Min
from django.db.models import OuterRef, Subquery


from django.conf import settings

from opencontext_py.libs import duckdb_con

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    ManifestCachedSpacetime,
)

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.legacy_all import update_old_id

from opencontext_py.apps.indexer.solrdocument_slim_schema import (
    EMBEDDING_FIELD_SOLR,
)
from opencontext_py.apps.indexer.embedding_configs import (
    ITEM_TYPE_RAG_EXPLAIN_DICT,
    CLASS_RAG_EXPLAIN_DICT,
)
from opencontext_py.apps.indexer.embeddings import (
    EMBEDDING_MODEL_DIM,
    chunk_text_for_embedding,
    embed_with_chunk_pooling
)

EXPLAINED_SEARCHES_LOCAL_PATH = os.path.join(
    settings.FILE_CACHE_PATH,
    'explained-searches.parquet', 
)

DC_META_PREDICATE_UUIDS = [
    configs.PREDICATE_DCTERMS_SUBJECT_UUID,
    configs.PREDICATE_DCTERMS_COVERAGE_UUID,
    configs.PREDICATE_DCTERMS_SPATIAL_UUID,
    configs.PREDICATE_DCTERMS_TEMPORAL_UUID,
]

DF_COLS_TO_DUCKDB_DATA_TYPES = {
    'item_type': 'VARCHAR',
    'item_class_id': 'UUID',
    'item_class__label': 'VARCHAR',
    'item_class__slug': 'VARCHAR',
    'project__slug': 'VARCHAR',
    'proj_short_desc': 'VARCHAR',
    'uuid': 'UUID',
    'item_type_class_count': 'BIGINT',
    'item_type_class_asserts_count': 'BIGINT',
    'item_type_class_asserts_rate': 'FLOAT',
    'bbox': 'VARCHAR',
    'path': 'VARCHAR',
    'metadata': 'VARCHAR',
    'latitude__min': 'FLOAT', 
    'longitude__min': 'FLOAT',
    'latitude__max': 'FLOAT',
    'longitude__max': 'FLOAT',
    'earliest__min': 'FLOAT',
    'latest__max': 'FLOAT',
    'explain_text': 'VARCHAR',
    'chunck_count': 'INTEGER',
    EMBEDDING_FIELD_SOLR: f'FLOAT[{EMBEDDING_MODEL_DIM}]',
}


def get_world_regions_two_levels_deep_qs():
    # Returns main country regions
    m_qs = AllManifest.objects.filter(
        item_type='subjects',
        item_class_id=configs.CLASS_OC_REGION_UUID,
        context__in=configs.LIST_SUBJECTS_WORLD_REGIONS_UUIDS
    )
    return m_qs


def get_world_regions_two_levels_deep_path_list():
    # Returns main country regions
    m_qs = get_world_regions_two_levels_deep_qs()
    world_path_list = [m.path for m in m_qs]
    return world_path_list


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
        'project__meta_json',
        'proj_short_desc',
    )
    return m_qs


def get_proj_item_type_class_count(project_slug, item_type, item_class_id):
    """Get count of the number of records for project's item_type and class"""
    return AllManifest.objects.filter(
        project__slug=project_slug,
        item_type=item_type,
        item_class=item_class_id
    ).order_by('?').count()


def get_proj_item_type_class_asserts_count(project_slug, item_type, item_class_id):
    return AllAssertion.objects.filter(
        subject__project__slug=project_slug,
        subject__item_type=item_type,
        subject__item_class=item_class_id,
        predicate__item_class=configs.CLASS_OC_VARIABLES_UUID,
    ).order_by('?').count()


def get_proj_dc_metadata_db(project_slug):
    a_qs = AllAssertion.objects.filter(
        subject__slug=project_slug,
        predicate_id__in=DC_META_PREDICATE_UUIDS,
    ).select_related(
        'object'
    )
    meta_list = [aa.object.label for aa in a_qs]
    return meta_list


def get_project_path_db(project_slug, world_path_list):
    proj_paths = []
    for world_path in world_path_list:
        m_obj = AllManifest.objects.filter(
            project__slug=project_slug,
            item_type='subjects',
            path__startswith=world_path
        ).first()
        if not m_obj:
            continue
        proj_paths.append(world_path)
        if len(proj_paths) > 1:
            return None
    if len(proj_paths) == 1:
        return proj_paths[0]
    # we only care if there's only 1 world path to
    # relevant to a project
    return None



def get_project_metadata_list(project_slug, proj_slug_metadata):
    meta_list = proj_slug_metadata.get(project_slug)
    if isinstance(meta_list, list):
        return meta_list, proj_slug_metadata
    meta_list = get_proj_dc_metadata_db(project_slug)
    proj_slug_metadata[project_slug] = meta_list
    return meta_list, proj_slug_metadata



def get_project_path(project_slug, proj_slug_paths, world_path_list):
    path = proj_slug_paths.get(project_slug)
    if path is not None and path != '':
        return path, proj_slug_paths
    if path is not None and path == '':
        return None, proj_slug_paths
    path = get_project_path_db(project_slug, world_path_list)
    if path:
        proj_slug_paths[project_slug] = path
    else:
        proj_slug_paths[project_slug] = ''
    return proj_slug_paths[project_slug], proj_slug_paths


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


def generate_bbox_from_m_dict(m_dict):
    """Makes a bounding box query value for an m_dict"""
    sw_keys = [
        'latitude__min',
        'longitude__min',
    ]
    ne_keys = [
        'latitude__max',
        'longitude__max',
    ]
    for k in (sw_keys + ne_keys):
        if not m_dict.get(k):
            return None
    lat_diff_factor = abs(m_dict['latitude__max'] - m_dict['latitude__min']) * 0.075
    if lat_diff_factor < 0.075:
        lat_diff_factor = 0.075
    lon_diff_factor = abs(m_dict['longitude__max'] - m_dict['longitude__min']) * 0.075
    if lon_diff_factor < 0.075:
        lon_diff_factor = 0.075
    sw_lat = round(
        (m_dict['latitude__min'] - lat_diff_factor), 4
    )
    sw_lon = round(
        (m_dict['longitude__min'] - lon_diff_factor), 4
    )
    ne_lat = round(
        (m_dict['latitude__max'] + lat_diff_factor), 4
    )
    ne_lon = round(
        (m_dict['longitude__max'] + lon_diff_factor), 4
    )
    return f'{sw_lon},{sw_lat},{ne_lon},{ne_lat}'


def explain_text_clean(txt):
    txt = txt.replace('\n', ' ')
    txt = txt.replace('\t', ' ')
    txt = txt.replace('  ', ' ')
    txt = txt.strip()
    if not txt.endswith('.'):
        txt += '.'
    return txt

def make_explain_text(m_dict):
    explain_item_class = CLASS_RAG_EXPLAIN_DICT.get(
        m_dict.get('item_class__label'),
        ITEM_TYPE_RAG_EXPLAIN_DICT.get(
            m_dict.get('item_type')
        )
    )
    explain_item_class = explain_item_class.replace('     ', ' ')
    explain_item_class = explain_text_clean(explain_item_class)
    places = ''
    if m_dict.get('path'):
        path = m_dict.get('path')
        places = 'Relevant places: ' + path.replace('/', ', ')
        places = explain_text_clean(places)
    project_desc = ''
    if m_dict.get('proj_short_desc'):
        project_desc = 'Project description: ' + m_dict.get('proj_short_desc')
        project_desc = explain_text_clean(project_desc)
    metadata = ''
    if m_dict.get('metadata'):     
        metadata = 'General topics: ' +  m_dict.get('metadata')
        metadata = explain_text_clean(metadata)
    all_text = [
        explain_item_class,
        places,
        project_desc,
        metadata,
    ]
    make_explain_text = ' '.join(
        [txt for txt in all_text if txt != '']
    )
    return make_explain_text


def get_distinct_project_item_type_item_classes_with_geo_chrono():
    """Gets projects, their short descriptions, and
    unique item types and item classes
    """
    world_path_list = get_world_regions_two_levels_deep_path_list()
    m_qs = get_distinct_project_item_type_item_classes()
    proj_dict = {}
    proj_slug_paths = {}
    proj_slug_metadata = {}
    output = []
    for m_dict in m_qs:
        proj_slug = m_dict.get('project__slug')
        id_str = f"{proj_slug}-{m_dict.get('item_type')}-{m_dict.get('item_class_id')}"
        _, uuid = update_old_id(id_str)
        m_dict['uuid'] = uuid 
        m_dict['item_type_class_count'] = get_proj_item_type_class_count(
            project_slug=proj_slug,
            item_type=m_dict.get('item_type'),
            item_class_id=m_dict.get('item_class_id'),
        )
        m_dict['item_type_class_asserts_count'] = get_proj_item_type_class_asserts_count(project_slug=proj_slug,
            item_type=m_dict.get('item_type'),
            item_class_id=m_dict.get('item_class_id'),
        )
        m_dict['item_type_class_asserts_rate'] = (
            m_dict['item_type_class_asserts_count'] / m_dict['item_type_class_count'] 
        )
        m_dict['bbox'] = None
        # Add a path for the project
        m_dict['path'] = m_dict.get('project__meta_json', {}).get('query_context_path')
        m_dict.pop('project__meta_json')
        meta_list, proj_slug_metadata = get_project_metadata_list(
            project_slug=proj_slug, 
            proj_slug_metadata=proj_slug_metadata
        )
        m_dict['metadata'] = '; '.join(meta_list)
        if not m_dict.get('path'):
            path, proj_slug_paths = get_project_path(proj_slug, proj_slug_paths, world_path_list)
            m_dict['path'] = path
        if m_dict.get('item_type') == 'subjects':
            sp_time = get_project_space_time(
                project_slug=proj_slug,
                item_type=m_dict.get('item_type'),
                item_class_id=m_dict.get('item_class_id'),
            )
        else:
            sp_time, proj_dict = get_general_project_space_time(
                project_slug=proj_slug, 
                proj_dict=proj_dict,
            )
        if sp_time:
            for k, v in sp_time.items():
                m_dict[k] = v
            # Make a bounding box for the space time values
            m_dict['bbox'] = generate_bbox_from_m_dict(m_dict)
        # Make the explanation text for this query, this will be used
        # to make embeddings to match with an embedding from a user query
        m_dict['explain_text'] = make_explain_text(m_dict)
        chunks = chunk_text_for_embedding(m_dict['explain_text'])
        m_dict['chunck_count'] = len(chunks)
        if len(chunks) > 1:
            print("Long text for embedding: " + str(m_dict['explain_text']))
        m_dict[EMBEDDING_FIELD_SOLR] = embed_with_chunk_pooling(m_dict['explain_text'])
        output.append(m_dict)
    return output    


def make_explained_searches_df():
    print('Start to generate search explanations')
    data = get_distinct_project_item_type_item_classes_with_geo_chrono()
    df = pd.DataFrame(data=data)
    print(f'Generated search explanations: {len(df.index)}')
    return df

        
def make_explained_searches_parquet_from_df(df):
    # Make an in-memory table via duckdb
    con = duckdb.connect(database=':memory:')
    con.execute("DROP TABLE IF EXISTS explained_searches")

    create_cols_data_types = []
    insert_cols_data_types = []
    for col in df.columns.tolist():
        data_type = DF_COLS_TO_DUCKDB_DATA_TYPES.get(col, 'VARCHAR')
        create_col_datatype = f'{col} {data_type}'
        create_cols_data_types.append(create_col_datatype)
        insert_cols_data_type = f'{col}::{data_type} AS {col}'
        insert_cols_data_types.append(insert_cols_data_type)
    
    create_cols_data_types_sql = ', \n'.join(create_cols_data_types)
    insert_cols_data_types = ', \n'.join(insert_cols_data_types)

    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS explained_searches (
            {create_cols_data_types_sql}
        );
        """
    )

    con.execute(
        f"""
        INSERT INTO explained_searches 
        SELECT 
            {insert_cols_data_types}
        FROM df;
        """
    )
    con.execute(f"COPY (SELECT * FROM explained_searches) TO '{EXPLAINED_SEARCHES_LOCAL_PATH}' ")
    print(f'Saved explained searches to: {EXPLAINED_SEARCHES_LOCAL_PATH}')
    return df