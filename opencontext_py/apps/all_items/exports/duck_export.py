import copy
import json
import os

import duckdb
from duckdb.typing import *

from django.conf import settings

from opencontext_py.apps.all_items import configs

from opencontext_py.libs import duckdb_con

"""
# Testing

import importlib
from opencontext_py.apps.all_items.exports import duck_export
importlib.reload(duck_export)

project_ids = ['df043419-f23b-41da-7e4d-ee52af22f92f', '3de4cd9c-259e-4c14-9b03-8b10454ba66e',]
duck_export.dump_data_for_projects(
    project_ids=project_ids, 
    output_dir_path='/home/ekansa/oc-data/oc_exports',
)
"""

OC_RAW_TABLES = [
    ('oc_all_manifest'),
    ('oc_all_assertions'),
    ('oc_all_resources'),
    ('oc_all_identifiers'),
    ('oc_all_spacetime'),
]

DB_CON = duckdb_con.create_duck_db_postgres_connection()

def append_to_temp_manifest(
    adding_alias,
    con=DB_CON, 
    alias_temp_manifest='temp_manifest',
    alias_temp_added='temp_added' 
):
    """Append additional context to the temporary manifest table"""
    sql = f"""
    SELECT adding.uuid, adding.project_uuid, adding.publisher_uuid, adding.context_uuid, adding.item_class_uuid
    FROM {adding_alias} AS adding
    WHERE 1=1

    UNION

    SELECT pm.uuid, pm.project_uuid, pm.publisher_uuid, pm.context_uuid, pm.item_class_uuid
    FROM {alias_temp_manifest} AS pm
    WHERE 1=1

    """
    con.execute(f"DROP TABLE IF EXISTS {alias_temp_added}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias_temp_added} AS ({sql})'
    con.execute(temp_table_sql)
    con.execute(f"DROP TABLE IF EXISTS {alias_temp_manifest}")

    # Make sure we have distinct records in the manifest table
    sql = f"""SELECT DISTINCT adding.uuid, adding.project_uuid, adding.publisher_uuid, adding.context_uuid, adding.item_class_uuid
    FROM {alias_temp_added} AS adding
    WHERE 1=1
    """
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias_temp_manifest} AS ({sql})'
    con.execute(temp_table_sql)



def add_related_objs_to_temp_manifest(
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA,
    alias_temp_manifest='temp_manifest',
):
    """Add referenced item_class_uuid to the temporary manifest table
    
    Args:
        con (duckdb.DuckDBPyConnection, optional): DuckDB connection object. Defaults to DB_CON
        db_schema (str, optional): Database schema name. Defaults to duckdb_con.DUCKDB_SCHEMA
        alias_temp_manifest (str, optional): Alias for the temporary manifest table. Defaults to 'temp_manifest'
    
    """
    rel_fields = [
        'project_uuid',
        'publisher_uuid',
        'context_uuid',
        'item_class_uuid',
    ]
    rel_fields_done = False
    cycle_count = 0
    while not rel_fields_done:
        cycle_count += 1
        sql = f"""
            SELECT COUNT(uuid) AS count
            FROM {alias_temp_manifest} AS man
            WHERE 1=1
            """
        prog = con.sql(sql).fetchone()
        print(f'Cycle [{cycle_count}] Manifest records used in projects is now: {prog[0]}') 
        before_count = prog[0]
        for rel_field in rel_fields:
            rel_field_alias = f'{rel_field}_temp_manifest'
            sql = f"""
            SELECT pm.uuid, pm.project_uuid, pm.publisher_uuid, pm.context_uuid, pm.item_class_uuid
            FROM {db_schema}.oc_all_manifest AS pm
            WHERE pm.uuid IN (
                SELECT DISTINCT {rel_field} FROM {alias_temp_manifest}
            )
            """
            con.execute(f"DROP TABLE IF EXISTS {rel_field_alias}")
            rel_table_sql = f'CREATE TEMPORARY TABLE {rel_field_alias} AS {sql}'
            con.execute(rel_table_sql)
            sql = f"""
            SELECT COUNT(uuid) AS count
            FROM {rel_field_alias}
            WHERE 1=1
            """
            prog = con.sql(sql).fetchone()
            print(f'Number of {rel_field} records used in projects: {prog[0]}')
            append_to_temp_manifest(adding_alias=rel_field_alias, con=con)
        sql = f"""
            SELECT COUNT(uuid) AS count
            FROM {alias_temp_manifest} AS man
            WHERE 1=1
            """
        prog = con.sql(sql).fetchone()
        print(f'Cycle [{cycle_count}] Manifest records used in projects is after adding related fields: {prog[0]}') 
        after_count = prog[0]
        rel_fields_done = (after_count == before_count)


