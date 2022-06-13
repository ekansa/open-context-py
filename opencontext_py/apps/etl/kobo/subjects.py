import uuid as GenUUID
import numpy as np
import pandas as pd

from django.db.models import Q
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.etl.kobo import utilities



"""Uses Pandas to prepare Kobotoolbox exports for Open Context import

import csv
from django.conf import settings
from opencontext_py.apps.imports.kobotoolbox.contexts import (
    context_sources_to_dfs,
    preload_contexts_to_df,
    prepare_all_contexts
)

excels_filepath = settings.STATIC_IMPORTS_ROOT + 'pc-2018/'
all_contexts_path = settings.STATIC_IMPORTS_ROOT +  'pc-2018/all-contexts-subjects.csv'
project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
all_contexts_df = preload_contexts_to_df(project_uuid)
source_dfs = context_sources_to_dfs(excels_filepath)
all_contexts_df = prepare_all_contexts(project_uuid, 2018, source_dfs)
all_contexts_df.to_csv(all_contexts_path, index=False, quoting=csv.QUOTE_NONNUMERIC)

"""
# Columns that define the context path for an item 
PATH_CONTEXT_COLS = [
    'region',
    'site',
    'area',
    'trench_name',
    'unit_name',
    'locus_name',
    'locus_content_name',
]

# Columns for the all_contexts_df that should come first
FIRST_CONTEXT_COLS = [
    'label',
    'context_uuid',
    'uuid_source',
    'class_uri',
    'parent_uuid',
    'parent_uuid_source',
] + PATH_CONTEXT_COLS


UNIT_CLASS_URI = 'oc-gen:cat-exc-unit'

# List of string replace arguments to cleanup
# labels generated from templates.
CONTEXT_LABEL_REPLACES = [
    (' (not tile)', ''),
    (' element', ''),
    ('PC', 'PC '),
    ('pc', 'PC '),
    ('PC  ', 'PC '),
    ('VDM', 'VdM '),
    ('vdm', 'VdM '),
    ('Vdm', 'VdM '),
    ('VdM  ', 'VdM '),
    ('  ', ' '),
]

UNIT_LABEL_REPLACES = [
      ('vt', 'Vescovado ',),
      ('vdm', 'Vescovado ',),
      ('cd8', 'Civitate D 8',),
      ('t25', 'Tesoro 25',),
      ('t62', 'Tesoro 62',),
      ('t89', 'Tesoro 89',),
      ('tr7', 'Tesoro Rectangle 7'),
]

# Override the general class_uri with a tuple of
# column - value -> class_uri mappings
COL_CLASS_URI_MAPPINGS = {
    'Object General Type': [
        ('Architectural', 'oc-gen:cat-arch-element',),
        ('Vessel', 'oc-gen:cat-pottery',),
    ],
}

CONTEXT_SOURCES = {
    'Locus Summary Entry': {
        'cols': ['Year', 'Trench ID', 'Unit ID', 'Locus ID'],
        'class_uri': 'oc-gen:cat-locus',
        'templates': {
            'label': {
                'template': 'Locus {}',
                'temp_cols': ['Locus ID'],
            },
        },
        'last_context_col': 'locus_name',
    },
    'Field Bulk Finds Entry': {
        'cols': ['Year', 'Trench ID', 'Unit ID', 'Locus ID', 'Bulk ID', 'Find Type'],
        'class_uri': 'oc-gen:cat-sample-col',
        'templates': {
            'label': {
                'template': 'Bulk {}-{}-{}-{}-{}',
                'temp_cols': [
                    'Find Type',
                    'Year',
                    'Trench ID',
                    'Locus ID',
                    'Bulk ID'
                ],
            },
            'locus_name': {
                'template': 'Locus {}',
                'temp_cols': ['Locus ID'],
            },
        },
        'last_context_col': 'locus_content_name',
    },
    'Field Small Find Entry': {
        'cols': ['Year', 'Trench ID', 'Unit ID', 'Locus ID', 'Find Number'],
        'class_uri': 'oc-gen:cat-sample',
        'templates': {
            'label': {
                'template': 'SF {}-{}-{}-{}',
                'temp_cols': [
                    'Year',
                    'Trench ID',
                    'Locus ID',
                    'Find Number',
                ],
            },
            'locus_name': {
                'template': 'Locus {}',
                'temp_cols': ['Locus ID'],
            },
        },
        'last_context_col': 'locus_content_name',
    },
    'Catalog Entry': {
        'cols': ['Year', 'Trench ID', 'Unit ID', 'Locus ID', 'Catalog ID (PC)', 'Object General Type'],
        'class_uri': 'oc-gen:cat-object',
        'templates': {
            'label': {
                'template': '{}',
                'temp_cols': ['Catalog ID (PC)'],
            },
            'locus_name': {
                'template': 'Locus {}',
                'temp_cols': ['Locus ID'],
            },
        },
        'last_context_col': 'locus_content_name',
    },
}


def make_subjects_df(excel_dirpath, trench_csv_path):
    xlsx_files = utilities.list_excel_files(excel_dirpath)
    if not xlsx_files:
        return None
    for excel_filepath in xlsx_files:
        dfs = utilities.read_excel_to_dataframes(excel_filepath)