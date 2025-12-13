import copy
import duckdb
from duckdb.typing import *

from django.conf import settings



import uuid as GenUUID

import numpy as np
import pandas as pd

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q, OuterRef, Subquery, Count

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
    ManifestCachedSpacetime,
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

start = time.time()
db_m = facets.get_spacetime_facet_counts(con=con)
end = time.time()
print(f'Elapsed: {(end-start)}')

start = time.time()
df = facets.get_space_time_facet_counts_via_orm()
end = time.time()
print(f'Elapsed: {(end-start)}')

start = time.time()
df = facets.get_assertion_facet_counts_via_orm()
end = time.time()
print(f'Elapsed: {(end-start)}')

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


def make_space_time_facets_query_sql(more_where_clauses=None, db_schema=duckdb_con.DUCKDB_SCHEMA):
    """Create a Facets SQL query"""
    
    where_clauses = []
    if isinstance(more_where_clauses, list):
        where_clauses.extend(more_where_clauses)

    # No results for items flagged as 'do not index'
    no_index_subj_clause = "item_man.meta_json::text NOT LIKE '%\"flag_do_not_index\": true,%'"
    no_index_proj_clause = "proj_m.meta_json::text NOT LIKE '%\"flag_do_not_index\": true,%'"
    where_clauses.append(no_index_subj_clause)
    where_clauses.append(no_index_proj_clause)

    # Exclude results where there's neither a geo or a chrono source
    no_spacetime_clause = "((spt.geo_source_uuid IS NOT NULL) OR (spt.chrono_source_uuid IS NOT NULL))"
    where_clauses.append(no_spacetime_clause)

    where_conditions = ' AND '.join(where_clauses)

    sql = f"""
    SELECT

        spt.geo_spacetime_uuid,
        geo_man.label AS geo_source_label,
        spt.geometry_type,
        spt.latitude,
        spt.longitude,
        spt.geo_specificity,

        spt.chrono_spacetime_uuid,
        chrono_man.label AS chrono_source_label,
        spt.earliest,
        spt.latest,

        COUNT(*) AS facet_count

    FROM {db_schema}.oc_all_manifest_cached_spacetime AS spt
    JOIN {db_schema}.oc_all_manifest AS item_man ON (
        spt.item_uuid = item_man.uuid
    )
    JOIN {db_schema}.oc_all_manifest AS proj_m ON (
        item_man.project_uuid = proj_m.uuid
    )
    LEFT JOIN {db_schema}.oc_all_manifest AS geo_man ON (
        spt.geo_source_uuid = geo_man.uuid
    )
    LEFT JOIN {db_schema}.oc_all_manifest AS chrono_man ON (
        spt.chrono_source_uuid = chrono_man.uuid
    )
    WHERE {where_conditions}
    GROUP BY

        spt.geo_spacetime_uuid,
        geo_man.label,
        spt.geometry_type,
        spt.latitude,
        spt.longitude,
        spt.geo_specificity,

        spt.chrono_spacetime_uuid,
        chrono_man.label,
        spt.earliest,
        spt.latest
    ORDER BY facet_count DESC
    """

    return sql


def get_spacetime_facet_counts(more_where_clauses=None, db_schema=duckdb_con.DUCKDB_SCHEMA, show_max_width=SHOW_MAX_WIDTH, con=DB_CON):
    """Get the number of assertions for each unique object UUID. This number is used to
    limit the insertion of IdentifiedConcepts to the iSamples PQG table so that only those with
    some frequency are included. 
    """
    sql = make_space_time_facets_query_sql(more_where_clauses=more_where_clauses, db_schema=db_schema)
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
        facet_count=Count('subject_id', distinct=True)
    ).order_by(
        'predicate__label',
        '-facet_count',
        'object__label',
    )
    df =  pd.DataFrame.from_records(qs)
    return df


def get_space_time_facet_counts_via_orm(more_where_clauses=None):
    """Gets space time facet counts"""
    
    qs = ManifestCachedSpacetime.objects.filter(
    ).exclude(
        item__meta_json__has_key='flag_do_not_index',
    ).exclude(
        item__project__meta_json__has_key='flag_do_not_index',
    ).select_related(
        'item'
    ).select_related(
        'item__project'
    ).values(
        # 'item_id',
        'geo_spacetime_id',
        'geometry_type',
        'latitude',
        'longitude',
        'geo_specificity',
        'chrono_spacetime_id',
        'earliest',
        'latest',
        'reference_type',
    ).annotate(
        facet_count=Count('item_id', distinct=True)
    ).order_by(
        '-facet_count',
    )
    df =  pd.DataFrame.from_records(qs)
    return df