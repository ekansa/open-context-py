
import copy
from re import S
import uuid as GenUUID
import json
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

from opencontext_py.libs.validategeojson import ValidateGeoJson


"""Uses Pandas to prepare Kobotoolbox exports for Open Context import

import importlib

from opencontext_py.apps.etl.kobo import catalog
importlib.reload(catalog)

dfs = catalog.prepare_catalog()


"""

TRENCH_COL_RENAMES = {
    'group_trench_book/Trench Book Date': 'Trench Book Entry Date',
    'group_trench_book/Trench Book Start Page': 'Trench Book Start Page',
    'group_trench_book/Trench Book End Page': 'Trench Book End Page',
}


TRENCH_OBJ_COLS = [
    'trench_id',
    'trench_year',
    'Trench Book Entry Date',
    'Trench Book Start Page',
    'Trench Book End Page'
]


DF_REL_ALL_COLS = (
    pc_configs.FIRST_LINK_REL_COLS
    + [c for _,c in pc_configs.RELS_RENAME_COLS.items() if c not in pc_configs.FIRST_LINK_REL_COLS]
    + TRENCH_OBJ_COLS
)


def make_locus_grid_df(dfs, subjects_df):
    df_grid, _ = utilities.get_df_by_sheet_name_part(
        dfs,
        sheet_name_part='group_elevations'
    )
    if df_grid is None:
        return None
    df_grid = utilities.fix_df_col_underscores(df_grid)
    cols = [c for c,_ in pc_configs.LOCUS_GRID_COLS if c in df_grid.columns]
    df_grid = df_grid[cols].copy()
    renames = {c:r for c, r in pc_configs.LOCUS_GRID_COLS if c in df_grid.columns}
    df_grid.rename(columns=renames, inplace=True)
    df_grid = utilities.add_final_subjects_uuid_label_cols(
        df=df_grid,
        subjects_df=subjects_df,
        form_type='locus',
        final_label_col='subject_label',
        final_uuid_col='subject_uuid',
        final_uuid_source_col='subject_uuid_source',
        orig_uuid_col='_uuid',
    )
    df_grid = utilities.df_fill_in_by_shared_id_cols(
        df=df_grid,
        col_to_fill='subject_label',
        id_cols=['subject_uuid'],
    )
    return df_grid


def make_locus_geo_df(df_grid):
    """Makes a dataframe of geospatial information from the locus df_grid"""
    missing_cols = [
        ('Elevation_Type', 'Elevation Type',),
        ('Grid_X', 'Grid X',),
        ('Grid_Y', 'Grid Y',),
    ]
    print(df_grid.columns.tolist())
    for f, r in missing_cols:
        if not r in df_grid.columns and f in df_grid.columns:
            df_grid[r] = df_grid[f]
    recs = []
    act_indx = ~df_grid['subject_uuid'].isnull()
    for uuid in df_grid[act_indx]['subject_uuid'].unique().tolist():
        uuid_indx = (df_grid['subject_uuid'] == uuid)
        for f_type in df_grid[uuid_indx]['Elevation Type'].unique().tolist():
            f_id_indx = uuid_indx & (df_grid['Elevation Type'] == f_type)
            coords = []
            for _, row in df_grid[f_id_indx].iterrows():
                out_x, out_y = grid_geo.grid_x_y_to_lat_lon(
                    grid_x=row['Grid X'],
                    grid_y=row['Grid Y'],
                )
                geo_tup = (out_x[0], out_y[0],)
                coords.append(geo_tup)
            sorted(coords, key=lambda x:(x[1],x[0]))
            coords.append(coords[0])
            geometry = {
                'type': 'Polygon',
                'coordinates':  [
                    coords
                ],
            }
            v_geojson = ValidateGeoJson()
            geometry['coordinates'] = v_geojson.fix_geometry_rings_dir(
                geometry['type'],
                geometry['coordinates']
            )
            geojson = json.dumps(geometry)
            rec = {
                'subject_label': row['subject_label'],
                'subject_uuid': row['subject_uuid'],
                'subject_uuid_source': row['subject_uuid_source'],
                pc_configs.EVENT_GEOJSON_COL: f_type,
                pc_configs.REPROJECTED_GEOJSON_COL: geojson,
            }
            recs.append(rec)
    df_geo = pd.DataFrame(data=recs)
    return df_geo


