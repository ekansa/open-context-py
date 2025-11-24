import copy
import duckdb
from duckdb.typing import *

from django.conf import settings



import uuid as GenUUID

import numpy as np
import pandas as pd

from django.db.models import Q, OuterRef, Subquery, Count

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

"""
# Testing

import importlib
from opencontext_py.apps.db_searcher import facets
importlib.reload(facets)

import time

con = facets.DB_CON
db_m = facets.get_assertion_facet_counts(con=con)



"""



DB_CON = duckdb_con.create_duck_db_postgres_connection()
SHOW_MAX_WIDTH = 200


def make_facets_query_sql(more_where_clauses=None, db_schema=duckdb_con.DUCKDB_SCHEMA):
    """Create a Facets SQL query"""
    
    where_clauses = []
    if isinstance(more_where_clauses, list):
        where_clauses.extend(more_where_clauses)

    # where_clauses.append("m.item_type = 'subjects'")
    where_clauses.append("a.visible = true")
    where_clauses.append("p_m.data_type = 'id'")
    where_clauses.append(f"p_m.item_class_uuid = '{configs.CLASS_OC_VARIABLES_UUID}'")

    # No results for items flagged as 'do not index'
    no_index_subj_clause = "s_m.meta_json::text NOT LIKE '%\"flag_do_not_index\": true,%'"
    no_index_proj_clause = "proj_m.meta_json::text NOT LIKE '%\"flag_do_not_index\": true,%'"
    where_clauses.append(no_index_subj_clause)
    where_clauses.append(no_index_proj_clause)

    where_conditions = ' AND '.join(where_clauses)

    sql = f"""
    SELECT

        p_m.uuid AS predicate_uuid,
        p_m.slug AS predicate_slug,
        p_m.label AS predicate_label,

        o_m.uuid AS object_uuid,
        o_m.slug AS object_slug,
        o_m.label AS object_label,

        COUNT(*) AS facet_count

    FROM {db_schema}.oc_all_assertions AS a
    JOIN {db_schema}.oc_all_manifest AS s_m ON (
        a.subject_uuid = s_m.uuid
    )
    JOIN {db_schema}.oc_all_manifest AS proj_m ON (
        s_m.project_uuid = proj_m.uuid
    )
    JOIN {db_schema}.oc_all_manifest AS p_m ON (
        a.predicate_uuid = p_m.uuid
    )
    JOIN {db_schema}.oc_all_manifest AS o_m ON (
        a.object_uuid = o_m.uuid
    )
    WHERE {where_conditions}
    GROUP BY 
        a.predicate_uuid,
        p_m.uuid,
        p_m.slug,
        p_m.label,

        a.object_uuid,
        o_m.uuid,
        o_m.slug,
        o_m.label

    ORDER BY predicate_label, facet_count DESC, object_label;
    """

    return sql


def get_assertion_facet_counts(more_where_clauses=None, db_schema=duckdb_con.DUCKDB_SCHEMA, show_max_width=SHOW_MAX_WIDTH, con=DB_CON):
    """Get the number of assertions for each unique object UUID. This number is used to
    limit the insertion of IdentifiedConcepts to the iSamples PQG table so that only those with
    some frequency are included. 
    """
    sql = make_facets_query_sql(more_where_clauses=more_where_clauses, db_schema=db_schema)
    db_m = con.sql(sql)
    db_m.show(max_width=show_max_width)
    return db_m



def get_assertion_facet_counts_via_orm(more_where_clauses=None):

    qs = AllAssertion.objects.filter(
        visible=True,
        predicate__data_type='id',
        predicate__item_class_id=configs.CLASS_OC_VARIABLES_UUID,
    ).exclude(
        subject__meta_json__has_key='flag_do_not_index',
    ).select_related(
        'subject'
    ).select_related(
        'predicate'
    ).select_related(
        'object'
    ).values(
        'predicate_id',
        'predicate__slug',
        'predicate__label',
        'object_id',
        'object__slug',
        'object__label',
    ).annotate(
        facet_count=Count('uuid', distinct=True)
    ).order_by(
        'predicate__label',
        '-facet_count',
        'object__label',
    )
    df =  pd.DataFrame.from_records(qs)
    return df


def get_space_time_facet_counts_via_orm(more_where_clauses=None):
    """Gets space time facet counts"""
    qs = AllSpaceTime.objects.exclude(
        item__meta_json__has_key='flag_do_not_index',
    ).select_related(
        'item'
    ).values(
        'item__path',
        'earliest',
        'latest',
        'latitude',
        'longitude',
    ).annotate(
        facet_count=Count('item_id', distinct=True)
    )