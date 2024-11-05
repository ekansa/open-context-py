
import copy
import uuid as GenUUID
import os
import numpy as np
import pandas as pd

from pathlib import Path

from django.db.models import Q
from opencontext_py.apps.all_items.models import (
    AllManifest,
)

from opencontext_py.apps.etl.kobo import db_lookups
from opencontext_py.apps.etl.kobo import grid_geo
from opencontext_py.apps.etl.kobo import pc_configs
from opencontext_py.apps.etl.kobo import utilities




"""Uses Pandas to prepare Kobotoolbox exports for Open Context import

import importlib

from opencontext_py.apps.etl.kobo import bulk_finds
importlib.reload(bulk_finds)

dfs = bulk_finds.prepare_attributes_links()


"""

def prep_links_df(
    dfs,
    subjects_df,
    links_csv_path=pc_configs.BULK_FINDS_LINKS_CSV_PATH,
):
    """Makes a dataframe for bulk finds linking relations"""
    df, _ = utilities.get_df_by_sheet_name_part(
        dfs, 
        sheet_name_part='Bulk Find'
    )
    if df is None:
        return None
    # Fixes underscore columns in df
    df = utilities.fix_df_col_underscores(df)
    # Update the buk find entry uuids based on the
    # subjects_df uuids.
    df = utilities.add_final_subjects_uuid_label_cols(
        df=df, 
        subjects_df=subjects_df,
        form_type='bulk find',
        final_label_col='subject_label',
        final_uuid_col='subject_uuid',
        final_uuid_source_col='subject_uuid_source',
        orig_uuid_col='_uuid',
    )
    df_all_links = utilities.make_trench_supervisor_link_df(df)
    if df_all_links is None:
        return None
    if links_csv_path:
        df_all_links.to_csv(links_csv_path, index=False)
    return df_all_links


def prep_attributes_df(
    dfs,
    subjects_df, 
    attrib_csv_path=pc_configs.BULK_FINDS_ATTRIB_CSV_PATH,
):
    """Prepares the Bulk Finds attribute data"""
    df_f, sheet_name = utilities.get_df_by_sheet_name_part(
        dfs, 
        sheet_name_part='Bulk Find'
    )
    if df_f is None:
        return dfs
    # Fixes underscore columns in df
    # import pdb; pdb.set_trace()
    df_f = utilities.fix_df_col_underscores(df_f)
    df_f = utilities.drop_empty_cols(df_f)
    df_f = utilities.update_multivalue_columns(df_f)
    df_f = utilities.clean_up_multivalue_cols(df_f)
    # Update the buk find entry uuids based on the
    # subjects_df uuids.
    df_f = utilities.add_final_subjects_uuid_label_cols(
        df=df_f, 
        subjects_df=subjects_df,
        form_type='bulk find',
        final_label_col='subject_label',
        final_uuid_col='subject_uuid',
        final_uuid_source_col='subject_uuid_source',
        orig_uuid_col='_uuid',
    )
    # Make sure everything has a uuid.
    df_f = utilities.not_null_subject_uuid(df_f)
    if attrib_csv_path:
        df_f.to_csv(attrib_csv_path, index=False)
    dfs[sheet_name] = df_f
    return dfs


def prepare_attributes_links(
    excel_dirpath=pc_configs.KOBO_EXCEL_FILES_PATH, 
    attrib_csv_path=pc_configs.BULK_FINDS_ATTRIB_CSV_PATH,
    links_csv_path=pc_configs.BULK_FINDS_LINKS_CSV_PATH,
    subjects_path=pc_configs.SUBJECTS_CSV_PATH,
):
    """Prepares Bulk Find dataframes."""
    xlsx_files = utilities.list_excel_files(excel_dirpath)
    if not xlsx_files:
        return None
    subjects_df = pd.read_csv(subjects_path)
    dfs = None
    for excel_filepath in xlsx_files:
        if not 'Bulk_Find' in excel_filepath:
            continue
        dfs = utilities.read_excel_to_dataframes(excel_filepath)
        dfs = prep_attributes_df(
            dfs,
            subjects_df,
            attrib_csv_path=attrib_csv_path
        )
    # NOTE: Only trench supervisor links in this dataset
    _ = prep_links_df(
        dfs,
        subjects_df,
        links_csv_path=links_csv_path,
    )
    return dfs