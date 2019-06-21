import csv
import uuid as GenUUID
import os, sys, shutil
import codecs
import numpy as np
import pandas as pd

from django.db import models
from django.db.models import Q
from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.subjects.models import Subject

from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.sources.models import ImportSource

from opencontext_py.apps.imports.kobotoolbox.utilities import (
    UUID_SOURCE_KOBOTOOLBOX,
    UUID_SOURCE_OC_KOBO_ETL,
    UUID_SOURCE_OC_LOOKUP,
    list_excel_files,
    read_excel_to_dataframes,
    make_directory_files_df,
    drop_empty_cols,
    reorder_first_columns,
    lookup_manifest_uuid,
)




def process_hiearchy_col_values(df, delim='::'):
    """Processes columns with hierarchy values."""
    # NOTE: this assumes only 2 level hiearchies in column names
    hiearchy_preds = {}
    for col in df.columns.tolist():
        if not delim in col:
            continue
        col_parts = col.split(delim)
        pred_label = col_parts[0].strip()
        parent_val = col_parts[-1].strip()
        if not pred_label in hiearchy_preds:
            hiearchy_preds[pred_label] = []
        hiearchy_preds[pred_label].append(col)
        change_indx = (~df[col].isnull())
        df.loc[change_indx, col] = parent_val + delim + df[col]
        df.rename(
            columns={
                col: (pred_label + '/{}'.format(len(hiearchy_preds[pred_label])))
            },
            inplace=True
        )
    return df
    

def load_attribute_data_to_importer(df):
    pass


    


    