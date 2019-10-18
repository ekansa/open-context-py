
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
    LINK_RELATION_TYPE_COL,
    MULTI_VALUE_COL_PREFIXES,
    make_directory_files_df,
    list_excel_files,
    read_excel_to_dataframes,
    drop_empty_cols,
    reorder_first_columns,
    update_multivalue_col_vals,
    update_multivalue_columns,
    clean_up_multivalue_cols,
    parse_opencontext_uuid,
    parse_opencontext_type,
    lookup_manifest_uuid,
)

FILENAME_ATTRIBUTES_LOCUS ='attributes--field-locus.csv'
FILENAME_ATTRIBUTES_BULK_FINDS = 'attributes--field-bulk-finds.csv'
FILENAME_ATTRIBUTES_SMALL_FINDS = 'attributes--field-small-finds.csv'
FILENAME_ATTRIBUTES_TRENCH_BOOKS = 'attributes--field-trench-book.csv'


"""Uses Pandas to prepare Kobotoolbox exports for Open Context import


import csv
from django.conf import settings
from opencontext_py.apps.imports.kobotoolbox.preprocess import (
    make_locus_stratigraphy_df,
    prep_field_tables,
    make_final_trench_book_relations_df
)
from opencontext_py.apps.imports.kobotoolbox.utilities import (
    list_excel_files,
    read_excel_to_dataframes,
)

project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
excels_filepath = settings.STATIC_IMPORTS_ROOT +  'pc-2018/'
excels = list_excel_files(excels_filepath)
excel_filepath = settings.STATIC_IMPORTS_ROOT +  'pc-2018/Locus Summary Entry - latest version - labels - 2019-05-27-22-32-06.xlsx'

# dfs = read_excel_to_dataframes(excel_filepath)
# df_strat = make_locus_stratigraphy_df(dfs)
# strat_path = settings.STATIC_IMPORTS_ROOT +  'pc-2018/locus-stratigraphy.csv'
# df_strat.to_csv(strat_path, index=False)
field_config_dfs = prep_field_tables(excels_filepath, project_uuid, 2018)
for act_sheet, act_dict_dfs in field_config_dfs.items():
    file_path =  excels_filepath + act_dict_dfs['file']
    df = act_dict_dfs['dfs'][act_sheet]
    df.to_csv(file_path, index=False, quoting=csv.QUOTE_NONNUMERIC)

tb_dfs = field_config_dfs['Trench Book Entry']['dfs']
tb_all_rels_df = make_final_trench_book_relations_df(field_config_dfs)
tb_all_rels_path = settings.STATIC_IMPORTS_ROOT +  'pc-2018/trench-book-relations.csv'
tb_all_rels_df.to_csv(tb_all_rels_path, index=False, quoting=csv.QUOTE_NONNUMERIC)


"""

FIELD_DATA_PREPS = {
    'Locus Summary Entry': {
        'file': 'attributes--field-locus.csv',
        'child_context_cols': ['Locus ID'],
    },
    'Field Bulk Finds Entry': {
        'file': FILENAME_ATTRIBUTES_BULK_FINDS,
        'child_context_cols': ['Locus ID', 'Bulk ID'],
    },
    'Field Small Find Entry':  {
        'file': FILENAME_ATTRIBUTES_SMALL_FINDS,
        'child_context_cols': ['Locus ID', 'Find Number'],
    },
    'Trench Book Entry':   {
        'file': FILENAME_ATTRIBUTES_TRENCH_BOOKS,
        'child_context_cols': [],
        'tb_new_title': 'Trench Book Title',
        'tb_doc_type': ('Document Type', 'Trench Book Entry',),
        'tb_doc_type_root': ('Document Type', 'Trench Book',),
        'tb_entry_year': 'Entry Year',
        'tb_root_year': 'Book Year',
        'tb_root_entry': ('Entry Text', (
            '<p>A "trench book" provides a narrative account of '+
            'excavations activities and initial (preliminary) ' +
            'interpretations. Trench book documentation can provide ' +
            'key information about archaeological context. To ' +
            'facilitate discovery, access, and use, the project\'s ' +
            'hand-written trench books have been transcribed and ' +
            'associated with other data.</p> ' +
            '<br/> ' +
            '<p>The links below provide transcriptions of the entries ' +
            'for this trench book.</p>'
        )),
    },
}


