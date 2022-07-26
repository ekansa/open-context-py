
import uuid as GenUUID
import numpy as np
import pandas as pd

from opencontext_py.apps.all_items.models import (
    AllManifest,
)
from opencontext_py.apps.all_items import configs

from opencontext_py.apps.etl.kobo import db_lookups
from opencontext_py.apps.etl.kobo import kobo_oc_configs
from opencontext_py.apps.etl.kobo import pc_configs
from opencontext_py.apps.etl.kobo import utilities


"""Uses Pandas to prepare Kobotoolbox exports for Open Context import

"""

TB_ATTRIBUTE_COLS = [
    'subject_label',
    'subject_uuid',
    'subject_uuid_source',
    'Entry Type',
    'Entry Title',
    'Date Documented',
    'Start Page',
    'End Page',
    'Entry Text',
]

SUB_LINK_COLS = [
    'subject_label',
    'subject_uuid',
    'subject_uuid_source',
    pc_configs.LINK_RELATION_TYPE_COL,
    'object_label',
    'object_uuid',
    'object_uuid_source',
    'trench_id',
    'trench_year',
]

PAGE_LINKS_RENAMES = {
    'Date Documented': 'date_documented',
    'Start Page': 'start_page',
    'End Page': 'end_page',
}


def make_df_sub_subjects(dfs):
    "Makes a df_sub subjects only"
    df_sub, sheet_name = utilities.get_df_by_sheet_name_part(
        dfs, 
        sheet_name_part='Trench Book'
    )
    if df_sub is None:
        return dfs
    df_sub['subject_label'] = df_sub['Open Context Label']
    df_sub['subject_uuid'] = df_sub['_uuid']
    df_sub['subject_uuid_source'] = pc_configs.UUID_SOURCE_KOBOTOOLBOX
    return df_sub


def make_paging_links_df(dfs):
    """Makes paging links for trench books"""
    df_sub = make_df_sub_subjects(dfs)
    if df_sub is None:
        return None
    sort_cols = ['trench_id', 'date_documented', 'start_page',  'end_page',]
    df_sub.rename(columns=PAGE_LINKS_RENAMES, inplace=True)
    for c in SUB_LINK_COLS:
        if c in df_sub.columns:
            continue
        df_sub[c] = np.nan
    cols = [c for c in SUB_LINK_COLS if c in df_sub.columns]
    cols += [c for c in sort_cols if c in df_sub.columns and c not in SUB_LINK_COLS]
    df_sub = df_sub[cols].copy()
    tb_ent_indx = (
        (df_sub['trench_id'].notnull())
        & ((df_sub['start_page']>0) | (df_sub['end_page']>0))
    )
    df = df_sub[tb_ent_indx].copy().reset_index(drop=True)
    df.sort_values(by=sort_cols, inplace=True)
    df_links = []
    rel_configs = [
        ('Previous Entry', -1),
        ('Next Entry', 1),
    ]
    for trench_id in df['trench_id'].unique().tolist():
        for rel_type, index_dif in rel_configs:
            trench_indx = (df['trench_id'] == trench_id)
            df_l = df_sub[trench_indx].copy().reset_index(drop=True)
            df_l.sort_values(by=sort_cols, inplace=True)
            len_df_l = len(df_l.index)
            for i, row in df_l.iterrows():
                other_index = i + index_dif
                if other_index < 0 or other_index >= len_df_l:
                    # we're outside of the index range, so skip.
                    continue
                act_indx = (df_l['subject_uuid'] == row['subject_uuid'])
                df_l.loc[act_indx, pc_configs.LINK_RELATION_TYPE_COL] = rel_type
                df_l.loc[act_indx, 'object_label'] = df_l['subject_label'].iloc[other_index]
                df_l.loc[act_indx, 'object_uuid'] = df_l['subject_uuid'].iloc[other_index]
                df_l.loc[act_indx, 'object_uuid_source'] = pc_configs.UUID_SOURCE_KOBOTOOLBOX
            df_l = df_l[df_l[pc_configs.LINK_RELATION_TYPE_COL].notnull()]
            df_links.append(df_l)
    df_all_paging = pd.concat(df_links)
    df_all_paging.sort_values(by=sort_cols, inplace=True)
    return df_all_paging


def add_trench_unit_uuids(
    df, 
    unit_label_col, 
    unit_uuid_col, 
    unit_uuid_source_col
):
    for col in [unit_label_col, unit_uuid_col, unit_uuid_source_col]:
        if col in df.columns:
            continue
        df[col] = np.nan
    t_index = (
        ~df['trench_id'].isnull()
        & ~df['trench_year'].isnull()
    )
    for _, row in df[t_index].iterrows():
        man_obj = db_lookups.db_reconcile_trench_unit(
            trench_id=row['trench_id'], 
            trench_year=row['trench_year']
        )
        if not man_obj:
            continue
        act_indx = (
            (df['trench_id'] == row['trench_id'])
            & (df['trench_year'] == row['trench_year'])
        )
        df.loc[act_indx, unit_label_col] = man_obj.label
        df.loc[act_indx, unit_uuid_col] = str(man_obj.uuid)
        df.loc[act_indx, unit_uuid_source_col] = pc_configs.UUID_SOURCE_OC_LOOKUP
    return df


