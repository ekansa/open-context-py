from time import sleep
import uuid as GenUUID
import os, sys, shutil
import numpy as np
import pandas as pd
import xlrd
from django.conf import settings

def make_directory_files_df(attachments_path):
    """Makes a dataframe listing all the files a Kobo Attachments directory."""
    file_data = {
        'path':[],
        'path-uuid':[],
        'filename': [],
    }
    for dirpath, dirnames, filenames in os.walk(attachments_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            uuid_dir = os.path.split(os.path.abspath(dirpath))[-1]
            file_data['path'].append(file_path)
            file_data['path-uuid'].append(uuid_dir)
            file_data['filename'].append(filename)
    df = pd.DataFrame(data=file_data)
    return df

def list_excel_files(excel_dirpath):
    """Makes a list of Excel files in a directory path."""
    xlsx_files = []
    for item in os.listdir(excel_dirpath):
        item_path = os.path.join(excel_dirpath, item)
        if not os.path.isfile(item_path):
            continue
        if not (item.endswith('.xlsx') or
           item.endswith('.xls')):
            continue
        xlsx_files.append(item_path)
    return xlsx_files  

def read_excel_to_dataframes(excel_filepath):
    """Reads an Excel workbook into a dictionary of dataframes keyed by sheet names."""
    dfs = {}
    xls = xlrd.open_workbook(excel_filepath)
    for sheet_name in xls.sheet_names():
        print('Reading sheet ' + sheet_name)
        # This probably needs an upgraded pandas
        # dfs[sheet_name] = pd.read_excel(xls, sheet_name=sheet_name, engine='xlrd')
        dfs[sheet_name] = pd.read_excel(xls, sheet_name, engine='xlrd')
    return dfs

def drop_empty_cols(df):
    """Drops columns with empty or null values."""
    for col in df.columns:
        df[col].replace('', np.nan, inplace=True)
    df_output = df.dropna(axis=1,how='all').copy()
    df_output.reset_index(drop=True, inplace=True)
    return df_output          