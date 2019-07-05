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
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.imports.kobotoolbox.utilities import (
    UUID_SOURCE_KOBOTOOLBOX,
    UUID_SOURCE_OC_KOBO_ETL,
    UUID_SOURCE_OC_LOOKUP,
    LINK_RELATION_TYPE_COL,
    list_excel_files,
    read_excel_to_dataframes,
    drop_empty_cols,
    reorder_first_columns,
    lookup_manifest_uuid
)

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

PRELOAD_CONTEXTS = [
    {
        'region': 'Italy',
        'class_uri': 'oc-gen:cat-region',
        'label': 'Italy',
    },
    {
        'region': 'Italy',
        'site': 'Poggio Civitate',
        'class_uri': 'oc-gen:cat-site',
        'label': 'Poggio Civitate',
    },
    {
        'region': 'Italy',
        'site': 'Vescovado di Murlo',
        'class_uri': 'oc-gen:cat-site',
        'label': 'Vescovado di Murlo',
    },
    {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Civitate B',
        'class_uri': 'oc-gen:cat-area',
        'label': 'Civitate B',
    },
    {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Tesoro',
        'class_uri': 'oc-gen:cat-area',
        'label': 'Tesoro',
    },
    {
        'region': 'Italy',
        'site': 'Vescovado di Murlo',
        'area': 'Upper Vescovado',
        'class_uri': 'oc-gen:cat-area',
        'label': 'Upper Vescovado',
    },
    {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Civitate B',
        'trench_name': 'Civitate B64',
        'class_uri': 'oc-gen:cat-trench',
        'label': 'Civitate B64',
    },
    {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Civitate B',
        'trench_name': 'Civitate B65',
        'class_uri': 'oc-gen:cat-trench',
        'label': 'Civitate B65',
    },
    {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Tesoro',
        'trench_name': 'Tesoro 90',
        'class_uri': 'oc-gen:cat-trench',
        'label': 'Tesoro 90',
    },
    {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Tesoro',
        'trench_name': 'Tesoro 91',
        'class_uri': 'oc-gen:cat-trench',
        'label': 'Tesoro 91',
    },
    {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Tesoro',
        'trench_name': 'Tesoro 92',
        'class_uri': 'oc-gen:cat-trench',
        'label': 'Tesoro 92',
    },
    {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Tesoro',
        'trench_name': 'Tesoro 93',
        'class_uri': 'oc-gen:cat-trench',
        'label': 'Tesoro 93',
    },
]

