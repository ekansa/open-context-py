import copy
import json
import uuid as GenUUID

import reversion

from django.conf import settings
from django.core.validators import (
    validate_slug as django_validate_slug,
    URLValidator
)

from django.db.models import Q
from django.db import transaction
from django.utils import timezone


from opencontext_py.libs.general import LastUpdatedOrderedDict


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    sting_number_splitter,
    suggest_project_short_id,
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities as model_utils
from opencontext_py.apps.all_items.legacy_all import update_old_id
from opencontext_py.apps.all_items.editorial.api import manifest_obj_to_json_safe_dict

from opencontext_py.apps.all_items.editorial.item import edit_configs

from opencontext_py.libs.models import (
    make_dict_json_safe, 
    make_model_object_json_safe_dict
)


DATA_TYPE_LABELS = {
    dt.get('value'):dt.get('text') for dt in edit_configs.DATA_TYPE_OPTIONS
}



# ---------------------------------------------------------------------
# NOTE: The functions support user interfaces for navigating the
# content of projects
# ---------------------------------------------------------------------

def make_grouped_by_dict_from_dict_list(list_dicts, index_list):
    """Makes a dictionary, grouped by attributes of query set objects
    
    :param list index_list: List of attributes in objects of the
       query set we want to use as group-by criteria.
    """
    keyed_objects = LastUpdatedOrderedDict()
    for obj in list_dicts:
        key = tuple(obj.get(act_attrib) for act_attrib in index_list)
        keyed_objects.setdefault(key, []).append(obj)
    return keyed_objects


def make_tree_dict_from_grouped_dict_list(list_dicts, index_list):
    """Groups a queryset according to index list of attributes to
    make hierarchically organized lists of dicts
    """
    # NOTE: This works because it relies on mutating a dictionary
    # tree_dict. It's a little hard to understand, which is why
    # there's a debugging function _print_tree_dict to show the
    # outputs.
    grouped_objs = make_grouped_by_dict_from_dict_list(list_dicts, index_list)
    tree_dict = LastUpdatedOrderedDict()
    for group_tup_key, obj_list in grouped_objs.items():
        level_dict = tree_dict
        for key in group_tup_key:
            if isinstance(key, GenUUID.UUID):
                key = str(key)
            if key != group_tup_key[-1]:
                level_dict.setdefault(key, LastUpdatedOrderedDict())
                level_dict = level_dict[key]
            else:
                level_dict[key] = make_dict_json_safe(obj_list)
    return tree_dict


def convert_tree_dict_to_children(
    parent_id, 
    tree_dict, 
    key_label_dict, 
    bottom_uuid_label_tup=('predicate_id', 'predicate__label')
):
    """Conversts a tree dict into nested lists of children
    
    :param str parent_id: An id, unique in the context of this
        tree that helps make a unique uuid for child nodes in
        this tree. We do this because we cache items and their
        children with a uuid key, and making a context based
        uuid makes it easier to cache the same item that may
        be in multiple tree contexts.
    :param dict tree_dict: An dictionary of that recursively
        contains child dictionaries. The bottom level is a 
        list. The order of keys is significant in these
        dictionaries.
    :param dict key_label_dict: A dict to look up the label
        of an entity that goes with a specific key
    :param tuple bottom_uuid_label_tup: A tuple specifying
        the mapping of keys needed to fill 'uuid' and 'label'
        key values.
    """
    level_list = []
    for key, sub_dict in tree_dict.items():
        _, key_uuid = update_old_id(f'{parent_id}-{key}') 
        if isinstance(sub_dict, list):
            # We have a list, so we're at the bottom of the
            # tree-hierarchy. 
            act_children = []
            for item in sub_dict:
                item['uuid'] = item.get(bottom_uuid_label_tup[0])
                item['label'] = item.get(bottom_uuid_label_tup[1])
                item['no_root_cache'] = True
                act_children.append(item)
        else:
            act_children = convert_tree_dict_to_children(
                key_uuid, 
                sub_dict, 
                key_label_dict=key_label_dict,
            )
        act_item = {
            'uuid': key_uuid,
            'label': key_label_dict.get(key, key),
            'key': key,
            'children': act_children,
        }
        level_list.append(act_item)
    return level_list


def project_descriptions_tree(project_id):
    """Returns predicates used in a project, organized by item_type, item_class, and data_type"""
    proj_obj = AllManifest.objects.filter(uuid=project_id).first()
    if not proj_obj:
        return None

    p_qs = AllAssertion.objects.filter(
        project_id=project_id,
        predicate__project_id=project_id,
    ).select_related(
        'subject'
    ).select_related(
        'subject__item_class'
    ).select_related(
        'predicate'
    ).distinct(
        'subject__item_type',
        'subject__item_class',
        'predicate__data_type',
        'predicate__label',
        'predicate_id',
    ).order_by(
        'subject__item_type',
        'subject__item_class',
        'predicate__data_type',
        'predicate__label',
        'predicate_id',
    ).values(
        'subject__item_type',
        'subject__item_class_id',
        'subject__item_class__label',
        'predicate_id',
        'predicate__data_type',
        'predicate__label',
    )

    proj_root = manifest_obj_to_json_safe_dict(proj_obj)
    _, proj_root_uuid = update_old_id(f'project_description_tree_{project_id}')
    proj_root['label'] = f"Descriptions: {proj_root['label']}"
    proj_root['uuid'] = proj_root_uuid
    
    key_label_dict = {k:v for k,v in DATA_TYPE_LABELS.items()}
    
    key_label_tups = [
        ('subject__item_class_id', 'subject__item_class__label',),
        ('predicate_id', 'predicate__label',),
    ]
    for item in p_qs:
        for key_id, key_label in key_label_tups:
            key = str(item.get(key_id))
            if key in key_label_dict:
                continue
            key_label_dict[key] = item.get(key_label)

    index_list = [
        'subject__item_type', 
        'subject__item_class_id', 
        'predicate__data_type', 
    ]
    children_dict = make_tree_dict_from_grouped_dict_list(p_qs, index_list)
    proj_root['children'] = convert_tree_dict_to_children(
        proj_root_uuid, 
        children_dict,
        key_label_dict=key_label_dict,
    )
    return proj_root


def project_spatial_tree(project_id):
    """Returns predicates used in a project, organized by item_type, item_class, and data_type"""
    proj_obj = AllManifest.objects.filter(uuid=project_id).first()
    if not proj_obj:
        return None
    
    m_qs = AllManifest.objects.filter(
        item_type='subjects',
        project_id=project_id,
    ).exclude(
        context__project_id=project_id
    )
    count_m_qs = len(m_qs)
    while count_m_qs > 20:
        level_uuids = [m.context.uuid for m in m_qs]
        m_qs = AllManifest.objects.filter(
            item_type='subjects',
            uuid__in=level_uuids
        )
        count_m_qs = len(m_qs)

    proj_root = manifest_obj_to_json_safe_dict(proj_obj)
    _, proj_root_uuid = update_old_id(f'project_spatial_tree_{project_id}')
    proj_root['label'] = f"Contexts, Objects: {proj_root['label']}"
    proj_root['uuid'] = proj_root_uuid
    proj_root['children'] = []
    for m_obj in m_qs:
        child_item = manifest_obj_to_json_safe_dict(m_obj)
        child_item['no_root_cache'] = True
        proj_root['children'].append(child_item)
    return proj_root