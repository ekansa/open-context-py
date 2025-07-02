
import numpy as np
import pandas as pd
from scipy import stats

from sklearn.cluster import KMeans, AffinityPropagation, SpectralClustering
from shapely.geometry import mapping, shape


from django.db.models import Q


from opencontext_py.libs.globalmaptiles import GlobalMercator

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
    AllAssertion,
)

from opencontext_py.apps.all_items.geospace import aggregate as geo_agg


def flag_outlier_points_in_df(df_geo, z_threshold=2.5):
    """Finds latitude, longitude outliers within a df_geo dataframe"""
    df_z = df_geo[['longitude', 'latitude']].apply(stats.zscore)
    for c_col in ['longitude', 'latitude']:
        flag_col = f'flag__{c_col}'
        df_geo[flag_col] = False
        zscore_col = f'zscore__{c_col}'
        df_z.rename(columns={c_col: zscore_col}, inplace=True)
    df_eval = pd.merge(df_geo, df_z, left_index=True, right_index=True)
    for c_col in ['longitude', 'latitude']:
        flag_col = f'flag__{c_col}'
        zscore_col = f'zscore__{c_col}'
        extreme_index = (df_eval[zscore_col] > z_threshold) | (df_eval[zscore_col] < (z_threshold * -1))
        print(f'Found {len(df_eval[extreme_index])} with extreme {c_col}')
        df_eval.loc[extreme_index, flag_col] = True
    return df_eval


def remove_outlier_points_in_df_geo(df_geo, z_threshold=2.5):
    """Removes outlier points in a df_geo dataframe"""
    df_eval = flag_outlier_points_in_df(
        df_geo=df_geo, 
        z_threshold=z_threshold
    )
    flag_index = (
        (df_eval['flag__longitude'] == True)
        | (df_eval['flag__latitude'] == True)
    )
    # Keep only those rows that are not flagged
    df = df_eval[~flag_index].copy()
    drop_cols = []
    for c_col in ['longitude', 'latitude']:
        drop_cols.append(f'flag__{c_col}')
        drop_cols.append(f'zscore__{c_col}')
    df.drop(columns=drop_cols, inplace=True)
    return df