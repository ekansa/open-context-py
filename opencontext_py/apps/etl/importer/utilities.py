import pytz

from dateutil.parser import parse

from django.conf import settings



# Dictionary for mapping common strings to boolean values
STR_TO_BOOLEANS = {
    'n': False,
    'no': False,
    'none': False,
    'absent': False,
    'abs': False,
    'false': False,
    'f': False,
    '0': False,
    '0.0': False,
    'y': True,
    'yes': True,
    'present': True,
    'pres': True,
    'true': True,
    't': True,
    '1': True,
    '1.0': True,
}

def validate_transform_data_type_value(raw_str_value, data_type, timezone=settings.TIME_ZONE):
    """Validates the raw value of a data_type"""
    if not raw_str_value:
        return None
    raw_str_value = str(raw_str_value).strip()
    if not raw_str_value:
        return None
    if data_type == 'xsd:string':
        return raw_str_value
    elif data_type == 'xsd:boolean':
        return STR_TO_BOOLEANS.get(raw_str_value.lower())
    elif data_type == 'xsd:integer':
        try:
            int_val = int(float(raw_str_value))
        except:
            int_val = None
        return int_val
    elif data_type == 'xsd:double':
        try:
            float_val = float(raw_str_value)
        except:
            float_val = None
        return float_val
    elif data_type == 'xsd:date':
        # Parse a date / datetime string, set to a timezone.
        if raw_str_value.endswith('Z'):
            raw_str_value = raw_str_value[0:-1]
        try:
            naive_date_obj = parse(raw_str_value)
            date_obj = pytz.timezone(timezone).localize(naive_date_obj, is_dst=None)
        except:
            date_obj = None
        return date_obj
    else:
        return None
