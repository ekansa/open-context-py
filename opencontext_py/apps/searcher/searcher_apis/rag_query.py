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

from opencontext_py.apps.indexer.solrdocument_slim_schema import (
    EMBEDDING_FIELD_SOLR,
)
from opencontext_py.apps.indexer.rag_data import (
    EXPLAINED_SEARCHES_LOCAL_PATH 
)
from opencontext_py.apps.indexer.embeddings import (
    EMBEDDING_MODEL_DIM,
    embed_with_chunk_pooling
)


"""
from opencontext_py.apps.searcher.searcher_apis import rag_query as vibes

query_str = 'food preparation for the pyramid builders of Egypt'
db_m = vibes.make_vibe_query_sql(query_str)

query_str = 'ancient building material in Tuscany'
db_m = vibes.make_vibe_query_sql(query_str)

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
]
for query_str in query_strs:
    db_m = vibes.make_vibe_query_sql(query_str)

"""



EXPLAINED_SEARCHES_TABLE = 'explained_searches'

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

def make_vibe_query_sql(query_str):
    if not query_str:
        return None
    if not query_str.startswith('query: '):
        query_str = 'query: ' + query_str
    print(query_str)
    emb_query = embed_with_chunk_pooling(query_str)
    sql = f"""
    SELECT 
        
        item_type,
        item_class__slug,
        project__slug,
        object__slug,
        path,
        item_type_class_asserts_rate,
        array_cosine_similarity(
            {EMBEDDING_FIELD_SOLR}::FLOAT[{EMBEDDING_MODEL_DIM}], 
            {emb_query}::FLOAT[{EMBEDDING_MODEL_DIM}]
        ) AS similarity_metric
    FROM {EXPLAINED_SEARCHES_TABLE}
    WHERE item_type_class_asserts_rate > 3
    ORDER BY similarity_metric DESC
    LIMIT 15;
    """
    db_m = duckdb.sql(sql)
    db_m.show()
    return db_m