LOCUS_STRAT_FIELDS = [
    'group_strat_same',
    'group_strat_other',
    'group_strat_contemp',
    'group_strat_above',
    'group_strat_below',
    'group_strat_over',
    'group_strat_cuts'
]

LOCUS_CONTEXT_COLS = [
    'Trench',
    'Trench ID',
    'Unit ID',
    'Locus ID',
]

TRENCH_BOOK_PREVIOUS_REL = ''

TRENCH_BOOK_CONTEXT_COLS = [
    'Trench ID',
    'Unit ID'
]

TRENCH_BOOK_ROOT_GROUPS = [
    'region',
    'site',
    'area',
    'trench_name',
    'Trench ID',
    'Unit ID',
    'Trench Supervisor'
]

# These columns uniquely describe a trench book entry.
# They are useful for look ups of a given trench book.
TRENCH_BOOK_INDEX_COLS = [
    'Trench Book Title',
    'Date Documented',
    'Start Page',
    'End Page',
]

TRENCH_BOOK_REL_CONFIGS = {
    'tb-locus-links': {
        'tb_entry_sheet': 'Trench Book Entry',
        'tb_rel_sheet': 'group_rel_locus',
        'tb_rel_col': 'Related Locus / Loci (Discussed in this entry)/Related Locus',
        'tb_rel_col_rename': 'object__Locus ID',
        'tb_rel_link_type': 'Related Open Locus',
    },
    'tb-finds-links': {
        'tb_entry_sheet': 'Trench Book Entry',
        'tb_rel_sheet': 'group_rel_find',
        'tb_rel_col': 'Related Find(s) (Discussed in this entry)/Related Find',
        'tb_rel_col_rename': 'object__Find Number',
        'tb_rel_link_type': 'Related Small Find',
    },
}

TRENCH_BOOK_REL_UUID_CONFIGS = {
    'tb-locus-links': {
        'lookup_sheet': 'Locus Summary Entry',
        'index_cols': {
            'Unit ID': 'object__Unit ID',
            'Locus ID': 'object__Locus ID',
        },
        'final_renames': {
            'Trench Book Title': 'subject__Trench Book Title'
        },
    },
    'tb-finds-links': {
        'lookup_sheet': 'Field Small Find Entry',
        'index_cols': {
            'Unit ID': 'object__Unit ID',
            'Find Number': 'object__Find Number',
        },
        'final_renames': {
            'Trench Book Title': 'subject__Trench Book Title'
        },
    }
}

TRENCH_BOOK_FINAL_REL_COLS = [
    'Date Documented',
    'Start Page',
    'End Page',
    'Trench ID',
    'Trench Book Title',
    
    'subject__Trench Book Title',
    'subject__Trench Supervisor',
    'subject__Unit ID',
    'subject_uuid_source',
    'subject_uuid',
    
    LINK_RELATION_TYPE_COL,
    
    'object_uuid',
    'object_uuid_source',
    'object__Trench Supervisor',
    'object__Unit ID',
    'object__Trench ID',
    'object__Locus ID',
    'object__Find Number',
    'object__subject__Trench Book Title'
]

# Columns found in related sheets that can be dropped
RELATED_SHEET_DROP_COLS = [
    '_index',
    '_parent_table_name',
    '_parent_index',
    '_submission__id',
    '_submission__submission_time',
]

SKIP_MULTI_VALUE_REDACTIONS = [
    'Trench Supervisor'
]
        
def look_up_parent(parent_sheet, parent_uuid, dfs, parent_uuid_col='_uuid'):
    """Looks up and returns a 1 record dataframe of the record for the parent item."""
    df_parent = dfs[parent_sheet][
        dfs[parent_sheet]['_uuid'] == parent_uuid
    ].copy().reset_index(drop=True)
    return df_parent

def lookup_related_locus(
    rel_locus_id,
    parent_sheet,
    parent_locus_uuid,
    dfs,
    context_delim='/'
):
    """Looks up a related locus on the parent sheet, and returns a dictionary of relevant data for the locus"""
    df_parent = look_up_parent(parent_sheet, parent_locus_uuid, dfs)
    if df_parent.empty:
        raise RuntimeError('Parent locus uuid {} not found.'.format(parent_locus_uuid))
    orig_rel_locus_id = rel_locus_id
    rel_locus_id = str(rel_locus_id)
    trench_id = str(df_parent['Trench ID'].iloc[0])
    if context_delim in rel_locus_id:
        locus_ex = rel_locus_id.split(context_delim)
        trench_id = locus_ex[0].strip()
        rel_locus_id = locus_ex[1].strip()
    df = dfs[parent_sheet]
    df['Trench ID'] = df['Trench ID'].astype(str)
    df['Locus ID'] = df['Locus ID'].astype(str)
    df_rel = df[
        (df['Trench ID'] == trench_id) & (df['Locus ID'] == rel_locus_id)
    ].copy().reset_index(drop=True)
    df_rel['object__Locus ID'] = orig_rel_locus_id
    df_rel['object__Locus ID'] = df_rel['object__Locus ID'].astype(str)
    df_rel['subject_uuid'] = parent_locus_uuid
    return df_rel

