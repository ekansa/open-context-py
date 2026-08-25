import duckdb
from duckdb.sqltypes import *

import copy
import os
import json
import numpy as np
import pandas as pd
import re

from django.db.models import Max, Min
from django.db.models import OuterRef, Subquery, Q


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

"""
from opencontext_py.apps.indexer.explained_topic_data import (
    make_explained_searches_df,
    make_explained_searches_parquet_from_df,
    start_explained_searches_df,
    augment_explained_searches_vocabularies,
    EXPLAINED_SEARCHES_PREP_PATH,
    add_explain_texts_and_embeddings_to_df
)

df = start_explained_searches_df()
df = augment_explained_searches_vocabularies(df)
df.to_csv(EXPLAINED_SEARCHES_PREP_PATH, index=False)
df = add_explain_texts_and_embeddings_to_df(df)
df = make_explained_searches_parquet_from_df(df)

df = make_explained_searches_df()
df = make_explained_searches_parquet_from_df(df)

"""

EXPLAINED_SEARCHES_PREP_PATH = os.path.join(
    settings.FILE_CACHE_PATH,
    'explained-searches-prep.csv', 
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

SKIP_VOCABULARY_UUIDS = [
    "00000000-5b81-e1ff-eb39-8d5224e02cec", # eol.org
    "00000000-fea3-7dfb-e94f-396fe724f56b", # british museum
]


DF_GENERAL_COLS_TO_DUCKDB_DATA_TYPES = {
    'item_type': 'VARCHAR',
    'item_class_id': 'UUID',
    'item_class__label': 'VARCHAR',
    'item_class__slug': 'VARCHAR',
    'project__label': 'VARCHAR',
    'project__slug': 'VARCHAR',
    'uuid': 'UUID',
    'proj_short_desc': 'VARCHAR',
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
}

DF_COLS_PROPERTY_DUCKDB_DATA_TYPES = {
    'predicate_id': 'UUID',
    'predicate__label': 'VARCHAR',
    'predicate__slug': 'VARCHAR',
    'object_id': 'UUID',
    'object__label': 'VARCHAR',
    'object__context_id':  'UUID',
    'object__slug': 'VARCHAR',
    'equiv_predicate_slug': 'VARCHAR',
    'equiv_predicate_label': 'VARCHAR',
    'equiv_object_slug': 'VARCHAR',
    'equiv_object_label': 'VARCHAR',
    'equiv_object_alt_labels': 'VARCHAR',
}

DF_EMBEDDING_COLS_TO_DUCKDB_DATA_TYPES = {
    'explain_text': 'VARCHAR',
    'explain_text_html': 'VARCHAR',
    'chunck_count': 'INTEGER',
    EMBEDDING_FIELD_SOLR: f'FLOAT[{EMBEDDING_MODEL_DIM}]',
}

DF_COLS_ALL_TO_DUCKDB_DATA_TYPES = (
    DF_GENERAL_COLS_TO_DUCKDB_DATA_TYPES
    | DF_COLS_PROPERTY_DUCKDB_DATA_TYPES
    | DF_EMBEDDING_COLS_TO_DUCKDB_DATA_TYPES
)


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
    m_qs = AllManifest.objects.filter(
        item_type__in=['subjects', 'media', 'documents',],
        # meta_json__flag_do_not_index__isnull=True,
        # project__meta_json__flag_do_not_index__isnull=True,
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
    ).values(
        'item_type',
        'item_class_id',
        'item_class__label',
        'item_class__slug',
        'project__label',
        'project__slug',
        'meta_json',
        'project__meta_json',
    )
    return m_qs


def get_proj_short_description_db(project_slug):
    proj_short_obj = AllAssertion.objects.filter(
        subject__slug=project_slug,
        predicate_id=configs.PREDICATE_DCTERMS_DESCRIPTION_UUID,
        visible=True,
    ).first()
    if not proj_short_obj:
        return None
    return proj_short_obj.obj_string


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



def get_project_short_desc(project_slug, proj_slug_short_desc):
    if project_slug in proj_slug_short_desc:
        return proj_slug_short_desc.get(project_slug), proj_slug_short_desc
    short_desc = get_proj_short_description_db(
        project_slug=project_slug,
    )
    if not short_desc:
        short_desc = ''
    proj_slug_short_desc[project_slug] = short_desc
    return short_desc, proj_slug_short_desc


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


def get_distinct_project_item_type_item_classes_with_geo_chrono():
    """Gets projects, their short descriptions, and
    unique item types and item classes
    """
    world_path_list = get_world_regions_two_levels_deep_path_list()
    m_qs = get_distinct_project_item_type_item_classes()
    proj_dict = {}
    proj_slug_short_desc = {}
    proj_slug_paths = {}
    proj_slug_metadata = {}
    output = []
    for m_dict in m_qs:
        if m_dict['meta_json'].get('flag_do_not_index'):
            continue
        if m_dict['project__meta_json'].get('flag_do_not_index'):
            continue
        m_dict.pop('meta_json')
        proj_slug = m_dict.get('project__slug')
        id_str = f"{proj_slug}-{m_dict.get('item_type')}-{m_dict.get('item_class_id')}"
        _, uuid = update_old_id(id_str)
        m_dict['uuid'] = uuid
        short_desc, proj_slug_short_desc = get_project_short_desc(proj_slug, proj_slug_short_desc)
        m_dict['proj_short_desc'] = short_desc
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
        output.append(m_dict)
    return output    


def get_distinct_project_item_class_types(
    project_slug, 
    item_type, 
    item_class_id=None,
    item_class_slug=None,        
):
    equiv_pred_qs = AllAssertion.objects.filter(
        subject=OuterRef('predicate'),
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        visible=1,
        object__item_type='property',
    ).select_related(
        'object'
    ).values(
        'object__slug'
    )[:1]

    equiv_pred_label_qs = AllAssertion.objects.filter(
        subject=OuterRef('predicate'),
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        visible=1,
        object__item_type='property',
    ).select_related(
        'object'
    ).values(
        'object__label'
    )[:1]
    
    equiv_type_qs = AllAssertion.objects.filter(
        subject=OuterRef('object'),
        predicate_id__in=(configs.PREDICATE_LIST_SBJ_EQUIV_OBJ + [configs.PREDICATE_DCTERMS_REFERENCES_UUID]),
        visible=1,
        object__item_type__in=['class', 'uri',],
    ).exclude(
        object__context_id__in=SKIP_VOCABULARY_UUIDS,
    ).select_related(
        'object'
    ).values(
        'object__slug'
    )[:1]

    equiv_type_label_qs = AllAssertion.objects.filter(
        subject=OuterRef('object'),
        predicate_id__in=(configs.PREDICATE_LIST_SBJ_EQUIV_OBJ + [configs.PREDICATE_DCTERMS_REFERENCES_UUID]),
        object__item_type__in=['class', 'uri',],
        visible=1,
    ).exclude(
        object__context_id__in=SKIP_VOCABULARY_UUIDS,
    ).select_related(
        'object'
    ).values(
        'object__label'
    )[:1]

    a_qs = AllAssertion.objects.filter(
        subject__project__slug=project_slug,
        subject__item_type=item_type,
        object__item_type__in=['types', 'class', 'uri',],
        visible=1,
    )
    if item_class_id:
        a_qs = a_qs.filter(
            subject__item_class_id=item_class_id,
        )
    if item_class_slug:
        a_qs = a_qs.filter(
            subject__item_class__slug=item_class_slug,
        )
    
    a_qs = a_qs.distinct(
        'predicate',
        'object',
    ).order_by(
        'predicate',
        'object',
    ).select_related(
        'predicate',
    ).select_related(
        'object',
    ).annotate(
        equiv_predicate_slug=Subquery(equiv_pred_qs)
    ).annotate(
        equiv_predicate_label=Subquery(equiv_pred_label_qs)
    ).annotate(
        equiv_object_slug=Subquery(equiv_type_qs)
    ).annotate(
        equiv_object_label=Subquery(equiv_type_label_qs)
    ).filter(
        Q(equiv_predicate_slug__isnull=False)
        |Q(predicate__item_type__in=['property']),
    ).filter(
        Q(equiv_object_slug__isnull=False)
        |Q(object__item_type__in=['class', 'uri',]),
    ).values(
        'predicate_id',
        'predicate__label',
        'predicate__slug',
        'predicate__item_type',
        'object_id',
        'object__item_type',
        'object__label',
        'object__context_id',
        'object__slug',
        'equiv_predicate_slug',
        'equiv_predicate_label',
        'equiv_object_slug',
        'equiv_object_label',
    )
    return a_qs

def get_entity_alt_labels(slug):
    """Gets the alternative label for an entity"""
    a_qs = AllAssertion.objects.filter(
        subject__slug=slug,
        predicate_id=configs.PREDICATE_SKOS_ALTLABEL_UUID,
        visible=1,
    ).select_related(
        'subject'
    )
    alt_labels = []
    for a_obj in a_qs:
        if a_obj.obj_string == a_obj.subject.label:
            continue
        if a_obj.obj_string in alt_labels:
            continue
        alt_labels.append(a_obj.obj_string)
    return alt_labels


def augment_explained_searches_vocabularies(df):
    """Adds important vocabularies to item_classes for richer embeddings"""
    print(f'Before extending for vocabularies, df length: {len(df.index)}')
    vocab_dfs = []
    act_index = (
        ~df['project__slug'].isnull()
        & ~df['item_type'].isnull()
        & ~df['item_class_id'].isnull()
    )
    for _, class_row in df[act_index].iterrows():
        prop_qs = get_distinct_project_item_class_types(
            project_slug=class_row['project__slug'], 
            item_type=class_row['item_type'], 
            item_class_id=class_row['item_class_id'], 
        )
        if prop_qs.count() == 0:
            continue
        new_rows = []
        for prop_dict in prop_qs:
            # Do this to handle properties, classes, and uris directly linked to 
            # items
            if prop_dict.get('predicate__item_type') != 'predicates':
                prop_dict['equiv_predicate_label'] = prop_dict.get('predicate__label')
                prop_dict['equiv_predicate_slug'] = prop_dict.get('predicate__slug')
            if prop_dict.get('object__item_type') != 'types':
                prop_dict['equiv_object_label'] = prop_dict.get('object__label')
                prop_dict['equiv_object_slug'] = prop_dict.get('object__slug')
            new_row = class_row.copy()
            for k, v in prop_dict.items():
                if k in ['predicate__item_type', 'object__item_type']:
                    continue
                new_row[k] = v
            id_parts = [
                new_row.get('project__slug'),
                new_row.get('item_type'),
                str(new_row.get('item_class_id')),
                str(new_row.get('predicate_id')),
                str(new_row.get('object_id')),
                new_row.get('equiv_object_slug'),
            ]    
            id_str = '-'.join(id_parts)
            _, uuid = update_old_id(id_str)
            new_row['uuid'] = uuid
            new_rows.append(new_row)
        new_df = pd.DataFrame(data=new_rows)
        vocab_dfs.append(new_df)
    old_df = df.copy()
    df = pd.concat(([old_df] + vocab_dfs), ignore_index=True)
    df.drop_duplicates(subset=['uuid'], inplace=True)
    df['equiv_object_alt_labels'] = ''
    equiv_obj_slug_index = ~df['equiv_object_slug'].isnull()
    for obj_slug in df[equiv_obj_slug_index]['equiv_object_slug'].unique().tolist():
        alt_labels = get_entity_alt_labels(obj_slug)
        if not alt_labels:
            continue
        act_index = df['equiv_object_slug'] == obj_slug
        df.loc[act_index, 'equiv_object_alt_labels'] = ', '.join(alt_labels)
    print(f'After extending for vocabularies, df length: {len(df.index)}')
    return df


def explain_text_clean(txt):
    txt = txt.replace('\n', ' ')
    txt = txt.replace('\t', ' ')
    txt = " ".join(txt.split())
    txt = txt.strip()
    if not txt.endswith('.'):
        txt += '.'
    return txt


def has_key_str_value(m_dict, key):
    if not m_dict.get(key):
        return False
    if str(m_dict.get(key)).lower() in ['nan', 'none']:
        return False
    return True


def make_explain_text(m_dict):
    explain_item_class = CLASS_RAG_EXPLAIN_DICT.get(
        m_dict.get('item_class__label'),
        ITEM_TYPE_RAG_EXPLAIN_DICT.get(
            m_dict.get('item_type')
        )
    )
    explain_item_class = explain_text_clean(explain_item_class)
    explain_item_class = f'<p>{explain_item_class}</p>'
    places = ''
    if has_key_str_value(m_dict, 'path'):
        path = m_dict.get('path')
        places = '<br/><b>Relevant Places:</b> in ' + path.replace('/', ', in ')
        places = explain_text_clean(places)
    specific_desc = ''
    if (has_key_str_value(m_dict, 'predicate__label')
        and has_key_str_value(m_dict, 'object__label')
        and has_key_str_value(m_dict, 'equiv_predicate_label')
        and has_key_str_value(m_dict, 'equiv_object_label')
        and has_key_str_value(m_dict, 'predicate__label')
    ):
        specific_desc = f"<br/><b>Specific Topics:</b> {m_dict.get('equiv_predicate_label')}; {m_dict.get('object__label')}"
        if m_dict.get('object__label') != m_dict.get('equiv_object_label'):
            specific_desc += f" and {m_dict.get('equiv_object_label')}"
        if m_dict.get('equiv_object_alt_labels') and not str(m_dict.get('equiv_object_alt_labels')) in ['nan', 'None']:
            specific_desc += f", {m_dict.get('equiv_object_alt_labels')}"
        specific_desc = explain_text_clean(specific_desc)
    project_label = ''
    if has_key_str_value(m_dict, 'project__label'):
        project_label = '<br/><b>Project Name:</b> ' + str(m_dict.get('project__label'))
        project_label = explain_text_clean(project_label)
    project_desc = ''
    if has_key_str_value(m_dict, 'proj_short_desc'):
        project_desc = '<br/><b>Description:</b> ' + str(m_dict.get('proj_short_desc'))
        project_desc = explain_text_clean(project_desc)
    metadata = ''
    if has_key_str_value(m_dict, 'metadata'):     
       # only add metadata if we don't already have specific data
        metadata = '<br/><b>General Topics:</b> ' +  str(m_dict.get('metadata'))
        metadata = explain_text_clean(metadata)
    all_text = [
        explain_item_class,
        places,
        specific_desc,
        project_desc,
        metadata,
    ]
    make_explain_text = ' '.join(
        [txt for txt in all_text if txt != '']
    )
    make_explain_text = f'<div>{make_explain_text}</div>'
    return make_explain_text


def  add_explain_texts_and_embeddings_to_df(df):
    """Adds explanation texts and associated embeddings to the df"""
    df['explain_text'] = ''
    df['chunck_count'] = 0
    df[EMBEDDING_FIELD_SOLR] = None
    print(f'Generate explanation text and embeddings for: {len(df.index)}')
    clean = re.compile(r'<[^>]+>')
    for i, row in df.iterrows():
        explain_text_html = make_explain_text(m_dict=row)
        explain_text = re.sub(clean, '', explain_text_html)
        # See documentation here: https://huggingface.co/intfloat/multilingual-e5-large
        explain_text = 'passage: ' + explain_text
        chunks = chunk_text_for_embedding(explain_text)
        chunk_count = len(chunks)
        if chunk_count > 1:
            print(f'Long text for embedding: "{explain_text}"')
        embedding = embed_with_chunk_pooling(explain_text)
        df.at[i, 'explain_text'] = explain_text_html
        df.at[i, 'chunck_count'] = chunk_count
        df.at[i, EMBEDDING_FIELD_SOLR] = embedding
    return df


def start_explained_searches_df():
    print('Start to generate search explanations')
    data = get_distinct_project_item_type_item_classes_with_geo_chrono()
    df = pd.DataFrame(data=data)
    return df


def make_explained_searches_df():
    df = start_explained_searches_df()
    df = augment_explained_searches_vocabularies(df)
    df.to_csv(EXPLAINED_SEARCHES_PREP_PATH, index=False)
    df = add_explain_texts_and_embeddings_to_df(df)
    print(f'Generated search explanations: {len(df.index)}')
    return df

        
def make_explained_searches_parquet_from_df(df):
    # Make an in-memory table via duckdb
    con = duckdb.connect(database=':memory:')
    con.execute("DROP TABLE IF EXISTS explained_searches")

    create_cols_data_types = []
    insert_cols_data_types = []
    for col in df.columns.tolist():
        data_type = DF_COLS_ALL_TO_DUCKDB_DATA_TYPES.get(col, 'VARCHAR')
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