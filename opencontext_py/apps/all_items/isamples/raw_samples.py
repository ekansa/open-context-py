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
from opencontext_py.apps.all_items.isamples import sample_sites


DB_CON = duckdb_con.create_duck_db_postgres_connection()

ADDED_FIELDS_DATA_TYPES = [
    ('isam_sampling_site_label', 'VARCHAR'),
    ('isam_sampling_site_type', 'VARCHAR'),
    ('isam_sampling_site_uri', 'VARCHAR'),
    ('item__geo_source', 'VARCHAR'),
    ('item__geo_source_uri', 'VARCHAR'),
    ('item__geometry_type', 'VARCHAR'),
    ('item__geo_specificity', 'BIGINT'),
    ('item__latitude', 'DOUBLE'),
    ('item__longitude', 'DOUBLE'),
    ('item__earliest', 'DOUBLE'),
    ('item__latest', 'DOUBLE'),
    ('item__chrono_source', 'VARCHAR'),
    ('item__chrono_source_uri', 'VARCHAR'),
    # For iSamples vocabularies
    ('isam_msamp_object_type', 'VARCHAR'),
    ('isam_msamp_material_type', 'VARCHAR'),
]

HUMAN_SUBJECT_CLASS_UUID = '00000000-6e24-babc-3eb9-95e716e400e6'


def get_isamples_item_classes():
    """Get all item-class manifest objects related to iSamples records"""
    m_qs = AllManifest.objects.filter(
        item_type='class',
        slug__in=search_configs.ISAMPLES_DEFAULT_CLASS_SLUGS,
    )
    isamples_item_classes = []
    for man_obj in m_qs:
        m_children = hierarchy.get_list_concept_children_recursive(man_obj)
        if str(man_obj.uuid) != HUMAN_SUBJECT_CLASS_UUID and man_obj not in isamples_item_classes:
            isamples_item_classes.append(man_obj)
        for child_obj in m_children:
            if str(child_obj.uuid) == HUMAN_SUBJECT_CLASS_UUID:
                continue
            if child_obj not in isamples_item_classes:
                isamples_item_classes.append(child_obj)
    return isamples_item_classes


