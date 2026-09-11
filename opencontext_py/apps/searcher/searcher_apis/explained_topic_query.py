import duckdb
from duckdb.sqltypes import *

import hashlib
import json
import os
import numpy as np
import pandas as pd
import re
from scipy.spatial.distance import cosine
import urllib.parse

from itertools import combinations

from django.db.models import Max, Min
from django.db.models import OuterRef, Subquery


from django.conf import settings

from opencontext_py.libs import duckdb_con


from opencontext_py.apps.all_items.icons import configs as icon_configs

from opencontext_py.apps.indexer.solrdocument_slim_schema import (
    EMBEDDING_FIELD_SOLR,
)
from opencontext_py.apps.indexer.explained_topic_data import (
    EXPLAINED_SEARCHES_LOCAL_PATH,
    explain_text_clean,
    get_unique_non_null_values_from_keys,
)
from opencontext_py.apps.indexer.embedding_configs import (
    QUERY_ITEM_TYPE_EXPLAIN_DICT,
    CLASS_SLUG_EXPLAIN_DICT,
    EQUIV_OBJ_SLUG_EXPLAIN_DICT,
    EQUIV_PRED_CLASS_SLUG_EXPLAIN_DICT,
)
from opencontext_py.apps.indexer.embeddings import (
    EMBEDDING_MODEL_DIM,
    ACTIVE_EMBEDDING_MODEL_READY,
    embed_with_chunk_pooling
)


"""
from IPython.display import display
import json
from opencontext_py.apps.searcher.searcher_apis import explained_topic_query as vibes
query_strs = [
    'Ancient Greek god of the sun',
    'Ancient Greek mythology',
    'Roman numismatics',
    'origins of agriculture in the middle east',
    'settlement patterns in America',
    'beer and bread to feed pyramid builders in Egypt',
    'evidence for etruscan weaving',
    'warfare in mesopotamia',
    'bronze age near east craft production',
    'everyday life in ancient Egypt',
    'origins of herding in the Near East',
    'evidence for making clothing in Etruscan times',
    'weaving in tuscany',
    'wool production in Mesopotamia',
    'ancient divination or magic',
    'tel kedesh administration',
    'a mythological monster',
    'architecture in the ancient near east',
    'building techniques in the ancient middle east',
    'representation of the ancient greek goddess of wisdom',
    'depiction of ulysses',
    'evidence for ovens or fireplaces in Anatolia',
]
for query_str in query_strs:
    print('')
    df, emb_query = vibes.make_df_from_vibe_query_sql(query_str)
    # df = vibes.check_path_distances(df, emb_query)
    # df_gen = vibes.get_top_general_queries(df)
    # print(df_gen.head(5))
    json_str = df[vibes.DEMO_COLS].head(5).to_json(orient='records')
    recs = json.loads(json_str)
    for rec in recs:
        print('-' * 100)
        print(rec)
    print('')
"""

# This is used to signal that the language model and explained searches data
# are both available and can be used.
EXPLAINED_SEARCH_READY = ACTIVE_EMBEDDING_MODEL_READY and os.path.exists(EXPLAINED_SEARCHES_LOCAL_PATH)

EXPLAINED_SEARCHES_TABLE = 'explained_searches'

COLS_MAIN_SEARCH_PARAMS = [
    ['project__slug'],
    # ['item_type', 'item_class__slug',],
    ['path',],
    ['bbox',],
    ['equiv_predicate_slug', 'equiv_object_slug',],
]

DEMO_COLS = [
    # 'bbox',
    'similarity_metric',
    'item_class__label',
    'equiv_predicate_label',
    'equiv_object_label',
    'equiv_object_alt_labels',
    'explain_text', 
    'url',
]

START_API_COLS = [
    'similarity_metric',
    'project__slug',
    'project__label',
    'proj_short_desc',
    'metadata',
    'path',
    'item_type',
    'item_class__slug',
    'item_class__label',
    'predicate__slug',
    'predicate__label',
    'object__label',
    'object__slug',
    'equiv_predicate_slug',
    'equiv_predicate_label',
    'equiv_object_slug',
    'equiv_object_label',
    'equiv_object_alt_labels',
    # 'explain_text', 
    'url',
]

API_COLS = START_API_COLS + [
    # Added in make_api_output_from_vibe_query_df
    'place',
    'class_icon_url',
    'class_explain',
    'predicate_labels',
    'object_labels',
    'predicate_object_explain',
]


def make_hash_id_from_query_str(query_str):
    """Makes a hash identifier for a query_str"""
    hash_obj = hashlib.sha1()
    hash_obj.update(str(query_str).encode('utf-8'))
    return hash_obj.hexdigest()


def is_null_str(val):
    if str(val).lower() in ['', 'nan', 'none']:
        return True
    return False


def generate_query_url_from_row(row, root_url='https://opencontext.org/query/'):
    url = root_url
    if not is_null_str(row['path']):
        url += str(row['path']).replace(' ', '+')
    params = {}
    if 'row_num' in row:
        params['vector-rec'] = row['row_num']
    if not is_null_str(row['bbox']):
        params['bbox'] = str(row['bbox'])
    if not is_null_str(row['item_type']):
        params['type'] = str(row['item_type'])
    if not is_null_str(row['item_class__slug']):
        params['cat'] = str(row['item_class__slug'])
    if not is_null_str(row['equiv_predicate_slug']) and not is_null_str(row['equiv_object_slug']):
        params['prop'] = f"{str(row['equiv_predicate_slug'])}---{str(row['equiv_object_slug'])}"
    if not params and not is_null_str(row['predicate__slug']):
        return url
    url = url + '?' + urllib.parse.urlencode(params)
    if not is_null_str(row['predicate__slug']) and not is_null_str(row['object__slug']):
        new_prop_filter = f"{str(row['predicate__slug'])}---{str(row['object__slug'])}"
        if new_prop_filter in url:
            # we already have this, so skip out
            return url
        if '?' in url:
            sep = '&'
        else:
            sep = '?'
        # We can have multiple 'prop' args in a URL
        url += f"{sep}prop={new_prop_filter}"
    return url


