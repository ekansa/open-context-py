import copy
import os
import duckdb
from duckdb.typing import *

from django.conf import settings

from opencontext_py.apps.all_items.isamples import duckdb_con


OC_RAW_TABLES = [
    ('oc_all_manifest'),
    ('oc_all_assertions'),
    ('oc_all_resources'),
    ('oc_all_identifiers'),
    ('oc_all_spacetime'),
]

DB_CON = duckdb_con.create_duck_db_postgres_connection()

def dump_oc_raw_tables_to_parquet(output_dir_path, con=DB_CON, db_schema=duckdb_con.DUCKDB_SCHEMA):
    """Dump Open Context raw tables to parquet files"""
    for table_name in OC_RAW_TABLES:
        filepath = os.path.join(output_dir_path, f"{table_name}.parquet")
        print(f'Dumping {table_name} to {filepath}')
        con.execute(f"COPY (SELECT * FROM {db_schema}.{table_name}) TO '{filepath}' ")