def merge_context_df(
    df,
    df_context,
    key_cols,
    context_cols,
    rename_prefix
):
    """Merges a df_context with a df"""
    df_context = df_context[(context_cols + key_cols)]
    renames = {
        c: (rename_prefix + c)
        for c in df_context.columns
        if (not c in key_cols) and ((rename_prefix + c) not in df_context.columns)
    }
    df_context.rename(columns=renames, inplace=True)
    df_output = pd.merge(
        df,
        df_context,
        how='left',
        on=key_cols
    )
    return df_output

def make_loci_stratigraph_cols(df, context_cols=None):
    """Makes a list of loci stratigraphy columns in the expected order"""
    if context_cols is None:
        context_cols = LOCUS_CONTEXT_COLS
    strata_cols = [('subject__' + c) for c in context_cols]
    strata_cols += ['subject_uuid', LINK_RELATION_TYPE_COL]
    strata_cols += [('object__' + c) for c in context_cols]
    strata_cols += ['object_uuid']
    final_cols = [c for c in strata_cols if c in df.columns]
    return final_cols

def join_related_uri_loci_df(dfs, sheet, context_cols=None):
    df = dfs[sheet].copy().reset_index(drop=True)
    df.rename(
        columns={
            'Stratigraphy: Relation with Prior Season Locus/Relation Type': LINK_RELATION_TYPE_COL,
            'Stratigraphy: Relation with Prior Season Locus/URL to Locus': 'rel_uri',
            '_submission__uuid': 'subject_uuid',
        },
        inplace=True
    )
    df['object_uuid'] = df['rel_uri'].apply(parse_opencontext_uuid)
    df_parents = []
    if context_cols is None:
        context_cols = LOCUS_CONTEXT_COLS
    for i, row in df.iterrows():
        df_parent = look_up_parent(
            row['_parent_table_name'],
            row['subject_uuid'],
            dfs
        )
        df_parent = df_parent[(context_cols + ['_uuid'])]
        df_parents.append(df_parent)
    # Now combine all the related data
    df_all_parents = pd.concat(df_parents)
    df_all_parents.drop_duplicates(inplace=True)
    df_all_parents.rename(
        columns={'_uuid': 'subject_uuid'},
        inplace=True
    )
    df = merge_context_df(
        df,
        df_all_parents,
        ['subject_uuid'],
        context_cols,
        'subject__'
    )
    final_cols = make_loci_stratigraph_cols(df, context_cols=context_cols)
    return df[final_cols]
    
def join_related_loci_in_sheet_df(dfs, sheet, context_cols=None):
    """Makes a locus stratigraph dataframe"""
    df = dfs[sheet].copy().reset_index(drop=True)
    rel_column = None
    for c in df.columns:
        if not 'Locus' in c:
            continue
        rel_column = c
    if rel_column is None:
        return None
    df[LINK_RELATION_TYPE_COL] = rel_column
    df.rename(
        columns={
            rel_column: 'object__Locus ID',
            '_submission__uuid': 'subject_uuid'
        },
        inplace=True
    )
    df['object__Locus ID'] = df['object__Locus ID'].astype(str)
    df_parents = []
    df_rels = []
    if context_cols is None:
        context_cols = LOCUS_CONTEXT_COLS
    for i, row in df.iterrows():
        df_parent = look_up_parent(
            row['_parent_table_name'],
            row['subject_uuid'],
            dfs
        )
        df_parent = df_parent[(context_cols + ['_uuid'])]
        df_parents.append(df_parent)
        df_rel = lookup_related_locus(
            row['object__Locus ID'],
            row['_parent_table_name'],
            row['subject_uuid'],
            dfs
        )
        df_rel = df_rel[
            (context_cols + ['_uuid', 'object__Locus ID', 'subject_uuid'])
        ]
        df_rels.append(df_rel)
    # Now combine all the related data
    df_all_parents = pd.concat(df_parents)
    df_all_parents.drop_duplicates(subset=['_uuid'], inplace=True)
    df_all_rels = pd.concat(df_rels)
    df_all_rels.drop_duplicates(inplace=True)
    df_all_parents.rename(
        columns={'_uuid': 'subject_uuid'},
        inplace=True
    )
    df = merge_context_df(
        df,
        df_all_parents,
        ['subject_uuid'],
        context_cols,
        'subject__'
    )
    df['object__Locus ID'] = df['object__Locus ID'].astype(str)
    df_all_rels['object__Locus ID'] = df_all_rels['object__Locus ID'].astype(str)
    df = merge_context_df(
        df,
        df_all_rels,
        ['object__Locus ID', 'subject_uuid'],
        (context_cols + ['_uuid']),
        'object__'
    )
    df.rename(
        columns={'object___uuid': 'object_uuid'},
        inplace=True
    )
    final_cols = make_loci_stratigraph_cols(df, context_cols=context_cols)
    return df[final_cols]

