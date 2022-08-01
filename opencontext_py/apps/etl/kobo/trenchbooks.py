
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
    'Entry Year',
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

LOCUS_LINK_COLS = [
    'subject_label',
    'subject_uuid',
    'subject_uuid_source',
    'unit_label',
    'unit_uuid',
    pc_configs.LINK_RELATION_TYPE_COL,
    'object_label',
    'object_uuid',
    'object_uuid_source',
    'locus_number',
]


def make_df_sub_subjects(dfs):
    """Makes a df_sub subjects only"""
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


def make_trench_super_link_df(dfs):
    """Makes a dataframe for locus trench supervisors"""
    df = make_df_sub_subjects(dfs)
    if df is None:
        return None
    return utilities.make_trench_supervisor_link_df(df)


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
    

def get_df_sub(dfs, subjects_df):
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
    # Use the subjects_df to fill in missing trench/unit ids.
    missing_indx = (
        df_sub['object_uuid'].isnull()
        & ~df_sub['trench_id'].isnull()
        & ~df_sub['trench_year'].isnull()
    )
    for _, row in df_sub[missing_indx].iterrows():
        lookup_indx = (
            (subjects_df['trench_id'] == row['trench_id'])
            & (subjects_df['trench_year'] == row['trench_year'])
        )
        if subjects_df[lookup_indx].empty:
            continue
        act_indx = (
            (df_sub['trench_id'] == row['trench_id'])
            & (df_sub['trench_year'] == row['trench_year'])
        )
        df_sub.loc[act_indx, pc_configs.LINK_RELATION_TYPE_COL] = 'Has Related Trench'
        df_sub.loc[act_indx, 'object_label'] = subjects_df[lookup_indx]['unit_name'].iloc[0]
        df_sub.loc[act_indx, 'object_uuid'] = subjects_df[lookup_indx]['unit_uuid'].iloc[0]
        df_sub.loc[act_indx, 'object_uuid_source'] = 'subjects_df'
    cols = [c for c in SUB_LINK_COLS if c in df_sub.columns]
    df_sub = df_sub[cols].copy()
    return df_sub


def make_df_rel_with_units(dfs, df_sub, sheet_name_part, related_orig_col, related_new_col):
    """Makes a dataframe of items related to trenchbooks that includes unit_labels, unit_uuids"""
    df, _ = utilities.get_df_by_sheet_name_part(
        dfs, 
        sheet_name_part=sheet_name_part,
    )
    if df is None:
        return None
    df['subject_uuid'] = df['_submission__uuid']
    df[related_new_col] = df[related_orig_col]
    df = df[['subject_uuid', related_new_col]].copy()
    # Now merge the df_sub, which has the trench/unit uuid associated.
    df_sub = df_sub.copy()
    df_sub.rename(columns={'object_label': 'unit_name', 'object_uuid': 'unit_uuid'}, inplace=True)
    df_sub = df_sub[
        [
            'subject_label', 
            'subject_uuid', 
            'subject_uuid_source',
            'unit_name',
            'unit_uuid',
            'trench_id',
            'trench_year',
        ]
    ].copy()
    df = pd.merge(df, df_sub, on='subject_uuid', how='left')
    for col in [pc_configs.LINK_RELATION_TYPE_COL, 'object_label', 'object_uuid', 'object_uuid_source']:
        df[col] = np.nan
    return df


def make_locus_links_df(df_sub, subjects_df, dfs):
    """Make a dataframe for linking relations with loci"""
    df_loci = make_df_rel_with_units(
        dfs=dfs, 
        df_sub=df_sub, 
        sheet_name_part='locus', 
        related_orig_col='Related Locus', 
        related_new_col='locus_number'
    )
    if df_loci is None:
        return None
    for _, row in df_loci.iterrows():
        lookup_indx = (
            (subjects_df['unit_uuid'] == row['unit_uuid'])
            & (subjects_df['locus_number'] == row['locus_number'])
        )
        if subjects_df[lookup_indx].empty:
            continue
        act_indx = (
            (df_loci['unit_uuid'] == row['unit_uuid'])
            & (df_loci['locus_number'] == row['locus_number'])
        )
        df_loci.loc[act_indx, pc_configs.LINK_RELATION_TYPE_COL] = 'Related Open Locus'
        df_loci.loc[act_indx, 'object_label'] = subjects_df[lookup_indx]['locus_name'].iloc[0]
        df_loci.loc[act_indx, 'object_uuid'] = subjects_df[lookup_indx]['locus_uuid'].iloc[0]
        df_loci.loc[act_indx, 'object_uuid_source'] = 'subjects_df'
    return df_loci


def make_small_find_links_df(df_sub, subjects_df, dfs):
    """Make a dataframe for linking relations with loci"""
    df_sf = make_df_rel_with_units(
        dfs=dfs, 
        df_sub=df_sub, 
        sheet_name_part='find', 
        related_orig_col='Related Find', 
        related_new_col='rel_find'
    )
    if df_sf is None:
        return None
    for _, row in df_sf.iterrows():
        lookup_indx = (
            (subjects_df['unit_uuid'] == row['unit_uuid'])
            & (subjects_df['find_name'].str.endswith(f"-{row['rel_find']}"))
        )
        if subjects_df[lookup_indx].empty:
            continue
        act_indx = (
            (df_sf['unit_uuid'] == row['unit_uuid'])
            & (df_sf['rel_find'] == row['rel_find'])
        )
        df_sf.loc[act_indx, pc_configs.LINK_RELATION_TYPE_COL] = 'Related Small Find'
        df_sf.loc[act_indx, 'object_label'] = subjects_df[lookup_indx]['find_name'].iloc[0]
        df_sf.loc[act_indx, 'object_uuid'] = subjects_df[lookup_indx]['find_uuid'].iloc[0]
        df_sf.loc[act_indx, 'object_uuid_source'] = 'subjects_df'
    return df_sf


def prep_links_df(
    dfs,
    subjects_df,
    links_csv_path=pc_configs.TB_LINKS_CSV_PATH,
):
    """Prepares the trench book attribute data"""
    df_list = []
    df_sub = get_df_sub(dfs, subjects_df)
    if df_sub is None:
        return dfs
    df_list.append(df_sub)
    df_main = make_tb_main_links_df(df_sub)
    df_list.append(df_main)
    df_all_paging = make_paging_links_df(dfs)
    if df_all_paging is not None:
        df_list.append(df_all_paging)
    df_loci = make_locus_links_df(df_sub, subjects_df, dfs)
    if df_loci is not None:
        df_list.append(df_loci)
    df_sf = make_small_find_links_df(df_sub, subjects_df, dfs)
    if df_sf is not None:
        df_list.append(df_sf)
    # Make a dataframe of trench supervisors
    df_super = make_trench_super_link_df(dfs)
    if df_super is not None:
        df_list.append(df_super)
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
    # Make sure everything has a uuid.
    df_f = utilities.not_null_subject_uuid(df_f)
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