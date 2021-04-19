
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
from opencontext_py.apps.all_items.representations import item
from opencontext_py.apps.all_items.representations import rep_utils

from opencontext_py.apps.all_items.legacy_all import update_old_id



KEY_FIND_REPLACES = [
    ('-', '_',),
    (':', '__',),
    ('#', '',),
    (' ', '_',),
    ('/', '_',),
]


SPECIAL_KEYS = [
    'id',
    'uuid',
    'slug',
    'label',
    'category',
    'item_class__label',
    'type',
    'features',
    'oc-gen:has-obs',
    'oc-gen:has-contexts',
    'oc-gen:has-linked-contexts',
    'dc-terms:abstract',
    'dc-terms:description',
    'bibo:content',
    'dc-terms:title',
    'dc-terms:issued',
    'dc-terms:modified',
    'dc-terms:license',
    'dc-terms:isPartOf',
    'dc-terms:hasPart',
    'contexts',
]

ITEM_METADATA_OBS_ID = '#item-metadata'
ITEM_METADATA_OBS_LABEL = 'Item Metadata'


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


def prepare_citation_dict(rep_dict):
    """Prepares a citation dictionary object

    :param dict rep_dict: The item's JSON-LD representation dict
    """
    cite = {
        'title': rep_dict.get('dc-terms:title'),
        'uri': rep_dict.get('id'),
    }
    return cite


def prepare_item_metadata_obs(
    rep_dict,
    obs_id=ITEM_METADATA_OBS_ID,
    obs_label=ITEM_METADATA_OBS_LABEL, 
    skip_keys=SPECIAL_KEYS
):
    """Prepares an observation dict for metadata directly associated to an item

    :param dict rep_dict: The item's JSON-LD representation dict
    :param str obs_label: The label for the observation
    :param list skip_keys: A list of string dictionary keys to skip
        and not allocate to the output meta_obs_dict dict.
    """
    meta_attribute_group_dict = LastUpdatedOrderedDict()
    meta_attribute_group_dict['default'] = True

    meta_count = 0
    for key, vals in rep_dict.items():
        if key in skip_keys:
            # This key is not used for metadata.
            continue
        meta_attribute_group_dict[key] = vals
        meta_count += 1
    if meta_count == 0:
        # We have no linked data predicates / metadata
        # directly associated with this item. Return None.
        return None

    # Bundle the linked data metadata into nested 
    # attribute group, events to make templating more
    # consistent.
    meta_event_dict = LastUpdatedOrderedDict()
    meta_event_dict['default'] = True
    meta_event_dict['oc-gen:has-attribute-groups'] = [
        meta_attribute_group_dict
    ]
    meta_obs_dict = LastUpdatedOrderedDict()
    meta_obs_dict['id'] = obs_id
    meta_obs_dict['label'] = obs_label
    meta_obs_dict['default'] = True
    meta_obs_dict['oc-gen:has-events'] = [
        meta_event_dict
    ]
    return meta_obs_dict


def template_reorganize_attribute_group_dict(old_attrib_grp):
    """Reorganizes assertions in an observation for easier template use

    :param dictold_attrib_grp: An attribute group dict from the item's
        JSON-LD representation dict
    """
    
    # NOTE: To make templating easier, this function groups together
    # assertions by predicate and object item_type. The general structure
    # for the output is like:
    #
    # {
    #   'id': '#-attribute-group'
    #   'label': 'Default',
    #   'type': 'oc-gen:attribute-groups',
    #   'default': True,
    #   'descriptions': {
    #       'oc-pred:24-fabric-category': [
    #        ....lots of dicts of descriptions...
    #       ],
    #       'oc-pred:24-object-type': [
    #           ...lots of dicts of object types ...
    #       ],
    #   },
    #   'relations': {
    #       'subjects': {
    #           'oc-pred:oc_gen_links: [
    #            .... links to different subjects items...
    #           ],
    #       },
    #       'media': {
    #           'oc-pred:oc_gen_links: [
    #            .... links to different media items...
    #           ],
    #       }
    #   },
    # }

    node_keys = ['id', 'label', 'type', 'default']

    new_attrib_group = LastUpdatedOrderedDict()
    for key in node_keys:
        new_attrib_group[key] = old_attrib_grp.get(key)

    new_attrib_group['descriptions'] = LastUpdatedOrderedDict()
    new_attrib_group['relations'] = {}

    for pred_key, vals in old_attrib_grp.items():
        if pred_key in node_keys:
            # We've already copied over the node keys.
            continue
        if not isinstance(vals, list) or not len(vals):
            # This is not a list or it is an empty list.
            continue
        is_relation = (
            str(vals[0].get('predicate__item_class_id')) == configs.CLASS_OC_LINKS_UUID
        )
        if not is_relation:
            # This predicate (pred_key) is not used for a relation,
            # so treat this as a description.
            new_attrib_group['descriptions'][pred_key] = vals
            continue
        
        # Nest relations by the item_type of the object of the
        # assertion, then by the predicate for the assertion.
        for act_val in vals:
            act_item_type = act_val.get('object__item_type')
            if act_item_type not in configs.OC_PRED_LINK_OK_ITEM_TYPES:
                continue
            new_attrib_group['relations'].setdefault(
                act_item_type,
                LastUpdatedOrderedDict()
            )
            new_attrib_group['relations'][act_item_type].setdefault(
                pred_key,
                []
            )
            new_attrib_group['relations'][act_item_type][pred_key].append(
                act_val
            )

    return new_attrib_group