def add_trench_cols_to_df_link(df_link, dfs):
    df, _ = utilities.get_df_by_sheet_name_part(
        dfs,
        sheet_name_part='Locus'
    )
    if df is None:
        return df_link
    missing_cols = [
        ('Trench_ID', 'Trench ID',),
        ('Season', 'Field Season',),
    ]
    for f, r in missing_cols:
        if not r in df.columns and f in df.columns:
            df[r] = df[f]
    if not 'trench_id' in df_link:
        df_link['trench_id'] = ''
    if not 'trench_year' in df_link:
        df_link['trench_year'] = np.nan
    for _, row in df.iterrows():
        indx = df_link['_submission__uuid'] == row['_uuid']
        df_link.loc[indx, 'trench_id'] = row['Trench ID']
        df_link.loc[indx, 'trench_year'] = row['Field Season']
    return df_link


def make_locus_tb_links_df(dfs, subjects_df):
    """Makes dataframe for a catalog links to trench book entries"""
    df_link, _ = utilities.get_df_by_sheet_name_part(
        dfs,
        sheet_name_part='group_trench_book'
    )
    if df_link is None:
        return None
    # get the current trench books.
    df_tb = pd.read_json(pc_configs.KOBO_TB_JSON_PATH)
    df_link.rename(columns=TRENCH_COL_RENAMES, inplace=True)
    df_link = utilities.add_final_subjects_uuid_label_cols(
        df=df_link,
        subjects_df=subjects_df,
        form_type='locus',
        final_label_col='subject_label',
        final_uuid_col='subject_uuid',
        final_uuid_source_col='subject_uuid_source',
        orig_uuid_col='_submission__uuid',
    )
    # Add the trench_id column to the df_link.
    df_link = add_trench_cols_to_df_link(df_link, dfs)
    df_link[pc_configs.LINK_RELATION_TYPE_COL] = 'Has Related Trench Book Entry'
    df_link['object_label'] = np.nan
    df_link['object_uuid'] = np.nan
    df_link['object_uuid_source'] = np.nan
    rename_cols = {
        'Date_Trench_Book': 'Trench Book Entry Date',
        'TB_Start_Page': 'Trench Book Start Page',
        'TB_End_Page': 'Trench Book End Page',
    }
    r_c = {c:r for c, r in rename_cols.items() if c in df_link.columns.tolist()}
    if r_c:
        df_link.rename(columns=r_c, inplace=True)
    for i, row in df_link.iterrows():
        object_label = None
        object_uuid = None
        object_uuid_source = None
        # Try looking in the database for a match
        obj = db_lookups.db_lookup_trenchbook(
            row['trench_id'],
            row['trench_year'],
            row['Trench Book Entry Date'],
            row['Trench Book Start Page'],
            row['Trench Book End Page']
        )
        if obj:
            object_label = obj.label
            object_uuid = str(obj.uuid)
            object_uuid_source = pc_configs.UUID_SOURCE_OC_LOOKUP
        if not obj:
            object_label, object_uuid, object_uuid_source = utilities.get_trenchbook_item_from_trench_books_json(
                trench_id=row['trench_id'],
                year=row['trench_year'],
                entry_date=row['Trench Book Entry Date'],
                start_page=row['Trench Book Start Page'],
                end_page=row['Trench Book End Page'],
                df_tb=df_tb,
            )
        if not object_uuid:
            continue
        up_indx = (
            (df_link['trench_id'] == row['trench_id'])
            & (df_link['trench_year'] == row['trench_year'])
            # & (tb_df['Date Documented'] == row['Trench Book Entry Date'])
            & (df_link['Trench Book Start Page'] >= row['Trench Book Start Page'])
            & (df_link['Trench Book End Page'] <= row['Trench Book End Page'])
        )
        if df_link[up_indx].empty:
            print(
                f"Cannot update associate locus trenchbook: {row['trench_id']} "
                f"year: {row['trench_year']} "
                f"entry: {row['Trench Book Entry Date']}"
                f"pages: {row['Trench Book Start Page']} - {row['Trench Book End Page']}"
            )
        df_link.loc[up_indx, 'object_label'] = object_label
        df_link.loc[up_indx, 'object_uuid'] = object_uuid
        df_link.loc[up_indx, 'object_uuid_source'] = object_uuid_source

    df_link = df_link[
        (
           pc_configs.FIRST_LINK_REL_COLS
            + TRENCH_OBJ_COLS
        )
    ]
    return df_link


