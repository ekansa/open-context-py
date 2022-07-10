import copy
import uuid as GenUUID
import os
import numpy as np
import pandas as pd

from pathlib import Path


from opencontext_py.apps.etl.kobo import db_lookups
from opencontext_py.apps.etl.kobo import pc_configs
from opencontext_py.apps.etl.kobo import utilities



"""Uses Pandas to prepare Kobotoolbox exports for Open Context import

This is intended for use with the Poggio Civitate project.

import importlib

from pathlib import Path
from opencontext_py.apps.etl.kobo import subjects
from opencontext_py.apps.etl.kobo import pc_configs
importlib.reload(subjects)

home = str(Path.home())
excel_dirpath = f'{home}/data-dumps/pc-2022/kobo-data'
trench_csv_path = f'{home}/data-dumps/pc-2022/trenches-2022.csv'
save_path = f'{home}/data-dumps/pc-2022/'

df = subjects.make_and_classify_subjects_df(
    excel_dirpath, 
    trench_csv_path,
    save_path=pc_configs.SUBJECTS_CSV_PATH,
)


"""


TRENCH_CSV_COLS = [
    # Tuples as follows:
    # (csv_column_name, col_output_rename)
    ('site', 'site'),
    ('area', 'area'),
    ('p_trench', 'p_trench_name'),
    ('p_trench_uuid', 'p_trench_uuid'),
    ('label_oc', 'unit_name'),
    ('uuid', 'unit_uuid'),
]

SUBJECTS_GENERAL_KOBO_COLS = [
    ('__version__', 'kobo_source_version',),
    ('_id', 'kobo_row_id',),
    ('_index', 'kobo_row_index',),
]

SUBJECTS_SHEET_COLS = {
    'Locus Summary Entry 2022': [
        (pc_configs.KOBO_TRENCH_COL, pc_configs.KOBO_TRENCH_COL,),
        ('Field Season', 'trench_year',),
        ('Locus ID', 'locus_number',),
        ('OC Locus', 'locus_name',),
        ('_uuid', 'locus_uuid',),
    ],
    'Field Small Find Entry 2022': [
        (pc_configs.KOBO_TRENCH_COL, pc_configs.KOBO_TRENCH_COL,),
        ('Field Season', 'trench_year',),
        ('Locus ID', 'locus_number',),
        ('OC Locus', 'locus_name',),
        ('OC Find ID', 'find_name',),
        ('_uuid', 'find_uuid',),
    ],
    'Field Bulk Finds Entry 2022': [
        (pc_configs.KOBO_TRENCH_COL, pc_configs.KOBO_TRENCH_COL,),
        ('Field Season', 'trench_year',),
        ('Locus ID', 'locus_number',),
        ('OC Locus', 'locus_name',),
        ('OC Bulk', 'bulk_name',),
        ('_uuid', 'bulk_uuid',),
    ],
    'Catalog Entry 2022': [
        (pc_configs.KOBO_TRENCH_COL, pc_configs.KOBO_TRENCH_COL,),
        ('Year', 'trench_year',),
        ('Locus ID', 'locus_number',),
        ('OC Locus', 'locus_name',),
        ('Catalog ID (PC)', 'catalog_name',),
        ('_uuid', 'catalog_uuid',),
        ('Object General Type', 'object_general_type'),
    ],
}


SUBJECTS_IMPORT_COLS = [
    # Tuples organized in hierarchic containment order.
    # Tuples as follows:
    # (parent_context_col, child_label_col, child_uuid_col, child_class_slug_col)
    ('p_trench_uuid', 'unit_name', 'unit_uuid', 'unit_item_class_slug'),
    ('unit_uuid', 'locus_name', 'locus_uuid', 'locus_item_class_slug'),
    ('locus_uuid', 'find_name', 'find_uuid', 'find_item_class_slug'),
    ('locus_uuid', 'bulk_name', 'bulk_uuid', 'bulk_item_class_slug'),
    ('locus_uuid', 'catalog_name', 'catalog_uuid', 'catalog_item_class_slug'),
]


# The following configures item_classes for the
# different subjects gathered from the Kobo files
DEFAULT_CATALOG_ITEM_CLASS_SLUG = 'oc-gen-cat-object'

# Mapping between different items and their default
# item classes as identified by slugs
DEFAULT_ITEM_CLASS_SLUGS = {
    'unit_uuid': 'oc-gen-cat-exc-unit',
    'locus_uuid': 'oc-gen-cat-locus',
    'bulk_uuid': 'oc-gen-cat-sample-col',
    'find_uuid': 'oc-gen-cat-sample',
    'catalog_uuid': DEFAULT_CATALOG_ITEM_CLASS_SLUG,
}

