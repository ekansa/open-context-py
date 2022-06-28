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

This is intended for use with the Poggio Civitate project.

import importlib
from opencontext_py.apps.etl.kobo import subjects
importlib.reload(subjects)

excel_dirpath = '/home/ekansa/data-dumps/pc-2022/kobo-data'
trench_csv_path = '/home/ekansa/data-dumps/pc-2022/trenches-2022.csv'

subj_dfs = subjects.make_subjects_df(excel_dirpath, trench_csv_path)


"""

TRENCH_CSV_PATH = '~/data-dumps/pc-2022/trenches-2022.csv'

# The column in the Kobo exports with the trench identifier

KOBO_TRENCH_COL = 'Trench ID'

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
        (KOBO_TRENCH_COL, KOBO_TRENCH_COL,),
        ('Field Season', 'trench_year',),
        ('Locus ID', 'locus_number',),
        ('OC Locus', 'locus_name',),
        ('_uuid', 'locus_uuid',),
    ],
    'Field Small Find Entry 2022': [
        (KOBO_TRENCH_COL, KOBO_TRENCH_COL,),
        ('Field Season', 'trench_year',),
        ('Locus ID', 'locus_number',),
        ('OC Locus', 'locus_name',),
        ('Find ID', 'find_name',),
        ('_uuid', 'find_uuid',),
    ],
    'Field Bulk Finds Entry 2022': [
        (KOBO_TRENCH_COL, KOBO_TRENCH_COL,),
        ('Field Season', 'trench_year',),
        ('Locus ID', 'locus_number',),
        ('OC Locus', 'locus_name',),
        ('OC Bulk', 'bulk_name',),
        ('_uuid', 'bulk_uuid',),
    ],
    'Catalog Entry 2022': [
        (KOBO_TRENCH_COL, KOBO_TRENCH_COL,),
        ('Year', 'trench_year',),
        ('Locus ID', 'locus_number',),
        ('OC Locus', 'locus_name',),
        ('Catalog ID (PC)', 'catalog_name',),
        ('_uuid', 'catalog_uuid',),
        ('Object General Type', 'object_general_type'),
    ],
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
    if not KOBO_TRENCH_COL in df.columns:
        return None
    df.rename(columns={KOBO_TRENCH_COL:'trench_id',}, inplace=True)
    df = pd.merge(df, trench_df, on='trench_id', how='left')
    df.reset_index(drop=True, inplace=True)
    return df


def make_subjects_df(excel_dirpath, trench_csv_path=TRENCH_CSV_PATH):
    trench_df = pd.read_csv(trench_csv_path)
    if not 'trench_id' in trench_df.columns:
        trench_df['trench_id'] = trench_df['name']
    trench_configs = [('trench_id', 'trench_id')]
    trench_configs += TRENCH_CSV_COLS
    trench_df = limit_rename_cols_by_config_tuples(
        trench_df, 
        trench_configs,
    )
    final_cols = [r_c for _, r_c in trench_configs]
    xlsx_files = utilities.list_excel_files(excel_dirpath)
    if not xlsx_files:
        return None
    subj_dfs = []
    last_final_cols = [f_c for _, f_c in SUBJECTS_GENERAL_KOBO_COLS]
    for excel_filepath in xlsx_files:
        dfs = utilities.read_excel_to_dataframes(excel_filepath)
        for sheet_name, df in dfs.items():
            sheet_config = SUBJECTS_SHEET_COLS.get(sheet_name)
            if not sheet_config:
                continue
            sheet_config += SUBJECTS_GENERAL_KOBO_COLS
            df = limit_rename_cols_by_config_tuples(
                df, 
                sheet_config,
            )
            df = merge_trench_df(df, trench_df)
            if df is None:
                continue
            final_cols += [
                c for c in df.columns.tolist() 
                if c not in final_cols and c not in last_final_cols
            ]
            subj_dfs.append(df)
    df = pd.concat(subj_dfs, axis=0)
    final_cols += [c for c in last_final_cols if c in df.columns] 
    df = df[final_cols].copy()
    df.reset_index(drop=True, inplace=True)
    return df
    