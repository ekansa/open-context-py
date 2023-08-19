from copy import copy
import json
import os
import numpy as np
import pandas as pd
from unidecode import unidecode

from django.template.defaultfilters import slugify
from opencontext_py.apps.etl.kobo import pc_configs
from opencontext_py.apps.etl.kobo import utilities



def make_filename_friendly_string(act_str):
    act_str = act_str.lower()
    act_str = slugify(unidecode(act_str))
    act_str = act_str.replace(' ', '-').replace('_', '-').replace(',', '-')
    act_str = act_str.replace('----', '-').replace('---', '-').replace('--', '-')
    return act_str


def convert_multi_value_dict_to_row_dict(output_multi_row_dict, input_val_dict):
    """Converts a multi value dict value to a row dict"""
    for sub_key, sub_val in input_val_dict.items():
        sub_key_field = sub_key
        if '/' in sub_key:
            sub_key_ex = sub_key.split('/')
            key_group_i = 0
            for key_group in sub_key_ex:
                key_group_i += 1
                output_multi_row_dict[f'attribute_group_{key_group_i}'] = key_group
            sub_key_field = sub_key_ex[-1]
        if sub_key_field in pc_configs.SKIP_FIELDS:
            # we throw this key out. not used noise
            continue
        output_multi_row_dict[sub_key_field] = sub_val
    return output_multi_row_dict

def create_initial_row_dict(kobo_form, kobo_form_year, input_result_dict):
    """Creates an initial row dict from an input result dict"""
    row_dict = {
        'kobo_form': kobo_form,
        'kobo_form_year': kobo_form_year,
    }
    # Add naming keys to the beginning, just for consistency
    # multi-record sub-item.
    for naming_key in pc_configs.NAMING_FIELDS:
        if not input_result_dict.get(naming_key):
            continue
        row_dict[naming_key] = input_result_dict.get(naming_key)
    return row_dict


def extract_main_and_multi_rows_from_json_data(kobo_form, kobo_form_year, json_data):
    if not json_data:
        return None
    results = json_data.get('results')
    if not results:
        return None
    all_list_keys = []
    sub_item_rows = {}
    for result in results:
        uuid = result.get('_uuid')
        for key, val in result.items():
            if key in pc_configs.SKIP_FIELDS:
                # we throw this key out. not used noise
                continue
            if isinstance(val, list):
                if key == '_attachments' and len(val) > 0:
                    # we won't treat this as a "normal" multivalue key
                    continue
                # this is a multi-value value, meaning
                # the key has multiple values, so
                # record that this key is for multiple values
                all_list_keys.append(key)
    main_rows = []
    multi_rows = []
    attach_rows = []
    for result in results:
        uuid = result.get('_uuid')
        main_row = create_initial_row_dict(
            kobo_form=kobo_form,
            kobo_form_year=kobo_form_year,
            input_result_dict=result,
        )
        for key, val in result.items():
            if key in pc_configs.SKIP_FIELDS:
                # we throw this key out. not used noise
                continue
            if key in pc_configs.NAMING_FIELDS:
                # we already added this.
                continue
            if key in all_list_keys:
                # this field is at least sometimes used
                # multiple times, so skip for now.
                continue
            main_row[key] = val
        main_rows.append(main_row)
        # OK! Now add attachments if present
        for act_attach_dict in result.get('_attachments', []):
            attach_row = create_initial_row_dict(
                kobo_form=kobo_form,
                kobo_form_year=kobo_form_year,
                input_result_dict=result,
            )
            attach_row = convert_multi_value_dict_to_row_dict(
                output_multi_row_dict=attach_row,
                input_val_dict=act_attach_dict,
            )
            attach_rows.append(attach_row)
        # The sub_item_rows are multiple rows associated with the current result (dict)
        # we will add a sub_item_row dict for each of the multi-value attributes associated
        # with the current result_dict.
        max_len = 0
        for list_key in all_list_keys:
            val_list = result.get(list_key, [])
            if len(val_list) > max_len:
                max_len = len(val_list)
        sub_item_rows[uuid] = [
            create_initial_row_dict(
                kobo_form=kobo_form,
                kobo_form_year=kobo_form_year,
                input_result_dict=result,
            )
            for _ in range(0, max_len)
        ]
        if not sub_item_rows:
            # we don't have any sub item rows
            continue
        for list_key in all_list_keys:
            val_list = result.get(list_key, [])
            if not val_list:
                continue
            for sub_i, val_dict in enumerate(val_list):
                print(f'get sub_item_row {sub_i} from {len(sub_item_rows[uuid])} sub_item_rows')
                sub_item_row = sub_item_rows[uuid][sub_i]
                sub_item_row = convert_multi_value_dict_to_row_dict(
                    output_multi_row_dict=sub_item_row,
                    input_val_dict=val_dict,
                )
        multi_rows += sub_item_rows[uuid]
    return main_rows, multi_rows, attach_rows


def make_dfs_from_json_data(
    form_type,
    form_id,
    form_year,
    save_dir=pc_configs.KOBO_CSV_FROM_JSON_DATA_PATH,
):
    json_data = utilities.read_or_fetch_and_save_form_data_json(
        form_type=form_type,
        form_id=form_id,
        form_year=form_year,
    )
    if not json_data:
        return None, None, None
    main_filename = f'{form_type}--{form_year}--main.csv'
    main_path = os.path.join(save_dir, main_filename)
    multi_filename = f'{form_type}--{form_year}--multi.csv'
    multi_path = os.path.join(save_dir, multi_filename)
    attach_filename = f'{form_type}--{form_year}--attachments.csv'
    attach_path = os.path.join(save_dir, attach_filename)
    main_rows, multi_rows, attach_rows = extract_main_and_multi_rows_from_json_data(
        kobo_form=form_type,
        kobo_form_year=form_year,
        json_data=json_data,
    )
    df_main = pd.DataFrame(data=main_rows)
    df_main.to_csv(main_path, index=False)
    df_multi = pd.DataFrame(data=multi_rows)
    df_multi.to_csv(multi_path, index=False)
    df_attach = pd.DataFrame(data=attach_rows)
    df_attach.to_csv(attach_path, index=False)
    return df_main, df_multi, df_attach


def get_csv_save_all_form_data(
    form_tups=pc_configs.API_FORM_ID_FORM_LABELS_ALL,
    save_dir=pc_configs.KOBO_CSV_FROM_JSON_DATA_PATH,
):
    """Iterates through configured forms to fetch json data"""
    for form_id, form_type, form_year in form_tups:
        _ = make_dfs_from_json_data(
            form_type,
            form_id,
            form_year,
            save_dir=save_dir,
        )