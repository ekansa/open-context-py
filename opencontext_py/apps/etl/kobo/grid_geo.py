import numpy as np
import pandas as pd


# Needed to re-project the site grid
from opencontext_py.libs.reprojection import ReprojectUtilities

from opencontext_py.apps.etl.kobo import pc_configs



def grid_x_y_to_lat_lon(grid_x, grid_y, site_proj='poggio-civitate'):
    reproj = ReprojectUtilities()
    if site_proj in ReprojectUtilities.MURLO_PRE_TRANSFORMS:
        proj_x_vals, proj_y_vals = reproj.murlo_pre_transform(
            [grid_x],
            [grid_y],
            site_proj
        )
        site_proj = ReprojectUtilities.MURLO_PRE_TRANSFORMS[site_proj]
    else:
        proj_x_vals = [grid_x]
        proj_y_vals = [grid_y]
    reproj.set_in_out_crs(site_proj, 'EPSG:4326')
    out_x, out_y = reproj.reproject_coordinates(
        proj_x_vals,
        proj_y_vals
    )
    return out_x, out_y


def add_global_lat_lon_columns(df, grid_x_col, grid_y_col, default_site_proj='poggio-civitate'):
    """Makes global lat lon coordinates from local coordinates"""
    if (not grid_x_col in df.columns) or (not grid_y_col in df.columns):
        # No local coordinate columns to process for lat, lon columns.
        return df
    
    if not pc_configs.REPROJECTED_LAT_COL in df.columns:
        df[pc_configs.REPROJECTED_LAT_COL] = np.nan
    if not pc_configs.REPROJECTED_LON_COL in df.columns:    
        df[pc_configs.REPROJECTED_LON_COL] = np.nan
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
        site_proj = default_site_proj
        if row.get('site') and row['site'].startswith('Vescovado'):
            site_proj = 'vescovado-di-murlo'
        if row.get('subject_label') and row['subject_label'].startswith('VdM'):
            site_proj = 'vescovado-di-murlo'
        out_x, out_y = grid_x_y_to_lat_lon(
            grid_x=row[grid_x_col], 
            grid_y=row[grid_y_col], 
            site_proj=site_proj
        )
        # Remember that lat, Lon is the same as y, x !
        update_indx = (df['_uuid'] == row['_uuid'])
        df.loc[update_indx, pc_configs.REPROJECTED_LAT_COL] = out_y[0]
        df.loc[update_indx, pc_configs.REPROJECTED_LON_COL] = out_x[0]
    return df


def create_global_lat_lon_columns(
    df,
    default_site_proj='poggio-civitate'
):
    """Iterates through configured x, y local grid columns to make global lat, lon columns"""
    for grid_x_col, grid_y_col in pc_configs.X_Y_GRID_COLS:
        if (not grid_x_col in df.columns) or (not grid_y_col in df.columns):
            continue
        df = add_global_lat_lon_columns(
            df,
            grid_x_col,
            grid_y_col,
            default_site_proj=default_site_proj
        )
    return df


def q_low(s):
    return s.quantile(0.05)


def q_high(s):
    return s.quantile(0.95)


def create_grid_validation_columns(
    df,
    groupby_cols=['Trench ID'],
    flag_col='GRID_PROBLEM_FLAG'
):
    """Iterates through configured x, y local grid columns to make global lat, lon columns"""
    for grid_x_col, grid_y_col in pc_configs.X_Y_GRID_COLS:
        if not set([grid_x_col, grid_y_col] + groupby_cols).issubset(set(df.columns.tolist())):
            # We're missing the columns needed for this check.
            continue
        df_grp = df.groupby(groupby_cols, as_index=False).agg(
            ({grid_x_col: ['min', 'max', 'mean', 'size', q_low, q_high], grid_y_col: ['min', 'max', 'mean', 'size', q_low, q_high]})
        )
        
        df = pd.merge(
            df,
            df_grp,
            how='left',
            on=groupby_cols
        )
        df[flag_col] = np.nan
        # flags based on extreme x and 2y values.
        bad_indx = (
            (
                (df[(grid_x_col, 'size')] > 4)
                & (df[(grid_y_col, 'size')] > 4)
            )
               & 
            (
                (df[grid_x_col] <= df[(grid_x_col, 'q_low')])
                | (df[grid_x_col] >= df[(grid_x_col, 'q_high')])
                | (df[grid_y_col] <= df[(grid_y_col, 'q_low')])
                | (df[grid_y_col] >= df[(grid_y_col, 'q_high')])
            )
        )
        df.loc[bad_indx, flag_col] = 'Check Grid X-Y'
    return df