OBJECT_GENERAL_TYPE_ITEM_CLASS_SLUGS = {
    '24_architectural': 'oc-gen-cat-arch-element',
    '24_coin': 'oc-gen-cat-coin',
    '24_organic_ecofact': 'oc-gen-cat-bio-subj-ecofact',
    '24_vessel': 'oc-gen-cat-pottery',
}



def limit_rename_cols_by_config_tuples(df, config_tups):
    """Limits and renames dataframe columns by a list of config
    tuples
    """
    ok_cols = [c for c, _ in config_tups if c in df.columns]
    df = df[ok_cols].copy()
    rename_cols = {c:r_c for c, r_c in config_tups if c in df.columns}
    df.rename(columns=rename_cols, inplace=True)
    return df


def merge_trench_df(df, trench_df):
    if not pc_configs.KOBO_TRENCH_COL in df.columns:
        return None
    df.rename(columns={pc_configs.KOBO_TRENCH_COL:'trench_id',}, inplace=True)
    df = pd.merge(df, trench_df, on='trench_id', how='left')
    df.reset_index(drop=True, inplace=True)
    return df


def make_subjects_df(excel_dirpath, trench_csv_path=pc_configs.TRENCH_CSV_PATH):
    trench_df = pd.read_csv(trench_csv_path)
    if not 'trench_id' in trench_df.columns:
        trench_df['trench_id'] = trench_df['name']
    trench_configs = [('trench_id', 'trench_id')]
    trench_configs += copy.deepcopy(TRENCH_CSV_COLS)
    trench_df = limit_rename_cols_by_config_tuples(
        trench_df, 
        trench_configs,
    )
    start_cols = [r_c for _, r_c in trench_configs]
    xlsx_files = utilities.list_excel_files(excel_dirpath)
    if not xlsx_files:
        return None
    subj_dfs = []
    last_cols = [f_c for _, f_c in SUBJECTS_GENERAL_KOBO_COLS]
    mid_cols = []
    for excel_filepath in xlsx_files:
        dfs = utilities.read_excel_to_dataframes(excel_filepath)
        for sheet_name, df in dfs.items():
            sheet_config = SUBJECTS_SHEET_COLS.get(sheet_name)
            if not sheet_config:
                continue
            sheet_config += copy.deepcopy(SUBJECTS_GENERAL_KOBO_COLS)
            df = limit_rename_cols_by_config_tuples(
                df, 
                sheet_config,
            )
            df = merge_trench_df(df, trench_df)
            if df is None:
                continue
            mid_cols += [
                c for c in df.columns.tolist() 
                if (
                    c not in mid_cols 
                    and c not in start_cols 
                    and c not in last_cols 
                    and not c.startswith('locus_')
                )
            ]
            print('Made subject df')
            print(df.head())
            subj_dfs.append(df)
    df = pd.concat(subj_dfs, axis=0)
    locus_cols = [c for c in df.columns.tolist() if c.startswith('locus_')]
    all_cols = start_cols + locus_cols + mid_cols + last_cols
    final_cols = [c for c in all_cols if c in df.columns] 
    df = df[final_cols].copy()
    df.reset_index(drop=True, inplace=True)
    return df


def item_class_slug_col_from_uuid_col(col):
    """Gets a item class slug column name for a uuid column"""
    if not DEFAULT_ITEM_CLASS_SLUGS.get(col):
        return None
    return col.replace('_uuid', '_item_class_slug')


def update_object_general_type_item_class_slugs(df):
    """Updates item_class_slugs for Catalog items based on
    object_general_type values
    """
    if 'object_general_type' not in df.columns:
        return df
    not_null_indx = ~df['object_general_type'].isnull()
    for g_type in df[not_null_indx]['object_general_type'].unique().tolist():
        g_type_item_class_slug = OBJECT_GENERAL_TYPE_ITEM_CLASS_SLUGS.get(
            g_type,
            DEFAULT_CATALOG_ITEM_CLASS_SLUG
        )
        g_type_indx = df['object_general_type'] == g_type
        df.loc[g_type_indx, 'catalog_item_class_slug'] = g_type_item_class_slug
    return df


