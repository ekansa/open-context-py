import csv
import uuid as GenUUID
import os, sys, shutil
import codecs
import numpy as np
import pandas as pd

from django.db import models
from django.db.models import Q
from django.conf import settings

# Needed to repoject the site grid
from opencontext_py.libs.reprojection import ReprojectUtilities

from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.subjects.models import Subject

from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.sources.models import ImportSource

from opencontext_py.apps.imports.kobotoolbox.utilities import (
    UUID_SOURCE_KOBOTOOLBOX,
    UUID_SOURCE_OC_KOBO_ETL,
    UUID_SOURCE_OC_LOOKUP,
    list_excel_files,
    read_excel_to_dataframes,
    make_directory_files_df,
    drop_empty_cols,
    reorder_first_columns,
    lookup_manifest_uuid,
)

REPROJECTED_LAT_COL = 'REPROJ_LAT'
REPROJECTED_LON_COL = 'REPROJ_LON'
X_Y_GRID_COLS = [
    ('Find Spot/Grid X', 'Find Spot/Grid Y', ),
]

    

def process_hiearchy_col_values(df, delim='::'):
    """Processes columns with hierarchy values."""
    # NOTE: this assumes only 2 level hiearchies in column names
    hiearchy_preds = {}
    for col in df.columns.tolist():
        if not delim in col:
            continue
        col_parts = col.split(delim)
        pred_label = col_parts[0].strip()
        parent_val = col_parts[-1].strip()
        if not pred_label in hiearchy_preds:
            hiearchy_preds[pred_label] = []
        hiearchy_preds[pred_label].append(col)
        change_indx = (~df[col].isnull())
        df.loc[change_indx, col] = parent_val + delim + df[col]
        df.rename(
            columns={
                col: (pred_label + '/{}'.format(len(hiearchy_preds[pred_label])))
            },
            inplace=True
        )
    return df



def add_global_lat_lon_columns(df, grid_x_col, grid_y_col, default_site_proj='poggio-civitate'):
    """Makes global lat lon coordinates from local coordinates"""
    if (not grid_x_col in df.columns) or (not grid_y_col in df.columns):
        # No local coordinate columns to process for lat, lon columns.
        return df
    df[REPROJECTED_LAT_COL] = np.nan
    df[REPROJECTED_LON_COL] = np.nan
    coord_indx = (
        (~df[grid_x_col].isnull()) & (~df[grid_y_col].isnull())
    )
    print('Creating Lat, Lon columns for {} rows based on {}, {}'.format(
            len(df[coord_indx].index),
            grid_x_col,
            grid_y_col,
        )
    )
    for i, row in df[coord_indx].iterrows():
        reproj = ReprojectUtilities()
        site_proj = default_site_proj
        if 'site' in row and row['site'].startswith('Vescovado'):
            site_proj = 'vescovado-di-murlo'
        if row['label'].startswith('VdM'):
            site_proj = 'vescovado-di-murlo'
        if site_proj in ReprojectUtilities.MURLO_PRE_TRANSFORMS:
            # A Murlo Project local coordinate system
            # we can transform it to global, by first changing the values
            # of the x and y coordinates.
            proj_x_vals, proj_y_vals = reproj.murlo_pre_transform(
                [row[grid_x_col]],
                [row[grid_y_col]],
                site_proj
            )
            site_proj = ReprojectUtilities.MURLO_PRE_TRANSFORMS[site_proj]
        else:
            proj_x_vals = [row[grid_x_col]]
            proj_y_vals = [row[grid_y_col]]
        # Set the input and the output projections.
        reproj.set_in_out_crs(site_proj, 'EPSG:4326')
        out_x, out_y = reproj.reproject_coordinates(
            proj_x_vals,
            proj_y_vals
        )
        # Remember that lat, Lon is the same as y, x !
        update_indx = (df['_uuid'] == row['_uuid'])
        df.loc[update_indx, REPROJECTED_LAT_COL] = out_y[0]
        df.loc[update_indx, REPROJECTED_LON_COL] = out_x[0]
    return df

def create_global_lat_lon_columns(
    df,
    x_y_cols=X_Y_GRID_COLS,
    default_site_proj='poggio-civitate'
):
    """Iterates through configured x, y local grid columns to make global lat, lon columns"""
    for grid_x_col, grid_y_col in x_y_cols:
        if (not grid_x_col in df.columns) or (not grid_y_col in df.columns):
            continue
        df = add_global_lat_lon_columns(
            df,
            grid_x_col,
            grid_y_col,
            default_site_proj=default_site_proj
        )
    return df


    


    