def load_explained_search_table_from_parquet_path(
    parquet_path=EXPLAINED_SEARCHES_LOCAL_PATH, 
    table=EXPLAINED_SEARCHES_TABLE,
):
    """Loads a parquet file into the pqg table, in memory"""
    if not os.path.exists(parquet_path):
        return None
    sql = f"""
    CREATE VIEW {table} AS
    SELECT * FROM '{parquet_path}';
    """
    db_m = duckdb.sql(sql)
    return db_m


EXPLAINED_SEARCH_TABLE = load_explained_search_table_from_parquet_path()



def make_df_from_vibe_query_sql(query_str):
    if not query_str:
        return None
    if not query_str.startswith('query: '):
        query_str = 'query: ' + query_str
    print(query_str)
    emb_query = embed_with_chunk_pooling(query_str)
    sql = f"""
    SELECT
        uuid, 
        project__label,
        project__slug,
        proj_short_desc,
        metadata,
        item_type,
        item_class__label,
        item_class__slug,
        path,
        bbox,
        predicate__label,
        predicate__slug,
        object__label,
        object__slug,
        equiv_predicate_label,
        equiv_predicate_slug,
        equiv_object_slug,
        equiv_object_label,
        equiv_object_alt_labels,
        latitude__min, 
        longitude__min,
        latitude__max,
        longitude__max,
        earliest__min,
        latest__max,
        explain_text,
        item_type_class_asserts_rate,
        array_cosine_similarity(
            {EMBEDDING_FIELD_SOLR}::FLOAT[{EMBEDDING_MODEL_DIM}], 
            {emb_query}::FLOAT[{EMBEDDING_MODEL_DIM}]
        ) AS similarity_metric
    FROM {EXPLAINED_SEARCHES_TABLE}
    WHERE item_type_class_asserts_rate > 3
    ORDER BY round(similarity_metric, 4) DESC, item_type_class_asserts_rate  DESC
    LIMIT 50;
    """
    df = duckdb.sql(sql).df()
    df['row_num'] = df.index + 1
    df['url'] = ''
    df['url'] =  df.apply(lambda row: generate_query_url_from_row(row), axis=1)
    return df, emb_query


def get_item_type_item_class_icon(item_type, item_class_slug):
    icon_url = None
    for class_config_dict in icon_configs.ITEM_TYPE_CLASS_ICONS_DICT.get(item_type, []):
        if not icon_url:
            icon_url = class_config_dict.get('icon')
        if item_class_slug == class_config_dict.get('item_class__slug'):
            # we matched our the exact item_type, item_class__slug, skip out
            return class_config_dict.get('icon')
    return icon_url


def make_api_output_from_vibe_query_df(df, top_result_count=5):
    cols = [c for c in START_API_COLS if c in df.columns.tolist()]
    df = df[cols].head(top_result_count).copy()
    df['place'] = ''
    df['class_icon_url'] = ''
    df['class_explain'] = ''
    df['predicate_labels'] = ''
    df['object_labels'] = ''
    df['predicate_object_explain'] = ''
    for i, row in df.iterrows():
        
        if row['path']: 
            df.at[i, 'place'] = str(row['path']).replace('/', ', ')
                    
        df.at[i, 'class_icon_url'] = get_item_type_item_class_icon(
            item_type=row['item_type'], 
            item_class_slug=row['item_class__slug'], 
        )
        explain_item_class = CLASS_SLUG_EXPLAIN_DICT.get(
            row['item_class__slug'],
            QUERY_ITEM_TYPE_EXPLAIN_DICT.get(
                row['item_type']
            )
        )
        df.at[i, 'class_explain'] = explain_text_clean(explain_item_class)
        predicate_labels = get_unique_non_null_values_from_keys(
            row, 
            keys=['equiv_predicate_label'],
        )
        if not predicate_labels:
            # Only use the project specific predicate if there's no standard equivalent
            predicate_labels = get_unique_non_null_values_from_keys(
                row, 
                keys=['predicate__label',],
            )
        df.at[i, 'predicate_labels'] = ' or '.join(predicate_labels)
        object_labels = get_unique_non_null_values_from_keys(
            row, 
            keys=['object__label', 'equiv_object_label', 'equiv_object_alt_labels'],
        )
        df.at[i, 'object_labels'] = ', '.join(object_labels)
        po_explains = []
        if EQUIV_PRED_CLASS_SLUG_EXPLAIN_DICT.get((row['equiv_predicate_slug'], row['item_class__slug'])):
            p_explain = explain_text_clean(EQUIV_PRED_CLASS_SLUG_EXPLAIN_DICT.get((row['equiv_predicate_slug'], row['item_class__slug'])))
            po_explains.append(p_explain)
        if EQUIV_OBJ_SLUG_EXPLAIN_DICT.get(row['equiv_object_slug']):
            o_explain = explain_text_clean(EQUIV_OBJ_SLUG_EXPLAIN_DICT.get(row['equiv_object_slug']))
            po_explains.append(o_explain)
        df.at[i, 'predicate_object_explain'] = ' '.join(po_explains)
    return df
