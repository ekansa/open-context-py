
import copy
import hashlib
import uuid as GenUUID

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


# This provides a mappig between a predicate.data_type and
# the attribute of an assertion object for the object of that
# assertion.
ASSERTION_DATA_TYPE_LITERAL_MAPPINGS = {
    'xsd:string': 'obj_string',
    'xsd:boolean': 'obj_boolean',
    'xsd:integer': 'obj_integer',
    'xsd:double': 'obj_double',
    'xsd:date': 'obj_datetime',
}



def get_item_key_or_uri_value(manifest_obj):
    """Gets an item_key if set, falling back to uri value"""
    if manifest_obj.item_key:
        return manifest_obj.item_key
    return f"https://{manifest_obj.uri}"


def make_predicate_objects_list(predicate, assert_objs):
    """Makes a list of assertion objects for a predicate"""
    # NOTE: Predicates of different data-types will hae different values
    # for different 
    pred_objects = []
    for assert_obj in assert_objs:
        if predicate.data_type == 'id':
            obj = LastUpdatedOrderedDict()
            obj['id'] = f'https://{assert_obj.object.uri}'
            obj['slug'] = assert_obj.object.slug
            obj['label'] = assert_obj.object.label
            if assert_obj.object.item_class and str(assert_obj.object.item_class.uuid) != configs.DEFAULT_CLASS_UUID:
                obj['type'] = get_item_key_or_uri_value(
                    assert_obj.object.item_class
                )
            if getattr(assert_obj, 'object_thumbnail', None):
                obj['oc-gen:thumbnail-uri'] = f'https://{assert_obj.object_thumbnail}'
        elif predicate.data_type == 'xsd:string':
            obj = {
                f'@{assert_obj.language.item_key}': assert_obj.obj_string
            }
        else:
            act_attrib = ASSERTION_DATA_TYPE_LITERAL_MAPPINGS.get(
                predicate.data_type
            )
            obj = getattr(assert_obj, act_attrib)
            if predicate.data_type == 'xsd:double':
                obj = float(obj)
            elif predicate.data_type == 'xsd:date':
                obj = obj.date().isoformat()
        if obj in pred_objects:
            # We already have this object, so don't add it. We face this circumstance
            # when want to add objects to from different predicates that we
            # determined to be equivalent.
            continue
        pred_objects.append(obj)
    return pred_objects


def add_predicates_assertions_to_dict(pred_keyed_assert_objs, act_dict=None, add_objs_to_existing_pred=True):
    """Adds predicates with their grouped objects to a dictionary, keyed by each pred
    
    :param dict pred_keyed_assert_objs: A dictionary, keyed by a manifest predicate
        object that has a list of assertion objects related to that represent the
        objects of that predicate's description.
    :param dict act_dict: A dictionary that gets the predicate object list
    """
    if not act_dict:
        act_dict = LastUpdatedOrderedDict()
    for predicate, assert_objs in pred_keyed_assert_objs.items():
        if predicate.item_type == 'predicates':
            pred_key = f'oc-pred:{predicate.slug}'
        else:
            pred_key = get_item_key_or_uri_value(predicate)
        if not add_objs_to_existing_pred and pred_key in act_dict:
            # We do not want add any objects to an existing predicate.
            # So skip the rest.
            continue
        # Make list of dicts and literal values for the predicate objects.
        pred_objects = make_predicate_objects_list(predicate, assert_objs)
        # Set a default list for the pred_key. This lets us add to an
        # already existing list.
        act_dict.setdefault(pred_key, [])
        for pred_obj in pred_objects:
            if pred_obj in act_dict[pred_key]:
                # This pred_obj is already present (maybe added from an equivalent
                # predicate), so don't add it again. Skip to continue.
                continue
            act_dict[pred_key].append(pred_obj)
    return act_dict