PARENT_CONTEXTS = {
    'CB64': {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Civitate B',
        'trench_name': 'Civitate B64',
    },
    'CB65': {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Civitate B',
        'trench_name': 'Civitate B65',
    },
    'T90': {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Tesoro',
        'trench_name': 'Tesoro 90',
    },
    'T91': {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Tesoro',
        'trench_name': 'Tesoro 91',
    },
    'T92': {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Tesoro',
        'trench_name': 'Tesoro 92',
    },
    'T93': {
        'region': 'Italy',
        'site':'Poggio Civitate',
        'area': 'Tesoro',
        'trench_name': 'Tesoro 93',
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
    trench_id = trench_id.replace('-', '')
    return '{} {}'.format(trench_id, year)

def make_trench_year_unit_for_row(row):
    """Makes a trench_year excavation unit."""
    row['Trench ID'] = row['Trench ID'].replace('-', '')
    return '{} {}'.format(row['Trench ID'], row['Year'])

def prepare_trench_contexts(
    df,
    year,
    trench_id_col='Trench ID',
    child_context_cols=None
):
    """Prepares context information for a locus DF"""
    if child_context_cols is None:
        child_context_cols = ['Locus ID']
    p_contexts = ['region', 'site', 'area', 'trench_name']
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

def get_manifest_obj_from_parent(project_uuids, label, class_uri, parent_uuid):
    """Gets a uuid for an item based on label and class if an parent is known"""
    contain_rels = Assertion.objects.filter(
        project_uuid__in=project_uuids,
        uuid=parent_uuid,
        predicate_uuid=Assertion.PREDICATES_CONTAINS,
        object_type='subjects'
    )
    child_uuids = [a.object_uuid for a in contain_rels]
    man_obj = Manifest.objects.filter(
        label=label,
        uuid__in=child_uuids,
        project_uuid__in=project_uuids,
        class_uri=class_uri,
        item_type='subjects'
    ).first()
    return man_obj

def get_unit_manifest_obj(project_uuids, label, class_uri, contexts):
    if class_uri != 'oc-gen:cat-exc-unit':
        return None
    if not ' ' in label:
        # We don't know how to deal with this. No space
        return None
    l_parts = label.split(' ')
    if len(l_parts) != 2:
        # We don't know what to do.
        return None
    trench_part = l_parts[0]
    year = l_parts[1]
    parts = [label]
    for f, r in UNIT_LABEL_REPLACES:
        parts.append((trench_part.lower().replace(f, r).strip()))

    # De-duplicate the parts.
    parts = list(set(parts))
    print('Check Unit {}, year {} with parts {}'.format(label, year, parts))
    sub_uuids = []
    for part in parts:
        subs = Subject.objects.filter(
            project_uuid__in=project_uuids,
            context__contains=part
        ).filter(
            context__contains=year
        )
        sub_uuids += [s.uuid for s in subs]
    # Now query for the manifest items that may be related.
    man_objs = Manifest.objects.filter(
        (Q(label__contains=label)|Q(label__contains=year)),
        uuid__in=sub_uuids,
        project_uuid__in=project_uuids,
        class_uri=class_uri,
        item_type='subjects'
    )
    if len(man_objs) == 1:
        # The happy scenario where we find what we want without ambiguity.
        return man_objs[0]
    if len(man_objs) > 1:
        # Not great, too many potential matches
        poss_labels = [m.label for m in man_objs]
        print('Too many potential {} units - found (): {}.'.format(
                label,
                len(poss_labels),
                poss_labels
            )
        )
    return None
    
def get_context_manifest_obj(
    project_uuid,
    label,
    class_uri,
    contexts,
    parent_uuid=None,
):
    """Gets a manifest object for a subjects (context) item"""
    man_obj = None
    project_uuids = ['0', project_uuid]
    if parent_uuid is not None:
        man_obj = get_manifest_obj_from_parent(
            project_uuids,
            label,
            class_uri,
            parent_uuid
        )
    if man_obj is not None:
        # Our work is done . :)
        return man_obj
    context = '/'.join([c.strip() for c in contexts if isinstance(c, str)])
    subs = Subject.objects.filter(
        project_uuid__in=project_uuids,
        context=context
    )
    sub_uuids = [s.uuid for s in subs]
    man_obj = Manifest.objects.filter(
        uuid__in=sub_uuids,
        project_uuid__in=project_uuids,
        class_uri=class_uri,
        item_type='subjects'
    ).first()
    if man_obj is None and class_uri == 'oc-gen:cat-exc-unit':
        # Try special lookups for units.
        man_obj = get_unit_manifest_obj(
            project_uuids,
            label,
            class_uri,
            contexts
        )
    if man_obj is None and class_uri == 'oc-gen:cat-locus':
        # Try special lookups for units.
        man_obj = get_unit_manifest_obj(
            project_uuids,
            label,
            class_uri,
            contexts
        )
    return man_obj

def get_make_context_uuid(project_uuid, label, class_uri, contexts, parent_uuid=None):
    """Gets or makes a uuid for a subjects (context) item"""
    man_obj = get_context_manifest_obj(
        project_uuid,
        label,
        class_uri,
        contexts,
        parent_uuid
    )
    if man_obj is not None:
        uuid = man_obj.uuid
        uuid_source = UUID_SOURCE_OC_LOOKUP
    else:
        uuid = str(GenUUID.uuid4())
        uuid_source = UUID_SOURCE_OC_KOBO_ETL
    return uuid, uuid_source

def get_make_context_uuid_for_row(
    project_uuid,
    row,
    path_context_cols=PATH_CONTEXT_COLS
):
    """Gets or makes a uuid for a subjects (context) item"""
    contexts = [row[c] for c in path_context_cols if c in row]
    uuid, uuid_source = get_make_context_uuid(
        project_uuid,
        row['label'],
        row['class_uri'],
        contexts
    )
    return uuid, uuid_source

def df_parent_uuid_lookup_for_row(
    row,
    parents_df,
    path_context_cols=PATH_CONTEXT_COLS
):
    """Gets or makes a uuid for a subjects (context) item"""
    # Get the filter conditions for the parent item based on the matching
    # filter criteria for parent context columns.
    filter_list = []
    print_filters = []
    for c in path_context_cols:
        if not c in row or not c in parents_df:
            continue
        if row[c] == row['label']:
            filter_list.append((parents_df[c].isnull()))
            print_filters.append('{}: np.nan'.format(c))
            continue
        elif isinstance(row[c], str):
            filter_list.append((parents_df[c] == row[c]))
            print_filters.append('{}: {}'.format(c, row[c]))
        else:
            filter_list.append((parents_df[c].isnull()))
            print_filters.append('{}: np.nan'.format(c))
    # Skip out if we're looking up a parent_uuid for a root item.
    if len(filter_list) < 2:
        return np.nan, np.nan
    # Combine the filter conditions together.
    parent_indx = np.logical_and.reduce(filter_list)
    if parents_df[parent_indx].empty:
        # No parent found, return np.nan
        print('Empty parent look up of: {}  - has filters: {}'.format(row['label'], print_filters))
        return np.nan, np.nan
    parent_uuid = parents_df[parent_indx]['context_uuid'].iloc[0]
    parent_uuid_source = parents_df[parent_indx]['uuid_source'].iloc[0]
    return parent_uuid, parent_uuid_source

def update_all_context_df_with_parent_uuids(final_all_contexts_df):
    """Updates the all_context df to have parent uuids."""
    # Use the dataframe to assign parent uuids based on path lookups.
    context_uuid_parents = []
    parents_df = final_all_contexts_df.copy().reset_index(drop=True)
    for i, row in final_all_contexts_df.iterrows():
        if (row['parent_uuid_source'] == UUID_SOURCE_OC_LOOKUP
            and row['uuid_source'] == UUID_SOURCE_OC_LOOKUP):
            # Skip, because we already have looked up relations from
            # Open Context.
            continue
        # Do the lookup of parent_uuid from this dataframe as the source.
        parent_uuid, parent_uuid_source = df_parent_uuid_lookup_for_row(
            row,
            parents_df
        )
        if not isinstance(parent_uuid, str):
            # We found nothing, continue.
            continue
        context_uuid_parents.append((row['context_uuid'], parent_uuid, parent_uuid_source))
    
    # For some reason we need to do this convoluted way of updating the data frame
    # to have parent ids.
    for context_uuid, parent_uuid, parent_uuid_source in context_uuid_parents:
        if not isinstance(parent_uuid, str):
            continue
        context_indx = (final_all_contexts_df['context_uuid'] == context_uuid)
        final_all_contexts_df.loc[context_indx, 'parent_uuid'] = parent_uuid
        final_all_contexts_df.loc[context_indx, 'parent_uuid_source'] = parent_uuid_source
    return final_all_contexts_df

def preload_contexts_to_df(
    project_uuid,
    context_cols=FIRST_CONTEXT_COLS,
    preload_contexts=PRELOAD_CONTEXTS
):
    """Make an all_context_df by reloading contexts."""
    data = {c:[] for c in context_cols}
    for p_context in preload_contexts:
        for col in context_cols:
            data[col].append(p_context.get(col))
    all_contexts_df = pd.DataFrame(data=data)
    all_contexts_df = all_contexts_df[context_cols]
    for i, row in all_contexts_df.iterrows():
        uuid, uuid_source = get_make_context_uuid_for_row(
            project_uuid,
            row
        )
        row['context_uuid'] = uuid
        row['uuid_source'] = uuid_source
    # Fill in all the None or Null values with np.nan.
    all_contexts_df.fillna(value=np.nan, inplace=True)
    return all_contexts_df            

def fill_in_oc_context_paths(
    uuid,
    df_indx,
    df,
    path_context_cols=PATH_CONTEXT_COLS
):
    """Adds context path values for path_contexts."""
    if not isinstance(uuid, str):
        return df
    sub = Subject.objects.filter(uuid=uuid).first()
    if sub is None:
        return df
    context_items = sub.context.split('/')
    for i, context in enumerate(context_items):
        if i >= len(path_context_cols):
            continue
        col = path_context_cols[i]
        df.loc[df_indx, col] = context
    return df     

def update_all_context_df_with_unit_rows(project_uuid, final_all_contexts_df, unit_name_col='unit_name'):
    """Adds rows for Unit ID entities."""
    unit_context_cols = [unit_name_col]
    # Filter to only include rows with unit_name values.
    df_units = final_all_contexts_df[~final_all_contexts_df[unit_name_col].isnull()]
    # Group so we have unique unit_names.
    df_grp = df_units.groupby(unit_context_cols, as_index=False).first()
    df_grp = df_grp[FIRST_CONTEXT_COLS]
    df_grp['label'] = df_grp[unit_name_col]
    df_grp['context_uuid'] = np.nan
    df_grp['uuid_source'] = np.nan
    df_grp['class_uri'] = UNIT_CLASS_URI
    df_grp['parent_uuid'] = np.nan
    df_grp['parent_uuid_source'] = np.nan
    # Set child contexts to the unit to np.nan.
    for col in PATH_CONTEXT_COLS:
        if not 'locus' in col:
            continue
        df_grp[col] = np.nan
    # Look up unit uuids.
    unit_uuids = []
    for i, row in df_grp.iterrows():
        uuid, uuid_source = get_make_context_uuid_for_row(
            project_uuid,
            row
        )
        if ((not isinstance(row['trench_name'], str))
            and uuid_source != UUID_SOURCE_OC_LOOKUP):
            # We've got a reference to a unit that is not known, and
            # not definitively part of the current import. So skip
            # updating the unit's context ID.
            continue
        unit_uuids.append((row['label'], uuid, uuid_source))
    
    # Now update the df_grp to have the units
    for unit, uuid, uuid_source in unit_uuids:
        unit_indx = (df_grp['label'] == unit)
        df_grp.loc[unit_indx, 'context_uuid'] = uuid
        df_grp.loc[unit_indx, 'uuid_source'] = uuid_source
        df_grp = fill_in_oc_context_paths(uuid, unit_indx, df_grp)
    
    # Append the units to the main dataframe. 
    final_all_contexts_df = final_all_contexts_df.append(
        df_grp,
        ignore_index=True
    )
    return final_all_contexts_df
    
def update_all_context_df_with_missing_locus_rows(
    project_uuid,
    final_all_contexts_df,
    unit_name_col='unit_name',
    locus_name_col='locus_name'
):
    """Upates mising locus columns based on lookups of units."""
    loci_indx = (~final_all_contexts_df[locus_name_col].isnull())
    df_loci = final_all_contexts_df[loci_indx]
    df_grp = df_loci.groupby(
        [unit_name_col, locus_name_col],
        as_index=False
    ).first()
    df_grp = df_grp[FIRST_CONTEXT_COLS]
    df_grp = df_grp[~(df_grp['class_uri'] == 'oc-gen:cat-locus')]
    # Drop duplicated units and loci
    df_grp.drop_duplicates(
        subset=[unit_name_col, locus_name_col],
        inplace=True
    )
    df_grp['label'] = df_grp[locus_name_col]
    df_grp['context_uuid'] = np.nan
    df_grp['uuid_source'] = np.nan
    df_grp['class_uri'] = 'oc-gen:cat-locus'
    df_grp['parent_uuid'] = np.nan
    df_grp['parent_uuid_source'] = np.nan
    
    # Look up unit uuids.
    loci_uuids = []
    for i, row in df_grp.iterrows():
        unit_indx = (
            (final_all_contexts_df['label']==row[unit_name_col])
            &
            (final_all_contexts_df['class_uri']==UNIT_CLASS_URI)
        )
        df_unit = final_all_contexts_df[unit_indx]
        parent_uuid = df_unit['context_uuid'].iloc[0]
        parent_uuid_source = df_unit['uuid_source'].iloc[0]
        uuid, uuid_source = get_make_context_uuid(
            project_uuid,
            row['label'],
            row['class_uri'],
            [],
            parent_uuid=parent_uuid
        )
        locus_tups = (
            row['label'],
            row[unit_name_col],
            uuid,
            uuid_source,
            parent_uuid,
            parent_uuid_source
        )
        loci_uuids.append(locus_tups)
    
    # Now update the df_grp to have the locus uuid information.
    for label, unit, uuid, uuid_source, parent_uuid, parent_uuid_source in loci_uuids:
        locus_indx = (
            (df_grp['label'] == label)
            & (df_grp[unit_name_col] == unit)
        )
        if not isinstance(parent_uuid, str):
            uuid = np.nan
            uuid_source = np.nan
        df_grp.loc[locus_indx, 'context_uuid'] = uuid
        df_grp.loc[locus_indx, 'uuid_source'] = uuid_source
        df_grp.loc[locus_indx, 'parent_uuid'] = parent_uuid
        df_grp.loc[locus_indx, 'parent_uuid_source'] = parent_uuid_source
        df_grp.loc[locus_indx, 'locus_content_name'] = np.nan
        df_grp = fill_in_oc_context_paths(uuid, locus_indx, df_grp)
    
    # Append the units to the main dataframe. 
    final_all_contexts_df = final_all_contexts_df.append(
        df_grp,
        ignore_index=True
    )
    return final_all_contexts_df
    

def compose_label_from_row(row, template, temp_cols):
    """Composes a label frow a row based on a template and template cols"""
    label_args = [
        str(row[c]).replace('-', '').strip() for c in temp_cols if c in row
    ]
    if len(label_args) != len(temp_cols):
        return np.nan
    label = template.format(*label_args)
    for f, r in CONTEXT_LABEL_REPLACES:
        label = label.replace(f, r)
    return label

def prepare_all_contexts(
    project_uuid,
    year,
    source_dfs,
    all_contexts_df=None,
    context_sources=CONTEXT_SOURCES,
    parent_contexts=PARENT_CONTEXTS,
):
    """Prepares a dataframe of all the contexts (subject) items for this ETL"""
    p_contexts = ['region', 'site', 'area', 'trench_name']
    if all_contexts_df is None:
        all_contexts_df = preload_contexts_to_df(project_uuid)
    dfs_list = [all_contexts_df]
    for source_key, source_df in source_dfs.items():
        source_config = context_sources[source_key]
        if not 'Year' in source_df.columns:
            source_df['Year'] = year
        # Generate the Unit ID column from the Trench ID and
        # the Year.
        source_df['Unit ID'] = source_df.apply(
            make_trench_year_unit_for_row, axis=1
        )
        source_df['unit_name'] = source_df['Unit ID']
        source_df['context_uuid'] = source_df['_uuid']
        source_df['uuid_source'] = UUID_SOURCE_KOBOTOOLBOX
        source_df['class_uri'] = source_config['class_uri']
        # Update class_uri values from the default depending on
        # onfigured mappings for different columns.
        for col, class_mappings in COL_CLASS_URI_MAPPINGS.items():
            if not col in source_df.columns:
                continue
            for col_value, new_class_uri in class_mappings:
                ch_indx = (source_df[col] == col_value)
                source_df.loc[ch_indx, 'class_uri'] = new_class_uri
        # Use tempate rules defined in source_config to and the
        # compose_label_from_row function to make an item label
        for label_col, template_config in source_config['templates'].items():
            source_df[label_col] = source_df.apply(
                compose_label_from_row,
                template=template_config['template'],
                temp_cols=template_config['temp_cols'],
                axis=1
            )
        # Copy the label to the last (deepest, most specific)
        # context column
        source_df[
            source_config['last_context_col']
        ] = source_df['label']
            
        # Add parent contexts for Trench IDs.
        for p_context in p_contexts:
            source_df[p_context] = source_df['Trench ID'].apply(
                get_parent_context,
                parent_type=p_context
            )
        for col in FIRST_CONTEXT_COLS:
            if col in source_df.columns:
                continue
            source_df[col] = np.nan
        # Fill in all null, or None values with np.nan
        source_df.fillna(value=np.nan, inplace=True)
        # Get columns from the source dataframe relating to
        # conext information.
        source_df = source_df[
            (
                FIRST_CONTEXT_COLS + 
                source_config['cols']
            )
        ]
        dfs_list.append(source_df)
    
    # Now compose the full context dataframe from the parts in the dfs_list.
    final_all_contexts_df = pd.concat(dfs_list)
    final_all_contexts_df.drop_duplicates(subset=['context_uuid'], inplace=True)
    # Fill in all the None or Null values with np.nan.
    final_all_contexts_df.fillna(value=np.nan, inplace=True)
    
    # Append excavation units to the main dataframe.
    final_all_contexts_df = update_all_context_df_with_unit_rows(
        project_uuid,
        final_all_contexts_df
    )
    
    # Add locus information to the main dataframe
    final_all_contexts_df = update_all_context_df_with_missing_locus_rows(
        project_uuid,
        final_all_contexts_df
    )
    
    # Add parent_uuid values 
    final_all_contexts_df = update_all_context_df_with_parent_uuids(
        final_all_contexts_df
    )
    
    # Now sort the contexts for a predictable 
    final_all_contexts_df.sort_values(
        by=(PATH_CONTEXT_COLS + ['label']),
        inplace=True,
        na_position='first'
    )
    # Final sorting of the output columns.
    final_all_contexts_df = reorder_first_columns(
        final_all_contexts_df,
        FIRST_CONTEXT_COLS
    )
    return final_all_contexts_df
        

def context_sources_to_dfs(
    excel_dirpath,
    context_sources=CONTEXT_SOURCES
):
    """Loads sources of context data into data frames"""
    source_dfs = {}
    for excel_filepath in list_excel_files(excel_dirpath):
        dfs = read_excel_to_dataframes(excel_filepath)
        for source_key, _ in context_sources.items():
            if not source_key in dfs:
                continue
            source_dfs[source_key] = dfs[source_key]
    return source_dfs
