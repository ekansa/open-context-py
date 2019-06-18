
from time import sleep
import uuid as GenUUID
import os, sys, shutil
import numpy as np
import pandas as pd
import xlrd

from django.conf import settings
from opencontext_py.apps.imports.kobotoolbox.contexts import (
    prepare_trench_contexts
)
from opencontext_py.apps.imports.kobotoolbox.utilities import (
    UUID_SOURCE_KOBOTOOLBOX,
    UUID_SOURCE_OC_KOBO_ETL,
    UUID_SOURCE_OC_LOOKUP,
    MULTI_VALUE_COL_PREFIXES,
    make_directory_files_df,
    list_excel_files,
    read_excel_to_dataframes,
    drop_empty_cols,
    reorder_first_columns,
    update_multivalue_col_vals,
    update_multivalue_columns,
    parse_opencontext_uuid,
    parse_opencontext_type,
    lookup_manifest_uuid,
)

CATALOG_ATTRIBUTES_SHEET = 'Catalog Entry'

"""Uses Pandas to prepare Kobotoolbox exports for Open Context import


import csv
from django.conf import settings
from opencontext_py.apps.imports.kobotoolbox.catalog import (
    CATALOG_ATTRIBUTES_SHEET,
    prepare_catalog
)

project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
excels_filepath = settings.STATIC_IMPORTS_ROOT +  'pc-2018/'
catalog_dfs = prepare_catalog(project_uuid, excel_dirpath)


"""

def prepare_catalog(project_uuid, excel_dirpath):
    """Prepares catalog dataframes."""
    dfs = None
    for excel_filepath in list_excel_files(excel_dirpath):
        if not 'Catalog' in excel_filepath:
            continue
        dfs = read_excel_to_dataframes(excel_filepath)
        df_f = dfs[CATALOG_ATTRIBUTES_SHEET]
        df_f = drop_empty_cols(df_f)
        df_f = update_multivalue_columns(df_f)
        dfs[CATALOG_ATTRIBUTES_SHEET] = df_f
    return dfs
        

    