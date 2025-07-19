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


from opencontext_py.libs import duckdb_con
from opencontext_py.apps.all_items.isamples import utilities as duck_utils


DB_CON = duckdb_con.create_duck_db_postgres_connection()

REGION_CLASS_MAN_OBJS = AllManifest.objects.filter(
    slug='oc-gen-cat-region',
    item_type='class',
)
SITE_CLASS_MAN_OBJS = AllManifest.objects.filter(
    slug__in=search_configs.ISAMPLES_SAMPLING_SITE_ITEM_CLASS_SLUGS,
    item_type='class',
)

SAMPLE_SITE_MAX_PATH_LEVEL = 7


def make_project_path_level_temp_table(
    path_level, 
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
    alias='proj_path_level',
    con=DB_CON,
):
    """Create a temporary table with project path levels"""
    sql = f"""
    SELECT DISTINCT 
        project_uuid, 
        man.path_to___{path_level} AS act_path
    FROM {man_table} AS man
    WHERE man.isam_sampling_site_uri IS NULL
    """
    con.execute(f"DROP TABLE IF EXISTS {alias}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias} AS {sql}'
    con.execute(temp_table_sql)


def make_temp_region_table(
    more_where_clauses=None,
    alias='regions',
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA,
):
    """Create a temporary table with iSamples regions"""
    where_clauses = []
    if isinstance(more_where_clauses, list):
        where_clauses.extend(more_where_clauses)

    where_clauses.append("proj_path_level.act_path IS NOT NULL")
    where_clauses.append("m.item_type = 'subjects'")

    # No results for items flagged as 'do not index'
    no_index_subj_clause = "m.meta_json::text NOT LIKE '%\"flag_do_not_index\": true,%'"
    where_clauses.append(no_index_subj_clause)

    # Make sure we have the iSamples region item classes
    ok_class_uuids = REGION_CLASS_MAN_OBJS.values_list('uuid', flat=True)
    duck_class_uuids = [duck_utils.cast_duckdb_uuid(m) for m in ok_class_uuids]
    class_list = ', '.join(duck_class_uuids)
    class_clause = f"m.item_class_uuid IN ({class_list})"
    where_clauses.append(class_clause)
    where_conditions = ' AND '.join(where_clauses)

    sql = f"""
    SELECT 
        proj_path_level.project_uuid,
        proj_path_level.act_path,
        m.label,
        m.uri,
        'region' AS item_class_label,
        m.uuid
    FROM proj_path_level
    INNER JOIN {db_schema}.oc_all_manifest AS m ON proj_path_level.act_path = m.path 
    WHERE {where_conditions}
    """
    con.execute(f"DROP TABLE IF EXISTS {alias}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias} AS {sql}'
    con.execute(temp_table_sql)


def make_temp_site_table(
    more_where_clauses=None, 
    alias='sites',
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA, 
):
    """Create a temporary table with iSamples sampling sites"""

    where_clauses = []
    if isinstance(more_where_clauses, list):
        where_clauses.extend(more_where_clauses)

    where_clauses.append("proj_path_level.act_path IS NOT NULL")
    where_clauses.append("m.item_type = 'subjects'")

    # No results for items flagged as 'do not index'
    no_index_subj_clause = "m.meta_json::text NOT LIKE '%\"flag_do_not_index\": true,%'"
    where_clauses.append(no_index_subj_clause)

    # No results for projects where we want to omit sampling sites.
    omit_site_proj_clause = "proj.meta_json::text NOT LIKE '%\"omit_db_sampling_site\": true,%'"
    where_clauses.append(omit_site_proj_clause)

    # Make sure we have the iSamples sampling site item classes
    ok_class_uuids = SITE_CLASS_MAN_OBJS.values_list('uuid', flat=True)
    duck_class_uuids = [duck_utils.cast_duckdb_uuid(m) for m in ok_class_uuids]
    class_list = ', '.join(duck_class_uuids)
    class_clause = f"m.item_class_uuid IN ({class_list})"
    where_clauses.append(class_clause)

    where_conditions = ' AND '.join(where_clauses)

    sql = f"""
    SELECT 
        proj_path_level.project_uuid,
        proj_path_level.act_path,
        m.label,
        m.uri,
        'site' AS item_class_label,
        m.uuid
    FROM proj_path_level
    INNER JOIN {db_schema}.oc_all_manifest AS m ON proj_path_level.act_path = m.path 
    INNER JOIN {db_schema}.oc_all_manifest AS proj ON proj_path_level.project_uuid = proj.uuid
    WHERE {where_conditions}
    """
    con.execute(f"DROP TABLE IF EXISTS {alias}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias} AS {sql}'
    con.execute(temp_table_sql)


def update_regions_for_path_level(
    path_level, 
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
    con=DB_CON
):
    """Update the sampling site with a region item for a specific path level"""
    path_field = f'path_to___{path_level}'
    
    # Update the manifest table with the region information
    sql = f"""
    UPDATE {man_table}
    SET isam_sampling_site_label = regions.label,
        isam_sampling_site_type = regions.item_class_label,
        isam_sampling_site_uri = concat('https://', regions.uri)
    FROM regions
    WHERE {man_table}.isam_sampling_site_uri IS NULL
    AND {man_table}.{path_field} = regions.act_path
    AND {man_table}.project_uuid = regions.project_uuid
    AND regions.uri IS NOT NULL
    """
    con.execute(sql)


def update_sites_for_path_level(
    path_level, 
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
    con=DB_CON
):
    """Update the sampling site with a site item a specific path level"""
    path_field = f'path_to___{path_level}'
    
    # Update the manifest table with the site information
    sql = f"""
    UPDATE {man_table}
    SET isam_sampling_site_label = sites.label,
        isam_sampling_site_type = sites.item_class_label,
        isam_sampling_site_uri = concat('https://', sites.uri)
    FROM sites
    WHERE {man_table}.isam_sampling_site_uri IS NULL
    AND {man_table}.{path_field} = sites.act_path
    AND {man_table}.project_uuid = sites.project_uuid
    AND sites.uri IS NOT NULL
    """
    con.execute(sql)


def update_region_sites_for_path_level(path_level, con=DB_CON, db_schema=duckdb_con.DUCKDB_SCHEMA):
    """Update the sampling site information for a specific path level"""
    
    # Make the temporary table for the path level
    make_project_path_level_temp_table(path_level, con=con)

    # Make the temporary table for the sites at this path level
    make_temp_site_table(con=con, db_schema=db_schema)

    # Make the temporary table for the regions at this path level
    make_temp_region_table(con=con, db_schema=db_schema)

    # Update sites first, since those are preferred over regions.
    update_sites_for_path_level(path_level, con=con)

    # Where we don't have a site found yet, update to use regions at this path level
    update_regions_for_path_level(path_level, con=con)
    

def cleanup_temporary_tables(con=DB_CON):
    """Cleanup temporary tables"""
    # Save a little memory!
    temp_tables = ['proj_path_level', 'sites', 'regions']
    for table in temp_tables:
        con.execute(f"DROP TABLE IF EXISTS {table}")


def get_isamples_sampling_sites(
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE, 
    con=DB_CON, 
    show_progress=True,
):
    """Add sampling site information to the iSamples manifest dataframe"""

    act_path_level = SAMPLE_SITE_MAX_PATH_LEVEL + 1
    while act_path_level > 0:
        act_path_level -= 1
        if act_path_level == 0:
            break
        # We're going from the most specific to the most general.
        update_region_sites_for_path_level(act_path_level, con=con)
        if show_progress:
            sql = f"""
            SELECT COUNT(uuid) AS count
            FROM {man_table}
            WHERE isam_sampling_site_uri IS NOT NULL
            """
            prog = con.sql(sql).fetchone()
            print(f'Records with sampling sites at level {act_path_level}: {prog[0]}') 
    # Tidy up our temporary tables...
    cleanup_temporary_tables(con=con)