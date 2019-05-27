
from time import sleep
import uuid as GenUUID
import os, sys, shutil
import pandas as pd
import xlrd

from django.conf import settings

"""Uses Pandas to prepare Kobotoolbox exports for Open Context import


from django.conf import settings
from opencontext_py.apps.imports.kobotoolbox.preprocess import (
    read_excel_to_dataframes,
    look_up_parent,
    lookup_related_locus,
)

excel_filepath = settings.STATIC_IMPORTS_ROOT +  'pc-2018/Locus Summary Entry - latest version - labels - 2019-05-27-22-32-06.xlsx'
dfs = read_excel_to_dataframes(excel_filepath)
df_rel = lookup_related_locus(12, 'Locus Summary Entry', '5c9d521a-7b97-4dc6-9132-0d07070a8b51', dfs)

"""



def read_excel_to_dataframes(excel_filepath):
    """Reads an Excel workbook into a dictionary of dataframes keyed by sheet names."""
    dfs = {}
    xls = xlrd.open_workbook(excel_filepath)
    for sheet_name in xls.sheet_names():
        df = pd.read_excel(xls, sheet_name=sheet_name, engine='xlrd')
        dfs[sheet_name] = df
    return dfs

def look_up_parent(parent_sheet, parent_uuid, dfs):
    """Looks up and returns a 1 record dataframe of the record for the parent item."""
    df_parent = dfs[parent_sheet][dfs[parent_sheet]['_uuid'] == parent_uuid].copy().reset_index(drop=True)
    return df_parent

def lookup_related_locus(rel_locus_id, parent_sheet, parent_locus_uuid, dfs):
    """Looks up a related locus on the parent sheet, and returns a dictionary of relevant data for the locus"""
    df_parent = look_up_parent(parent_sheet, parent_locus_uuid, dfs)
    if df_parent.empty:
        raise RuntimeError('Parent locus uuid {} not found.'.format(parent_locus_uuid))
    trench_id = df_parent['Trench ID'].iloc[0]
    df = dfs[parent_sheet]
    df_rel = df[(df['Trench ID'] == trench_id) & (df['Locus ID'] == rel_locus_id)].copy().reset_index(drop=True)
    return df_rel



    