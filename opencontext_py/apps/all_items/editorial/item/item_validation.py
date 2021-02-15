import copy
import json
import uuid as GenUUID

import reversion

from django.conf import settings
from django.core.validators import validate_slug as django_validate_slug

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

def is_valid_uuid(val):
    try:
        return GenUUID.UUID(str(val))
    except ValueError:
        return None

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

    # First check to see if the required prefix has a numeric component.
    # This is used when the check_label is empty, meaning we're trying to suggest
    # a label that starts with a prefix, we're not trying to increment up from
    # a check_label.
    req_prefix_label_prefix = None
    req_prefix_last_num = None
    if required_prefix:
        # If we have a numeric prefix, check to to see if it has a number part.
        req_prefix_label_prefix, req_prefix_last_num = get_prefix_last_number_part(
            required_prefix
        )

    label_prefix, last_number = get_prefix_last_number_part(check_label)
    if last_number is None and req_prefix_last_num is None:
        # No number part, so we can't suggest a similar numeric value
        return None
    
    query_prefix = label_prefix
    if required_prefix and (not label_prefix or len(required_prefix) > len(label_prefix)):
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
    
    if check_label:
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

    print(f'Label man: {m.label} ({str(m.uuid)}), tested: {str(tested)}')

    new_prefix = label_prefix
    if not label_prefix and req_prefix_label_prefix:
        # We're composing a new_check_label from the starting point
        # of the required_prefix, not an old check_label.
        new_prefix = req_prefix_label_prefix

    new_last_number = None
    if last_number is not None:
        # Create a new check label to see if it is in use.
        new_last_number = int(float(last_number)) + 1

    _, query_last_number = get_prefix_last_number_part(m.label)
    if query_last_number is not None:
        query_last_number = int(float(query_last_number))
    
        if new_last_number is None or query_last_number > new_last_number:
            new_last_number = query_last_number + 1

    if new_last_number is None:
        # We couldn't find a new last number to check.
        return None

    new_check_label = f'{new_prefix}{new_last_number}'

    # Recursively call this function to see if our new label is OK
    return suggest_label(
        new_check_label,
        required_prefix=required_prefix,
        filter_args=filter_args, 
        exclude_uuid=exclude_uuid, 
        tested=tested
    )


def report_id_conflicts(m_qs, for_validation=True):
    """Reports identifer conflicts for conflicting identifer errors"""
    if for_validation:
        return {
            'is_valid': (len(m_qs) < 1),
            'valid_conflict_count': len(m_qs),
            'valid_conflict_examples': [
                make_model_object_json_safe_dict(m) for m in m_qs[:5]
            ],
            'suggested': None,
        }
    else:
        return {
            'is_warned': (len(m_qs) > 0),
            'warn_count': len(m_qs),
            'warn_examples': [
                make_model_object_json_safe_dict(m) for m in m_qs[:5]
            ],
        }