def make_locus_stratigraphy_df(dfs, locus_strat_sheets=None, context_cols=None):
    """Makes a consolidatd locus stratigraph dataframe"""
    if locus_strat_sheets is None:
        locus_strat_sheets = LOCUS_STRAT_FIELDS
    if context_cols is None:
        context_cols = LOCUS_CONTEXT_COLS
    sheet_dfs = []
    for sheet in locus_strat_sheets:
        if not sheet in dfs:
            continue
        if sheet == 'group_strat_other':
            df_sheet = join_related_uri_loci_df(
                dfs,
                sheet,
                context_cols=context_cols
            )
        else:
            df_sheet = join_related_loci_in_sheet_df(
                dfs,
                sheet,
                context_cols=context_cols
            )
        if df_sheet is None:
            continue
        sheet_dfs.append(df_sheet)
    df = pd.concat(sheet_dfs)
    final_cols = make_loci_stratigraph_cols(
        df,
        context_cols=context_cols
    )
    return df[final_cols]
    df.drop_duplicates(inplace=True)
    return df


def make_new_trench_book_titles(row):
    """Makes a new trench book title for a row."""
    if row['Start Page'] < row['End Page']:
        page_part = '{}-{}'.format(
            int(row['Start Page']),
            int(row['End Page'])
        )
    elif row['Start Page'] == row['End Page']:
        page_part = int(row['Start Page'])
    elif row['Start Page'] > row['End Page']:
        page_part = '{}-{}'.format(
            int(row['End Page']),
            int(row['Start Page'])
        )
    
    return '{} ({}):{}; {}'.format(
        row['Trench ID'],
        row['Date Documented'],
        page_part,
        row['Entry Type']
    )

def add_make_new_trench_book_title_column(df, new_tb_title_col):
    """Adds a new column with a new trench book title."""
    df[new_tb_title_col] = df.apply(
        make_new_trench_book_titles,
        axis=1
    )
    return df

