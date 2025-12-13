import copy
import duckdb
from duckdb.typing import *

from django.conf import settings

from opencontext_py.libs import duckdb_con
from opencontext_py.apps.all_items.isamples import duckdb_functions as duck_funcs
from opencontext_py.apps.all_items.isamples import utilities as duck_utils
from opencontext_py.apps.all_items.isamples import raw_samples
from opencontext_py.apps.all_items.isamples import sample_sites
from opencontext_py.apps.all_items.isamples import space_time
from opencontext_py.apps.all_items.isamples import persons

# Imports related to iSamples PQG generation
from opencontext_py.apps.all_items.isamples import isamples_pqg


"""
# Testing
import importlib
from opencontext_py.apps.all_items.isamples import isamples_explore
from opencontext_py.apps.all_items.isamples import parquet
importlib.reload(isamples_explore)

import time

con = isamples_explore.DB_CON
isamples_explore.load_pqg_table_from_parquet_path(
    parquet_path='/home/ekansa/oc-data/parquet/oc_isamples_pqg.parquet'
)

isamples_explore.load_pqg_table_from_parquet_path(
    parquet_path='/home/ekansa/oc-data/parquet/oc_isamples_pqg_wide.parquet',
    table='pqg_wide',
) 

# alias file on local filesystem
isamples_explore.alias_pqg_table_from_parquet_path(
    parquet_path='/home/ekansa/oc-data/oc_isamples_pqg.parquet'
)
# alias remote file
isamples_explore.alias_pqg_table_from_remote_parquet_url(
    parquet_url='https://storage.googleapis.com/opencontext-parquet/oc_isamples_pqg.parquet'
)
isamples_explore.alias_pqg_table_from_remote_parquet_url(
    parquet_url='https://storage.googleapis.com/opencontext-parquet/oc_isamples_pqg_wide.parquet',
    table='pqg_wide',
)

geo_loc_pid = 'geoloc_4449bb33095fcb9ba95430d9f444b983f16db075'
start_m = time.time()
db_m = isamples_explore.get_samples_at_geo_cord_location_via_sample_event(geo_loc_pid)
end_m = time.time()
start_w = time.time()
db_w = isamples_explore.get_samples_at_geo_cord_location_via_sample_event_wide(geo_loc_pid)
end_w = time.time()
print(f'Query with edges took {(end_m - start_m)}; query with wide schema took {(end_w - start_w)}')

sample_pid = 'ark:/28722/r2p24/pc_19970127'
db_m = isamples_explore.get_sample_data_via_sample_pid(sample_pid)
db_m = isamples_explore.get_sample_types_and_keywords_via_sample_pid(sample_pid)
db_m = isamples_explore.get_sample_data_agents_sample_pid(sample_pid)

db_w = isamples_explore.get_sample_data_via_sample_pid_wide(sample_pid)
db_w = isamples_explore.get_sample_types_and_keywords_via_sample_pid_wide(sample_pid)
db_w = isamples_explore.get_sample_data_agents_sample_pid_wide(sample_pid)


"""

DB_CON = duckdb_con.create_duck_db_postgres_connection()
SHOW_MAX_WIDTH = 200


def load_pqg_table_from_parquet_path(parquet_path, table='pqg', con=DB_CON,):
    """Loads a parquet file into the pqg table, in memory"""
    sql = f"""
    CREATE TABLE {table} AS
    SELECT * FROM '{parquet_path}';
    """
    db_m = con.sql(sql)
    if table != 'pqg':
        return db_m
    isamples_pqg.summarize_pqg(con=con)
    return db_m


def alias_pqg_table_from_parquet_path(parquet_path, table='pqg', con=DB_CON,):
    """Sets up a pqg table as an alias 
    parquet file into the pqg table, in memory"""
    sql = f"""
    ATTACH '{parquet_path}' AS {table} (default_table pqg);
    """
    db_m = con.sql(sql)
    if table != 'pqg':
        return db_m
    isamples_pqg.summarize_pqg(con=con)
    return db_m


