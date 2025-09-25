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
geo_loc_pid = 'geoloc_4449bb33095fcb9ba95430d9f444b983f16db075'
db_m = isamples_explore.get_samples_at_geo_cord_location_via_sample_event(geo_loc_pid)

"""

DB_CON = duckdb_con.create_duck_db_postgres_connection()
SHOW_MAX_WIDTH = 200


def load_pqg_table_from_parquet_path(parquet_path, con=DB_CON,):
    sql = f"""
    CREATE TABLE pqg AS
    SELECT * FROM '{parquet_path}';
    """
    db_m = con.sql(sql)
    isamples_pqg.summarize_pqg(con=con)
    return db_m


def get_samples_at_geo_cord_location_via_sample_event(geo_loc_pid, con=DB_CON, show_max_width=SHOW_MAX_WIDTH):
    """Gets samples from a given GeospatialCoordLocation identified by a pid"""
    
    sql = f"""
    SELECT geo_pqg.latitude, geo_pqg.longitude, 
    site_pqg.label AS sample_site_label,
    site_pqg.pid AS sample_site_pid,
    samp_pqg.pid AS sample_pid,
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
    )
    JOIN pqg AS rel_site_pqg ON (
        se_pqg.row_id = rel_site_pqg.s
        AND
        rel_site_pqg.p = 'sampling_site'
    )
    JOIN pqg AS site_pqg ON (
        list_extract(rel_site_pqg.o, 1) = site_pqg.row_id
    )
    JOIN pqg AS rel_samp_pqg ON (
        rel_samp_pqg.p = 'produced_by'
        AND
        contains(rel_samp_pqg.o, se_pqg.row_id)
    )
    JOIN pqg AS samp_pqg ON (
        rel_samp_pqg.s = samp_pqg.row_id
    )
    WHERE geo_pqg.pid = '{geo_loc_pid}'
    ORDER BY has_thumbnail DESC
    LIMIT 50
    """

    db_m = con.sql(sql)
    db_m.show(max_width=show_max_width)
    return db_m
