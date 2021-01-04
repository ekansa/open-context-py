import copy
import decimal
import datetime
import uuid as GenUUID


def uuid_to_string(val):
    """Changes a UUID value to a string"""
    if not val:
        return val
    if not isinstance(val, GenUUID.UUID):
        return val
    return str(val)


def datetime_to_string(val):
    """Changes a datetime value to a string"""
    if not val:
        return val
    if not isinstance(val, datetime.datetime):
        return val
    return val.isoformat()


def decimal_to_float(val):
    """Changes a decimal value to a float"""
    if not val:
        return val
    if not isinstance(val,  decimal.Decimal):
        return val
    return float(val)


def make_javascript_friendly_key(key):
    """Make a key javascript friendly"""
    char_mappings = {
        '-': '_',
        ':': '_',
        '.': '_',
        ' ': '_',
    }
    for f, r in char_mappings.items():
        key = key.replace(f, r)
    return key


def make_dict_json_safe(input_obj, javascript_friendly_keys=False):
    """Makes a dictionary object json safe, recursively"""
    if not input_obj:
        return input_obj
    if  isinstance(input_obj, dict):
        output_dict = {}
        for key, value in input_obj.items():
            if javascript_friendly_keys:
                key = make_javascript_friendly_key(key)
                print(f'Key is {key}')
            output_dict[key] = make_dict_json_safe(value)
        return output_dict
    elif isinstance(input_obj, list):
        new_values = []
        for v in input_obj:
            v = make_dict_json_safe(
                v, 
                javascript_friendly_keys=javascript_friendly_keys
            )
            v = uuid_to_string(v)
            v = datetime_to_string(v)
            v = decimal_to_float(v)
            new_values.append(v)
        return new_values
    else:
        input_obj = uuid_to_string(input_obj)
        input_obj = datetime_to_string(input_obj)
        input_obj = decimal_to_float(input_obj)
        return input_obj


def make_model_object_json_safe_dict(model_obj):
    """Makes a model object a json safe dictionary"""
    raw_dict = model_obj.__dict__
    dict_obj = {k:v for k, v in raw_dict.items() if k not in ['_state', 'meta_json']}
    if raw_dict.get('meta_json'):
        dict_obj['meta_json'] = copy.deepcopy(model_obj.meta_json)
    return make_dict_json_safe(dict_obj)