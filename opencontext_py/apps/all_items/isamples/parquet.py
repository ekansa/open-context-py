import copy
import json
import os

import duckdb
from duckdb.typing import *

from django.conf import settings

from opencontext_py.libs import duckdb_con


OC_RAW_TABLES = [
    ('oc_all_manifest'),
    ('oc_all_assertions'),
    ('oc_all_resources'),
    ('oc_all_identifiers'),
    ('oc_all_spacetime'),
]

DB_CON = duckdb_con.create_duck_db_postgres_connection()


NODE_TYPES = {
  "Agent": {
    "name": "name VARCHAR DEFAULT NULL",
    "affiliation": "affiliation VARCHAR DEFAULT NULL",
    "contact_information": "contact_information VARCHAR DEFAULT NULL",
    "role": "role VARCHAR DEFAULT NULL",
    "label": "label VARCHAR DEFAULT NULL",
    "description": "description VARCHAR DEFAULT NULL"
  },
  "IdentifiedConcept": {
    "label": "label VARCHAR DEFAULT NULL",
    "scheme_name": "scheme_name VARCHAR DEFAULT NULL",
    "scheme_uri": "scheme_uri VARCHAR DEFAULT NULL",
    "description": "description VARCHAR DEFAULT NULL"
  },
  "GeospatialCoordLocation": {
    "elevation": "elevation VARCHAR DEFAULT NULL",
    "latitude": "latitude DOUBLE DEFAULT NULL",
    "longitude": "longitude DOUBLE DEFAULT NULL",
    "obfuscated": "obfuscated BOOLEAN ",
    "label": "label VARCHAR DEFAULT NULL",
    "description": "description VARCHAR DEFAULT NULL"
  },
  "SamplingSite": {
    "description": "description VARCHAR DEFAULT NULL",
    "label": "label VARCHAR DEFAULT NULL",
    "place_name": "place_name VARCHAR[]",
    "is_part_of": "is_part_of VARCHAR[]"
  },
  "SamplingEvent": {
    "label": "label VARCHAR DEFAULT NULL",
    "description": "description VARCHAR DEFAULT NULL",
    "has_feature_of_interest": "has_feature_of_interest VARCHAR DEFAULT NULL",
    "project": "project VARCHAR DEFAULT NULL",
    "result_time": "result_time VARCHAR DEFAULT NULL",
    "authorized_by": "authorized_by VARCHAR[]"
  },
  "MaterialSampleCuration": {
    "access_constraints": "access_constraints VARCHAR[]",
    "curation_location": "curation_location VARCHAR DEFAULT NULL",
    "description": "description VARCHAR DEFAULT NULL",
    "label": "label VARCHAR DEFAULT NULL"
  },
  "SampleRelation": {
    "description": "description VARCHAR DEFAULT NULL",
    "label": "label VARCHAR DEFAULT NULL",
    "relationship": "relationship VARCHAR DEFAULT NULL",
    "target": "target VARCHAR DEFAULT NULL"
  },
  "MaterialSampleRecord": {
    "label": "label VARCHAR DEFAULT NULL",
    "last_modified_time": "last_modified_time VARCHAR DEFAULT NULL",
    "description": "description VARCHAR DEFAULT NULL",
    "sample_identifier": "sample_identifier VARCHAR DEFAULT NULL",
    "alternate_identifiers": "alternate_identifiers VARCHAR[]",
    "sampling_purpose": "sampling_purpose VARCHAR DEFAULT NULL",
    "complies_with": "complies_with VARCHAR[]",
    "dc_rights": "dc_rights VARCHAR DEFAULT NULL"
  }
}

EDGE_FIELDS = [
  "pid",
  "otype",
  "s",
  "p",
  "o",
  "n",
  "altids",
  "geometry"
]

LITERAL_FIELDS = [
  "authorized_by",
  "has_feature_of_interest",
  "affiliation",
  "sampling_purpose",
  "complies_with",
  "project",
  "alternate_identifiers",
  "relationship",
  "elevation",
  "sample_identifier",
  "dc_rights",
  "result_time",
  "contact_information",
  "latitude",
  "target",
  "role",
  "scheme_uri",
  "is_part_of",
  "scheme_name",
  "name",
  "longitude",
  "obfuscated",
  "curation_location",
  "last_modified_time",
  "access_constraints",
  "place_name",
  "description",
  "label",
  "pid",
  "otype",
  "s",
  "p",
  "o",
  "n",
  "altids",
  "geometry"
]





