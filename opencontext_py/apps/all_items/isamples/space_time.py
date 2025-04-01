import copy
import duckdb
from duckdb.typing import *

from django.conf import settings



import uuid as GenUUID

import numpy as np
import pandas as pd

from django.db.models import Q, OuterRef, Subquery

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import hierarchy

from opencontext_py.apps.searcher.new_solrsearcher import db_entities
from opencontext_py.apps.searcher.new_solrsearcher import configs as search_configs


from opencontext_py.apps.all_items.isamples import duckdb_con
from opencontext_py.apps.all_items.isamples import utilities as duck_utils
from opencontext_py.apps.all_items.isamples import sample_sites


DB_CON = duckdb_con.create_duck_db_postgres_connection()



def make_new_context_table_from_old_context_table(
    con=DB_CON,
    db_schema=duckdb_con.DUCKDB_SCHEMA,
    alias='context',
):
    alias_old = f'{alias}_old'
    # Rename the old context table
    sql = f'ALTER TABLE {alias} RENAME TO {alias_old}'
    con.execute(sql)
    # Get the parent contexts of the old context table
    sql = f"""
    SELECT 
        {alias_old}.uuid,
        pm.label AS context_label,
        pm.uuid AS context_uuid
    FROM {db_schema}.oc_all_manifest AS m
    INNER JOIN {alias_old} ON m.uuid = {alias_old}.context_uuid
    INNER JOIN {db_schema}.oc_all_manifest AS pm ON pm.uuid = m.context_uuid
    WHERE m.context_uuid IS NOT NULL
    """
    con.execute(f"DROP TABLE IF EXISTS {alias}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias} AS {sql}'
    con.execute(temp_table_sql)
    # Drop the old contexts table
    con.execute(f"DROP TABLE IF EXISTS {alias_old}")



def make_first_temp_context_table(
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE, 
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA, 
    alias='context'
):
    """Create a temporary table with project path levels"""
    sql = f"""
    SELECT
        {man_table}.uuid,
        pm.label AS context_label,
       {man_table}.context_uuid
    FROM {man_table}
    INNER JOIN {db_schema}.oc_all_manifest AS pm ON pm.uuid = {man_table}.context_uuid
    WHERE ({man_table}.item__geo_source IS NULL) OR ({man_table}.item__chrono_source IS NULL)
    """
    con.execute(f"DROP TABLE IF EXISTS {alias}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias} AS {sql}'
    con.execute(temp_table_sql)
    

def update_sample_from_context_geo(
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE, 
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA
):
    """Update the sample manifest with the geo information specific to a given sample record"""

    sql = f"""
    UPDATE {man_table}
    SET item__latitude = spt.latitude,
        item__longitude = spt.longitude,
        item__geometry_type = spt.geometry_type,
        item__geo_specificity = spt.geo_specificity,
        item__geo_source = concat('Inferred from: ', context.context_label),
        item__geo_source_uri = concat('https://opencontext.org/subjects/', context.context_uuid)
    FROM {db_schema}.oc_all_spacetime AS spt
    INNER JOIN context ON context.context_uuid = spt.item_uuid
    WHERE {man_table}.item__geo_source IS NULL
    AND {man_table}.uuid = context.uuid
    AND context.context_uuid = spt.item_uuid
    AND spt.latitude IS NOT NULL
    AND spt.longitude IS NOT NULL
    """
    con.execute(sql)


def update_sample_from_context_chrono(
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE, 
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA
):
    """Update the sample manifest with the chrono information specific to a given sample record"""

    sql = f"""
    UPDATE {man_table}
    SET item__earliest = spt.earliest,
        item__latest = spt.latest,
        item__chrono_source = concat('Inferred from: ', context.context_label),
        item__chrono_source_uri = concat('https://opencontext.org/subjects/', context.context_uuid)
    FROM {db_schema}.oc_all_spacetime AS spt
    INNER JOIN context ON context.context_uuid = spt.item_uuid
    WHERE {man_table}.item__chrono_source IS NULL
    AND {man_table}.uuid = context.uuid
    AND spt.earliest IS NOT NULL
    AND spt.latest IS NOT NULL
    """
    con.execute(sql)


def update_sample_specific_geo(
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE, 
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA
):
    """Update the sample manifest with the geo information specific to a given sample record"""

    sql = f"""
    UPDATE {man_table}
    SET item__latitude = spt.latitude,
        item__longitude = spt.longitude,
        item__geometry_type = spt.geometry_type,
        item__geo_specificity = spt.geo_specificity,
        item__geo_source = concat('Given for: ', {man_table}.label),
        item__geo_source_uri = {man_table}.uri
    FROM {db_schema}.oc_all_spacetime AS spt
    WHERE {man_table}.item__geo_source IS NULL
    AND {man_table}.uuid = spt.item_uuid
    AND spt.latitude IS NOT NULL
    AND spt.longitude IS NOT NULL
    """
    con.execute(sql)


def update_sample_specific_chrono(
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE, 
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA
):
    """Update the sample manifest with the chrono information specific to a given sample record"""

    sql = f"""
    UPDATE {man_table}
    SET item__earliest = spt.earliest,
        item__latest = spt.latest,
        item__chrono_source = concat('Given for: ', {man_table}.label),
        item__chrono_source_uri = {man_table}.uri
    FROM {db_schema}.oc_all_spacetime AS spt
    WHERE {man_table}.item__chrono_source IS NULL
    AND {man_table}.uuid = spt.item_uuid
    AND spt.earliest IS NOT NULL
    AND spt.latest IS NOT NULL
    """
    con.execute(sql)



def update_geo_chrono_for_context(con=DB_CON, db_schema=duckdb_con.DUCKDB_SCHEMA):
    """Update the sample manifest with the geo and chrono information for a given path level"""

    # Check to make sure there are records to process
    sql = 'SELECT COUNT(uuid) FROM context'
    count = con.sql(sql).fetchone()
    if count[0] == 0:
        return None
    
    # Update the sample manifest with the geo information for a given path level
    update_sample_from_context_geo(con=con, db_schema=db_schema)

    # Update the sample manifest with the chrono information for a given path level
    update_sample_from_context_chrono(con=con, db_schema=db_schema)

    # Set up the context table for the next loop (more general) context
    make_new_context_table_from_old_context_table(con=con, db_schema=db_schema)
    return True


def get_isamples_spacetime_values(
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA, 
    show_progress=True,
):
    """Add sampling site information to the iSamples manifest dataframe"""

    # Add the geo information specific to a given sample record
    update_sample_specific_geo(con=con, db_schema=db_schema)
    # Add the chrono information specific to a given sample record
    update_sample_specific_chrono(con=con, db_schema=db_schema)

    # Make the first context table
    make_first_temp_context_table(con=con)

    act_path_level = sample_sites.SAMPLE_SITE_MAX_PATH_LEVEL + 1
    while act_path_level > 0:
        act_path_level -= 1
        if act_path_level == 0:
            break
        # We're going from the most specific to the most general.
        ok_continue = update_geo_chrono_for_context(con=con, db_schema=db_schema)
        if not ok_continue:
            print(f'No more context records to process at level {act_path_level}')
            break

        if show_progress:
            sql = f"""
            SELECT COUNT(uuid) AS count
            FROM {man_table} AS man
            WHERE man.item__geo_source IS NOT NULL
            """
            prog = con.sql(sql).fetchone()
            print(f'Records with geo-spatial data at level {act_path_level}: {prog[0]}') 
        