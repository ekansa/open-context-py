
from time import sleep
import uuid as GenUUID
import os, sys, shutil
import pandas as pd
import xlrd

from django.conf import settings

"""Uses Pandas to prepare Kobotoolbox exports for Open Context import


from django.conf import settings
from opencontext_py.apps.imports.kobotoolbox.preprocess import (
    read_excel_to_dataframes,
    look_up_parent,
    lookup_related_locus,
    make_locus_stratigraphy_df,
)

excel_filepath = settings.STATIC_IMPORTS_ROOT +  'pc-2018/Locus Summary Entry - latest version - labels - 2019-05-27-22-32-06.xlsx'
dfs = read_excel_to_dataframes(excel_filepath)
df_strat = make_locus_stratigraphy_df(dfs)
strat_path = settings.STATIC_IMPORTS_ROOT +  'pc-2018/locus-stratigraphy.csv'
df_strat.to_csv(strat_path, index=False)


"""

LOCUS_STRAT_FIELDS =[
    'group_strat_same',
    # 'group_strat_other',
    'group_strat_contemp',
    'group_strat_above',
    'group_strat_below',
    'group_strat_over',
    'group_strat_cuts'
]


def read_excel_to_dataframes(excel_filepath):
    """Reads an Excel workbook into a dictionary of dataframes keyed by sheet names."""
    dfs = {}
    xls = xlrd.open_workbook(excel_filepath)
    for sheet_name in xls.sheet_names():
        print('Reading sheet ' + sheet_name)
        # This probably needs an upgraded pandas
        # dfs[sheet_name] = pd.read_excel(xls, sheet_name=sheet_name, engine='xlrd')
        dfs[sheet_name] = pd.read_excel(xls, sheet_name, engine='xlrd')
    return dfs

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
    """Merges a df_parent with a df"""
    df_context = df_context[(context_cols + key_cols)]
    renames = {
        c: (rename_prefix + c)
        for c in df_context.columns
        if (not c in key_cols) and ((rename_prefix + c) not in df_context.columns)
    }
    df_context.rename(columns=renames, inplace=True)
    print('context cols {}'.format(df_context.columns))
    print('df cols {}'.format(df.columns))
    df_output = pd.merge(
        df,
        df_context,
        how='left',
        on=key_cols
    )
    return df_output

def join_related_loci_in_sheet_df(dfs, sheet):
    """Makes a locus stratigraph dataframe"""
    df = dfs[sheet].copy()
    rel_column = None
    for c in df.columns:
        if not 'Locus' in c:
            continue
        rel_column = c
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
    print('Getting related for: ' + sheet)
    context_cols = [
        'Trench',
        'Trench ID',
        'Locus ID',
    ]
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
    final_cols = [('subject__' + c) for c in context_cols]
    final_cols += ['subject_uuid', 'Relation_type']
    final_cols += [('object__' + c) for c in context_cols]
    final_cols += ['object_uuid']
    return df[final_cols]

def make_locus_stratigraphy_df(dfs, locus_strat_sheets=None):
    """Makes a locus stratigraph dataframe"""
    if locus_strat_sheets is None:
        locus_strat_sheets = LOCUS_STRAT_FIELDS
    sheet_dfs = []
    for sheet in locus_strat_sheets:
        df_sheet = join_related_loci_in_sheet_df(dfs, sheet)
        sheet_dfs.append(df_sheet)
    df = pd.concat(sheet_dfs)
    return df
    


    