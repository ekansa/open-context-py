
import copy
import hashlib
import uuid as GenUUID

from django.conf import settings
from django.core.cache import caches
from django.db.models import OuterRef, Subquery

from opencontext_py.libs.general import LastUpdatedOrderedDict

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities
from opencontext_py.apps.all_items.representations import rep_utils


KEY_FIND_REPLACES = [
    ('-', '_',),
    (':', '__',),
    ('#', '',),
    (' ', '_',),
    ('/', '_',),
]


def _make_key_template_ok(key, key_find_replaces=KEY_FIND_REPLACES):
    """Makes a key OK for a template"""
    if not isinstance(key, str):
        return key
    new_key = key.lower()
    for f, r in key_find_replaces:
        new_key = new_key.replace(f, r)
    return new_key


def make_template_ready_dict_obj(dict_obj):
    """Makes a result object ready for use in a template"""
    if not isinstance(dict_obj, dict):
        return dict_obj
    temp_dict = LastUpdatedOrderedDict()
    for key, value in dict_obj.items():
        new_key = _make_key_template_ok(key)
        if isinstance(value, dict):
            value = make_template_ready_dict_obj(value)
        elif isinstance(value, list):
            temp_dict[new_key] = [
                make_template_ready_dict_obj(v)
                for v in value
            ]
            continue
        temp_dict[new_key] = value
    return temp_dict

