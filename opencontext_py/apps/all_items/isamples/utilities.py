import copy
import duckdb
from duckdb.typing import *

from django.conf import settings

import uuid as GenUUID

import numpy as np
import pandas as pd


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
)




def cast_duckdb_uuid(uuid):
    """Convert a manifest object to a DuckDB compatible UUID string"""
    return f"CAST('{str(uuid)}' AS UUID)"


def cast_man_obj_duckdb_uuid(man_obj):
    """Convert a manifest object to a DuckDB compatible UUID string"""
    return cast_duckdb_uuid(man_obj.uuid)
