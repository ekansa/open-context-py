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
from opencontext_py.apps.all_items.isamples.create_df import add_isamples_sampling_sites_cols

"""
# Testing
import importlib
from opencontext_py.apps.all_items.isamples import duckdb_con
from opencontext_py.apps.all_items.isamples import query as isam_query
importlib.reload(isam_query)

import time

start = time.time()
db_m = isam_query.get_isamples_raw_manifest()
# db_r = isam_query.get_isamples_raw_asserts()
end = time.time()
print(end-start)

start = time.time()
isam_query.get_isamples_sampling_sites()
end = time.time()
print(end-start)


start = time.time()
df_m = isam_query.make_df_isamples_sampling_sites(db_m)
end = time.time()
print(end-start)

"""

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


def get_isamples_item_classes():
    """Get all item-class manifest objects related to iSamples records"""
    m_qs = AllManifest.objects.filter(
        item_type='class',
        slug__in=search_configs.ISAMPLES_DEFAULT_CLASS_SLUGS,
    )
    isamples_item_classes = []
    for man_obj in m_qs:
        m_children = hierarchy.get_list_concept_children_recursive(man_obj)
        if man_obj not in isamples_item_classes:
            isamples_item_classes.append(man_obj)
        for child_obj in m_children:
            if child_obj not in isamples_item_classes:
                isamples_item_classes.append(child_obj)
    return isamples_item_classes


def cast_duckdb_uuid(uuid):
    """Convert a manifest object to a DuckDB compatible UUID string"""
    return f"CAST('{str(uuid)}' AS UUID)"


def cast_man_obj_duckdb_uuid(man_obj):
    """Convert a manifest object to a DuckDB compatible UUID string"""
    return cast_duckdb_uuid(man_obj.uuid)


def get_path_level_item(path: str, level: int) -> str:
    if not path:
        return None
    path_list = path.split('/')
    if level >= len(path_list):
        return None
    return path_list[level]


def get_path_upto_level(path: str, level: int) -> str:
    if not path:
        return None
    path_list = path.split('/')
    level += 1
    if level > len(path_list):
        return None
    return '/'.join(path_list[:level])


def make_isamples_manifest_query_sql(more_where_clauses=None, db_schema=duckdb_con.DUCKDB_SCHEMA):
    """Create a SQL query string to get iSamples manifests"""
    
    duck_thumb_uuid = cast_duckdb_uuid(configs.OC_RESOURCE_THUMBNAIL_UUID)
    
    where_clauses = []
    if isinstance(more_where_clauses, list):
        where_clauses.extend(more_where_clauses)

    where_clauses.append("m.item_type = 'subjects'")

    # No results for items flagged as 'do not index'
    no_index_subj_clause = "m.meta_json::text NOT LIKE '%\"flag_do_not_index\": true,%'"
    no_index_proj_clause = "proj.meta_json::text NOT LIKE '%\"flag_do_not_index\": true,%'"
    where_clauses.append(no_index_subj_clause)
    where_clauses.append(no_index_proj_clause)

     # Add the where clause for the iSamples item classes
    isamples_item_classes = get_isamples_item_classes()
    duck_class_uuids = [cast_man_obj_duckdb_uuid(m) for m in isamples_item_classes]
    class_list = ', '.join(duck_class_uuids)
    class_clause = f"m.item_class_uuid IN ({class_list})"
    where_clauses.append(class_clause)

    # Add path levels to a desired depth.
    path_level_fields = []
    for i in range(SAMPLE_SITE_MAX_PATH_LEVEL):
        path_level_fields.append(f"get_path_upto_level(m.path, {i}) AS path_to___{i+1}")
    if len(path_level_fields) > 0:
        path_level_fields_sql = ', \n'.join(path_level_fields) + ', '
    else:
        path_level_fields_sql = ''


    where_conditions = ' AND '.join(where_clauses)

    sql = f"""
    SELECT
        m.uuid,
        m.slug,
        m.label,
        m.sort,
        m.published,
        m.revised,
        m.updated,
        m.uri,
        m.path,
        m.hash_id,
        m.context_uuid,
        m.item_class_uuid,
        m.project_uuid,
        m.meta_json,

    -- Subquery for object_thumbnail
    (
        SELECT r.uri 
        FROM {db_schema}.oc_all_resources r 
        WHERE r.item_uuid = m.uuid 
        AND r.resourcetype_uuid = {duck_thumb_uuid} 
        ORDER BY r.item_uuid ASC, r.rank ASC, r.resourcetype_uuid ASC 
        LIMIT 1
    ) AS object_thumbnail,

    -- Subqueries for persistent identifiers
    (
        SELECT i.id 
        FROM {db_schema}.oc_all_identifiers i 
        WHERE i.item_uuid = m.uuid 
        AND i.scheme = 'doi' 
        ORDER BY i.item_uuid ASC, i.rank ASC, i.scheme ASC 
        LIMIT 1
    ) AS persistent_doi,

    (
        SELECT i.id 
        FROM {db_schema}.oc_all_identifiers i 
        WHERE i.item_uuid = m.uuid 
        AND i.scheme = 'ark' 
        ORDER BY i.item_uuid ASC, i.rank ASC, i.scheme ASC 
        LIMIT 1
    ) AS persistent_ark,

    NULL AS persistent_orcid,

    -- Path upto levels
    {path_level_fields_sql}

    NULL as isam_sampling_site_label,
    NULL as isam_sampling_site_uri


    FROM {db_schema}.oc_all_manifest AS m
    INNER JOIN {db_schema}.oc_all_manifest proj ON m.project_uuid = proj.uuid
    WHERE {where_conditions}
    """
    return sql


