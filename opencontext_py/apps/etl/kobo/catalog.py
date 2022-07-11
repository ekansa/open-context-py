
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
from opencontext_py.apps.etl.kobo import pc_configs
from opencontext_py.apps.etl.kobo import utilities




"""Uses Pandas to prepare Kobotoolbox exports for Open Context import


"""

CATALOG_ATTRIBUTES_SHEET = 'Catalog Entry'
CATALOG_RELS_SHEET = 'rel_ids_repeat'


FIRST_LINK_REL_COLS = [
    'subject_label',
    'subject_item_class_slug',
    'uuid_source',
    'subject_uuid',
    pc_configs.LINK_RELATION_TYPE_COL,
    'object_uuid',
    'object_uuid_source'
]

RELS_RENAME_COLS = {
    '_submission__uuid': 'subject_uuid',
    'Related Identifiers/Related Record Object/Type of Relationship': pc_configs.LINK_RELATION_TYPE_COL,
    'Related Identifiers/Related Record Object/Related ID': 'object_related_id',
    'Related Identifiers/Related Record Object/Type of Related ID': 'object_related_type',
    'Related Identifiers/Related Record Object/Note about Relationship': 'object_related_note',
}


def get_main_catalog_df(dfs):
    for sheet_name, df in dfs.items():
        if not 'Catalog' in sheet_name:
            continue
        return df, sheet_name
    return None, None


def make_catalog_small_finds_links_df(dfs):
    """Makes dataframe for a catalog links to small finds entries"""
    obj_prop_cols = [
        'Trench ID',
        'Year',
        'Locus ID',
        'Field Given Find ID',
    ]
    df_link, _ = get_main_catalog_df(dfs)
    df_link = df_link.copy().reset_index(drop=True)
    df_link['subject_uuid'] = df_link['_uuid']
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
        )
        df_link.loc[up_indx, 'object_uuid'] = object_uuid
        df_link.loc[up_indx, 'object_uuid_source'] = object_source
    df_link = df_link[
        (
            ['subject_label', 'subject_item_class_slug', 'uuid_source', 'subject_uuid']
            + [pc_configs.LINK_RELATION_TYPE_COL]
            + ['object_uuid', 'object_uuid_source']
            + obj_prop_cols
        )
    ]
    return df_link


def make_catalog_tb_links_df(dfs):
    """Makes dataframe for a catalog links to trench book entries"""
    obj_prop_cols = [
        'Trench ID',
        'Year',
        'Trench Book Entry Date',
        'Trench Book Start Page',
        'Trench Book End Page'
    ]
    df_link, _ = get_main_catalog_df(dfs)
    df_link = df_link.copy().reset_index(drop=True)
    df_link['subject_uuid'] = df_link['_uuid']
    df_link[pc_configs.LINK_RELATION_TYPE_COL] = 'Has Related Trench Book Entry'
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
        up_indx = (
            (df_link['Trench ID'] == row['Trench ID'])
            & (df_link['Year'] == row['Year'])
            # & (tb_df['Date Documented'] == row['Trench Book Entry Date'])
            & (df_link['Trench Book Start Page'] >= row['Trench Book Start Page'])
            & (df_link['Trench Book Start Page'] <= row['Trench Book Start Page'])
        )
        df_link.loc[up_indx, 'object_uuid'] = object_uuid
        df_link.loc[up_indx, 'object_uuid_source'] = object_source
    
    df_link = df_link[
        (
            ['subject_label', 'subject_item_class_slug', 'uuid_source', 'subject_uuid']
            + [pc_configs.LINK_RELATION_TYPE_COL]
            + ['object_uuid', 'object_uuid_source']
            + obj_prop_cols
        )
    ]
    return df_link

def get_links_from_rel_ids(dfs):
    """Gets links from the related links sheet"""
    df_rel, _ = get_main_catalog_df(dfs)
    if df_rel is None:
        return None
    df_rel.rename(
        columns=RELS_RENAME_COLS,
        inplace=True
    )
    # Now look up the UUIDs for the objects.
    for i, row in df_rel.iterrows():
        object_uuid = None
        object_uuid_source = None
        raw_object_id = row['object_related_id']
        object_type = row['object_related_type']
        act_labels = [str(raw_object_id)]
        act_prefixes, act_classes = pc_configs.REL_SUBJECTS_PREFIXES.get(object_type, ([], []))
        if len(act_classes) == 0:
            # Didn't find any classes in our object type lookup, so continue
            continue
        act_labels += [p + str(raw_object_id) for p in act_prefixes]
        
        man_obj = db_lookups.db_reconcile_by_labels_item_class_slugs(
            label_list=act_labels, 
            item_class_slug_list=act_classes,
        )
        if not man_obj:
            object_uuid = np.nan
            object_uuid_source = np.nan
        else:
            # Only accept a single result from the 
            # lookup.
            object_uuid = str(man_obj.uuid)
            object_uuid_source = pc_configs.UUID_SOURCE_OC_LOOKUP
        update_indx = (
            (df_rel['object_related_id'] == raw_object_id)
            & (df_rel['object_related_type'] == object_type)
        )
        df_rel.loc[update_indx, 'object_uuid'] = object_uuid
        df_rel.loc[update_indx, 'object_uuid_source'] = object_uuid_source
    return df_rel


def make_catalog_links_df(dfs):
    """Makes a dataframe for catalog object linking relations"""
    df_small_finds_link = make_catalog_small_finds_links_df(
        dfs,
    )
    df_tb_link = make_catalog_tb_links_df(
        dfs,
    )
    df_rel = get_links_from_rel_ids(
        dfs,
    )
    df_all_links = pd.concat([df_small_finds_link, df_tb_link, df_rel])
    df_all_links = utilities.reorder_first_columns(
        df_all_links,
        FIRST_LINK_REL_COLS
    )
    return df_all_links


def prepare_catalog(excel_dirpath):
    """Prepares catalog dataframes."""
    xlsx_files = utilities.list_excel_files(excel_dirpath)
    if not xlsx_files:
        return None
    dfs = None
    for excel_filepath in xlsx_files:
        if not 'Catalog' in excel_filepath:
            continue
        dfs = utilities.read_excel_to_dataframes(excel_filepath)
        df_f, sheet_name = get_main_catalog_df(dfs)
        if df_f is None:
            continue
        df_f = utilities.drop_empty_cols(df_f)
        df_f = utilities.update_multivalue_columns(df_f)
        df_f = utilities.clean_up_multivalue_cols(df_f)
        dfs[sheet_name] = df_f
    return dfs