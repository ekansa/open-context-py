import fnmatch
from time import sleep
import uuid as GenUUID
import os, sys, shutil
import codecs
import numpy as np
import pandas as pd

from django.db import models
from django.db.models import Q
from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.imports.kobotoolbox.utilities import (
    make_directory_files_df,
    list_excel_files,
    read_excel_to_dataframes,
    reorder_first_columns,
    drop_empty_cols,
)

"""Uses Pandas to prepare Kobotoolbox exports for Open Context import

import csv
from django.conf import settings
from opencontext_py.apps.imports.kobotoolbox.contexts import (

)
from opencontext_py.apps.imports.kobotoolbox.utilities import (
    make_directory_files_df,
    lookup_manifest_uuid
)

excels_filepath = settings.STATIC_IMPORTS_ROOT + 'pc-2018/'
project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'

df_files = make_directory_files_df(files_path)
df_all.to_csv(all_media_csv_path, index=False, quoting=csv.QUOTE_NONNUMERIC)

"""

SUBJECTS_COLS = [
    {
        'col': 'Trench ID',
        'class_uri': 'oc-gen:cat-trench',
        'prefix': 'Trench ' 
    },
    {
        'col': 'Unit ID',
        'class_uri': 'oc-gen:cat-exc-unit',
        'prefix': ''
    },
    {
        'col': 'Locus ID',
        'class_uri': 'oc-gen:cat-locus',
        'prefix': 'Locus '
    },
    'Locus ID',
    'Bulk ID',
    'Field Given Find ID',
    'Find Number',
    'Find ID'
    'Catalog ID (PC)',
]

PARENT_CONTEXTS = {
    'CB64': {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Civitate B',
        'trench-name': 'Civitate B64',
    },
    'T90': {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Tesoro',
        'trench-name': 'Tesoro 90',
    },
    'T91': {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Tesoro',
        'trench-name': 'Tesoro 91',
    },
    'T92': {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Tesoro',
        'trench-name': 'Tesoro 92',
    },
    'T93': {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Tesoro',
        'trench-name': 'Tesoro 93',
    },
    
}

def get_parent_context(context_key, parent_type, config=None):
    """Gets a parent context of a given type."""
    if config is None:
        config = PARENT_CONTEXTS
    key_dict = config.get(context_key)
    if key_dict is None:
        return None
    return key_dict.get(parent_type)

def make_trench_year_unit(trench_id, year):
    """Makes a trench_year excavation unit."""
    return '{} {}'.format(trench_id, year)

def prepare_trench_contexts(
    df,
    year,
    trench_id_col='Trench ID',
    child_context_cols=None
):
    """Prepares context information for a locus DF"""
    if child_context_cols is None:
        child_context_cols = ['Locus ID']
    p_contexts = ['region', 'site', 'area', 'trench-name']
    df['Unit ID'] = df[trench_id_col].apply(
        make_trench_year_unit,
        year=year
    )
    for p_context in p_contexts:
        df[p_context] = df[trench_id_col].apply(
            get_parent_context,
            parent_type=p_context
        )
    context_cols = (
        p_contexts +
        [trench_id_col, 'Unit ID',] +
        child_context_cols
    )
    # Put the context columns at the start of the dataframe.
    df = reorder_first_columns(df, context_cols)
    return df