def make_strat_other_link_df(df):
    """Makes a single dataframe for locus stratigraphy relations"""
    cols_renames = {
        'Stratigraphy: Relation with Prior Season Locus/Relation Type': 'kobo_rel',
        'Stratigraphy: Relation with Prior Season Locus/URL to Locus': 'kobo_url',
    }
    cols = [c for c,_ in cols_renames.items()]
    if not set(cols).issubset(set(df.columns.tolist())):
        return None
    df.rename(columns=cols_renames, inplace=True)
    df[pc_configs.LINK_RELATION_TYPE_COL] = np.nan
    df['object_label'] = np.nan
    df['object_uuid'] = np.nan
    df['object_orig_uuid'] = np.nan
    df['object_uuid_source'] = np.nan
    for _, row in df.iterrows():
        obj = db_lookups.db_lookup_manifest_by_uri(
            row['kobo_url'],
            item_class_slugs=['oc-gen-cat-locus'],
        )
        if not obj:
            continue
        object_uuid = str(obj.uuid)
        object_source = pc_configs.UUID_SOURCE_OC_LOOKUP
        up_indx = (
            (df['kobo_url'] == row['kobo_url'])
            & (df['kobo_rel'] == row['kobo_rel'])
        )
        if df[up_indx].empty:
            print(
                f"Cannot update associate locus : {row['kobo_url']} "
                f"with obj: {obj.label} ({object_uuid})"
            )
            continue
        df.loc[up_indx, pc_configs.LINK_RELATION_TYPE_COL] = row['kobo_rel']
        df.loc[up_indx, 'object_label'] = obj.label
        df.loc[up_indx, 'object_uuid'] = object_uuid
        df.loc[up_indx, 'object_uuid_source'] = object_source

    return df


def make_strat_link_df(df, dfs, subjects_df):
    """Makes a single dataframe for locus stratigraphy relations"""
    df = utilities.add_final_subjects_uuid_label_cols(
        df=df,
        subjects_df=subjects_df,
        form_type='locus',
        final_label_col='subject_label',
        final_uuid_col='subject_uuid',
        final_uuid_source_col='subject_uuid_source',
        orig_uuid_col='_submission__uuid',
    )
    # Add the trench_id column to the df_link.
    df = add_trench_cols_to_df_link(df, dfs)
    do_other_rel = False
    act_col = None
    for c in df.columns.tolist():
        if c.startswith('Stratigraphy'):
            act_col = c
        if 'Relation with Prior Season Locus' in c:
            do_other_rel = True
    if do_other_rel:
        return make_strat_other_link_df(df)
    if not act_col:
        return None
    df[pc_configs.LINK_RELATION_TYPE_COL] = act_col
    df['object_label'] = np.nan
    df['object_uuid'] = np.nan
    df['object_orig_uuid'] = np.nan
    df['object_uuid_source'] = np.nan
    df_f, _ = utilities.get_df_by_sheet_name_part(
        dfs,
        sheet_name_part='Locus'
    )
    act_indx = ~df[act_col].isnull()
    for _, row in df[act_indx].iterrows():
        rel_locus_index = (
            (df_f['Trench ID'] == row['trench_id'])
            & (df_f['Locus ID'] == row[act_col])
        )
        if df_f[rel_locus_index].empty:
            continue
        up_index = (
            (df['trench_id'] == row['trench_id'])
            & (df[act_col] == row[act_col])
        )
        df.loc[up_index, 'object_orig_uuid'] = df_f[rel_locus_index]['_uuid'].iloc[0]
    # Now update the uuids of the related loci
    df = utilities.add_final_subjects_uuid_label_cols(
        df=df,
        subjects_df=subjects_df,
        form_type='locus',
        final_label_col='object_label',
        final_uuid_col='object_uuid',
        final_uuid_source_col='object_uuid_source',
        orig_uuid_col='object_orig_uuid',
    )
    return df