def dump_oc_raw_tables_to_parquet(output_dir_path, con=DB_CON, db_schema=duckdb_con.DUCKDB_SCHEMA):
    """Dump Open Context raw tables to parquet files.
    
    Args:
        output_dir_path (str): Directory path where parquet files will be saved
        con (duckdb.DuckDBPyConnection, optional): DuckDB connection object. Defaults to DB_CON
        db_schema (str, optional): Database schema name. Defaults to duckdb_con.DUCKDB_SCHEMA
    
    The function dumps the following tables to parquet format:
    - oc_all_manifest
    - oc_all_assertions
    - oc_all_resources
    - oc_all_identifiers
    - oc_all_spacetime
    """
    for table_name in OC_RAW_TABLES:
        filepath = os.path.join(output_dir_path, f"{table_name}.parquet")
        print(f'Dumping {table_name} to {filepath}')
        con.execute(f"COPY (SELECT * FROM {db_schema}.{table_name}) TO '{filepath}' ")


def dump_oc_pqg_table_to_parquet(output_dir_path, con=DB_CON):
    """Dump Open Context PQG (Property Graph) table to parquet format with metadata.
    
    Args:
        output_dir_path (str): Directory path where parquet file will be saved
        con (duckdb.DuckDBPyConnection, optional): DuckDB connection object. Defaults to DB_CON
    
    The function creates a parquet file with the following metadata:
    - pqg_version: Version of the PQG format
    - pqg_primary_key: Primary key field name
    - pqg_node_types: JSON string of node type definitions
    - pqg_edge_fields: JSON string of edge field definitions
    - pqg_literal_fields: JSON string of literal field definitions
    """
    outpath = os.path.join(output_dir_path, 'oc_isamples_pqg.parquet')
    sql = f"COPY (SELECT * FROM pqg ) TO '{outpath}' "
    sql += "(FORMAT PARQUET, KV_METADATA {"
    sql += "pqg_version: '0.2.0', "
    sql += "pqg_primary_key: 'pid', "
    sql += f"pqg_node_types: '{json.dumps(NODE_TYPES)}', "
    sql += f"pqg_edge_fields: '{json.dumps(EDGE_FIELDS)}', "
    sql += f"pqg_literal_fields: '{json.dumps(LITERAL_FIELDS)}' "
    sql += '})'
    con.execute(sql)


def dump_isamples_tables_to_parquet(output_dir_path, con=DB_CON, db_schema=duckdb_con.DUCKDB_SCHEMA):
    """Dump iSamples related tables to parquet files.
    
    Args:
        output_dir_path (str): Directory path where parquet files will be saved
        con (duckdb.DuckDBPyConnection, optional): DuckDB connection object. Defaults to DB_CON
        db_schema (str, optional): Database schema name. Defaults to duckdb_con.DUCKDB_SCHEMA
    
    The function dumps the following tables to parquet format:
    1. iSamples preparation manifest table
    2. iSamples preparation assertion table (joined with manifest)
    3. iSamples preparation person table
    4. Open Context PQG table (via dump_oc_pqg_table_to_parquet)
    
    The assertion table dump includes joined data from both manifest and assertion tables
    with specific fields related to predicates and objects.
    """
    tables_sql_files = [
        (
            f"""
            SELECT * FROM {duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE}
            """,
            f'oc_test_{duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE}.parquet',
        ),
        (
            f"""
            SELECT 
            m.PID_SAMP,
            m.uuid,
            m.label,
            m.path,
            m.uri,
            a.predicate_equiv_ld_uri,
            a.predicate_equiv_ld_label,
            a.object_equiv_ld_uri,
            a.object_equiv_ld_label,
            a.predicate_label,
            a.predicate_uri,
            a.object_label,
            a.object_uri,
            a.object_item_type
            FROM {duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE} AS m
            INNER JOIN {duckdb_con.ISAMPLES_PREP_ASSERTION_TABLE} AS a ON m.uuid = a.subject_uuid
            WHERE a.predicate_equiv_ld_uri IS NOT null
            """,
            f'oc_test_{duckdb_con.ISAMPLES_PREP_ASSERTION_TABLE}.parquet',
        ),
        (
            f"""
            SELECT * FROM {duckdb_con.ISAMPLES_PREP_PERSON_TABLE}
            """,
            f'oc_test_{duckdb_con.ISAMPLES_PREP_PERSON_TABLE}.parquet',
        ),
    ]
    for sql, filename in tables_sql_files:
        filepath = os.path.join(output_dir_path, filename)
        print(f'Dumping {filename} to {filepath}')
        con.execute(f"COPY ({sql}) TO '{filepath}' ")
    dump_oc_pqg_table_to_parquet(output_dir_path, con=con)