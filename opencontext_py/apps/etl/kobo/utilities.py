import os
import numpy as np
import pandas as pd
from openpyxl import load_workbook
import openpyxl

from django.db.models import Q
from opencontext_py.apps.all_items.models import AllManifest

from opencontext_py.apps.etl.kobo import pc_configs


MULTI_VALUE_COL_PREFIXES = [
    'Preliminary Phasing/',
    'Trench Supervisor/',
    'Decorative Techniques and Motifs/Decorative Technique/',
    'Decorative Techniques and Motifs/Motif/',
    'Fabric Category/',
    'Vessel Part Present/',
    'Modification/',
    'Type of Composition Subject/',
]

UUID_SOURCE_KOBOTOOLBOX = 'kobotoolbox' # UUID minted by kobotoolbox
UUID_SOURCE_OC_KOBO_ETL = 'oc-kobo-etl' # UUID minted by this ETL process
UUID_SOURCE_OC_LOOKUP = 'open-context' # UUID existing in Open Context

LINK_RELATION_TYPE_COL = 'relation_type'

def make_directory_files_df(attachments_path):
    """Makes a dataframe listing all the files a Kobo Attachments directory."""
    file_data = {
        'path':[],
        'path_uuid':[],
        'filename': [],
    }
    for dirpath, _, filenames in os.walk(attachments_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            uuid_dir = os.path.split(os.path.abspath(dirpath))[-1]
            file_data['path'].append(file_path)
            file_data['path_uuid'].append(uuid_dir)
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
    wb = load_workbook(excel_filepath)
    for sheet_name in wb.sheetnames:
        print('Reading sheet ' + sheet_name)
        # This probably needs an upgraded pandas
        # dfs[sheet_name] = pd.read_excel(xls, sheet_name=sheet_name, engine='xlrd')
        dfs[sheet_name] = pd.read_excel(wb, sheet_name, engine='openpyxl')
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

def update_multivalue_col_vals(df, multi_col_prefix):
    """Updates the values of multi-value nominal columns"""
    multi_cols = [c for c in df.columns.tolist() if c.startswith(multi_col_prefix)]
    drop_cols = []
    for col in multi_cols:
        df[col] = df[col].astype(str)
        val_index = ((df[col] == '1')|(df[col] == '1.0')|(df[col] == 'True'))
        if df[val_index].empty:
            drop_cols.append(col)
            continue
        # Set rows to the column's value if "True" (1).
        df.loc[val_index, col] = col.split(
            multi_col_prefix
        )[-1].strip()
        # Set rows to blank if the column is not True (1).
        df.loc[~val_index, col] = np.nan
    # Drop the columns that where not actually used.
    df.drop(drop_cols, axis=1, inplace=True, errors='ignore')
    rename_cols = {}
    i = 0
    for col in multi_cols:
        if col in drop_cols:
            continue
        i += 1
        rename_cols[col] = multi_col_prefix + str(i)
    # Rename the columns that were used.
    df.rename(columns=rename_cols, inplace=True)
    return drop_empty_cols(df)

def update_multivalue_columns(df, multival_col_prefixes=None):
    """Updates multivalue columns, removing the ones not in use"""
    if multival_col_prefixes is None:
        multival_col_prefixes = MULTI_VALUE_COL_PREFIXES
    for multi_col_prefix in multival_col_prefixes:
        df = update_multivalue_col_vals(df, multi_col_prefix)
    return df

def clean_up_multivalue_cols(df, skip_cols=[], delim='::'):
    """Cleans up multivalue columns where one column has values that concatenate values from other columns"""
    poss_multi_value_cols = {}
    cols = df.columns.tolist()
    sub_cols = []
    for col in cols:
        if col in skip_cols:
            continue
        for other_col in cols:
            if other_col == col:
                # Same column, skip it.
                continue
            if not other_col.startswith(col) or not '/' in other_col:
                # This other column is not prefixed by col
                continue
            if other_col in sub_cols:
                # We want to avoid a situation where something/1 is considered to be a
                # parent of something/10
                continue
            other_col_vals = df[df[other_col].notnull()][other_col].unique().tolist()
            if len(other_col_vals) > 1:
                # This is not a column with a single value, so skip.
                continue
            sub_cols.append(other_col)
            if col not in poss_multi_value_cols:
                poss_multi_value_cols[col] = []
            # Add a tuple of the other column name, and it's unique value.
            poss_multi_value_cols[col].append((other_col, other_col_vals[0],))
    for col, rel_cols_vals in poss_multi_value_cols.items():
        for act_rel_col, act_val  in rel_cols_vals:
            # Update the col by filtering for non null values for col,
            # and for where the act_rel_col has it's act_val.
            print('Remove the column {} value "{}" in the column {}'.format(act_rel_col, act_val, col))
            rep_indx = (df[col].notnull() & (df[act_rel_col] == act_val))
            # Remove the string we don't want, from col, which concatenates multiple
            # values.
            df.loc[rep_indx, col] = df[col].str.replace(act_val, '')
            if delim in act_val:
                # Remove the first part of a hiearchy delimited value from a likely parent column.
                df.loc[rep_indx, col] = df[col].str.replace(
                    act_val.split(delim)[0],
                    ''
                )
            # Now do final cleanup
            df.loc[rep_indx, col] = df[col].str.strip()
    # Now do a file cleanup, removing anything that's no longer present.
    df = drop_empty_cols(df)
    return df
            

def get_alternate_labels(
    label, 
    project_uuid=pc_configs.PROJECT_UUID, 
    config=None
):
    """Returns a list of a label and alternative versions based on project config"""
    label = str(label)
    if config is None:
        config = pc_configs.LABEL_ALTERNATIVE_PARTS
    if not project_uuid in config:
        return [label]
    label_variations = []
    for label_part, label_alts in config[project_uuid].items():
        label_part = str(label_part)
        if not label_part in label:
            label_variations.append(label)
        for label_alt in label_alts:
            label_variations.append(
                label.replace(label_part, label_alt)
            )
    return label_variations

def parse_opencontext_url(s):
    """Returns a tuple of the item_type and uuid for an Open Context url"""
    s = AllManifest().clean_uri(s)
    if not isinstance(s, str):
        return None, None
    if not s.startswith('opencontext.org/'):
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


def get_trench_unit_mapping_dict(trench_id):
    """Gets mapping information for a trench_id based on prefix string"""
    for prefix, map_dict in pc_configs.TRENCH_CONTEXT_MAPPINGS.items():
        if not trench_id.startswith(prefix):
            continue
        return map_dict
    return None


def normalize_catalog_label(raw_label):
    """Makes a catalog label fit Poggio Civitate conventions"""
    prefix = ''
    num_part = ''
    for c in str(raw_label):
        if c.isnumeric():
            num_part += c
        else:
            prefix += c
    return f'{prefix} {num_part}'