def add_space_time_related_manifest_records(
    project_ids,
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA,
    alias_temp_manifest='temp_manifest',
    alias_rel_spacetime='rel_spacetime_temp_manifest',
):
    """Add space-time related manifest records to the temporary manifest table
    
    Args:
        con (duckdb.DuckDBPyConnection, optional): DuckDB connection object. Defaults to DB_CON
        db_schema (str, optional): Database schema name. Defaults to duckdb_con.DUCKDB_SCHEMA
        alias_temp_manifest (str, optional): Alias for the temporary manifest table. Defaults to 'temp_manifest'
    
    """
    projects_sql = ', '.join([duckdb_con.cast_duckdb_uuid(pid) for pid in project_ids])

    space_time_fks = [
        'item_uuid',
        'event_uuid',
        'project_uuid',
        'publisher_uuid',
    ]
    i = 0
    sp_fk_sql = ''
    for fk in space_time_fks:
        i += 1
        sp_fk_sql += f"""
        OR pm.uuid IN (
          SELECT DISTINCT sp{i}.{fk}
          FROM {db_schema}.oc_all_spacetime AS sp{i}
          INNER JOIN {alias_temp_manifest} AS m{i} ON sp{i}.item_uuid = m{i}.uuid
          WHERE m{i}.project_uuid IN ({projects_sql})
          OR m{i}.uuid IN ({projects_sql})
          OR sp{i}.project_uuid IN ({projects_sql})
        )
         """
    sql = f"""
    SELECT pm.uuid, pm.project_uuid, pm.publisher_uuid, pm.context_uuid, pm.item_class_uuid
    FROM {db_schema}.oc_all_manifest AS pm
    WHERE pm.uuid IN (
        SELECT DISTINCT m.uuid
        FROM {alias_temp_manifest} AS m
        WHERE 1=1
    )
    {sp_fk_sql}
    """
    con.execute(f"DROP TABLE IF EXISTS {alias_rel_spacetime}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias_rel_spacetime} AS {sql}'
    con.execute(temp_table_sql)
    append_to_temp_manifest(adding_alias=alias_rel_spacetime, con=con, alias_temp_manifest=alias_temp_manifest)
    con.execute(f"DROP TABLE IF EXISTS {alias_rel_spacetime}")


def add_resources_related_manifest_records(
    project_ids,
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA,
    alias_temp_manifest='temp_manifest',
    alias_rel_resources='rel_resources_temp_manifest',
):
    """Add resources related manifest records to the temporary manifest table
    
    Args:
        con (duckdb.DuckDBPyConnection, optional): DuckDB connection object. Defaults to DB_CON
        db_schema (str, optional): Database schema name. Defaults to duckdb_con.DUCKDB_SCHEMA
        alias_temp_manifest (str, optional): Alias for the temporary manifest table. Defaults to 'temp_manifest'
    
    """
    projects_sql = ', '.join([duckdb_con.cast_duckdb_uuid(pid) for pid in project_ids])

    resource_fks = [
        'item_uuid',
        'mediatype_uuid',
        'project_uuid',
        'resourcetype_uuid',
    ]
    i = 0
    sp_fk_sql = ''
    for fk in resource_fks:
        i += 1
        sp_fk_sql += f"""
        OR pm.uuid IN (
          SELECT DISTINCT r{i}.{fk}
          FROM {db_schema}.oc_all_resources AS r{i}
          INNER JOIN {alias_temp_manifest} AS m{i} ON r{i}.item_uuid = m{i}.uuid
          WHERE m{i}.project_uuid IN ({projects_sql})
          OR m{i}.uuid IN ({projects_sql})
          OR r{i}.project_uuid IN ({projects_sql})
        )
         """
    sql = f"""
    SELECT pm.uuid, pm.project_uuid, pm.publisher_uuid, pm.context_uuid, pm.item_class_uuid
    FROM {db_schema}.oc_all_manifest AS pm
    WHERE pm.uuid IN (
        SELECT DISTINCT m.uuid
        FROM {alias_temp_manifest} AS m
        WHERE 1=1
    )
    {sp_fk_sql}
    """
    con.execute(f"DROP TABLE IF EXISTS {alias_rel_resources}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias_rel_resources} AS {sql}'
    con.execute(temp_table_sql)
    append_to_temp_manifest(adding_alias=alias_rel_resources, con=con, alias_temp_manifest=alias_temp_manifest)
    con.execute(f"DROP TABLE IF EXISTS {alias_rel_resources}")




def start_temp_manifest_table(
    project_ids,
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA,
    alias_temp_manifest='temp_manifest'
):
    """Create a temporary manifest table containing all the items for the given project IDs, including items
    from other projects referenced in assertions.

    Args:
        project_ids (list): List of project UUIDs to include in the manifest table
        con (duckdb.DuckDBPyConnection, optional): DuckDB connection object. Defaults to DB_CON
        db_schema (str, optional): Database schema name. Defaults to duckdb_con.DUCKDB_SCHEMA
        alias_temp_manifest (str, optional): Alias for the temporary manifest table. Defaults to 'manifest_1'
    """
    projects_sql = ', '.join([duckdb_con.cast_duckdb_uuid(pid) for pid in project_ids])

    assert_fks = [
        'subject_uuid',
        'project_uuid',
        'publisher_uuid',
        'predicate_uuid',
        'object_uuid',
        'observation_uuid',
        'attribute_group_uuid',
        'event_uuid',
        'language_uuid',
    ]
    i = 0
    assert_fk_sql = ''
    for fk in assert_fks:
        i += 1
        assert_fk_sql += f"""
        OR pm.uuid IN (
          SELECT DISTINCT a{i}.{fk}
          FROM {db_schema}.oc_all_assertions AS a{i}
          INNER JOIN {db_schema}.oc_all_manifest AS m{i} ON a{i}.subject_uuid = m{i}.uuid
          WHERE m{i}.project_uuid IN ({projects_sql})
          OR m{i}.uuid IN ({projects_sql})
          OR a{i}.project_uuid IN ({projects_sql})
        )
         """
    sql = f"""
    SELECT pm.uuid, pm.project_uuid, pm.publisher_uuid, pm.context_uuid, pm.item_class_uuid
    FROM {db_schema}.oc_all_manifest AS pm
    WHERE pm.project_uuid IN ({projects_sql})
    {assert_fk_sql}
    """
    print(sql)

    con.execute(f"DROP TABLE IF EXISTS {alias_temp_manifest}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias_temp_manifest} AS {sql}'
    con.execute(temp_table_sql)
    sql = f"""
            SELECT COUNT(uuid) AS count
            FROM {alias_temp_manifest} AS man
            WHERE 1=1
            """
    prog = con.sql(sql).fetchone()
    print(f'Inital number of manifest records used in projects: {prog[0]}') 


def gather_all_manifest_records_for_projects(
    project_ids,
    alias_temp_manifest='temp_manifest',
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA,
):
    start_temp_manifest_table(project_ids, con=con, db_schema=db_schema)
    # Get related objects to the temporary manifest table
    add_related_objs_to_temp_manifest(
        con=con, 
        db_schema=db_schema,
        alias_temp_manifest=alias_temp_manifest,
    )
    # Add space-time related records to the manifest
    add_space_time_related_manifest_records(
        project_ids=project_ids,
        con=con,
        db_schema=db_schema,
        alias_temp_manifest=alias_temp_manifest,
    )
    add_resources_related_manifest_records(
        project_ids=project_ids,
        con=con,
        db_schema=db_schema,
        alias_temp_manifest=alias_temp_manifest,  
    )
    # Finish off the related objects from the space-time table
    # and the reources table
    add_related_objs_to_temp_manifest(
        con=con, 
        db_schema=db_schema,
        alias_temp_manifest=alias_temp_manifest,
    )


def dump_assertions_for_projects(
    project_ids, 
    output_dir_path, 
    format='csv',
    alias_temp_assertions='temp_assertions',
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA,
):
    if format not in ['parquet', 'csv']:
        raise ValueError("Format must be either 'parquet' or 'csv'")
    if not os.path.exists(output_dir_path):
        os.makedirs(output_dir_path, exist_ok=True)
    
    projects_sql = ', '.join([duckdb_con.cast_duckdb_uuid(pid) for pid in project_ids])
    sql = f"""
    SELECT * FROM {db_schema}.oc_all_assertions
    WHERE project_uuid IN ({projects_sql})
    OR subject_uuid IN ({projects_sql})
    OR subject_uuid IN (
      SELECT m.uuid 
      FROM {db_schema}.oc_all_manifest AS m
      WHERE m.project_uuid IN ({projects_sql})
    )
    """
    con.execute(f"DROP TABLE IF EXISTS {alias_temp_assertions}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias_temp_assertions} AS {sql}'
    con.execute(temp_table_sql)
    sql = f"""
            SELECT COUNT(uuid) AS count
            FROM {alias_temp_assertions} AS tmp
            WHERE 1=1
            """
    prog = con.sql(sql).fetchone()
    print(f'Count assertion records from projects: {prog[0]}')
    filepath = os.path.join(output_dir_path, f"oc_all_assertions.{format}")
    print(f'Dumping {alias_temp_assertions} to {filepath}')
    con.execute(f"COPY (SELECT * FROM {alias_temp_assertions}) TO '{filepath}' ")
    con.execute(f"DROP TABLE IF EXISTS {alias_temp_assertions}")


def dump_other_tables_for_projects( 
    output_dir_path, 
    format='csv',
    alias_temp_manifest='temp_manifest',
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA,
):
    if format not in ['parquet', 'csv']:
        raise ValueError("Format must be either 'parquet' or 'csv'")
    if not os.path.exists(output_dir_path):
        os.makedirs(output_dir_path, exist_ok=True)

    table_configs = [
        ('oc_all_manifest', 'uuid',),
        ('oc_all_spacetime', 'item_uuid',),
        ('oc_all_resources', 'item_uuid',),
        ('oc_all_identifiers', 'item_uuid',),
    ]
    for table_name, key_field in table_configs:
        sql = f"""
        SELECT COUNT(uuid) AS count
        FROM {db_schema}.{table_name} AS oc
        WHERE oc.{key_field} IN (
            SELECT uuid FROM {alias_temp_manifest}
        )
        """
        prog = con.sql(sql).fetchone()
        print(f'Count {table_name} records from projects: {prog[0]}')
        filepath = os.path.join(output_dir_path, f"{table_name}.{format}")
        print(f'Dumping selected {table_name} to {filepath}')
        con.execute(f"COPY (SELECT * FROM {db_schema}.{table_name} AS oc WHERE oc.{key_field} IN (SELECT uuid FROM {alias_temp_manifest})) TO '{filepath}' ")



def dump_data_for_projects(
    project_ids, 
    output_dir_path, 
    format='csv',
    alias_temp_manifest='temp_manifest',
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA
):
    if format not in ['parquet', 'csv']:
        raise ValueError("Format must be either 'parquet' or 'csv'")
    if not os.path.exists(output_dir_path):
        os.makedirs(output_dir_path, exist_ok=True)
    
    dump_assertions_for_projects(
        project_ids=project_ids, 
        output_dir_path=output_dir_path, 
        format=format, 
        con=con, 
        db_schema=db_schema
    )
    gather_all_manifest_records_for_projects(
        project_ids=project_ids,
        alias_temp_manifest=alias_temp_manifest, 
        con=con, 
        db_schema=db_schema
    )
    dump_other_tables_for_projects(
        output_dir_path=output_dir_path, 
        format=format, 
        alias_temp_manifest=alias_temp_manifest, 
        con=con, 
        db_schema=db_schema
    )





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

