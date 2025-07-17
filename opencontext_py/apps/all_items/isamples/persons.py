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


def make_persons_direct_dc_relations_sql(
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
    asserts_table=duckdb_con.ISAMPLES_PREP_ASSERTION_TABLE,
    db_schema=duckdb_con.DUCKDB_SCHEMA, 
):
    """Makes the SQL to get persons directly associated with samples"""
    where_clauses = []
    where_clauses.append("a.object_item_type = 'persons'")

    dc_predicate_uuids = [configs.PREDICATE_DCTERMS_CONTRIBUTOR_UUID, configs.PREDICATE_DCTERMS_CREATOR_UUID]
    duck_pred_uuids = [duck_utils.cast_duckdb_uuid(uuid) for uuid in dc_predicate_uuids]
    duck_list = ', '.join(duck_pred_uuids)
    class_clause = f"asr.object_uuid IN ({duck_list})"
    where_clauses.append(class_clause)

    where_conditions = ' AND '.join(where_clauses)

    sql = f"""
        SELECT
        m.uuid,
        m.label,
        m.path,
        m.uri,
        m.project_uuid,
        m.project_label,
        m.project_uri,
        a.predicate_uuid,
        a.predicate_label,
        dc_m.label AS direct_sample_dc_label,
        concat('https://', dc_m.uri) AS direct_sample_dc_uri,
        a.object_label AS direct_sample_dc_object_label,
        a.object_uri AS direct_sample_dc_object_uri,

        -- get the person's orcid

        (
            SELECT concat('orcid:', i.id) 
            FROM {db_schema}.oc_all_identifiers i 
            WHERE i.item_uuid = a.object_uuid
            AND i.scheme = 'orcid' 
            ORDER BY i.item_uuid ASC, i.rank ASC, i.scheme ASC 
            LIMIT 1
        ) AS direct_sample_dc_orcid

        FROM {man_table} AS m
        INNER JOIN {asserts_table} AS a ON m.uuid = a.subject_uuid
        INNER JOIN {db_schema}.oc_all_assertions asr ON a.predicate_uuid = asr.subject_uuid
        INNER JOIN {db_schema}.oc_all_manifest AS dc_m ON asr.object_uuid = dc_m.uuid
        WHERE {where_conditions}
    """
    return sql


def make_persons_indirect_dc_relations_sql(
    man_table=duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE,
    db_schema=duckdb_con.DUCKDB_SCHEMA, 
):
    """Makes the SQL to get persons directly associated with samples"""
    where_clauses = []
    where_clauses.append("proj_asr.visible = TRUE")
    where_clauses.append("proj_dc_obj_m.item_type = 'persons'")

    dc_predicate_uuids = [configs.PREDICATE_DCTERMS_CONTRIBUTOR_UUID, configs.PREDICATE_DCTERMS_CREATOR_UUID]
    duck_pred_uuids = [duck_utils.cast_duckdb_uuid(uuid) for uuid in dc_predicate_uuids]
    duck_list = ', '.join(duck_pred_uuids)
    class_clause = f"proj_asr.predicate_uuid IN ({duck_list})"
    where_clauses.append(class_clause)

    where_conditions = ' AND '.join(where_clauses)

    sql = f"""
        SELECT
        m.uuid,
        m.label,
        m.path,
        m.uri,
        m.project_uuid,
        m.project_label,
        m.project_uri,
       
        dc_m.label AS indirect_sample_dc_label,
        concat('https://', dc_m.uri) AS indirect_sample_dc_uri,
        proj_dc_obj_m.label AS indirect_sample_dc_object_label,
        concat('https://', proj_dc_obj_m.uri) AS indirect_sample_dc_object_uri,

        -- get the person's orcid

        (
            SELECT concat('orcid:', i.id) 
            FROM {db_schema}.oc_all_identifiers i 
            WHERE i.item_uuid = proj_dc_obj_m.uuid
            AND i.scheme = 'orcid' 
            ORDER BY i.item_uuid ASC, i.rank ASC, i.scheme ASC 
            LIMIT 1
        ) AS indirect_sample_dc_orcid

        FROM {man_table} AS m
        INNER JOIN {db_schema}.oc_all_assertions AS proj_asr ON m.project_uuid = proj_asr.subject_uuid
        INNER JOIN {db_schema}.oc_all_manifest AS proj_dc_obj_m ON proj_asr.object_uuid = proj_dc_obj_m.uuid
        INNER JOIN {db_schema}.oc_all_manifest AS dc_m ON proj_asr.predicate_uuid = dc_m.uuid
        WHERE {where_conditions}
    """
    return sql


def get_isamples_direct_dc_relations(con=DB_CON, db_schema=duckdb_con.DUCKDB_SCHEMA, alias='direct_persons'):
    """Get persons directly associated with samples"""
    sql = make_persons_direct_dc_relations_sql(db_schema=db_schema)
    con.execute(f"DROP TABLE IF EXISTS {alias}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias} AS {sql}'
    con.execute(temp_table_sql)


def get_isamples_indirect_dc_relations(con=DB_CON, db_schema=duckdb_con.DUCKDB_SCHEMA, alias='indirect_persons'):
    """Get persons indirectly associated with samples"""
    sql = make_persons_indirect_dc_relations_sql(db_schema=db_schema)
    con.execute(f"DROP TABLE IF EXISTS {alias}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias} AS {sql}'
    con.execute(temp_table_sql)


def get_all_isamples_dc_relations(
    con=DB_CON, 
    db_schema=duckdb_con.DUCKDB_SCHEMA,
    alias=duckdb_con.ISAMPLES_PREP_PERSON_TABLE,
):
    """Get all persons associated with samples"""
    get_isamples_direct_dc_relations(con=con, db_schema=db_schema, alias='direct_persons')
    get_isamples_indirect_dc_relations(con=con, db_schema=db_schema, alias='indirect_persons')
    sql = f"""
        SELECT
        ind.uuid,
        ind.label,
        ind.path,
        ind.uri,
        ind.project_uuid,
        ind.project_label,
        ind.project_uri,
        d.predicate_uuid,
        d.predicate_label,
        d.direct_sample_dc_label,
        d.direct_sample_dc_uri,
        d.direct_sample_dc_object_label,
        d.direct_sample_dc_object_uri,
        d.direct_sample_dc_orcid,
        ind.indirect_sample_dc_label,
        ind.indirect_sample_dc_uri,
        ind.indirect_sample_dc_object_label,
        ind.indirect_sample_dc_object_uri,
        ind.indirect_sample_dc_orcid
        FROM indirect_persons AS ind
        FULL OUTER JOIN direct_persons AS d ON ind.uuid = d.uuid
    """
    con.execute(f"DROP TABLE IF EXISTS {alias}")
    temp_table_sql = f'CREATE TEMPORARY TABLE {alias} AS {sql}'
    con.execute(temp_table_sql)