def make_strat_links_dfs(
    dfs,
    subjects_df,
    df_list,
):
    """Makes dataframes for locus stratigraphy relations"""
    for sheet_key, df in dfs.items():
        if not sheet_key.startswith('group_strat_'):
            continue
        df = make_strat_link_df(df, dfs, subjects_df)
        if df is None:
            continue
        df_list.append(df)
    return df_list


def make_trench_super_link_df(dfs, subjects_df):
    """Makes a dataframe for locus trench supervisors"""
    df, _ = utilities.get_df_by_sheet_name_part(
        dfs,
        sheet_name_part='Locus'
    )
    if df is None:
        return None
    # Update the locus entry uuids based on the
    # subjects_df uuids.
    df = utilities.add_final_subjects_uuid_label_cols(
        df=df,
        subjects_df=subjects_df,
        form_type='locus',
        final_label_col='subject_label',
        final_uuid_col='subject_uuid',
        final_uuid_source_col='subject_uuid_source',
        orig_uuid_col='_uuid',
    )
    return utilities.make_trench_supervisor_link_df(df)


def prep_links_df(
    dfs,
    subjects_df,
    links_csv_path=pc_configs.LOCUS_LINKS_CSV_PATH
):
    """Makes a dataframe for locus object linking relations"""
    df_list = []
    df_tb_link = make_locus_tb_links_df(dfs, subjects_df)
    if df_tb_link is not None:
        df_list.append(df_tb_link)
    # Make a dataframe of trench supervisors
    df_super = make_trench_super_link_df(dfs, subjects_df)
    if df_super is not None:
        df_list.append(df_super)
    df_list = make_strat_links_dfs(dfs, subjects_df, df_list)
    if len(df_list) == 0:
        return None
    df_all_links = pd.concat(df_list)
    cols = [c for c in DF_REL_ALL_COLS if c in df_all_links.columns]
    df_all_links = df_all_links[cols].copy()
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
    attrib_csv_path=pc_configs.LOCUS_ATTRIB_CSV_PATH,
):
    """Prepares the locus attribute data"""
    df_f, sheet_name = utilities.get_df_by_sheet_name_part(
        dfs,
        sheet_name_part='Locus'
    )
    if df_f is None:
        return dfs
    df_f = utilities.drop_empty_cols(df_f)
    df_f = utilities.update_multivalue_columns(df_f)
    df_f = utilities.clean_up_multivalue_cols(df_f)
    # Update the locus entry uuids based on the
    # subjects_df uuids.
    df_f = utilities.add_final_subjects_uuid_label_cols(
        df=df_f,
        subjects_df=subjects_df,
        form_type='locus',
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
    attrib_csv_path=pc_configs.LOCUS_ATTRIB_CSV_PATH,
    links_csv_path=pc_configs.LOCUS_LINKS_CSV_PATH,
    geo_csv_path=pc_configs.LOCUS_GEO_CSV_PATH,
    subjects_path=pc_configs.SUBJECTS_CSV_PATH,
):
    """Prepares locus dataframes."""
    xlsx_files = utilities.list_excel_files(excel_dirpath)
    if not xlsx_files:
        return None
    subjects_df = pd.read_csv(subjects_path)
    dfs = None
    for excel_filepath in xlsx_files:
        if not 'Locus' in excel_filepath:
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
    df_grid = make_locus_grid_df(dfs, subjects_df)
    df_geo = make_locus_geo_df(df_grid)
    if geo_csv_path:
        df_geo.to_csv(geo_csv_path, index=False)
    return dfs