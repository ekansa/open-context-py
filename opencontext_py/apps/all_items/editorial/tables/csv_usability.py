import io
import uuid as GenUUID

import numpy as np
import pandas as pd

from django.conf import settings


def make_df_without_col_uris(df_orig):
    """Removes URIs from the column names of a dataframe"""
    df = df_orig.copy()
    col_renames = {}
    new_cols = []
    for col in df.columns.tolist():
        if not ' [https://' in col:
            new_cols.append(col)
            continue
        col_ex = col.split(' [https://')
        col_prefix = col_ex[0].strip()
        new_col = col_prefix
        if new_col in new_cols:
            i = 1
            while new_not_unique:
                i += 1
                new_col = f'{col_prefix}_{i}'
                new_not_unique = new_col in new_cols

        col_renames[col] = new_col
        new_cols.append(new_col)
    df.rename(columns=col_renames, inplace=True)
    return df


def cloud_store_full_csv_without_col_uris(full_object_name=None, uuid=None, version=1, df=None):
    if not full_object_name and uuid and version:
        full_object_name = f'{str(uuid)}--v{version}--full.csv'
    full_without_col_uris_obj_name = full_object_name.replace('--full.csv', '--full-cols-no-uris.csv')
