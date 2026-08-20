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

from opencontext_py.apps.indexer.solrdocument_slim_schema import (
    EMBEDDING_FIELD_SOLR,
)
from opencontext_py.apps.indexer.explained_topic_data import (
    EXPLAINED_SEARCHES_LOCAL_PATH 
)
from opencontext_py.apps.indexer.embeddings import (
    EMBEDDING_MODEL_DIM,
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
    if not is_null_str(row['bbox']):
        params['bbox'] = str(row['bbox'])
    if not is_null_str(row['item_type']):
        params['type'] = str(row['item_type'])
    if not is_null_str(row['item_class__slug']):
        params['cat'] = str(row['item_class__slug'])
    if not is_null_str(row['equiv_predicate_slug']) and not is_null_str(row['equiv_object_slug']):
        params['prop'] = f"{str(row['equiv_predicate_slug'])}---{str(row['equiv_object_slug'])}"
    if not params:
        return url
    return url + '?' + urllib.parse.urlencode(params)


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
    ORDER BY round(similarity_metric, 3) DESC, item_type_class_asserts_rate  DESC
    LIMIT 50;
    """
    df = duckdb.sql(sql).df()
    df['url'] = ''
    df['url'] =  df.apply(lambda row: generate_query_url_from_row(row), axis=1)
    return df, emb_query


def make_group_by_col_combos():
    combos = [c for c in COLS_MAIN_SEARCH_PARAMS]
    for i in range(2, len(COLS_MAIN_SEARCH_PARAMS)):
        new_combos_tups = combinations(COLS_MAIN_SEARCH_PARAMS, i)
        combos += [list(n) for n in new_combos_tups]
    return combos


def get_difference_between_embeddings(e1, e2):
    """Get a difference distance between two embeddings"""
    v1 = np.array(e1)
    v2 = np.array(e2)
    return cosine(v1, v2)


def reduce_top_query_params(df_gen):
    metrics = df_gen['similarity_metric'].unique().tolist()
    metrics.sort(reverse=True)
    best_metrics = metrics[0:5]
    final_index = False
    for metric in best_metrics:
        metric_index = df_gen['similarity_metric'] == metric
        metric_top_null_count = df_gen[metric_index]['null_count'].max()
        final_index |= (metric_index & (df_gen['null_count'] == metric_top_null_count ))
    df_gen = df_gen[final_index].copy()
    return df_gen


def check_path_distances(df, emb_query):
    df['path_similarity_metric'] = float(0.0)
    df['all_similarity_metrics'] = df['similarity_metric']
    paths = df['path'].unique().tolist()
    for path in paths:
        places = 'Relevant Places: in ' + path.replace('/', ', in ')
        place_embedding = embed_with_chunk_pooling(
            embedding_str=places
        )
        place_distance = get_difference_between_embeddings(emb_query, place_embedding)
        place_similarity = 1 - place_distance
        act_index = df['path'] == path
        df.loc[act_index, 'path_similarity_metric'] = place_similarity
    relevant_path_index = df['path_similarity_metric'] > 0.75
    for i, row in df[relevant_path_index].iterrows():
        df.at[i, 'all_similarity_metrics'] = (
        row['similarity_metric'] * 0.8 
        + row['path_similarity_metric'] * 0.20
    )
    df.sort_values(by=[ 'all_similarity_metrics'], ascending=False, inplace=True)
    return df



def get_top_general_queries(df):
    combos = make_group_by_col_combos()
    all_group_by_cols = []
    for act_col_combo in combos:
        for act_cols in act_col_combo:
            if isinstance(act_cols, str):
                all_group_by_cols.append(act_cols)
            else:
                all_group_by_cols += act_cols
    all_group_by_cols = list(set(all_group_by_cols))
    df.drop(columns=['uuid'], inplace=True)
    group_include_cols = [c for c in df.columns.tolist() if c not in all_group_by_cols]
    df_gs = [df[group_include_cols].head(5)]
    cols = df.columns.tolist()
    combos = make_group_by_col_combos()
    for act_col_combo in combos:
        grp_by_cols = []
        for act_cols in act_col_combo:
            if isinstance(act_cols, str):
                grp_by_cols.append(act_cols)
            else:
                grp_by_cols += act_cols
        g_cols = group_include_cols + grp_by_cols
        agg_dict = {c:'first' for c in group_include_cols}
        agg_dict['similarity_metric'] = 'mean'
        df_g = df[g_cols].groupby(grp_by_cols).agg(
            agg_dict
        ).reset_index()
        df_g.sort_values(by='similarity_metric', ascending=False, inplace=True)
        df_gs.append(df_g)
    df_gen = pd.concat(df_gs, ignore_index=True, sort=False)
    df_gen['null_count'] = df_gen.isnull().sum(axis=1)
    df_gen = reduce_top_query_params(df_gen)
    df_gen.sort_values(by=['similarity_metric', 'null_count'], ascending=False, inplace=True)
    return df_gen