def make_isamples_assertion_query_sql(more_where_clauses=None, db_schema=duckdb_con.DUCKDB_SCHEMA):
    """Create a SQL query string to get iSamples assertions"""
    where_clauses = []
    if isinstance(more_where_clauses, list):
        where_clauses.extend(more_where_clauses)

    where_clauses.append("a.visible = TRUE")
    where_clauses.append("subj.item_type = 'subjects'")

    # No containment assertions
    duck_contain_pred = cast_duckdb_uuid(configs.PREDICATE_CONTAINS_UUID)
    where_clauses.append(f"a.predicate_uuid <> {duck_contain_pred}")

    # Limit to query results referencing named entities
    where_clauses.append(f"a.object_uuid IS NOT NULL")

    # Add the where clause for the iSamples item classes
    isamples_item_classes = get_isamples_item_classes()
    duck_class_uuids = [cast_man_obj_duckdb_uuid(m) for m in isamples_item_classes]
    class_list = ', '.join(duck_class_uuids)
    class_clause = f"subj.item_class_uuid IN ({class_list})"
    where_clauses.append(class_clause)

    # No results for items flagged as 'do not index'
    no_index_subj_clause = "subj.meta_json::text NOT LIKE '%\"flag_do_not_index\": true,%'"
    no_index_proj_clause = "proj.meta_json::text NOT LIKE '%\"flag_do_not_index\": true,%'"
    where_clauses.append(no_index_subj_clause)
    where_clauses.append(no_index_proj_clause)

    where_conditions = ' AND '.join(where_clauses)

    sql = f"""
    SELECT
        a.uuid, 
        a.publisher_uuid, 
        a.project_uuid, 
        a.source_id, 
        a.subject_uuid, 
        a.observation_uuid, 
        a.obs_sort, 
        a.event_uuid, 
        a.event_sort, 
        a.attribute_group_uuid, 
        a.attribute_group_sort, 
        a.predicate_uuid, 
        a.sort, 
        a.visible, 
        a.certainty, 
        a.object_uuid, 
        a.language_uuid, 
        a.obj_string_hash, 
        a.obj_string, 
        a.obj_boolean, 
        a.obj_integer, 
        a.obj_double, 
        a.obj_datetime, 
        a.created, 
        a.updated, 
        a.meta_json,

            -- Predicate Equivalent Label and URI
    (
        SELECT m.label 
        FROM {db_schema}.oc_all_assertions asr 
        INNER JOIN {db_schema}.oc_all_manifest m ON asr.object_uuid = m.uuid 
        INNER JOIN {db_schema}.oc_all_manifest ctx ON m.context_uuid = ctx.uuid 
        WHERE m.item_type IN ('class', 'property', 'uri') 
        AND asr.predicate_uuid IN (
            CAST('00000000-2470-aa02-9342-e9d5b2ed3149' AS UUID), 
            CAST('00000000-081a-dc93-af22-4cbcca550517' AS UUID), 
            CAST('00000000-081a-1d47-f617-1699079819cf' AS UUID)
        ) 
        AND asr.subject_uuid = a.predicate_uuid 
        AND asr.visible 
        AND (m.meta_json::text NOT LIKE '%\"deprecated\": true,%') 
        AND (ctx.meta_json::text NOT LIKE '%\"deprecated\": true,%') 
        AND asr.object_uuid NOT IN (
            CAST('00000000-ed50-3cf1-c266-683c89afdac4' AS UUID), 
            CAST('00000000-ed50-8ee5-c7a2-21a012593f25' AS UUID)
        ) 
        ORDER BY asr.sort ASC 
        LIMIT 1
    ) AS predicate_equiv_ld_label,

    (
        SELECT m.uri 
        FROM {db_schema}.oc_all_assertions asr 
        INNER JOIN {db_schema}.oc_all_manifest m ON asr.object_uuid = m.uuid 
        INNER JOIN {db_schema}.oc_all_manifest ctx ON m.context_uuid = ctx.uuid 
        WHERE m.item_type IN ('class', 'property', 'uri') 
        AND asr.predicate_uuid IN (
            CAST('00000000-2470-aa02-9342-e9d5b2ed3149' AS UUID), 
            CAST('00000000-081a-dc93-af22-4cbcca550517' AS UUID), 
            CAST('00000000-081a-1d47-f617-1699079819cf' AS UUID)
        ) 
        AND asr.subject_uuid = a.predicate_uuid 
        AND asr.visible 
        AND (m.meta_json::text NOT LIKE '%\"deprecated\": true,%') 
        AND (ctx.meta_json::text NOT LIKE '%\"deprecated\": true,%')  
        AND asr.object_uuid NOT IN (
            CAST('00000000-ed50-3cf1-c266-683c89afdac4' AS UUID), 
            CAST('00000000-ed50-8ee5-c7a2-21a012593f25' AS UUID)
        ) 
        ORDER BY asr.sort ASC 
        LIMIT 1
    ) AS predicate_equiv_ld_uri

    FROM {db_schema}.oc_all_assertions AS a
    INNER JOIN {db_schema}.oc_all_manifest subj ON a.subject_uuid = subj.uuid
    INNER JOIN {db_schema}.oc_all_manifest proj ON a.project_uuid = proj.uuid
    WHERE {where_conditions};
    """
    return sql