def add_missing_unit_contexts(df):
    """Adds missing unit (trench) uuid information"""
    needed_cols = ['trench_id', 'unit_uuid', 'trench_year']
    if not set(needed_cols).issubset(set(df.columns.tolist())):
        # Missing required columns, so skip out
        return df
    indx = (
        df['unit_uuid'].isnull() 
        & ~df['trench_id'].isnull()
        & ~df['trench_year'].isnull()
    )
    if df[indx].empty:
        # We're missing rows suited for looking up
        # unknown trench units.
        return df
    grp_cols = ['trench_id', 'trench_year']
    df_g = df[indx][grp_cols].groupby(grp_cols, as_index=False).first()
    df_g.reset_index(drop=True, inplace=True)
    for _, row in df_g.iterrows():
        trench_id = str(row['trench_id'])
        trench_year = row['trench_year']
        map_dict = utilities.get_trench_unit_mapping_dict(trench_id)
        if not map_dict:
            # We don't have mapping configured for this
            # trench.
            continue
        print(f'Lookup trench_id {trench_id}, trench_year {trench_year}')
        man_obj = db_lookups.db_reconcile_trench_unit(trench_id, trench_year)
        if not man_obj:
            # We could find any unambiguous matches.
            continue
        up_index = (
            (df['trench_id'] == trench_id)
            & (df['trench_year'] == trench_year)
            & df['unit_uuid'].isnull()
        )
        df.loc[up_index, 'site'] = map_dict['site']
        df.loc[up_index, 'area'] = map_dict['area']
        df.loc[up_index, 'p_trench_name'] = man_obj.context.label
        df.loc[up_index, 'p_trench_uuid'] = str(man_obj.context.uuid)
        df.loc[up_index, 'unit_name'] = man_obj.label
        df.loc[up_index, 'unit_uuid'] = str(man_obj.uuid)
    return df


def add_missing_locus_contexts(df):
    """Adds missing unit (trench) uuid information"""
    needed_cols = ['unit_uuid', 'locus_name', 'locus_uuid']
    if not set(needed_cols).issubset(set(df.columns.tolist())):
        # Missing required columns, so skip out
        return df
    indx = (
        ~df['unit_uuid'].isnull() 
        & ~df['locus_name'].isnull()
    )
    if df[indx].empty:
        # We're missing rows suited for looking up
        # unknown loci.
        return df
    grp_cols = ['unit_uuid', 'locus_name']
    df_g = df[indx][grp_cols].groupby(grp_cols, as_index=False).first()
    df_g.reset_index(drop=True, inplace=True)
    for _, row in df_g.iterrows():
        unit_uuid = str(row['unit_uuid'])
        locus_name = str(row['locus_name'])
        locus_uuid = None
        if locus_name == 'Locus -1':
            # A hack. There are no loci in earlier years of
            # excavation at the site, so skip lookups.
            continue
        # Always defer to the the database to find the locus within
        # this unit.
        man_obj = db_lookups.db_reconcile_locus(unit_uuid, locus_name)
        if man_obj:
            locus_uuid = str(man_obj.uuid)
            up_index = (
                (df['unit_uuid'] == unit_uuid)
                & (df['locus_name'] == locus_name)
            )
            df.loc[up_index, 'locus_uuid'] = str(locus_uuid)
        exist_indx = (
            (df['unit_uuid'] == unit_uuid)
            & (df['locus_name'] == locus_name)
            & ~df['locus_uuid'].isnull()
        )
        if not locus_uuid and not df[exist_indx].empty:
            # This is a NEW locus, so use the Kobo provided UUID.
            # We're using data from elsewhere in the df to 
            # set the locus_uuid (no need to hit the database)
            locus_uuid = df[exist_indx]['locus_uuid'].iloc[0]
        if not locus_uuid:
            # We failed in finding a locus uuid to match
            continue
        no_exist_indx = (
            (df['unit_uuid'] == unit_uuid)
            & (df['locus_name'] == locus_name)
            & df['locus_uuid'].isnull()
        )
        df.loc[no_exist_indx, 'locus_uuid'] = str(locus_uuid)
    return df


def add_missing_contexts(df):
    """Adds missing unit (trench) and locus uuid information"""
    df = add_missing_unit_contexts(df)
    df = add_missing_locus_contexts(df)
    return df


def add_item_class_slugs(df):
    """Adds item class slugs to the subjects dataframe"""
    # The new_cols is used to order columns so the item_class_slug
    # columns associated for different _uuid columns are kept next
    # to each other
    new_cols = []
    for c in df.columns.tolist():
        new_cols.append(c)
        item_classs_slug_col = item_class_slug_col_from_uuid_col(c)
        if not item_classs_slug_col:
            continue
        # Make sure we have 
        new_cols.append(item_classs_slug_col)
        # Add8 the default item_c2lass_slug value for this 
        # uuid column
        df[item_classs_slug_col] = np.nan
        not_null_indx = ~df[c].isnull()
        df.loc[not_null_indx, item_classs_slug_col] = DEFAULT_ITEM_CLASS_SLUGS.get(c)
    # Update the item_class_slugs for any catalog records
    # based on their associated object general type
    df = update_object_general_type_item_class_slugs(df)
    # Reorder the columns so the new item_class_slug columns
    # follow the corresponding uuid columns
    df = df[new_cols].copy()
    return df


def make_and_classify_subjects_df(
    excel_dirpath, 
    trench_csv_path=pc_configs.TRENCH_CSV_PATH,
    save_path=None
):
    """Makes a subjects df with item_class_slug classifications"""
    df = make_subjects_df(excel_dirpath, trench_csv_path)
    df = add_missing_contexts(df)
    df = add_item_class_slugs(df)
    if save_path:
        df.to_csv(save_path, index=False)
    return df