def join_trenbook_entries_to_related_df(
    tb_dfs,
    tb_entry_sheet='Trench Book Entry',
    tb_index_cols=None,
    tb_rel_sheet='group_rel_locus',
    tb_rel_col='Related Locus / Loci (Discussed in this entry)/Related Locus',
    tb_rel_col_rename='object__Locus ID',
    tb_rel_link_type='Related Open Locus',
    context_cols=None,
    rel_drop_cols=None
):
    """Joins trench book entries to a trench book related DF."""
    df_output = tb_dfs[tb_rel_sheet].copy().reset_index(drop=True)
    df_output[LINK_RELATION_TYPE_COL] = tb_rel_link_type
    df_output.rename(
        columns={
            tb_rel_col: tb_rel_col_rename,
            '_submission__uuid': 'subject_uuid'
        },
        inplace=True
    )
    df_parents = []
    if tb_index_cols is None:
        tb_index_cols = TRENCH_BOOK_INDEX_COLS
    if context_cols is None:
        context_cols = TRENCH_BOOK_CONTEXT_COLS
    for i, row in df_output.iterrows():
        df_parent = look_up_parent(
            row['_parent_table_name'],
            row['subject_uuid'],
            tb_dfs
        )
        df_parent = df_parent[(
            context_cols +
            ['_uuid'] +
            tb_index_cols
        )]
        df_parents.append(df_parent)
    # Now combine all the related data
    df_all_parents = pd.concat(df_parents)
    df_all_parents.drop_duplicates(subset=['_uuid'], inplace=True)
    df_all_parents.rename(
        columns={'_uuid': 'subject_uuid'},
        inplace=True
    )
    # Make a dataframe that has the index columns
    # of the trench book entries.
    df_tb_index = df_all_parents[(
        tb_index_cols +
        ['subject_uuid']
    )].copy().reset_index(drop=True)
    # Now drop the trenchbook index colums from the df_all_parents,
    # because we don't want to rename the columns when we merge it
    # into the tb_locus_df.
    df_all_parents.drop(tb_index_cols, axis=1, inplace=True, errors='ignore')
    df_output = merge_context_df(
        df_output,
        df_all_parents,
        ['subject_uuid'],
        context_cols,
        'object__'
    )
    # Merge in the index columns that uniquely describe a
    # trench book entry
    df_output = pd.merge(
        df_output,
        df_tb_index,
        how='left',
        on=['subject_uuid']
    )
    obj_context_cols = ['object__' + c for c in context_cols]
    # Make sure the output df has the tb_index_cols first.
    df_output = reorder_first_columns(
        df_output, (
            tb_index_cols +
            ['subject_uuid', LINK_RELATION_TYPE_COL] +
            obj_context_cols
        )
    )
    if rel_drop_cols is None:
        rel_drop_cols = RELATED_SHEET_DROP_COLS
    # Drop columns that we don't want.
    df_output.drop(rel_drop_cols, axis=1, inplace=True, errors='ignore')
    return df_output

def prep_trench_book_related(tb_dfs, related_config=None):
    """Prepares trench book related relationship dfs"""
    if related_config is None:
        related_config = TRENCH_BOOK_REL_CONFIGS
    tb_rel_dfs = {}
    for rel_type, rel_config_args in related_config.items():
        rel_config_args['tb_dfs'] = tb_dfs
        tb_rel_dfs[rel_type] = join_trenbook_entries_to_related_df(
            **rel_config_args
        )
    
    return tb_rel_dfs

def add_trench_book_related_uuids(
    tb_rel_dfs,
    field_config_dfs,
    tb_rel_uuid_configs=None
):
    """Adds UUIDS of trench book related entitites."""
    if tb_rel_uuid_configs is None:
        tb_rel_uuid_configs = TRENCH_BOOK_REL_UUID_CONFIGS
    new_tb_rel_dfs = {}
    for rel_type, tb_rel_df in tb_rel_dfs.items():
        if not rel_type in tb_rel_uuid_configs:
            # We do not have a configuation to look this up, so skip
            new_tb_rel_dfs[rel_type] = tb_rel_df
            continue
        # Get the configuration for joining in UUIDs for this type of related entity
        config = tb_rel_uuid_configs[rel_type]
        join_cols = [join_col for _, join_col in config['index_cols'].items()]
        keep_cols = [col for col in config['index_cols'].keys()]
        keep_cols.append('_uuid')
        lookup_sheet = config['lookup_sheet']
        lookup_df = field_config_dfs[lookup_sheet]['dfs'][lookup_sheet]
        lookup_df = lookup_df[keep_cols].copy().reset_index(drop=True)
        lookup_df.rename(columns={'_uuid':'object_uuid'}, inplace=True)
        lookup_df.rename(columns=config['index_cols'], inplace=True)
        # Convert join columns to string to ensure joins.
        for join_col in join_cols:
            lookup_df[join_col] = lookup_df[join_col].astype(str)
            tb_rel_df[join_col] = tb_rel_df[join_col].astype(str)
        
        # Now finally merge the data with UUIDs.
        tb_rel_df = pd.merge(
            tb_rel_df,
            lookup_df,
            how='left',
            on=join_cols
        )
        # Now indicate where we got the UUID
        good_index = (tb_rel_df['object_uuid'] != np.nan)
        tb_rel_df.loc[good_index, 'object_uuid_source'] = UUID_SOURCE_KOBOTOOLBOX
        tb_rel_df.loc[~good_index, 'object_uuid_source'] = np.nan
        
        # Rename columns as needed.
        if 'final_renames' in config:
            tb_rel_df.rename(columns=config['final_renames'], inplace=True)
        
        # Add the revised tb_rel_df to the output dict.
        new_tb_rel_dfs[rel_type] = tb_rel_df
    return new_tb_rel_dfs



