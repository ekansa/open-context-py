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


def json_friendly_datatype_input_obj(input_obj):
    input_obj = uuid_to_string(input_obj)
    input_obj = datetime_to_string(input_obj)
    input_obj = decimal_to_float(input_obj)
    return input_obj


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
            v = json_friendly_datatype_input_obj(v)
            new_values.append(v)
        return new_values
    else:
        input_obj = json_friendly_datatype_input_obj(input_obj)
        return input_obj


def get_attrib_value_from_rel_objects(model_obj, act_attrib):
    """Gets an attribute value from a model_obj's related objects"""
    attrib_path = act_attrib.split('__')
    last_path_index = len(attrib_path) - 1
    act_model_obj = copy.deepcopy(model_obj)
    for i, attrib_item in enumerate(attrib_path):
        act_attrib_value = getattr(act_model_obj, attrib_item, None)
        if not act_attrib_value:
            continue
        if i == last_path_index:
            return act_attrib_value
        act_model_obj = copy.deepcopy(act_attrib_value)
    return None


def make_model_object_json_safe_dict(model_obj, more_attributes=None):
    """Makes a model object a json safe dictionary

    :param model.Object model_obj: An instance of a Django model object
    :param list more_attributes: A list of additional model attributes
        to include in the json_safe dict to return.
    """
    dict_skips = [
        '_django_version', '_state', 'meta_json'
    ]
    raw_dict = model_obj.__dict__
    if more_attributes:
        for act_attrib in more_attributes:
            act_attrib_value = get_attrib_value_from_rel_objects(model_obj, act_attrib)
            if not act_attrib_value:
                continue
            raw_dict[act_attrib] = act_attrib_value
    dict_obj = {k:v for k, v in raw_dict.items() if k not in dict_skips}
    if raw_dict.get('meta_json'):
        dict_obj['meta_json'] = copy.deepcopy(model_obj.meta_json)
    return make_dict_json_safe(dict_obj)