def alias_pqg_table_from_remote_parquet_url(parquet_url, table='pqg', con=DB_CON, show_summary=False):
    """Sets up a pqg table as an alias 
    parquet file into the pqg table, in memory"""
    sql = f"""
    CREATE VIEW {table} AS
    SELECT * FROM PARQUET_SCAN('{parquet_url}');
    """
    db_m = con.sql(sql)
    if show_summary and table == 'pqg':
        isamples_pqg.summarize_pqg(con=con)
    return db_m


def get_sample_data_via_sample_pid(sample_pid, con=DB_CON, show_max_width=SHOW_MAX_WIDTH):
    """Gets 1 row of iSamples data for a sample idendified by a PID"""

    sql = f"""
    SELECT 
    samp_pqg.row_id,
    samp_pqg.pid AS sample_pid,
    samp_pqg.alternate_identifiers AS sample_alternate_identifiers,
    samp_pqg.label AS sample_label,
    samp_pqg.description AS sample_description,
    samp_pqg.thumbnail_url AS sample_thumbnail_url,
    samp_pqg.thumbnail_url is NOT NULL as has_thumbnail,

    geo_pqg.latitude, 
    geo_pqg.longitude,

    site_pqg.label AS sample_site_label,
    site_pqg.pid AS sample_site_pid,

    FROM pqg AS samp_pqg

    JOIN pqg AS samp_rel_se_pqg ON (
        samp_rel_se_pqg.s = samp_pqg.row_id
        AND
        samp_rel_se_pqg.p = 'produced_by'
    )
    JOIN pqg AS se_pqg ON (
        list_extract(samp_rel_se_pqg.o, 1) = se_pqg.row_id
        AND
        se_pqg.otype = 'SamplingEvent'
    )
    JOIN pqg AS geo_rel_se_pqg ON (
        geo_rel_se_pqg.s = se_pqg.row_id
        AND
        geo_rel_se_pqg.p = 'sample_location'
    )
    JOIN pqg AS geo_pqg ON (
        list_extract(geo_rel_se_pqg.o, 1) = geo_pqg.row_id
        AND
        geo_pqg.otype = 'GeospatialCoordLocation'
    )

    JOIN pqg AS site_rel_se_pqg ON (
        site_rel_se_pqg.s = se_pqg.row_id
        AND
        site_rel_se_pqg.p = 'sampling_site'
    )
    JOIN pqg AS site_pqg ON (
        list_extract(site_rel_se_pqg.o, 1) = site_pqg.row_id
        AND
        site_pqg.otype = 'SamplingSite'
    )
    
    WHERE samp_pqg.pid = '{sample_pid}' 
    AND samp_pqg.otype = 'MaterialSampleRecord'
    
    ;
    """

    db_m = con.sql(sql)
    db_m.show(max_width=show_max_width)
    return db_m



def get_sample_data_agents_sample_pid(sample_pid, con=DB_CON, show_max_width=SHOW_MAX_WIDTH):
    """Gets the agent iSamples data for a sample idendified by a PID"""

    sql = f"""
    SELECT 
    samp_pqg.row_id,
    samp_pqg.pid AS sample_pid,
    samp_pqg.alternate_identifiers AS sample_alternate_identifiers,
    samp_pqg.label AS sample_label,
    samp_pqg.description AS sample_description,
    samp_pqg.thumbnail_url AS sample_thumbnail_url,
    samp_pqg.thumbnail_url is NOT NULL as has_thumbnail,
    agent_rel_se_pqg.p AS predicate,
    agent_pqg.pid AS agent_pid,
    agent_pqg.name AS agent_name,
    agent_pqg.alternate_identifiers AS agent_alternate_identifiers

    FROM pqg AS samp_pqg

    JOIN pqg AS samp_rel_se_pqg ON (
        samp_rel_se_pqg.s = samp_pqg.row_id
        AND
        samp_rel_se_pqg.p = 'produced_by'
    )
    JOIN pqg AS se_pqg ON (
        list_extract(samp_rel_se_pqg.o, 1) = se_pqg.row_id
        AND
        se_pqg.otype = 'SamplingEvent'
    )
    JOIN pqg AS agent_rel_se_pqg ON (
        agent_rel_se_pqg.s = se_pqg.row_id
        AND
        list_contains(['responsibility', 'registrant'], agent_rel_se_pqg.p)
    )
    JOIN pqg AS agent_pqg ON (
        agent_pqg.row_id = ANY(agent_rel_se_pqg.o)
        AND
        agent_pqg.otype = 'Agent'
    )
    
    WHERE samp_pqg.pid = '{sample_pid}' 
    AND samp_pqg.otype = 'MaterialSampleRecord'
    
    ;
    """

    db_m = con.sql(sql)
    db_m.show(max_width=show_max_width)
    return db_m




