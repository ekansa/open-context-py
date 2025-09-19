
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

from opencontext_py.apps.etl.kobo import small_finds
importlib.reload(small_finds)

dfs = small_finds.prepare_attributes_links()


"""

CATALOG_OBJ_COLS = [
    'Catalog ID',
]

DF_REL_ALL_COLS = (
    pc_configs.FIRST_LINK_REL_COLS
    + [c for _,c in pc_configs.RELS_RENAME_COLS.items() if c not in pc_configs.FIRST_LINK_REL_COLS]
    + CATALOG_OBJ_COLS
)


def ensure_catalog_id(df):
    """Make sure we have a catalog ID in the dataframe"""
    if 'Catalog ID' in df.columns.tolist():
        return df
    for pc_id_col in ['PC ID', 'PC_ID']:
        if pc_id_col in df.columns.tolist():
            df['Catalog ID'] = df[pc_id_col]
            break
    if not 'Catalog ID' in df.columns.tolist():
        raise ValueError('We do not have a Catalog ID field in the small_finds data')
    return df


def get_links_from_rel_ids(dfs):
    """Gets links from the related links sheet"""
    # import pdb; pdb.set_trace()
    df_link, sheet_name = utilities.get_df_by_sheet_name_part(
        dfs,
        sheet_name_part='Small Find'
    )
    if df_link is None:
        return None
    df_subjects = pd.read_csv(pc_configs.SUBJECTS_CSV_PATH)
    link_indx = ~df_link['Catalog ID'].isnull()
    # Fix columns underscores for required columns.
    replace_cols = {
        'Find_ID': 'Find ID',
        'OC_Find_ID': 'OC Find ID', 
        'Catalog_ID': 'Catalog ID',
    }
    fix_cols = {c:v for c, v in replace_cols.items() if c in df_link.columns}
    df_link.rename(columns=fix_cols, inplace=True)
    # Make a dataframe of small finds records that link to PC numbers
    df_link = df_link[link_indx][['Find ID', 'OC Find ID', 'Catalog ID', '_uuid']].copy()
    df_link['find_name'] = df_link['OC Find ID']
    df_link['find_uuid'] = df_link['_uuid']
    df_link['subject_label'] = df_link['OC Find ID']
    df_link['subject_uuid'] = df_link['_uuid']
    df_link['object_label'] = df_link['Catalog ID'].apply(
        lambda x: utilities.normalize_catalog_label(x),
    )
    df_link[pc_configs.LINK_RELATION_TYPE_COL] = 'Cataloged as'
    df_link['object_uuid'] = np.nan
    df_link['object_uuid_source'] = np.nan
    # Now look up the UUIDs for the objects.
    for i, row in df_link.iterrows():
        object_label = None
        object_uuid = None
        object_uuid_source = None
        raw_object_id = row['object_label']
        act_labels = [str(raw_object_id)]
        _, act_classes = pc_configs.REL_SUBJECTS_PREFIXES.get('Cataloged Object', ([], []))
        if len(act_classes) == 0:
            # Didn't find any classes in our object type lookup, so continue
            continue
        man_obj = db_lookups.db_reconcile_by_labels_item_class_slugs(
            label_list=act_labels,
            item_class_slug_list=act_classes,
        )
        if not man_obj:
            # try to extract the related ID from the label of the media resource
            man_obj = db_lookups.get_related_object_from_item_label(
                item_label=row['Catalog ID']
            )
        if man_obj:
            # Only accept a single result from the
            # lookup.
            object_label = man_obj.label
            object_uuid = str(man_obj.uuid)
            object_uuid_source = pc_configs.UUID_SOURCE_OC_LOOKUP
        if not object_uuid:
            object_label, object_uuid, object_uuid_source = utilities.get_missing_catalog_item_from_df_subjects(
                item_label=row['Catalog ID'],
                df_subjects=df_subjects,
            )
        if not object_uuid:
            continue
        up_indx = (
            (df_link['object_label'] == raw_object_id)
        )
        df_link.loc[up_indx, 'object_label'] = object_label
        df_link.loc[up_indx, 'object_uuid'] = object_uuid
        df_link.loc[up_indx, 'object_uuid_source'] = object_uuid_source
    return df_link


def make_trench_super_link_df(dfs, subjects_df):
    """Makes a dataframe for locus trench supervisors"""
    df, _ = utilities.get_df_by_sheet_name_part(
        dfs,
        sheet_name_part='Small Find'
    )
    if df is None:
        return None
    # Update the locus entry uuids based on the
    # subjects_df uuids.
    df = utilities.add_final_subjects_uuid_label_cols(
        df=df,
        subjects_df=subjects_df,
        form_type='small find',
        final_label_col='subject_label',
        final_uuid_col='subject_uuid',
        final_uuid_source_col='subject_uuid_source',
        orig_uuid_col='_uuid',
    )
    return utilities.make_trench_supervisor_link_df(df)


def prep_links_df(
    dfs,
    subjects_df,
    links_csv_path=pc_configs.SMALL_FINDS_LINKS_CSV_PATH
):
    """Makes a dataframe for small find object linking relations"""
    df_list = []
    df_rel = get_links_from_rel_ids(
        dfs,
    )
    if df_rel is not None:
        df_list.append(df_rel)
    # Make a dataframe of trench supervisors
    df_super = make_trench_super_link_df(dfs, subjects_df)
    if df_super is not None:
        df_list.append(df_super)
    if len(df_list) == 0:
        return None
    df_all_links = pd.concat(df_list)
    cols = [c for c in DF_REL_ALL_COLS if c in df_all_links.columns]
    df_all_links = df_all_links[cols].copy()
    # Update the catalog entry uuids based on the
    # subjects_df uuids.
    df_all_links = utilities.add_final_subjects_uuid_label_cols(
        df=df_all_links,
        subjects_df=subjects_df,
        form_type='small find',
        final_label_col='subject_label',
        final_uuid_col='subject_uuid',
        final_uuid_source_col='subject_uuid_source',
        orig_uuid_col='_uuid',
    )
    df_all_links = utilities.df_fill_in_by_shared_id_cols(
        df=df_all_links,
        col_to_fill='subject_label',
        id_cols=['subject_uuid'],
    )
    if links_csv_path:
        df_all_links.to_csv(links_csv_path, index=False)
    return df_all_links





def prep_attributes_df(
    dfs,
    subjects_df,
    attrib_csv_path=pc_configs.SMALL_FINDS_ATTRIB_CSV_PATH,
):
    """Prepares the small finds attribute data"""
    df_f, sheet_name = utilities.get_df_by_sheet_name_part(
        dfs,
        sheet_name_part='Small Find'
    )
    if df_f is None:
        return dfs
    # Fixes underscore columns in df
    df_f = utilities.fix_df_col_underscores(df_f)
    df_f = ensure_catalog_id(df_f)
    df_f = utilities.drop_empty_cols(df_f)
    df_f = utilities.update_multivalue_columns(df_f)
    df_f = utilities.clean_up_multivalue_cols(df_f)
     # Make sure the trench doesn't have an underscore
    df_f = utilities.remove_col_value_underscores(df_f, col='Trench')
    # Update the catalog entry uuids based on the
    # subjects_df uuids.
    df_f = utilities.add_final_subjects_uuid_label_cols(
        df=df_f,
        subjects_df=subjects_df,
        form_type='small find',
        final_label_col='subject_label',
        final_uuid_col='subject_uuid',
        final_uuid_source_col='subject_uuid_source',
        orig_uuid_col='_uuid',
    )
    # small find data has lots of Kobo expressed slugs that need to be
    # normalized to normal Open Context slugs
    df_f = utilities.make_oc_normal_slug_values(df_f)
    # Add geospatial coordinates
    df_f = grid_geo.create_global_lat_lon_columns(df_f)
    # Make sure everything has a uuid.
    df_f = utilities.not_null_subject_uuid(df_f)
    if attrib_csv_path:
        df_f.to_csv(attrib_csv_path, index=False)
    dfs[sheet_name] = df_f
    return dfs


def prepare_attributes_links(
    excel_dirpath=pc_configs.KOBO_EXCEL_FILES_PATH,
    attrib_csv_path=pc_configs.SMALL_FINDS_ATTRIB_CSV_PATH,
    links_csv_path=pc_configs.SMALL_FINDS_LINKS_CSV_PATH,
    subjects_path=pc_configs.SUBJECTS_CSV_PATH,
):
    """Prepares small find dataframes."""
    xlsx_files = utilities.list_excel_files(excel_dirpath)
    if not xlsx_files:
        return None
    subjects_df = pd.read_csv(subjects_path)
    dfs = None
    for excel_filepath in xlsx_files:
        if not 'Small_Find' in excel_filepath:
            continue
        dfs = utilities.read_excel_to_dataframes(excel_filepath)
        dfs = prep_attributes_df(
            dfs,
            subjects_df,
            attrib_csv_path=attrib_csv_path
        )
    _ = prep_links_df(
        dfs,
        subjects_df,
        links_csv_path=links_csv_path,
    )
    return dfs