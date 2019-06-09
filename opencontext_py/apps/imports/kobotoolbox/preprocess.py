
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
    make_directory_files_df,
    list_excel_files,
    read_excel_to_dataframes,
    drop_empty_cols,
    parse_opencontext_uuid,
    parse_opencontext_type
)

"""Uses Pandas to prepare Kobotoolbox exports for Open Context import


from django.conf import settings
from opencontext_py.apps.imports.kobotoolbox.preprocess import (
    make_locus_stratigraphy_df,
    prep_field_tables,
)
from opencontext_py.apps.imports.kobotoolbox.utilities import (
    list_excel_files,
    read_excel_to_dataframes,
)

excels_filepath = settings.STATIC_IMPORTS_ROOT +  'pc-2018/'
excels = list_excel_files(excels_filepath)
excel_filepath = settings.STATIC_IMPORTS_ROOT +  'pc-2018/Locus Summary Entry - latest version - labels - 2019-05-27-22-32-06.xlsx'

dfs = read_excel_to_dataframes(excel_filepath)
df_strat = make_locus_stratigraphy_df(dfs)
strat_path = settings.STATIC_IMPORTS_ROOT +  'pc-2018/locus-stratigraphy.csv'
df_strat.to_csv(strat_path, index=False)
field_dfs = prep_field_tables(excels_filepath, 2018)
for file_name, df in field_dfs.items():
    file_path =  excels_filepath + file_name
    df.to_csv(file_path, index=False)



"""

FIELD_DATA_PREPS = {
    'Locus Summary Entry': {
        'file': 'field-locus-summary.csv',
        'child_context_cols': ['Locus ID'],
    },
    'Field Bulk Finds Entry': {
        'file': 'field-bulk-finds-summary.csv',
        'child_context_cols': ['Locus ID', 'Bulk ID'],
    },
    'Field Small Find Entry':  {
        'file': 'field-small-finds-summary.csv',
        'child_context_cols': ['Locus ID', 'Find Number'],
    },
    'Trench Book Entry':   {
        'file': 'field-trench-book-summary.csv',
        'child_context_cols': [],
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
    'Locus ID',
]

MULTI_VALUE_COL_PREFIXES = [
    'Preliminary Phasing/',
    'Trench Supervisor/',
    'Decorative Techniques and Motifs/Decorative Technique/',
    'Decorative Techniques and Motifs/Motif/',
    'Fabric Category/',
    'Vessel Part Present/',
    'Modification/',
    'Type of Composition Subject/',
]

def update_multivalue_col_vals(df, multi_col_prefix):
    """Updates the values of multi-value nominal columns"""
    multi_cols = [c for c in df.columns.tolist() if c.startswith(multi_col_prefix)]
    drop_cols = []
    for col in multi_cols:
        df[col] = df[col].astype(str)
        val_index = ((df[col] == '1')|(df[col] == '1.0')|(df[col] == 'True'))
        if df[val_index].empty:
            drop_cols.append(col)
            continue
        # Set rows to the column's value if "True" (1).
        df.loc[val_index, col] = col.split(
            multi_col_prefix
        )[-1].strip()
        # Set rows to blank if the column is not True (1).
        df.loc[~val_index, col] = np.nan
    # Drop the columns that where not actually used.
    df.drop(drop_cols, axis=1, inplace=True, errors='ignore')
    rename_cols = {}
    i = 0
    for col in multi_cols:
        if col in drop_cols:
            continue
        i += 1
        rename_cols[col] = multi_col_prefix + str(i)
    # Rename the columns that were used.
    df.rename(columns=rename_cols, inplace=True)
    return drop_empty_cols(df)

def update_multivalue_columns(df, multival_col_prefixes=None):
    """Updates mulivalue columns, removing the ones not in use"""
    if multival_col_prefixes is None:
        multival_col_prefixes = MULTI_VALUE_COL_PREFIXES
    for multi_col_prefix in multival_col_prefixes:
        df = update_multivalue_col_vals(df, multi_col_prefix)
    return df
        
def look_up_parent(parent_sheet, parent_uuid, dfs):
    """Looks up and returns a 1 record dataframe of the record for the parent item."""
    df_parent = dfs[parent_sheet][
        dfs[parent_sheet]['_uuid'] == parent_uuid
    ].copy().reset_index(drop=True)
    return df_parent

def lookup_related_locus(rel_locus_id, parent_sheet, parent_locus_uuid, dfs):
    """Looks up a related locus on the parent sheet, and returns a dictionary of relevant data for the locus"""
    df_parent = look_up_parent(parent_sheet, parent_locus_uuid, dfs)
    if df_parent.empty:
        raise RuntimeError('Parent locus uuid {} not found.'.format(parent_locus_uuid))
    trench_id = df_parent['Trench ID'].iloc[0]
    df = dfs[parent_sheet]
    df['Trench ID'] = df['Trench ID'].astype(str)
    df['Locus ID'] = df['Locus ID'].astype(str)
    df_rel = df[
        (df['Trench ID'] == str(trench_id)) & (df['Locus ID'] == str(rel_locus_id))
    ].copy().reset_index(drop=True)
    df_rel['object__Locus ID'] = rel_locus_id
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
    strata_cols += ['subject_uuid', 'Relation_type']
    strata_cols += [('object__' + c) for c in context_cols]
    strata_cols += ['object_uuid']
    final_cols = [c for c in strata_cols if c in df.columns]
    return final_cols

def join_related_uri_loci_df(dfs, sheet, context_cols=None):
    df = dfs[sheet].copy()
    df.rename(
        columns={
            'Stratigraphy: Relation with Prior Season Locus/Relation Type': 'Relation_type',
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
    df = dfs[sheet].copy()
    rel_column = None
    for c in df.columns:
        if not 'Locus' in c:
            continue
        rel_column = c
    if rel_column is None:
        return None
    df['Relation_type'] = rel_column
    df.rename(
        columns={
            rel_column: 'object__Locus ID',
            '_submission__uuid': 'subject_uuid'
        },
        inplace=True
    )
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
    df_all_parents.drop_duplicates(inplace=True)
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

def prep_field_tables(excels_filepath, year, field_data_preps=None):
    """Prepares main field created data tables."""
    if field_data_preps is None:
        field_data_preps = FIELD_DATA_PREPS
    excels = list_excel_files(excels_filepath)
    field_dfs = {}
    for excel_filepath in excels:
        dfs = read_excel_to_dataframes(excel_filepath)
        for act_sheet, config in field_data_preps.items():
            if not act_sheet in dfs:
                # Not applicable.
                continue
            save_file = config['file']
            df_f = drop_empty_cols(dfs[act_sheet])
            df_f = update_multivalue_columns(df_f)
            df_f = prepare_trench_contexts(
                df_f,
                year,
                child_context_cols=config['child_context_cols']
            )
            field_dfs[save_file] = df_f
    return field_dfs

    