def get_sample_types_and_keywords_via_sample_pid(sample_pid, con=DB_CON, show_max_width=SHOW_MAX_WIDTH):
    """Gets 1 row of iSamples data for a sample idendified by a PID"""

    sql = f"""
    SELECT 
    samp_pqg.row_id,
    samp_pqg.pid AS sample_pid,
    samp_pqg.alternate_identifiers AS sample_alternate_identifiers,
    samp_pqg.label AS sample_label,

    kw_rel_se_pqg.p AS predicate,
    kw_pqg.pid AS keyword_pid,
    kw_pqg.label AS keyword

    FROM pqg AS samp_pqg

    JOIN pqg AS kw_rel_se_pqg ON (
        kw_rel_se_pqg.s = samp_pqg.row_id
        AND
        list_contains(['keywords', 'has_sample_object_type', 'has_material_category'], kw_rel_se_pqg.p)
    )
    JOIN pqg AS kw_pqg ON (
        kw_pqg.row_id = ANY(kw_rel_se_pqg.o)
        AND
        kw_pqg.otype = 'IdentifiedConcept'
    )
      
    WHERE samp_pqg.pid = '{sample_pid}' 
    AND samp_pqg.otype = 'MaterialSampleRecord'
    
    ;
    """

    db_m = con.sql(sql)
    db_m.show(max_width=show_max_width)
    return db_m



def get_samples_at_geo_cord_location_via_sample_event(geo_loc_pid, con=DB_CON, show_max_width=SHOW_MAX_WIDTH):
    """Gets samples from a given GeospatialCoordLocation identified by a pid"""
    
    sql = f"""
    SELECT geo_pqg.latitude, geo_pqg.longitude, 
    site_pqg.label AS sample_site_label,
    site_pqg.pid AS sample_site_pid,
    samp_pqg.pid AS sample_pid,
    samp_pqg.alternate_identifiers AS sample_alternate_identifiers,
    samp_pqg.label AS sample_label,
    samp_pqg.description AS sample_description,
    samp_pqg.thumbnail_url AS sample_thumbnail_url,
    samp_pqg.thumbnail_url is NOT NULL as has_thumbnail 

    FROM pqg AS geo_pqg
    JOIN pqg AS rel_se_pqg ON (
        rel_se_pqg.p = 'sample_location'
        AND
        contains(rel_se_pqg.o, geo_pqg.row_id)
    )
    JOIN pqg AS se_pqg ON (
        rel_se_pqg.s = se_pqg.row_id
        AND
        se_pqg.otype = 'SamplingEvent'
    )
    JOIN pqg AS rel_site_pqg ON (
        se_pqg.row_id = rel_site_pqg.s
        AND
        rel_site_pqg.p = 'sampling_site'
    )
    JOIN pqg AS site_pqg ON (
        list_extract(rel_site_pqg.o, 1) = site_pqg.row_id
        AND
        site_pqg.otype = 'SamplingSite'
    )
    JOIN pqg AS rel_samp_pqg ON (
        rel_samp_pqg.p = 'produced_by'
        AND
        contains(rel_samp_pqg.o, se_pqg.row_id)
    )
    JOIN pqg AS samp_pqg ON (
        rel_samp_pqg.s = samp_pqg.row_id
        AND
        samp_pqg.otype = 'MaterialSampleRecord'
    )
    WHERE geo_pqg.pid = '{geo_loc_pid}' AND geo_pqg.otype = 'GeospatialCoordLocation'
    ORDER BY has_thumbnail DESC
    """

    db_m = con.sql(sql)
    db_m.show(max_width=show_max_width)
    return db_m