def make_previous_next_trench_book_rels_dfs(
    df_f
):
    """Makes previous and next relations between entries"""

    sort_cols = ['Trench ID', 'Date Documented', 'Start Page',  'End Page']
    tb_ent_indx = (
        (df_f['Trench ID'].notnull())
        & ((df_f['Start Page']>0) | (df_f['End Page']>0))
    )
    df_tb_ents = df_f[tb_ent_indx].copy().reset_index(drop=True)
    trench_ids = df_tb_ents['Trench ID'].unique().tolist()
    
    df_tb_ents.sort_values(by=['Trench ID', 'Date Documented', 'Start Page',  'End Page'], inplace=True)
    
    df_rels = []
    rel_configs = [
        ('Previous Entry', -1),
        ('Next Entry', 1),
    ]
    for trench_id in trench_ids:
        for rel_type, index_dif in rel_configs:
            df_rel = df_tb_ents[
                (df_tb_ents['Trench ID'] == trench_id)
            ].copy().reset_index(drop=True)
            len_df = len(df_rel.index)
            df_rel.rename(
                columns={
                    '_uuid':'subject_uuid',
                    'Trench Book Title': 'subject__Trench Book Title',
                },
                inplace=True
            )
            # Organize the columns that we want to keep for the df_p_n output.
            df_rel_cols_temp = sort_cols + [c for c in TRENCH_BOOK_INDEX_COLS if not c in sort_cols]
            df_rel_cols_temp += [c for c in TRENCH_BOOK_CONTEXT_COLS if not c in sort_cols]
            df_rel_cols = [c for c in df_rel_cols_temp if c in df_rel.columns]
            df_rel_cols += ['subject__Trench Book Title', 'subject_uuid']
            df_rel = df_rel[df_rel_cols]
            # Sort the df rel!
            df_rel.sort_values(by=sort_cols, inplace=True)
            df_rel[LINK_RELATION_TYPE_COL] = np.nan
            df_rel['object_uuid'] = np.nan
            df_rel['object__subject__Trench Book Title'] = np.nan
            for i, row in df_rel.iterrows():
                other_index = i + index_dif
                if other_index < 0 or other_index >= len_df:
                    # we're outside of the index range, so skip.
                    continue
                up_indx = (df_rel['subject_uuid'] == row['subject_uuid'])
                df_rel.loc[up_indx, LINK_RELATION_TYPE_COL] = rel_type
                df_rel.loc[up_indx, 'object_uuid'] = df_rel['subject_uuid'].iloc[other_index]
                df_rel.loc[up_indx, 'object__subject__Trench Book Title'] = df_rel['subject__Trench Book Title'].iloc[other_index]

            # Drop missing records.
            df_rel = df_rel[df_rel[LINK_RELATION_TYPE_COL].notnull()]
            df_rels.append(df_rel)

    return df_rels

def make_trench_book_unit_id_relations_df(df_f, all_contexts_df):
    """Makes a dataframe of relations between trench books and Units"""
    tb_first_cols = [
        'Date Documented',
        'Start Page',
        'End Page',
        'Trench ID',
        'Unit ID',
        'Trench Book Title',
        'Document Type',
    ]
    rel_df = df_f[tb_first_cols + ['_uuid']].copy()
    rel_df['subject__Trench Book Title'] = rel_df['Trench Book Title']
    rel_df['subject_uuid'] = rel_df['_uuid']
    rel_df[LINK_RELATION_TYPE_COL] = 'link'
    unit_df = all_contexts_df[all_contexts_df['class_uri']=='oc-gen:cat-exc-unit'].copy()
    unit_df = unit_df[['label',	'context_uuid',	'uuid_source']]
    unit_df['object__Unit ID'] = unit_df['label']
    unit_df.rename(
        columns={
            'label': 'Unit ID',
            'context_uuid': 'object_uuid',
            'uuid_source': 'object_uuid_source',
        },
        inplace=True
    )
    # Now join the Units to the trench books.
    rel_df = pd.merge(
        rel_df,
        unit_df,
        how='left',
        on=['Unit ID']
    )
    return rel_df
    
    
