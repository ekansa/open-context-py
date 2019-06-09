from time import sleep
import uuid as GenUUID
import os, sys, shutil
import numpy as np
import pandas as pd
import xlrd
from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest

LABEL_ALTERNATIVE_PARTS = {
    # Keyed by project_uuid
    'DF043419-F23B-41DA-7E4D-EE52AF22F92F': {
        'PC': ['PC', 'PC '], 
        'VDM': ['VDM', 'VdM', 'VdM ']
    }
}


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

def reorder_first_columns(df, first_columns):
    """Reorders a columns in a dataframe so first_columns appear first"""
    return df[move_to_prefix(list(df.columns), first_columns)]

def move_to_prefix(all_list, prefix_list):
    """Reorders elements in a list to move the prefix_list elements first"""
    all_list = list(all_list)  # So we don't mutate all_list
    for p_element in prefix_list:
        all_list.remove(p_element)
    return prefix_list + all_list

def drop_empty_cols(df):
    """Drops columns with empty or null values."""
    for col in df.columns:
        df[col].replace('', np.nan, inplace=True)
    df_output = df.dropna(axis=1,how='all').copy()
    df_output.reset_index(drop=True, inplace=True)
    return df_output

def get_alternate_labels(label, project_uuid, config=None):
    """Returns a list of a label and alternative versions based on project config"""
    if config is None:
        config = LABEL_ALTERNATIVE_PARTS
    if not project_uuid in config:
        return [label]
    label_variations = []
    for label_part, label_alts in config[project_uuid]:
        if not label_part in label:
            label_variations.append(label)
        for label_alt in label_alts:
            label_variations.append(
                label.replace(label_part, label_alt)
            )
    return label_variations

def parse_opencontext_url(s):
    """Returns a tuple of the item_type and uuid for an Open Context url"""
    if ((not s.startswith('https://opencontext.org')) and
       (not s.startswith('http://opencontext.org'))):
        return None, None
    oc_split = s.split('opencontext.org/')
    id_part = oc_split[-1]
    id_parts = id_part.split('/')
    if len(id_parts) < 2:
        # The ID parts is not complete
        return None, None
    item_type = id_parts[0]
    uuid = id_parts[1]
    return item_type, uuid

def parse_opencontext_uuid(s):
    """Returns an Open Context UUID from an OC URL"""
    _, uuid = parse_opencontext_url(s)
    return uuid

def parse_opencontext_type(s):
    """Returns the Open Context item type from an OC URL"""
    item_type, _ = parse_opencontext_url(s)
    return item_type

def lookup_manifest_obj(
    label,
    project_uuid,
    item_type,
    label_alt_configs=None
):
    """Returns a manifest object based on label variations"""
    label_variations = get_alternate_labels(
        label,
        project_uuid,
        config=label_alt_configs
    )
    man_obj = Manifest.objects.filter(
        label__in=label_variations,
        item_type=item_type,
        project_uuid=project_uuid
    ).first()
    return man_obj

def lookup_manifest_uuid(
    label,
    project_uuid,
    item_type,
    label_alt_configs=None
):
    """Returns a manifest object uuid on label variations"""
    man_obj = lookup_manifest_obj(
        label,
        project_uuid,
        item_type,
        label_alt_configs=label_alt_configs
    )
    if man_obj is None:
        return None
    return man_obj.uuid