# ============================================================================
# Wide table versions - query pqg_wide instead of pqg
# ============================================================================

def get_sample_data_via_sample_pid_wide(sample_pid, con=DB_CON, show_max_width=SHOW_MAX_WIDTH):
    """Gets 1 row of iSamples data for a sample identified by a PID (using pqg_wide table)"""

    sql = f"""
    SELECT 
    samp_pqg.row_id,
    samp_pqg.pid AS sample_pid,
    samp_pqg.alternate_identifiers AS sample_alternate_identifiers,
    samp_pqg.label AS sample_label,
    samp_pqg.description AS sample_description,
    samp_pqg.thumbnail_url AS sample_thumbnail_url,
    samp_pqg.thumbnail_url is NOT NULL as has_thumbnail,

    geo_pqg.latitude, 
    geo_pqg.longitude,

    site_pqg.label AS sample_site_label,
    site_pqg.pid AS sample_site_pid

    FROM pqg_wide AS samp_pqg

    JOIN pqg_wide AS se_pqg ON (
        se_pqg.row_id = list_extract(samp_pqg.p__produced_by, 1)
        AND
        se_pqg.otype = 'SamplingEvent'
    )
    JOIN pqg_wide AS geo_pqg ON (
        geo_pqg.row_id = list_extract(se_pqg.p__sample_location, 1)
        AND
        geo_pqg.otype = 'GeospatialCoordLocation'
    )
    JOIN pqg_wide AS site_pqg ON (
        site_pqg.row_id = list_extract(se_pqg.p__sampling_site, 1)
        AND
        site_pqg.otype = 'SamplingSite'
    )
    
    WHERE samp_pqg.pid = '{sample_pid}' 
    AND samp_pqg.otype = 'MaterialSampleRecord'
    
    ;
    """

    db_m = con.sql(sql)
    db_m.show(max_width=show_max_width)
    return db_m