def make_trench_book_parent_relations_df(
    df_f,
    config=FIELD_DATA_PREPS['Trench Book Entry']
):
    """Makes relations between trench book entries and parent books
    
    :param dataframe df_f: Trench book description dataframe
    :parma dict tb_rel_dfs: Dictionary of trench book relations
        dataframes.
    """
    # Configures columns and how columns get renamed for subject_df and
    # object_df.
    mapping_tups = [
        (
            'Trench Supervisor',
            'subject__Trench Supervisor',
            'object__Trench Supervisor'
        ),
        ('Unit ID', 'subject__Unit ID', 'object__Unit ID'),
        (
            config['tb_new_title'],
            'subject__' + config['tb_new_title'],
            'object__' + 'subject__' + config['tb_new_title']
        ),
        ('subject_uuid_source', 'subject_uuid_source', 'object_uuid_source'),
        ('_uuid', 'subject_uuid', 'object_uuid'),
    ]
    
    # The columns used to join parent_df and child_df
    join_cols = [
        'Trench Supervisor',
        'Unit ID',
    ]
    doc_type_col, doc_type = config.get('tb_doc_type_root')
    parent_df = df_f[
        (df_f[doc_type_col] == doc_type)
    ].copy().reset_index(drop=True)
    child_df = df_f[
        (df_f[doc_type_col] != doc_type)
    ].copy().reset_index(drop=True)
    
    # Copy the join columns to make temporary join columns that
    # will be common in the parent_df and child_df and will not
    # get renamed.
    temp_join_cols = []
    for i, join_col in enumerate(join_cols, 1):
        temp_join = 'TEMP_JOIN_COL_{}'.format(i)
        parent_df[temp_join] = parent_df[join_col].astype(str)
        child_df[temp_join] = child_df[join_col].astype(str)
        temp_join_cols.append(temp_join)
    
    subset_cols = [col for col, _, _ in mapping_tups] + temp_join_cols
    subject_df_cols = [col for _, col, _ in mapping_tups]
    object_df_cols = [col for _, _, col in mapping_tups]
    rel_df_cols = subject_df_cols + [LINK_RELATION_TYPE_COL] + object_df_cols
    
    # Now iterate through and actually do the joins
    rel_dfs = []
    linking_rels = [
        ('Is Part of', child_df, parent_df, 'left'),
        ('Has Part', parent_df, child_df, 'right'),
    ]
    for link_rel, subject_df, object_df, join_how in linking_rels:
        subject_df = subject_df[subset_cols].copy().reset_index(drop=True)
        object_df = object_df[subset_cols].copy().reset_index(drop=True)
        # Now rename the columns
        subject_df.rename(
            columns={old:new for old, new, _ in mapping_tups},
            inplace=True
        )
        object_df.rename(
            columns={old:new for old, _, new in mapping_tups},
            inplace=True
        )
        # Do the join, as a left or right join depending
        # on if the child_df is the object_df or subject_df.
        rel_df = pd.merge(
            subject_df,
            object_df,
            how=join_how,
            on=temp_join_cols
        )
        rel_df[LINK_RELATION_TYPE_COL] = link_rel
        rel_dfs.append(rel_df)
    # Make the TB parent relation dataframe
    tb_parent_rels = pd.concat(rel_dfs)
    tb_parent_rels = tb_parent_rels[rel_df_cols]
    return tb_parent_rels
    

def make_final_trench_book_relations_df(field_config_dfs, all_contexts_df):
    """Makes final consolidated dataframe of Trench Book link relations."""
    tb_dfs = field_config_dfs['Trench Book Entry']['dfs']
    df_f = tb_dfs['Trench Book Entry']
    # Make several dataframes of TB relations to loci, small finds.
    tb_rel_dfs = prep_trench_book_related(tb_dfs)
    tb_rel_dfs = add_trench_book_related_uuids(tb_rel_dfs, field_config_dfs)
    all_rel_dfs = [rel_df for _, rel_df in tb_rel_dfs.items()]
    all_rel_dfs += make_previous_next_trench_book_rels_dfs(df_f)
    # Add a single dataframe of TB entry and TB book relations
    tb_parent_rels = make_trench_book_parent_relations_df(df_f)
    all_rel_dfs.append(tb_parent_rels)
    # Add a single dataframe of TB relations to Unit IDs.
    tb_unit_rel_df = make_trench_book_unit_id_relations_df(df_f, all_contexts_df)
    all_rel_dfs.append(tb_unit_rel_df)
    # Now bring all of these individual TB relations dataframes into a single
    # dataframe of TB relations.
    tb_all_rels_df = pd.concat(all_rel_dfs)
    # Reorder and limit final output columns to a pre-determined config.
    use_cols = [c for c in TRENCH_BOOK_FINAL_REL_COLS if c in tb_all_rels_df.columns]
    tb_all_rels_df = tb_all_rels_df[use_cols]
    tb_all_rels_df.sort_values(by=[
        LINK_RELATION_TYPE_COL,
        'subject__Trench Book Title',
        'object__subject__Trench Book Title',
        'object__Unit ID',
        'object__Locus ID',
        'object__Find Number',
    ], inplace=True)
    return tb_all_rels_df


