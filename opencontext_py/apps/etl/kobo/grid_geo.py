import numpy as np
import pandas as pd


# Needed to re-project the site grid
from opencontext_py.libs.reprojection import ReprojectUtilities

from opencontext_py.apps.etl.kobo import pc_configs


def add_global_lat_lon_columns(df, grid_x_col, grid_y_col, default_site_proj='poggio-civitate'):
    """Makes global lat lon coordinates from local coordinates"""
    if (not grid_x_col in df.columns) or (not grid_y_col in df.columns):
        # No local coordinate columns to process for lat, lon columns.
        return df
    df[pc_configs.REPROJECTED_LAT_COL] = np.nan
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
        reproj = ReprojectUtilities()
        site_proj = default_site_proj
        if row.get('site') and row['site'].startswith('Vescovado'):
            site_proj = 'vescovado-di-murlo'
        if row.get('label') and row['label'].startswith('VdM'):
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
        df.loc[update_indx, pc_configs.REPROJECTED_LAT_COL] = out_y[0]
        df.loc[update_indx, pc_configs.REPROJECTED_LON_COL] = out_x[0]
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


def q_low(s):
    return s.quantile(0.05)


def q_high(s):
    return s.quantile(0.95)


def create_grid_validation_columns(
    df,
    x_y_cols=X_Y_GRID_COLS,
    groupby_cols=['Trench ID'],
    flag_col='GRID_PROBLEM_FLAG'
):
    """Iterates through configured x, y local grid columns to make global lat, lon columns"""
    for grid_x_col, grid_y_col in x_y_cols:
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