def template_reorganize_obs(old_obs_dict):
    """Reorganizes assertions in an observation for easier template use

    :param dict old_obs_dict: An observation dict from the item's
        JSON-LD representation dict
    """
    new_obs_dict = LastUpdatedOrderedDict()
    for key, vals in old_obs_dict.items():
        if key == 'oc-gen:has-events':
            continue
        new_obs_dict[key] = vals
    
    new_obs_dict['oc-gen:has-events'] = []
    for old_event_dict in old_obs_dict.get('oc-gen:has-events', []):
        new_event_dict = LastUpdatedOrderedDict()
        for key, vals in old_event_dict.items():
            if key == 'oc-gen:has-attribute-groups':
                continue
            new_event_dict[key] = vals
        
        new_event_dict['has_descriptions'] = None
        new_event_dict['has_relations'] = None
        new_event_dict['oc-gen:has-attribute-groups'] = []
        for old_attrib_grp in old_event_dict.get('oc-gen:has-attribute-groups', []):
            new_attrib_group = template_reorganize_attribute_group_dict(
                old_attrib_grp
            )
            if len(new_attrib_group.get('descriptions', {})):
                new_event_dict['has_descriptions'] = True
            if len(new_attrib_group.get('relations', {})):
                new_event_dict['has_relations'] = True
            new_event_dict['oc-gen:has-attribute-groups'].append(
                new_attrib_group
            )

        
        new_obs_dict['oc-gen:has-events'].append(new_event_dict)
    return new_obs_dict


def template_reorganize_all_obs(rep_dict):
    """Iterates through all observations to make easy to template groups

    :param dict rep_dict: The item's JSON-LD representation dict
    """
    if not rep_dict.get('oc-gen:has-obs'):
        return rep_dict
    
    all_new_obs = []
    for old_obs_dict in rep_dict.get('oc-gen:has-obs'):
        new_obs_dict = template_reorganize_obs(old_obs_dict)
        all_new_obs.append(new_obs_dict)
    
    rep_dict['oc-gen:has-obs'] = all_new_obs
    return rep_dict


def prepare_for_item_dict_html_template(man_obj, rep_dict):
    """Prepares a representation dict for HTML templating"""

    # Consolidate the contexts paths
    rep_dict['contexts'] = (
        rep_dict.get('oc-gen:has-contexts', []) 
        + rep_dict.get('oc-gen:has-linked-contexts', [])
    )

    # Add any metadata about this item.
    meta_obs_dict = prepare_item_metadata_obs(rep_dict)
    if meta_obs_dict:
        rep_dict.setdefault('oc-gen:has-obs', [])
        rep_dict['oc-gen:has-obs'].append(meta_obs_dict)

    # Reorganize the nesting of the assertions to make
    # them more consistent and easier to use in the template
    rep_dict = template_reorganize_all_obs(rep_dict)


    # Now ensure easy to template characters in the keys
    # in this dict
    item_dict = make_template_ready_dict_obj(rep_dict)

    return item_dict