def make_isamples_manifest_query_sql(more_where_clauses=None, db_schema=duckdb_con.DUCKDB_SCHEMA):
    """Create a SQL query string to get iSamples manifests"""
    
    duck_thumb_uuid = duck_utils.cast_duckdb_uuid(configs.OC_RESOURCE_THUMBNAIL_UUID)
    
    where_clauses = []
    if isinstance(more_where_clauses, list):
        where_clauses.extend(more_where_clauses)

    where_clauses.append("m.item_type = 'subjects'")
    where_clauses.append(f"m.item_class_uuid <> '{HUMAN_SUBJECT_CLASS_UUID}'")

    # No results for items flagged as 'do not index'
    no_index_subj_clause = "m.meta_json::text NOT LIKE '%\"flag_do_not_index\": true,%'"
    no_index_proj_clause = "proj.meta_json::text NOT LIKE '%\"flag_do_not_index\": true,%'"
    where_clauses.append(no_index_subj_clause)
    where_clauses.append(no_index_proj_clause)

     # Add the where clause for the iSamples item classes
    isamples_item_classes = get_isamples_item_classes()
    duck_class_uuids = [duck_utils.cast_man_obj_duckdb_uuid(m) for m in isamples_item_classes]
    class_list = ', '.join(duck_class_uuids)
    class_clause = f"m.item_class_uuid IN ({class_list})"
    where_clauses.append(class_clause)

    # Add path levels to a desired depth.
    path_level_fields = []
    for i in range(sample_sites.SAMPLE_SITE_MAX_PATH_LEVEL):
        path_level_fields.append(f"get_path_upto_level(m.path, {i}) AS path_to___{i+1}")
    if len(path_level_fields) > 0:
        path_level_fields_sql = ', \n'.join(path_level_fields) + ', '
    else:
        path_level_fields_sql = ''

    # Add fields populated with null values
    null_fields = [f'NULL AS {field}' for field, _ in ADDED_FIELDS_DATA_TYPES]
    null_fields_sql = ', \n'.join(null_fields)


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
        m.indexed,
        concat('https://', m.uri) AS uri,
        m.path,
        m.context_uuid,
        m.item_class_uuid,
        ic.label AS item_class_label,
        concat('https://', ic.uri) AS item_class_uri,
        m.project_uuid,
        proj.label AS project_label,
        concat('https://', proj.uri) AS project_uri,
        m.meta_json,
    
    -- Subquery for assertion updated
    (
        SELECT a.updated
        FROM {db_schema}.oc_all_assertions AS a 
        WHERE a.subject_uuid = m.uuid 
        ORDER BY a.updated DESC 
        LIMIT 1
    ) AS assertion_updated,

    -- Subquery for object_thumbnail
    (
        SELECT concat('https://', r.uri)
        FROM {db_schema}.oc_all_assertions AS a
        INNER JOIN {db_schema}.oc_all_resources r ON (
            a.object_uuid = r.item_uuid
        )
        WHERE a.subject_uuid = m.uuid 
        AND r.resourcetype_uuid = {duck_thumb_uuid} 
        ORDER BY a.sort ASC, r.rank ASC, r.resourcetype_uuid ASC 
        LIMIT 1
    ) AS object_thumbnail,

    -- Subqueries for persistent identifiers
    (
        SELECT concat('doi:', i.id) 
        FROM {db_schema}.oc_all_identifiers i 
        WHERE i.item_uuid = m.uuid 
        AND i.scheme = 'doi' 
        ORDER BY i.item_uuid ASC, i.rank ASC, i.scheme ASC 
        LIMIT 1
    ) AS persistent_doi,

    (
        SELECT concat('ark:/', i.id) 
        FROM {db_schema}.oc_all_identifiers i 
        WHERE i.item_uuid = m.uuid 
        AND i.scheme = 'ark' 
        ORDER BY i.item_uuid ASC, i.rank ASC, i.scheme ASC 
        LIMIT 1
    ) AS persistent_ark,

    -- Subqueries for persistent identifiers
    (
        SELECT concat('doi:', i.id) 
        FROM {db_schema}.oc_all_identifiers i 
        WHERE i.item_uuid = proj.uuid 
        AND i.scheme = 'doi' 
        ORDER BY i.item_uuid ASC, i.rank ASC, i.scheme ASC 
        LIMIT 1
    ) AS project_persistent_doi,

    (
        SELECT concat('ark:/', i.id) 
        FROM {db_schema}.oc_all_identifiers i 
         WHERE i.item_uuid = proj.uuid
        AND i.scheme = 'ark' 
        ORDER BY i.item_uuid ASC, i.rank ASC, i.scheme ASC 
        LIMIT 1
    ) AS project_persistent_ark,

    NULL AS persistent_orcid,

    -- Path upto levels
    {path_level_fields_sql}

    -- Null fields for added fields needed for iSamples export
    {null_fields_sql}


    FROM {db_schema}.oc_all_manifest AS m
    INNER JOIN {db_schema}.oc_all_manifest proj ON m.project_uuid = proj.uuid
    INNER JOIN {db_schema}.oc_all_manifest ic ON m.item_class_uuid = ic.uuid
    WHERE {where_conditions}
    """
    return sql


def make_isamples_assertion_query_sql(
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
    more_where_clauses=None, 
    db_schema=duckdb_con.DUCKDB_SCHEMA,
):
    """Create a SQL query string to get iSamples assertions"""
    where_clauses = []
    if isinstance(more_where_clauses, list):
        where_clauses.extend(more_where_clauses)

    where_clauses.append("a.visible = TRUE")

    # No containment assertions
    duck_contain_pred = duck_utils.cast_duckdb_uuid(configs.PREDICATE_CONTAINS_UUID)
    where_clauses.append(f"a.predicate_uuid <> {duck_contain_pred}")

    # Limit to query results referencing named entities
    where_clauses.append(f"a.object_uuid IS NOT NULL")


    where_conditions = ' AND '.join(where_clauses)

    sql = f"""
    SELECT
        a.uuid,  
        a.subject_uuid, 
        a.obs_sort, 
        a.event_sort, 
        a.attribute_group_sort, 
        a.predicate_uuid, 
        a.sort, 
        a.object_uuid,
        pred.label AS predicate_label,
        concat('https://', pred.uri) AS predicate_uri,
        obj.label AS object_label,
        concat('https://', obj.uri) AS object_uri,
        obj.item_type AS object_item_type,
        0 AS obj_count, 
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
        SELECT concat('https://', m.uri)
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
    ) AS predicate_equiv_ld_uri,

    -- Object Equivalent Label and URI
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
        AND asr.subject_uuid = a.object_uuid 
        AND asr.visible 
        AND (m.meta_json::text NOT LIKE '%\"deprecated\": true,%') 
        AND (ctx.meta_json::text NOT LIKE '%\"deprecated\": true,%') 
        AND asr.object_uuid NOT IN (
            CAST('00000000-ed50-3cf1-c266-683c89afdac4' AS UUID), 
            CAST('00000000-ed50-8ee5-c7a2-21a012593f25' AS UUID)
        ) 
        ORDER BY asr.sort ASC 
        LIMIT 1
    ) AS object_equiv_ld_label,

    (
        SELECT concat('https://', m.uri)
        FROM {db_schema}.oc_all_assertions asr 
        INNER JOIN {db_schema}.oc_all_manifest m ON asr.object_uuid = m.uuid 
        INNER JOIN {db_schema}.oc_all_manifest ctx ON m.context_uuid = ctx.uuid 
        WHERE m.item_type IN ('class', 'property', 'uri') 
        AND asr.predicate_uuid IN (
            CAST('00000000-2470-aa02-9342-e9d5b2ed3149' AS UUID), 
            CAST('00000000-081a-dc93-af22-4cbcca550517' AS UUID), 
            CAST('00000000-081a-1d47-f617-1699079819cf' AS UUID)
        ) 
        AND asr.subject_uuid = a.object_uuid 
        AND asr.visible 
        AND (m.meta_json::text NOT LIKE '%\"deprecated\": true,%') 
        AND (ctx.meta_json::text NOT LIKE '%\"deprecated\": true,%')  
        AND asr.object_uuid NOT IN (
            CAST('00000000-ed50-3cf1-c266-683c89afdac4' AS UUID), 
            CAST('00000000-ed50-8ee5-c7a2-21a012593f25' AS UUID)
        ) 
        ORDER BY asr.sort ASC 
        LIMIT 1
    ) AS object_equiv_ld_uri

    FROM {db_schema}.oc_all_assertions AS a
    -- Use man table generated from the manifest query to 
    -- as a filter for assertion query.
    INNER JOIN {man_table} ON a.subject_uuid = {man_table}.uuid
    INNER JOIN {db_schema}.oc_all_manifest pred ON a.predicate_uuid = pred.uuid
    INNER JOIN {db_schema}.oc_all_manifest obj ON a.object_uuid = obj.uuid
    WHERE {where_conditions};
    """
    return sql


def get_isamples_raw_manifest(more_where_clauses=None, alias=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE, con=DB_CON):
    """Create a DuckDB connection to a PostgreSQL database"""
    sql = make_isamples_manifest_query_sql(more_where_clauses=more_where_clauses)
    con.execute(f"DROP TABLE IF EXISTS {alias}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias} AS {sql}'
    con.execute(temp_table_sql)
    # Make sure the added fields are the right data type
    for field, data_type in ADDED_FIELDS_DATA_TYPES:
        sql = f"ALTER TABLE {alias} ALTER {field} TYPE {data_type};"
        con.execute(sql)


def get_object_assertion_counts(alias=duckdb_con.ISAMPLES_PREP_ASSERTION_TABLE, con=DB_CON):
    """Get the number of assertions for each unique object UUID. This number is used to
    limit the insertion of IdentifiedConcepts to the iSamples PQG table so that only those with
    some frequency are included. 
    """
    sql = f"""
    UPDATE {alias}
    SET obj_count = (SELECT COUNT(uuid) FROM {alias} AS ac WHERE ac.object_uuid = {alias}.object_uuid)
    WHERE object_item_type IN ('types', 'class', 'uri')
    """
    con.execute(sql)


def get_isamples_raw_asserts(more_where_clauses=None, alias=duckdb_con.ISAMPLES_PREP_ASSERTION_TABLE, con=DB_CON):
    """Create a DuckDB connection to a PostgreSQL database"""
    sql = make_isamples_assertion_query_sql(more_where_clauses=more_where_clauses)
    con.execute(f"DROP TABLE IF EXISTS {alias}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias} AS {sql}'
    con.execute(temp_table_sql)
    print(f"Getting counts the use of different project specific objects (types) for {alias}")
    get_object_assertion_counts(alias=alias, con=con)


def get_distinct_subject_uuids(db_r, con=DB_CON, alias='subjects'):
    """Get distinct subject UUIDs from the DuckDB query results"""
    db_s = db_r.aggregate("subject_uuid").set_alias(alias)
    return db_s


        