def get_sample_data_agents_sample_pid_wide(sample_pid, con=DB_CON, show_max_width=SHOW_MAX_WIDTH):
    """Gets the agent iSamples data for a sample identified by a PID (using pqg_wide table)
    
    Note: This matches the original function which looks for both 'responsibility' and 
    'registrant' predicates on the sampling event. However, based on the data structure,
    'registrant' may actually be on the sample. This function checks the sampling event
    for both predicates to match the original behavior.
    """

    sql = f"""
    SELECT 
    samp_pqg.row_id,
    samp_pqg.pid AS sample_pid,
    samp_pqg.alternate_identifiers AS sample_alternate_identifiers,
    samp_pqg.label AS sample_label,
    samp_pqg.description AS sample_description,
    samp_pqg.thumbnail_url AS sample_thumbnail_url,
    samp_pqg.thumbnail_url is NOT NULL as has_thumbnail,
    'responsibility' AS predicate,
    agent_pqg.pid AS agent_pid,
    agent_pqg.name AS agent_name,
    agent_pqg.alternate_identifiers AS agent_alternate_identifiers

    FROM pqg_wide AS samp_pqg

    JOIN pqg_wide AS se_pqg ON (
        se_pqg.row_id = list_extract(samp_pqg.p__produced_by, 1)
        AND
        se_pqg.otype = 'SamplingEvent'
    )
    CROSS JOIN unnest(se_pqg.p__responsibility) AS resp_unnest_val
    JOIN pqg_wide AS agent_pqg ON (
        agent_pqg.row_id = resp_unnest_val.unnest
        AND
        agent_pqg.otype = 'Agent'
    )
    
    WHERE samp_pqg.pid = '{sample_pid}' 
    AND samp_pqg.otype = 'MaterialSampleRecord'
    AND se_pqg.p__responsibility IS NOT NULL

    UNION ALL

    SELECT 
    samp_pqg.row_id,
    samp_pqg.pid AS sample_pid,
    samp_pqg.alternate_identifiers AS sample_alternate_identifiers,
    samp_pqg.label AS sample_label,
    samp_pqg.description AS sample_description,
    samp_pqg.thumbnail_url AS sample_thumbnail_url,
    samp_pqg.thumbnail_url is NOT NULL as has_thumbnail,
    'registrant' AS predicate,
    agent_pqg.pid AS agent_pid,
    agent_pqg.name AS agent_name,
    agent_pqg.alternate_identifiers AS agent_alternate_identifiers

    FROM pqg_wide AS samp_pqg

    JOIN pqg_wide AS se_pqg ON (
        se_pqg.row_id = list_extract(samp_pqg.p__produced_by, 1)
        AND
        se_pqg.otype = 'SamplingEvent'
    )
    CROSS JOIN unnest(se_pqg.p__registrant) AS reg_unnest_val
    JOIN pqg_wide AS agent_pqg ON (
        agent_pqg.row_id = reg_unnest_val.unnest
        AND
        agent_pqg.otype = 'Agent'
    )
    
    WHERE samp_pqg.pid = '{sample_pid}' 
    AND samp_pqg.otype = 'MaterialSampleRecord'
    AND se_pqg.p__registrant IS NOT NULL

    UNION ALL

    SELECT 
    samp_pqg.row_id,
    samp_pqg.pid AS sample_pid,
    samp_pqg.alternate_identifiers AS sample_alternate_identifiers,
    samp_pqg.label AS sample_label,
    samp_pqg.description AS sample_description,
    samp_pqg.thumbnail_url AS sample_thumbnail_url,
    samp_pqg.thumbnail_url is NOT NULL as has_thumbnail,
    'registrant' AS predicate,
    agent_pqg.pid AS agent_pid,
    agent_pqg.name AS agent_name,
    agent_pqg.alternate_identifiers AS agent_alternate_identifiers

    FROM pqg_wide AS samp_pqg
    CROSS JOIN unnest(samp_pqg.p__registrant) AS reg_unnest_val
    JOIN pqg_wide AS agent_pqg ON (
        agent_pqg.row_id = reg_unnest_val.unnest
        AND
        agent_pqg.otype = 'Agent'
    )
    
    WHERE samp_pqg.pid = '{sample_pid}' 
    AND samp_pqg.otype = 'MaterialSampleRecord'
    AND samp_pqg.p__registrant IS NOT NULL
    
    ;
    """

    db_m = con.sql(sql)
    db_m.show(max_width=show_max_width)
    return db_m


