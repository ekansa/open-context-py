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
from opencontext_py.apps.all_items.isamples import prep_isamples
from opencontext_py.apps.all_items.isamples import parquet
importlib.reload(prep_isamples)

import time

con = prep_isamples.DB_CON
start = time.time()
db_m = prep_isamples.prepare_sample_manifest_and_metadata()
prep_end = time.time()
print('Time to prepare sample manifest and related assertions:')
print(prep_end - start)

# Now we can move the extracted data to iSamples PQG table.
prep_isamples.prepare_isamples_pqg()

output_dir_path = '/home/ekansa/oc-data/parquet'
parquet.dump_isamples_tables_to_parquet(output_dir_path=output_dir_path, con=con)
end = time.time()
print('Time to complete and save all iSamples preparation:')
print(end - start)
"""

DB_CON = duckdb_con.create_duck_db_postgres_connection()

def prepare_sample_manifest_and_metadata(con=DB_CON):
    """Prepare the iSamples samples manifest table"""
    
    duck_funcs.define_duckdb_functions(con=con)
    # Get the raw samples table from the Postgres database.
    raw_samples.get_isamples_raw_manifest(con=con,)
    # Do an assertions query using the man table as a limit
    raw_samples.get_isamples_raw_asserts(con=con,)
    # Populate the sampling site columns
    sample_sites.get_isamples_sampling_sites(con=con)
    # Populate the space-time columns
    space_time.get_isamples_spacetime_values(con=con)
    # Get an object with the samples manifest.
    persons.get_all_isamples_dc_relations(con=con)
    db_m = con.sql(f'SELECT * FROM {duckdb_con.ISAMPLES_PREP_MANIFEST_TABLE}')
    db_m.show()
    return db_m


def prepare_isamples_pqg(con=DB_CON):
    """Prepare the iSamples PQG"""
    isamples_pqg.create_pqg_table(con=con)
    isamples_pqg.add_new_keys_to_tables(con=con)
    isamples_pqg.add_preliminary_material_types_to_man_table(con=con)
    isamples_pqg.update_material_types_in_man_tab_via_assertions(con=con)
    isamples_pqg.add_isamples_entities_to_pqg(con=con)
    isamples_pqg.add_edge_rows_to_pq(con=con)
    isamples_pqg.summarize_pqg(con=con)