def get_isamples_raw_manifest(more_where_clauses=None, con=DB_CON, alias='man'):
    """Create a DuckDB connection to a PostgreSQL database"""
    sql = make_isamples_manifest_query_sql(more_where_clauses=more_where_clauses)
    con.create_function(
        "get_path_level_item", 
        get_path_level_item, 
        [VARCHAR, BIGINT], VARCHAR, 
        null_handling="special"
    )
    con.create_function(
        "get_path_upto_level", 
        get_path_upto_level, 
        [VARCHAR, BIGINT], VARCHAR, 
        null_handling="special"
    )
    con.execute(f"DROP TABLE IF EXISTS {alias}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias} AS {sql}'
    con.execute(temp_table_sql)
    # Make sure the sampling site columns are VARCHAR
    sql = f"ALTER TABLE {alias} ALTER isam_sampling_site_label TYPE VARCHAR;"
    con.execute(sql)
    sql = f"ALTER TABLE {alias} ALTER isam_sampling_site_uri TYPE VARCHAR;"
    con.execute(sql)
    db_m = con.sql(f'SELECT * FROM {alias}').set_alias(alias)
    db_m.show()
    return db_m


def get_isamples_raw_asserts(more_where_clauses=None, con=DB_CON, alias='asserts'):
    """Create a DuckDB connection to a PostgreSQL database"""
    sql = make_isamples_assertion_query_sql(more_where_clauses=more_where_clauses)
    db_r = con.sql(sql).set_alias(alias)
    db_r.show()
    return db_r


def get_distinct_subject_uuids(db_r, con=DB_CON, alias='subjects'):
    """Get distinct subject UUIDs from the DuckDB query results"""
    db_s = db_r.aggregate("subject_uuid").set_alias(alias)
    return db_s


def make_project_path_level_temp_table(path_level, con=DB_CON, alias='proj_path_level'):
    """Create a temporary table with project path levels"""
    sql = f"""
    SELECT DISTINCT 
        project_uuid, 
        path_to___{path_level} AS act_path
    FROM man
    WHERE man.isam_sampling_site_uri IS NULL
    """
    con.execute(f"DROP TABLE IF EXISTS {alias}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias} AS {sql}'
    con.execute(temp_table_sql)


def make_temp_region_table(more_where_clauses=None, con=DB_CON, db_schema=duckdb_con.DUCKDB_SCHEMA, alias='regions'):
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
    duck_class_uuids = [cast_duckdb_uuid(m) for m in ok_class_uuids]
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
        m.uuid
    FROM proj_path_level
    INNER JOIN {db_schema}.oc_all_manifest AS m ON proj_path_level.act_path = m.path 
    WHERE {where_conditions}
    """
    con.execute(f"DROP TABLE IF EXISTS {alias}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias} AS {sql}'
    con.execute(temp_table_sql)


def make_temp_site_table(more_where_clauses=None, con=DB_CON, db_schema=duckdb_con.DUCKDB_SCHEMA, alias='sites'):
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
    duck_class_uuids = [cast_duckdb_uuid(m) for m in ok_class_uuids]
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
        m.uuid
    FROM proj_path_level
    INNER JOIN {db_schema}.oc_all_manifest AS m ON proj_path_level.act_path = m.path 
    INNER JOIN {db_schema}.oc_all_manifest AS proj ON proj_path_level.project_uuid = proj.uuid 
    WHERE {where_conditions}
    """
    con.execute(f"DROP TABLE IF EXISTS {alias}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias} AS {sql}'
    con.execute(temp_table_sql)


def update_regions_for_path_level(path_level, con=DB_CON, db_schema=duckdb_con.DUCKDB_SCHEMA):
    """Update the sampling site with a region item for a specific path level"""
    path_field = f'path_to___{path_level}'
    
    # Update the manifest table with the region information
    sql = f"""
    UPDATE man
    SET isam_sampling_site_label = regions.label,
        isam_sampling_site_uri = regions.uri
    FROM regions
    WHERE man.isam_sampling_site_uri IS NULL
    AND man.{path_field} = regions.act_path
    AND man.project_uuid = regions.project_uuid
    AND regions.uri IS NOT NULL
    """
    con.execute(sql)


def update_sites_for_path_level(path_level, con=DB_CON, db_schema=duckdb_con.DUCKDB_SCHEMA):
    """Update the sampling site with a site item a specific path level"""
    path_field = f'path_to___{path_level}'
    
    # Update the manifest table with the site information
    sql = f"""
    UPDATE man
    SET isam_sampling_site_label = sites.label,
        isam_sampling_site_uri = sites.uri
    FROM sites
    WHERE man.isam_sampling_site_uri IS NULL
    AND man.{path_field} = sites.act_path
    AND man.project_uuid = sites.project_uuid
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
    update_sites_for_path_level(path_level, con=con, db_schema=db_schema)

    # Where we don't have a site found yet, update to use regions at this path level
    update_regions_for_path_level(path_level, con=con, db_schema=db_schema)
    


def get_isamples_sampling_sites(con=DB_CON, show_progress=True):
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
            FROM man
            WHERE isam_sampling_site_uri IS NOT NULL
            """
            prog = con.sql(sql).fetchone()
            print(f'Records with sampling sites at level {act_path_level}: {prog[0]}') 
        