def get_sample_types_and_keywords_via_sample_pid_wide(sample_pid, con=DB_CON, show_max_width=SHOW_MAX_WIDTH):
    """Gets types and keywords for a sample identified by a PID (using pqg_wide table)"""

    # NOTE TODO: We should update this to avoid UNIONs. The wide schema hnas the predicates:
    # 'keywords', 'has_sample_object_type', 'has_material_category' as additional columns
    # so we can get the same data (but expressed in a different output schema) with just
    # one query and not 3 queries stuck together with UNIONs.

    sql = f"""
    SELECT 
    samp_pqg.row_id,
    samp_pqg.pid AS sample_pid,
    samp_pqg.alternate_identifiers AS sample_alternate_identifiers,
    samp_pqg.label AS sample_label,
    'keywords' AS predicate,
    kw_pqg.pid AS keyword_pid,
    kw_pqg.label AS keyword

    FROM pqg_wide AS samp_pqg
    CROSS JOIN unnest(samp_pqg.p__keywords) AS unnest_val
    JOIN pqg_wide AS kw_pqg ON (
        kw_pqg.row_id = unnest_val.unnest
        AND
        kw_pqg.otype = 'IdentifiedConcept'
    )
      
    WHERE samp_pqg.pid = '{sample_pid}' 
    AND samp_pqg.otype = 'MaterialSampleRecord'
    AND samp_pqg.p__keywords IS NOT NULL

    UNION ALL

    SELECT 
    samp_pqg.row_id,
    samp_pqg.pid AS sample_pid,
    samp_pqg.alternate_identifiers AS sample_alternate_identifiers,
    samp_pqg.label AS sample_label,
    'has_sample_object_type' AS predicate,
    kw_pqg.pid AS keyword_pid,
    kw_pqg.label AS keyword

    FROM pqg_wide AS samp_pqg
    CROSS JOIN unnest(samp_pqg.p__has_sample_object_type) AS unnest_val
    JOIN pqg_wide AS kw_pqg ON (
        kw_pqg.row_id = unnest_val.unnest
        AND
        kw_pqg.otype = 'IdentifiedConcept'
    )
      
    WHERE samp_pqg.pid = '{sample_pid}' 
    AND samp_pqg.otype = 'MaterialSampleRecord'
    AND samp_pqg.p__has_sample_object_type IS NOT NULL

    UNION ALL

    SELECT 
    samp_pqg.row_id,
    samp_pqg.pid AS sample_pid,
    samp_pqg.alternate_identifiers AS sample_alternate_identifiers,
    samp_pqg.label AS sample_label,
    'has_material_category' AS predicate,
    kw_pqg.pid AS keyword_pid,
    kw_pqg.label AS keyword

    FROM pqg_wide AS samp_pqg
    CROSS JOIN unnest(samp_pqg.p__has_material_category) AS unnest_val
    JOIN pqg_wide AS kw_pqg ON (
        kw_pqg.row_id = unnest_val.unnest
        AND
        kw_pqg.otype = 'IdentifiedConcept'
    )
      
    WHERE samp_pqg.pid = '{sample_pid}' 
    AND samp_pqg.otype = 'MaterialSampleRecord'
    AND samp_pqg.p__has_material_category IS NOT NULL
    
    ;
    """

    db_m = con.sql(sql)
    db_m.show(max_width=show_max_width)
    return db_m


def get_samples_at_geo_cord_location_via_sample_event_wide(geo_loc_pid, con=DB_CON, show_max_width=SHOW_MAX_WIDTH):
    """Gets samples from a given GeospatialCoordLocation identified by a pid (using pqg_wide table)"""
    
    sql = f"""
    SELECT geo_pqg.latitude, geo_pqg.longitude, 
    site_pqg.label AS sample_site_label,
    site_pqg.pid AS sample_site_pid,
    samp_pqg.pid AS sample_pid,
    samp_pqg.alternate_identifiers AS sample_alternate_identifiers,
    samp_pqg.label AS sample_label,
    samp_pqg.description AS sample_description,
    samp_pqg.thumbnail_url AS sample_thumbnail_url,
    samp_pqg.thumbnail_url is NOT NULL as has_thumbnail 

    FROM pqg_wide AS geo_pqg
    JOIN pqg_wide AS se_pqg ON (
        contains(se_pqg.p__sample_location, geo_pqg.row_id)
        AND
        se_pqg.otype = 'SamplingEvent'
    )
    JOIN pqg_wide AS site_pqg ON (
        site_pqg.row_id = list_extract(se_pqg.p__sampling_site, 1)
        AND
        site_pqg.otype = 'SamplingSite'
    )
    JOIN pqg_wide AS samp_pqg ON (
        contains(samp_pqg.p__produced_by, se_pqg.row_id)
        AND
        samp_pqg.otype = 'MaterialSampleRecord'
    )
    WHERE geo_pqg.pid = '{geo_loc_pid}' AND geo_pqg.otype = 'GeospatialCoordLocation'
    ORDER BY has_thumbnail DESC
    """

    db_m = con.sql(sql)
    db_m.show(max_width=show_max_width)
    return db_m