def add_trench_book_parents(
    df,
    project_uuid,
    year,
    config
):
    """Adds root-level trench book parent records."""
    df_grp = df.groupby(TRENCH_BOOK_ROOT_GROUPS, as_index=False).first()
    df_grp = df_grp[TRENCH_BOOK_ROOT_GROUPS]
    doc_type_col, doc_type = config.get('tb_doc_type_root')
    entry_text_col, entry_text = config.get('tb_root_entry')
    # Add columns and values that apply to ALL the root documents
    df_grp[entry_text_col] = entry_text    
    df_grp[doc_type_col] = doc_type
    df_grp[config['tb_root_year']] = year
    #
    # Now iterate through the root documents to get or make their UUIDs
    # and titles.
    df_working = df_grp.copy().reset_index(drop=True)
    for i, row in df_working.iterrows():
        indx = (
            (df_grp['Unit ID'] == row['Unit ID']) &
            (df_grp['Trench Supervisor'] == row['Trench Supervisor'])
        )
        tb_title = doc_type + ' ' + row['Unit ID']
        df_grp.loc[indx, config['tb_new_title']] = doc_type + ' ' + row['Unit ID']
        uuid = lookup_manifest_uuid(
            tb_title,
            project_uuid,
            item_type='documents',
            label_alt_configs=[]
        )
        if uuid is not None:
            df_grp.loc[indx, '_uuid'] = uuid
            df_grp.loc[indx, 'subject_uuid_source'] = UUID_SOURCE_OC_LOOKUP
        else:
            df_grp.loc[indx, '_uuid'] = str(GenUUID.uuid4())
            df_grp.loc[indx, 'subject_uuid_source'] = UUID_SOURCE_OC_KOBO_ETL
    
    # Add the new root document records to the general trench book description
    # dataframe.
    df_first_cols = df.columns.tolist()
    df = df.append(df_grp, ignore_index=True)
    df = reorder_first_columns(df, df_first_cols)
    return df

def prep_field_tables(
    excels_filepath,
    project_uuid,
    year,
    field_data_preps=None
):
    """Prepares main field created data tables."""
    if field_data_preps is None:
        field_data_preps = FIELD_DATA_PREPS
    excels = list_excel_files(excels_filepath)
    field_config_dfs = {}
    for excel_filepath in excels:
        dfs = read_excel_to_dataframes(excel_filepath)
        for act_sheet, config in field_data_preps.items():
            if not act_sheet in dfs:
                # Not applicable.
                continue
            df_f = drop_empty_cols(dfs[act_sheet])
            df_f = update_multivalue_columns(df_f)
            df_f = clean_up_multivalue_cols(df_f, skip_cols=SKIP_MULTI_VALUE_REDACTIONS)
            if 'child_context_cols' in config:
                df_f = prepare_trench_contexts(
                    df_f,
                    year,
                    child_context_cols=config['child_context_cols']
                )
            if config.get('tb_new_title') is not None:
                # Do a Trench book specific change, making a new
                # title column.
                df_f = add_make_new_trench_book_title_column(
                    df_f,
                    config['tb_new_title']
                )
            if config.get('tb_doc_type') is not None:
                # Note that all of the data (so far) are for 
                doc_type_col, doc_type = config.get('tb_doc_type')
                df_f[doc_type_col] = doc_type
            if config.get('tb_entry_year') is not None:
                # Add the Trench Book entry year. 
                entry_year_col = config.get('tb_entry_year')
                df_f[entry_year_col] = year
            if config.get('tb_doc_type_root') is not None:
                df_f['subject_uuid_source'] = UUID_SOURCE_KOBOTOOLBOX
                df_f = add_trench_book_parents(
                    df_f,
                    project_uuid,
                    year,
                    config
                )
            dfs[act_sheet] = df_f
            config['dfs'] = dfs
            field_config_dfs[act_sheet] = config
    return field_config_dfs

    