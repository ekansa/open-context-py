
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

TB_JSON_COL_RENAMES = {
    "Season": 'Entry Year',
    "OC_Label": "Open Context Label",
    "OC Label": "Open Context Label",
}

TB_ATTRIBUTE_COLS = [
    'subject_label',
    'subject_uuid',
    'subject_uuid_source',
    'Book Year',
    'Document Type',
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
    sort_cols = ['trench_id', 'date_documented', 'start_page',  'end_page', ]
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
            # df_l = df_sub[trench_indx].copy().reset_index(drop=True)
            df_l = df_sub.loc[trench_indx].copy()
            df_l.reset_index(drop=True, inplace=True)
            df_l.sort_values(by=sort_cols, inplace=True)
            df_l.reset_index(drop=True, inplace=True)
            len_df_l = len(df_l.index)
            for i, row in df_l.iterrows():
                other_index = i + index_dif
                if other_index < 0 or other_index >= len_df_l:
                    # we're outside of the index range, so skip.
                    continue
                act_index = (df_l['subject_uuid'] == row['subject_uuid'])
                df_l.loc[act_index, pc_configs.LINK_RELATION_TYPE_COL] = rel_type
                df_l.loc[act_index, 'object_label'] = df_l['subject_label'].iloc[other_index]
                df_l.loc[act_index, 'object_uuid'] = df_l['subject_uuid'].iloc[other_index]
                df_l.loc[act_index, 'object_uuid_source'] = pc_configs.UUID_SOURCE_KOBOTOOLBOX
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
        df[col] = ''
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
        act_index = (
            (df['trench_id'] == row['trench_id'])
            & (df['trench_year'] == row['trench_year'])
        )
        df.loc[act_index, unit_label_col] = man_obj.label
        df.loc[act_index, unit_uuid_col] = str(man_obj.uuid)
        df.loc[act_index, unit_uuid_source_col] = pc_configs.UUID_SOURCE_OC_LOOKUP
    return df


def make_main_trench_books_df(trench_id_list):
    """Makes a dataframe of the main trench books (these are added 'hubs') to bundle
    multiple related trench book entries.
    """
    main_book_year_config = pc_configs.MAIN_TRENCH_BOOKS.get(pc_configs.DEFAULT_IMPORT_YEAR, {})
    rows = []
    for trench_id in trench_id_list:
        subject_label, subject_uuid = main_book_year_config.get(trench_id, (None, None))
        if not subject_uuid:
            continue
        row = {
            'subject_label': subject_label,
            'subject_uuid': subject_uuid,
            'subject_uuid_source': 'pc_configs',
            'Trench ID': trench_id,
            'trench_id': trench_id,
            'trench_year': pc_configs.DEFAULT_IMPORT_YEAR,
            'Book Year': pc_configs.DEFAULT_IMPORT_YEAR,
            'Document Type': 'Trench Book',
            'Entry Text': (
                """
                <div>
                <p>A "trench book" provides a narrative account of excavations activities and initial (preliminary) interpretations.
                Trench book documentation can provide key information about archaeological context.
                To facilitate discovery, access, and use, the project's hand-written trench books have been transcribed and associated with other data.
                </p> <br/>
                <p>The links below provide transcriptions of the entries for this trench book.</p>
                </div>
                """
            ),
        }
        rows.append(row)
    df_tb_m = pd.DataFrame(data=rows)
    return df_tb_m


def make_tb_main_links_df(df_sub):
    """Adds parent trenchbook links"""
    df_links = []
    act_index = ~df_sub['trench_id'].isnull()
    trench_id_list = df_sub[act_index]['trench_id'].unique().tolist()

    # First make the trench book main entries, and link them to their trenches (unit_uuids)
    df_tb_m = make_main_trench_books_df(trench_id_list)
    tb_m_cols = ['subject_label', 'subject_uuid', 'subject_uuid_source', 'trench_id', 'trench_year',]
    df_tb_m = df_tb_m[tb_m_cols]
    df_tb_m[pc_configs.LINK_RELATION_TYPE_COL] = 'Has Related Trench'
    df_tb_m = add_trench_unit_uuids(
        df=df_tb_m,
        unit_label_col='object_label',
        unit_uuid_col='object_uuid',
        unit_uuid_source_col='object_uuid_source',
    )
    df_links.append(df_tb_m)

    year_main_trenchbooks = pc_configs.MAIN_TRENCH_BOOKS.get(pc_configs.DEFAULT_IMPORT_YEAR, {})
    # Now link the various trench entries with their associate main trench books.
    for trench_id in trench_id_list:
        tb_label, tb_uuid = year_main_trenchbooks.get(trench_id, (None, None))
        if not tb_label:
            tb_label, tb_uuid = year_main_trenchbooks.get(trench_id.replace('_', ' '), (None, None))
        if not tb_label:
            print(f'Cannot find main trenchbook entry related to {trench_id}')
            continue
        act_index = (
            (df_sub['trench_id'] == trench_id)
            & ~df_sub['subject_label'].isnull()
            & ~df_sub['subject_uuid'].isnull()
            & (df_sub['subject_uuid'] != tb_uuid)
        )
        df_new = df_sub[act_index].copy()
        df_new[pc_configs.LINK_RELATION_TYPE_COL] = 'Is Part of'
        df_new['object_label'] = tb_label
        df_new['object_uuid'] = tb_uuid
        df_new['object_uuid_source'] = 'pc_configs'
        df_links.append(df_new)
    df_main = pd.concat(df_links)
    return df_main


def get_df_sub(dfs, subjects_df):
    """Gets the trench books as subject items """
    df_sub = make_df_sub_subjects(dfs)
    if df_sub is None:
        return None
    df_sub[pc_configs.LINK_RELATION_TYPE_COL] = 'Has Related Trench'
    df_sub['trench_id'] = df_sub['Trench ID']
    try:
        df_sub['trench_year'] = df_sub['Date Documented'].dt.year
    except:
        df_sub['trench_year'] = pc_configs.DEFAULT_IMPORT_YEAR
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
        act_index = (
            (df_sub['trench_id'] == row['trench_id'])
            & (df_sub['trench_year'] == row['trench_year'])
        )
        df_sub.loc[act_index, pc_configs.LINK_RELATION_TYPE_COL] = 'Has Related Trench'
        df_sub.loc[act_index, 'object_label'] = subjects_df[lookup_indx]['unit_name'].iloc[0]
        df_sub.loc[act_index, 'object_uuid'] = subjects_df[lookup_indx]['unit_uuid'].iloc[0]
        df_sub.loc[act_index, 'object_uuid_source'] = 'subjects_df'
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
    df = utilities.fix_df_col_underscores(df)
    cols = df.columns.tolist()
    if related_orig_col not in cols:
        partial_match_col = None
        for col in cols:
            if related_orig_col in col:
                partial_match_col = col
        if not partial_match_col:
            # skip out, we can't find a matching column.
            return None
        related_orig_col = partial_match_col
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
    # Check to make sure we have the required columns in the subjects_df
    subjects_df_req_cols = ['unit_uuid', 'locus_number']
    for req_col in subjects_df_req_cols:
        if not req_col in subjects_df.columns:
            return None
    for _, row in df_loci.iterrows():
        try:
            locus_number = int(float(row['locus_number']))
        except:
            locus_number = row['locus_number']
        lookup_indx = (
            (subjects_df['unit_uuid'] == row['unit_uuid'])
            & (subjects_df['locus_number'] == locus_number)
        )
        if subjects_df[lookup_indx].empty:
            print(f"Cannot find locus {locus_number} in unit_uuid {row['unit_uuid']}")
            continue
        act_index = (
            (df_loci['unit_uuid'] == row['unit_uuid'])
            & (df_loci['locus_number'] == str(locus_number))
        )
        df_loci.loc[act_index, pc_configs.LINK_RELATION_TYPE_COL] = 'Related Open Locus'
        df_loci.loc[act_index, 'object_label'] = subjects_df[lookup_indx]['locus_name'].iloc[0]
        df_loci.loc[act_index, 'object_uuid'] = subjects_df[lookup_indx]['locus_uuid'].iloc[0]
        df_loci.loc[act_index, 'object_uuid_source'] = 'subjects_df'
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
    # Check to make sure we have the required columns in the subjects_df
    subjects_df_req_cols = ['unit_uuid', 'find_name']
    for req_col in subjects_df_req_cols:
        if not req_col in subjects_df.columns:
            return None
    for _, row in df_sf.iterrows():
        find_rel = 'Related Small Find'
        find_name = row['rel_find']
        alt_find_name = find_name.replace('sf-', 'sf ').replace('bf-', 'bf ').replace('SF-', 'SF ')
        lookup_indx = (
            (subjects_df['unit_uuid'] == row['unit_uuid'])
            & (
                (subjects_df['find_name'].str.endswith(f"-{find_name}"))
                | (subjects_df['find_name'].str.contains(find_name, na=False, case=False))
                | (subjects_df['find_name'].str.contains(alt_find_name, na=False, case=False))
            )
        )
        if subjects_df[lookup_indx].empty:
            continue
        act_index = (
            (df_sf['unit_uuid'] == row['unit_uuid'])
            & (df_sf['rel_find'] == row['rel_find'])
        )
        df_sf.loc[act_index, pc_configs.LINK_RELATION_TYPE_COL] = find_rel
        df_sf.loc[act_index, 'object_label'] = subjects_df[lookup_indx]['find_name'].iloc[0]
        df_sf.loc[act_index, 'object_uuid'] = subjects_df[lookup_indx]['find_uuid'].iloc[0]
        df_sf.loc[act_index, 'object_uuid_source'] = 'subjects_df'
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
    print('Make trenchbook main links...')
    df_main = make_tb_main_links_df(df_sub)
    df_list.append(df_main)
    print('Make trenchbook paging links...')
    df_all_paging = make_paging_links_df(dfs)
    if df_all_paging is not None:
        df_list.append(df_all_paging)
    print('Make trenchbook locus links...')
    df_loci = make_locus_links_df(df_sub, subjects_df, dfs)
    if df_loci is not None:
        df_list.append(df_loci)
    print('Make trenchbook small finds links...')
    df_sf = make_small_find_links_df(df_sub, subjects_df, dfs)
    if df_sf is not None:
        df_list.append(df_sf)
    # Make a dataframe of trench supervisors
    print('Make trenchbook locus links...')
    df_super = make_trench_super_link_df(dfs)
    if df_super is not None:
        df_list.append(df_super)
    df_all_links = pd.concat(df_list)
    if links_csv_path:
        df_all_links.to_csv(links_csv_path, index=False)
    return df_all_links


def add_main_trench_books(df_f):
    """Adds the main trench books so they can be imported with the others"""
    act_index = ~df_f['Trench ID'].isnull()
    trench_id_list = df_f[act_index]['Trench ID'].unique().tolist()
    df_tb_m = make_main_trench_books_df(trench_id_list)
    df_f = pd.concat([df_f, df_tb_m])
    return df_f

def add_tb_json_entries(df_f, json_path=pc_configs.KOBO_TB_JSON_PATH):
    """Adds the Entry Text data to the attributes"""
    # NOTE: Kobo can't export long entry text data into Excel or CSV,
    # So we need to use the Kobo API to download these as JSON data.
    # The JSON file of Trenchbook attributes has the expected data, and
    # will merge this in via a join.
    df_j = pd.read_json(json_path)
    # Fixes underscore columns in df_f
    df_j = utilities.fix_df_col_underscores(df_j)
    r_cols = {c:r for c, r in TB_JSON_COL_RENAMES.items() if c in df_j.columns}
    df_j.rename(columns=r_cols, inplace=True)
    if 'Entry Text' in df_j.columns:
        pass
    elif 'Entry_Text' in df_j.columns:
        df_j['Entry Text'] = df_j['Entry_Text']
    df_j = df_j[['_uuid', 'Entry Text']].copy()
    if 'Entry Text' in df_f.columns:
        df_f.drop('Entry Text', axis=1, inplace=True)
    df_f = pd.merge(df_f, df_j, on='_uuid', how='left')
    # import pdb; pdb.set_trace()
    return df_f


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
    # Fixes underscore columns in df_f
    df_f = utilities.fix_df_col_underscores(df_f)
    r_cols = {c:r for c, r in TB_JSON_COL_RENAMES.items() if c in df_f.columns}
    df_f.rename(columns=r_cols, inplace=True)
    df_f = add_tb_json_entries(df_f)
    df_f = utilities.drop_empty_cols(df_f)
    df_f = utilities.update_multivalue_columns(df_f)
    df_f = utilities.clean_up_multivalue_cols(df_f)
    # Update the catalog entry uuids based on the
    # subjects_df uuids.
    try:
        df_f['Entry Year'] = df_f['Date Documented'].dt.year
    except:
        df_f['Entry Year'] = pc_configs.DEFAULT_IMPORT_YEAR
    df_f['subject_label'] = df_f['Open Context Label']
    df_f['subject_uuid'] = df_f['_uuid']
    df_f['subject_uuid_source'] = pc_configs.UUID_SOURCE_KOBOTOOLBOX
    # Add the main trench book records so they can be added to the
    df_f = add_main_trench_books(df_f)
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
    print('-'*50)
    print('Now prepare trenchbook links!')
    print('-'*50)
    _ = prep_links_df(
        dfs,
        subjects_df,
        links_csv_path=links_csv_path,
    )
    return dfs