def make_tb_main_links_df(df_sub):
    """Adds parent trenchbook links"""
    rows = []
    for trench_id in df_sub['trench_id'].unique().tolist():
        tb_label, tb_uuid = pc_configs.MAIN_TRENCH_BOOKS.get(trench_id, (None, None))
        if not tb_label:
            print(f'Cannot find main trenchbook entry related to {trench_id}')
            continue
        act_index = (
            (df_sub['trench_id'] == trench_id)
            & ~df_sub['subject_label'].isnull()
            & ~df_sub['subject_uuid'].isnull()
        )
        rec = {
            'subject_label': df_sub[act_index]['subject_label'].iloc[0],
            'subject_uuid': df_sub[act_index]['subject_uuid'].iloc[0],
            'subject_uuid_source': df_sub[act_index]['subject_uuid_source'].iloc[0],
            pc_configs.LINK_RELATION_TYPE_COL: 'Is Part of',
            'object_label': tb_label,
            'object_uuid': tb_uuid,
            'object_uuid_source': 'pc_configs',
        }
        rows.append(rec)
    df_main = pd.DataFrame(data=rows)
    return df_main
    

def get_df_sub(dfs):
    """Gets the trench books as subject items """
    df_sub = make_df_sub_subjects(dfs)
    if df_sub is None:
        return None
    df_sub[pc_configs.LINK_RELATION_TYPE_COL] = 'Has Related Trench'
    df_sub['trench_id'] = df_sub['Trench ID']
    df_sub['trench_year'] = df_sub['Date Documented'].dt.year
    df_sub = add_trench_unit_uuids(
        df=df_sub, 
        unit_label_col='object_label',
        unit_uuid_col='object_uuid', 
        unit_uuid_source_col='object_uuid_source',
    )
    cols = [c for c in SUB_LINK_COLS if c in df_sub.columns]
    df_sub = df_sub[cols].copy()
    return df_sub


def prep_links_df(
    dfs,
    subjects_df,
    links_csv_path=pc_configs.TB_LINKS_CSV_PATH,
):
    """Prepares the trench book attribute data"""
    df_list = []
    df_sub = get_df_sub(dfs)
    if df_sub is None:
        return dfs
    df_list.append(df_sub)
    df_main = make_tb_main_links_df(df_sub)
    df_list.append(df_main)
    df_all_paging = make_paging_links_df(dfs)
    if df_all_paging is not None:
        df_list.append(df_all_paging)
    df_all_links = pd.concat(df_list)
    if links_csv_path:
        df_all_links.to_csv(links_csv_path, index=False)
    return df_all_links


def prep_attributes_df(
    dfs,
    attrib_csv_path=pc_configs.TB_ATTRIB_CSV_PATH,
):
    """Prepares the trench book attribute data"""
    df_f, sheet_name = utilities.get_df_by_sheet_name_part(
        dfs, 
        sheet_name_part='Trench Book'
    )
    if df_f is None:
        return dfs
    df_f = utilities.drop_empty_cols(df_f)
    df_f = utilities.update_multivalue_columns(df_f)
    df_f = utilities.clean_up_multivalue_cols(df_f)
    # Update the catalog entry uuids based on the
    # subjects_df uuids.
    df_f['Entry Year'] = df_f['Date Documented'].dt.year
    df_f['subject_label'] = df_f['Open Context Label']
    df_f['subject_uuid'] = df_f['_uuid']
    df_f['subject_uuid_source'] = pc_configs.UUID_SOURCE_KOBOTOOLBOX
    cols = [c for c in TB_ATTRIBUTE_COLS if c in df_f.columns]
    df_f = df_f[cols].copy()
    if attrib_csv_path:
        df_f.to_csv(attrib_csv_path, index=False)
    return dfs


def prepare_attributes_links(
    excel_dirpath=pc_configs.KOBO_EXCEL_FILES_PATH, 
    attrib_csv_path=pc_configs.TB_ATTRIB_CSV_PATH,
    links_csv_path=pc_configs.TB_LINKS_CSV_PATH,
    subjects_path=pc_configs.SUBJECTS_CSV_PATH,
):
    """Prepares trench book dataframes."""
    xlsx_files = utilities.list_excel_files(excel_dirpath)
    if not xlsx_files:
        return None
    subjects_df = pd.read_csv(subjects_path)
    dfs = None
    for excel_filepath in xlsx_files:
        if not 'Trench_Book' in excel_filepath:
            continue
        dfs = utilities.read_excel_to_dataframes(excel_filepath)
        dfs = prep_attributes_df(
            dfs,
            attrib_csv_path=attrib_csv_path
        )
    _ = prep_links_df(
        dfs,
        subjects_df,
        links_csv_path=links_csv_path,
    )
    return dfs