def validate_label(check_label, filter_args=None, exclude_uuid=None):
    """This validates a label for a manifest object given filter args"""
    check_label = str(check_label).strip()
    if filter_args and filter_args.get('item_type') == 'subjects':
        if '/' in check_label:
            return {
                'is_valid': False,
                'label': check_label,
                'errors': [
                    f'"{check_label}"" invalid. Item type "subjects" cannot have "/" characters.'
                ],
                'valid_conflict_count': 0,
                'valid_conflict_examples': [],
                'suggested': None,
            }


    m_qs = AllManifest.objects.filter(label=check_label)
    if filter_args:
        m_qs = m_qs.filter(**filter_args)
    if exclude_uuid:
        m_qs = m_qs.exclude(uuid=exclude_uuid)
    # First check for validity
    report = report_id_conflicts(m_qs)
    report['label'] = check_label
    report['suggested'] = None
    if not report['is_valid']:
        report['suggested'] = suggest_label(
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
    warning = report_id_conflicts(m_qs, for_validation=False)
    for key, value in warning.items():
        report[key] = value
    return report


def suggest_project_short_id():
    """Suggests a project short id, not already in use"""
    m_qs = AllManifest.objects.filter(item_type='projects')
    short_ids = []
    for m in m_qs:
        if not m.meta_json.get('short_id'):
            continue
        short_ids.append(m.meta_json.get('short_id'))
    if not len(short_ids):
        # We don't have any project short ids yet, so suggest the first.
        return 1
    # Suggest 1 plus the max we already have.
    return max(short_ids) + 1


def validate_project_short_id(raw_short_id, exclude_uuid=None):
    """Validates a (project) short integer id"""
    try:
        short_id = int(float(raw_short_id))
    except:
        short_id = None
    if not short_id or short_id < 1:
        return {
            'is_valid': False,
            'short_id': raw_short_id,
            'errors': [f'{raw_short_id} invalid, not a positive integer'],
            'valid_conflict_count': 0,
            'valid_conflict_examples': [],
            'suggested': suggest_project_short_id(),
        }
    
    m_qs = AllManifest.objects.filter(
        item_type='projects',
        meta_json__short_id=short_id,
    )
    if exclude_uuid:
        m_qs = m_qs.exclude(uuid=exclude_uuid)
    
    report = report_id_conflicts(m_qs)
    report['short_id'] = short_id
    if not report['is_valid']:
        report['suggested'] = suggest_project_short_id()
    return report


def validate_slug(slug, exclude_uuid=None):
    """Validates a slug identifier"""
    errors = []
    if not slug or slug != slug.lower() or '_' in slug:
        errors.append(
            f'"{slug}" invalid. Open Context slugs must be lower case letters, numbers, or hyphens'
        )
    try:
        ok = django_validate_slug(slug)
    except:
        errors.append(f'"{slug}" invalid. Must consist of letters, numbers, or hyphens.')
    if '--' in slug:
        errors.append(f'"{slug}" invalid. Must not have multiple adjacent hyphens.')
    if errors:
        return {
            'is_valid': False,
            'slug': slug,
            'errors': errors,
            'valid_conflict_count': 0,
            'valid_conflict_examples': [],
        }

    m_qs = AllManifest.objects.filter(
        slug=slug,
    )
    if exclude_uuid:
        m_qs = m_qs.exclude(uuid=exclude_uuid)
    report = report_id_conflicts(m_qs)
    report['slug'] = slug
    return report


def validate_uuid(uuid, exclude_uuid=None):
    """Validates a slug identifier"""
    errors = []
    if not uuid or uuid != uuid.lower() or not '-' in uuid or not is_valid_uuid(uuid):
        errors.append(
            f'"{uuid}" invalid. Open Context uuids must be lower case letters, numbers, or hyphens'
        )

    if errors:
        return {
            'is_valid': False,
            'uuid': uuid,
            'errors': errors,
            'valid_conflict_count': 0,
            'valid_conflict_examples': [],
        }

    m_qs = AllManifest.objects.filter(
        uuid=uuid,
    )
    if exclude_uuid:
        m_qs = m_qs.exclude(uuid=exclude_uuid)
    report = report_id_conflicts(m_qs)
    report['uuid'] = uuid
    return report


def validate_item_key(item_key, exclude_uuid=None):
    """Validates a item_key identifier"""
    m_qs = AllManifest.objects.filter(
        item_key=item_key,
    )
    if exclude_uuid:
        m_qs = m_qs.exclude(uuid=exclude_uuid)
    report = report_id_conflicts(m_qs)
    report['item_key'] = item_key
    return report


def validate_uri(raw_uri, exclude_uuid=None):
    """Validates a uri identifier"""
    uri = AllManifest().clean_uri(raw_uri)
    m_qs = AllManifest.objects.filter(
        uri=uri,
    )
    if exclude_uuid:
        m_qs = m_qs.exclude(uuid=exclude_uuid)
    report = report_id_conflicts(m_qs)
    report['uri'] = raw_uri
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
    if request_dict.get('label_prefix'):
        label_prefix = request_dict.get('label_prefix')
        filter_args = {
            attrib:request_dict.get(attrib) 
            for attrib in LABEL_UNIQUENESS_ATTRIBUTES
            if request_dict.get(attrib)
        }        
        return {
            'suggested': suggest_label(
                check_label=None,
                required_prefix=label_prefix,
                filter_args=filter_args, 
                exclude_uuid=request_dict.get('uuid')
            ),
        }
    if request_dict.get('short_id'):
        check_short_id = request_dict.get('short_id')
        return validate_project_short_id(
            check_short_id,
            exclude_uuid=request_dict.get('uuid')
        )
    
    if request_dict.get('slug'):
        slug = request_dict.get('slug')
        return validate_slug(
            slug,
            exclude_uuid=request_dict.get('uuid')
        )
    
    if request_dict.get('new_uuid'):
        uuid = request_dict.get('new_uuid')
        return validate_uuid(
            uuid,
            exclude_uuid=request_dict.get('uuid')
        )
    
    if request_dict.get('item_key'):
        item_key = request_dict.get('item_key')
        return validate_item_key(
            item_key,
            exclude_uuid=request_dict.get('uuid')
        )
    
    if request_dict.get('uri'):
        uri = request_dict.get('uri')
        return validate_uri(
            uri,
            exclude_uuid=request_dict.get('uuid')
        )