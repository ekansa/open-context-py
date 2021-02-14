import copy
import json
import uuid as GenUUID

import reversion

from django.conf import settings

from django.db.models import Q
from django.db import transaction
from django.utils import timezone


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    sting_number_splitter,
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities as model_utils
from opencontext_py.apps.all_items.legacy_all import update_old_id
from opencontext_py.apps.all_items.editorial import api as editorial_api

from opencontext_py.apps.all_items.editorial.item import edit_configs
from opencontext_py.apps.all_items.editorial.item import updater_general
from opencontext_py.apps.all_items.editorial.item import updater_manifest
from opencontext_py.apps.all_items.editorial.item import updater_assertions
from opencontext_py.apps.all_items.editorial.item import updater_spacetime
from opencontext_py.apps.all_items.editorial.item import updater_resources
from opencontext_py.apps.all_items.editorial.item import updater_identifiers


from opencontext_py.libs.models import (
    make_dict_json_safe, 
    make_model_object_json_safe_dict
)

MAX_LABEL_SUGGEST_ITERATIONS = 10

LABEL_UNIQUENESS_ATTRIBUTES = [
    'item_type',
    'project_id',
    'context_id',
]


def get_prefix_last_number_part(check_label):
    """Parses a check label to get a prefix and a last number part"""
    label_parts, has_number_part = sting_number_splitter(check_label)
    if not has_number_part:
        # There's no numeric part to the label, so don't suggest an ID.
        return None, None

    last_number_index = None
    last_number = None
    for i, (is_num, part) in enumerate(label_parts):
        if not is_num:
            continue
        last_number_index = i
        last_number = part
    label_prefix = ''
    for is_num, part in label_parts[:last_number_index]:
        label_prefix += part
    return label_prefix, last_number


def suggest_label(check_label, required_prefix=None, filter_args=None, exclude_uuid=None, tested=None):
    """Determine a suggested label using the check_label as a template"""
    label_prefix, last_number = get_prefix_last_number_part(check_label)
    if last_number is None:
        # No number part, so we can't suggest a similar numeric value
        return None
    
    query_prefix = label_prefix
    if required_prefix and len(required_prefix) > len(label_prefix):
        query_prefix = required_prefix

    if tested is None:
        tested = []
    if len(tested) >= MAX_LABEL_SUGGEST_ITERATIONS:
        return None

    m_qs = AllManifest.objects.filter(
        label__startswith=query_prefix
    )
    if filter_args:
        m_qs = m_qs.filter(**filter_args)
    if exclude_uuid:
        m_qs = m_qs.exclude(uuid=exclude_uuid)
    if tested:
        m_qs = m_qs.exclude(label__in=tested)
    
    m_exact = m_qs.filter(label=check_label).first()
    if not m_exact:
        # The check label is OK, because we don't have any
        # manifest items with that label.
        return check_label

    m = m_qs.order_by('-sort', '-label',).first()
    if not m:
        # The check label is OK, because we don't have any
        # manifest items with that label.
        return check_label
    
    # Note that we've already checked on some labels,
    # This prevents us for checking on them over and over.
    tested.append(check_label)
    tested.append(m.label)

    # Create a new check label to see if it is in use.
    last_number = int(float(last_number))
    _, query_last_number = get_prefix_last_number_part(m.label)
    if query_last_number is None:
        new_last_number = last_number + 1
    else:
        query_last_number = int(float(query_last_number))
        if last_number > query_last_number:
            new_last_number = last_number + 1
        else:
            new_last_number = query_last_number + 1

    new_check_label = f'{label_prefix}{new_last_number}'

    # Recursively call this function to see if our new label is OK
    return suggest_label(
        new_check_label,
        required_prefix=required_prefix,
        filter_args=filter_args, 
        exclude_uuid=exclude_uuid, 
        tested=tested
    )


def validate_label(check_label, filter_args=None, exclude_uuid=None):
    """This validates a label for a manifest object given filter args"""
    report = {
        'label': check_label,
    }
    m_qs = AllManifest.objects.filter(label=check_label)
    if filter_args:
        m_qs = m_qs.filter(**filter_args)
    if exclude_uuid:
        m_qs = m_qs.exclude(uuid=exclude_uuid)
    # First check for validity
    report['is_valid'] = (len(m_qs) < 1)
    report['valid_conflict_count'] = len(m_qs)
    report['valid_conflict_examples'] = [
        make_model_object_json_safe_dict(m) for m in m_qs[:5]
    ]
    if not report['is_valid']:
        report['suggested_label'] = suggest_label(
            check_label, 
            required_prefix=None, 
            filter_args=filter_args, 
            exclude_uuid=exclude_uuid, 
        )

    # Now check for warnings.
    m_qs = AllManifest.objects.filter(label=check_label)
    if filter_args:
        no_context_args = {k:v for k,v in filter_args.items() if k != 'context_id'}
        m_qs = m_qs.filter(**no_context_args)
    if exclude_uuid:
        m_qs = m_qs.exclude(uuid=exclude_uuid)

    # First check for validity
    report['is_warn'] = (len(m_qs) > 0)
    report['warn_conflict_count'] = len(m_qs)
    report['warn_conflict_examples'] = [
        make_model_object_json_safe_dict(m) for m in m_qs[:5]
    ]
    return report


def validate_manifest_attributes(request_dict, value_delim=editorial_api.MULTI_VALUE_DELIM):
    """Validates manifest attributes for a request dict"""
    if request_dict.get('label'):
        check_label = request_dict.get('label')
        filter_args = {
            attrib:request_dict.get(attrib) 
            for attrib in LABEL_UNIQUENESS_ATTRIBUTES
            if request_dict.get(attrib)
        }
        return validate_label(
            check_label, 
            filter_args=filter_args, 
            exclude_uuid=request_dict.get('uuid')
        )
    if request_dict.get('short_id'):
        check_short_id = request_dict.get('short_id')