
import copy
from re import U
from turtle import up
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

from opencontext_py.apps.etl.kobo import catalog
importlib.reload(catalog)

dfs = catalog.prepare_catalog()


"""

CATALOG_ATTRIBUTES_SHEET = 'Catalog Entry'
CATALOG_RELS_SHEET = 'rel_ids_repeat'

SMALL_FIND_OBJ_COLS = [
    'Trench ID',
    'Year',
    'Locus ID',
    'Field Given Find ID',
]

TRENCH_OBJ_COLS = [
    'Trench ID',
    'Year',
    'Trench Book Entry Date',
    'Trench Book Start Page',
    'Trench Book End Page'
]

DF_REL_ALL_COLS = (
    pc_configs.FIRST_LINK_REL_COLS
    + [c for _,c in pc_configs.RELS_RENAME_COLS.items() if c not in pc_configs.FIRST_LINK_REL_COLS]
    + SMALL_FIND_OBJ_COLS
    + TRENCH_OBJ_COLS
)


def prep_df_link_from_attrib_sheet(dfs):
    df_link, _ = utilities.get_df_by_sheet_name_part(
        dfs, 
        sheet_name_part='Catalog'
    )
    if df_link is None:
        return None
    df_link = df_link.copy().reset_index(drop=True)
    df_link['subject_uuid'] = df_link['_uuid']
    df_link['subject_label'] = df_link['catalog_name']
    df_link['object_label'] = np.nan
    df_link['object_uuid'] = np.nan
    df_link['object_uuid_source'] = np.nan
    return df_link


def make_catalog_small_finds_links_df(dfs):
    """Makes dataframe for a catalog links to small finds entries"""
    df_link = prep_df_link_from_attrib_sheet(dfs)
    if df_link is None:
        return None
    if not set(SMALL_FIND_OBJ_COLS).issubset(set(df_link.columns.tolist())):
        return None
    df_link[pc_configs.LINK_RELATION_TYPE_COL] = 'Initially documented as'
    for i, row in df_link[df_link['Field Given Find ID'].notnull()].iterrows():
        object_uuid = None
        object_source = None
        find_num = int(float(row['Field Given Find ID']))
        # Try looking in the database for a match
        obj = db_lookups.db_lookup_smallfind(
            row['Trench ID'],
            row['Year'],
            row['Locus ID'],
            find_num
        )
        if not obj:
            continue
        object_uuid = str(obj.uuid)
        object_source = pc_configs.UUID_SOURCE_OC_LOOKUP
        print('Catalog small find lookup: {}-{}-{}-{} -> {}'.format(
                row['Year'],
                row['Trench ID'],
                row['Locus ID'],
                find_num,
                object_uuid,
            )
        )
        up_indx = (
            (df_link['Year'] == row['Year'])
            & (df_link['Trench ID'] == row['Trench ID'])
            & (df_link['Locus ID'] == row['Locus ID'])
            & (df_link['Field Given Find ID'] == row['Field Given Find ID'])
        )
        df_link.loc[up_indx, 'object_label'] = obj.label
        df_link.loc[up_indx, 'object_uuid'] = object_uuid
        df_link.loc[up_indx, 'object_uuid_source'] = object_source
    df_link = df_link[
        (
           pc_configs.FIRST_LINK_REL_COLS
            + SMALL_FIND_OBJ_COLS
        )
    ]
    return df_link


def make_catalog_tb_links_df(dfs):
    """Makes dataframe for a catalog links to trench book entries"""
    df_link = prep_df_link_from_attrib_sheet(dfs)
    if df_link is None:
        return None
    if not set(TRENCH_OBJ_COLS).issubset(set(df_link.columns.tolist())):
        return None
    for col in df_link.columns:
        df_link[col].replace('', np.nan, inplace=True)
    df_link[pc_configs.LINK_RELATION_TYPE_COL] = 'Has Related Trench Book Entry'
    for col in ['object_label', 'object_uuid', 'object_uuid_source']:
        if col in df_link.columns:
            continue
        df_link[col] = np.nan
    for i, row in df_link.iterrows():
        object_uuid = None
        object_source = None
        # Try looking in the database for a match
        obj = db_lookups.db_lookup_trenchbook(
            row['Trench ID'],
            row['Year'],
            row['Trench Book Entry Date'],
            row['Trench Book Start Page'],
            row['Trench Book End Page']
        )
        if not obj:
            continue
        object_uuid = str(obj.uuid)
        object_source = pc_configs.UUID_SOURCE_OC_LOOKUP
        ind_criteria = []
        up_indx = (
            (df_link[pc_configs.LINK_RELATION_TYPE_COL] == 'Has Related Trench Book Entry')
            & (df_link['Trench ID'] == row['Trench ID'])
            & (df_link['Year'] == row['Year'])
        )
        ind_criteria = [
            f"trench_id {row['Trench ID']}", 
            f"year {row['Year']}", 
        ]
        if isinstance(row['Trench Book Entry Date'], pd.Timestamp):
            up_indx &= (df_link['Trench Book Entry Date'] == row['Trench Book Entry Date'])
            ind_criteria.append(f"Entry {row['Trench Book Entry Date']}")
        else:
            up_indx &= df_link['Trench Book Entry Date'].isnull()
            ind_criteria.append(f"entry is null")
        if row['Trench Book Start Page'] > 0:
            up_indx &= (df_link['Trench Book Start Page'] >= row['Trench Book Start Page'])
            ind_criteria.append(f"start {row['Trench Book Start Page']}")
        else:
            up_indx &= df_link['Trench Book Start Page'].isnull()
            ind_criteria.append(f"start is null")
        if row['Trench Book End Page'] > 0:
            up_indx &= (df_link['Trench Book End Page'] <= row['Trench Book End Page'])
            ind_criteria.append(f"end {row['Trench Book Start Page']}")
        else:
            up_indx &= df_link['Trench Book End Page'].isnull()
            ind_criteria.append(f"end is null")
        if df_link[up_indx].empty:
            print(f'Problem associating {obj.label} ({obj.uuid})')
            print(', '.join(ind_criteria))
            # import pdb; pdb.set_trace()
            continue
        df_link.loc[up_indx, 'object_label'] = obj.label
        df_link.loc[up_indx, 'object_uuid'] = object_uuid
        df_link.loc[up_indx, 'object_uuid_source'] = object_source
    
    df_link = df_link[
        (
           pc_configs.FIRST_LINK_REL_COLS
            + TRENCH_OBJ_COLS
        )
    ]
    return df_link


def get_links_from_rel_ids(dfs):
    """Gets links from the related links sheet"""
    # import pdb; pdb.set_trace()
    df_link = utilities.get_prepare_df_link_from_rel_id_sheet(dfs)
    if df_link is None:
        return None
    df_f = prep_df_link_from_attrib_sheet(dfs)
    if df_f is None:
        return None
    df_f['subject_uuid'] = df_f['_uuid']
    df_f = df_f[['subject_uuid', 'Year', 'Trench ID', 'Locus ID']].copy()
    df_link = pd.merge(df_link, df_f, on='subject_uuid', how='left')
    link_indx = ~df_link['object_related_id'].isnull()
    # Now look up the UUIDs for the objects.
    for i, row in df_link[link_indx].iterrows():
        object_uuid = None
        object_uuid_source = None
        raw_object_id = row['object_related_id']
        object_type = row['object_related_type']
        act_labels = [str(raw_object_id)]
        if object_type == 'Cataloged Object':
            act_labels.append(utilities.normalize_catalog_label(str(raw_object_id)))
        act_prefixes, act_classes = pc_configs.REL_SUBJECTS_PREFIXES.get(object_type, ([], []))
        if len(act_classes) == 0:
            # Didn't find any classes in our object type lookup, so continue
            continue
        act_labels += [p + str(raw_object_id) for p in act_prefixes if not str(raw_object_id).startswith(p)] 
        man_obj = db_lookups.db_reconcile_by_labels_item_class_slugs(
            label_list=act_labels, 
            item_class_slug_list=act_classes,
        )
        if not man_obj and object_type == 'Small Find':
            man_obj = db_lookups.db_lookup_smallfind(
                row['Trench ID'],
                row['Year'],
                row['Locus ID'],
                raw_object_id
            )
        if not man_obj:
            print(f'Cannot find labels {act_labels} for classes {act_classes}')
            object_label = np.nan
            object_uuid = np.nan
            object_uuid_source = np.nan
        else:
            # Only accept a single result from the 
            # lookup.
            object_label = man_obj.label
            object_uuid = str(man_obj.uuid)
            object_uuid_source = pc_configs.UUID_SOURCE_OC_LOOKUP
        up_indx = (
            (df_link['object_related_id'] == raw_object_id)
            & (df_link['object_related_type'] == object_type)
        )
        df_link.loc[up_indx, 'object_label'] = object_label
        df_link.loc[up_indx, 'object_uuid'] = object_uuid
        df_link.loc[up_indx, 'object_uuid_source'] = object_uuid_source
    return df_link


def prep_links_df(
    dfs,
    subjects_df,
    links_csv_path=pc_configs.CATALOG_LINKS_CSV_PATH
):
    """Makes a dataframe for catalog object linking relations"""
    df_list = []
    df_small_finds_link = make_catalog_small_finds_links_df(
        dfs,
    )
    if df_small_finds_link is not None:
        df_list.append(df_small_finds_link)
    df_tb_link = make_catalog_tb_links_df(
        dfs,
    )
    if df_tb_link is not None:
        df_list.append(df_tb_link)
    df_rel = get_links_from_rel_ids(
        dfs,
    )
    if df_rel is not None:
        df_list.append(df_rel)
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
        form_type='catalog',
        final_label_col='subject_label',
        final_uuid_col='subject_uuid',
        final_uuid_source_col='subject_uuid_source',
        orig_uuid_col='subject_uuid',
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
    attrib_csv_path=pc_configs.CATALOG_ATTRIB_CSV_PATH,
):
    """Prepares the catalog attribute data"""
    df_f, sheet_name = utilities.get_df_by_sheet_name_part(
        dfs, 
        sheet_name_part='Catalog'
    )
    if df_f is None:
        return dfs
    df_f = utilities.drop_empty_cols(df_f)
    df_f = utilities.update_multivalue_columns(df_f)
    df_f = utilities.clean_up_multivalue_cols(df_f)
    df_f = utilities.split_all_cols_with_delim_into_multiple_cols(
        form_type='catalog', 
        df=df_f, 
    )
    # Catalog data has lots of Kobo expressed slugs that need to be
    # normalized to normal Open Context slugs
    df_f = utilities.make_oc_normal_slug_values(df_f)
    # import pdb; pdb.set_trace()
    df_f['catalog_name'] = df_f['Catalog ID (PC)'].apply(
        lambda x: utilities.normalize_catalog_label(x), 
    )
    # Update the catalog entry uuids based on the
    # subjects_df uuids.
    df_f = utilities.add_final_subjects_uuid_label_cols(
        df=df_f, 
        subjects_df=subjects_df,
        form_type='catalog',
        final_label_col='subject_label',
        final_uuid_col='subject_uuid',
        final_uuid_source_col='subject_uuid_source',
        orig_uuid_col='_uuid',
    )
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
    attrib_csv_path=pc_configs.CATALOG_ATTRIB_CSV_PATH,
    links_csv_path=pc_configs.CATALOG_LINKS_CSV_PATH,
    subjects_path=pc_configs.SUBJECTS_CSV_PATH,
):
    """Prepares catalog dataframes."""
    xlsx_files = utilities.list_excel_files(excel_dirpath)
    if not xlsx_files:
        return None
    subjects_df = pd.read_csv(subjects_path)
    dfs = None
    for excel_filepath in xlsx_files:
        if not 'Catalog' in excel_filepath:
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