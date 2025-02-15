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
from opencontext_py.apps.all_items.isamples import raw_samples
from opencontext_py.apps.all_items.isamples import sample_sites

"""
# Testing
import importlib
from opencontext_py.apps.all_items.isamples import prep_isamples
importlib.reload(prep_isamples)

import time

start = time.time()
db_m = prep_isamples.prepare_sample_manifest()
end = time.time()
print(end-start)


"""

DB_CON = duckdb_con.create_duck_db_postgres_connection()

def prepare_sample_manifest(alias='man', con=DB_CON):
    """Prepare the iSamples samples manifest table"""
    
    # Get the raw samples table from the Postgres database.
    raw_samples.get_isamples_raw_manifest(con=con, alias=alias)
    # Populate the sampling site columns
    sample_sites.get_isamples_sampling_sites(con=con)
    # Get an object with the samples manifest.
    db_m = con.sql(f'SELECT * FROM {alias}').set_alias(alias)
    db_m.show()
    return db_m


        