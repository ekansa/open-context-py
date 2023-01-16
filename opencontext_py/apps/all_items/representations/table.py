import json
import pandas as pd

from django.conf import settings


def get_preview_csv_data(item_man_obj, act_dict):
    """Gets preview CSV data as a JSON object

    :param AllManifest item_man_obj: An all manifest instance object
    :param dict act_dict: The acting representation dict for the item

    returns act_dict
    """
    csv_url = item_man_obj.table_preview_csv_url
    if not csv_url:
        return act_dict
    try:
        df = pd.read_csv(csv_url, low_memory=False)
    except:
        df = None
    if df is None:
        return act_dict
    t_dict = json.loads(df.to_json(orient='table'))
    fields = []
    field_label_keys = {}
    for raw_field in t_dict.get('schema', {}).get('fields', []):
        if len(fields) == 0 and raw_field.get('name') == 'index':
            # We don't want to include the index (row number)
            continue
        field_key = f'field_{len(fields)}'
        field = {
            'key': field_key,
            'label': raw_field.get('name'),
        }
        fields.append(field)
        field_label_keys[raw_field.get('name')] = field_key
    items = []
    for row in t_dict.get('data', []):
        item = {}
        for field_label, value in row.items():
            if field_label == 'index':
                # We don't want to include the index (row number)
                continue
            field_key =  field_label_keys.get(field_label)
            if not field_key:
                continue
            item[field_key] = value
        items.append(item)
    act_dict['count_fields'] = item_man_obj.meta_json.get('count_fields')
    act_dict['count_rows'] = item_man_obj.meta_json.get('count_rows')
    act_dict['table_sample_fields'] = fields
    act_dict['table_sample_data'] = items
    return act_dict