
import copy
import hashlib
import uuid as GenUUID

from django.conf import settings

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

# ---------------------------------------------------------------------
# NOTE: These functions are widely use in making item representations.
# Open Context's primary representation for a database item is a
# JSON-LD (with GeoJSON for records with geospatial data) document.
# To insure that the JSON-LD representation is well supported, 
# all other representations (esp. HTML) will be built from the JSON-LD
# representation as a starting point.
# ---------------------------------------------------------------------


def get_item_key_or_uri_value(manifest_obj):
    """Gets an item_key if set, falling back to uri value"""
    if manifest_obj.item_key:
        return manifest_obj.item_key
    return f"https://{manifest_obj.uri}"


def make_predicate_objects_list(predicate, assert_objs, for_edit=False, for_html=False):
    """Makes a list of assertion objects for a predicate
    
    :param AllManifest predicate: An all manifest object for the
        predicate for which we want a list of assertion objects.
    :param list or QuerySet assert_objs: A list of query set of
        AllAssertion objects. We iterate through this list to pull
        out the objects of the 'predicate' assertions.
    :param bool for_edit: Do we want an output with additional identifiers
        useful for editing.
    returns list of JSON-LD formated assertion dicts or literals. 
    """
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
            if for_edit or for_html:
                obj['object_id'] = str(assert_obj.object.uuid)
                obj['object__item_type'] = assert_obj.object.item_type
                obj['object__label'] = assert_obj.object.label
                obj['object__uri'] = assert_obj.object.uri
                obj['object__meta_json'] = assert_obj.object.meta_json
                if assert_obj.object.context:
                    obj['object__context_id'] = str(assert_obj.object.context.uuid)
                    obj['object__context__label'] = assert_obj.object.context.label
                    obj['object__context__uri'] = assert_obj.object.context.uri
                if assert_obj.object.item_class:
                    obj['object__item_class__label'] = assert_obj.object.item_class.label
                if hasattr(assert_obj, 'object_class_icon'):
                    obj['object__item_class__icon'] = assert_obj.object_class_icon
        elif predicate.data_type == 'xsd:string':
            # A string gets a language code key, so it's not just a naked
            # literal returned in the pred_objects list.
            obj = {
                f'@{assert_obj.language.item_key}': assert_obj.obj_string
            }
            if for_edit or for_html:
                obj['obj_string'] = assert_obj.obj_string
        else:
            act_attrib = ASSERTION_DATA_TYPE_LITERAL_MAPPINGS.get(
                predicate.data_type
            )
            obj = getattr(assert_obj, act_attrib)
            if predicate.data_type == 'xsd:double':
                obj = float(obj)
            elif predicate.data_type == 'xsd:date':
                obj = obj.date().isoformat()
            if for_edit or for_html:
                obj = {act_attrib: obj}
        
        if for_edit or for_html:
            # Add lots of extra information about the assertion to make editing easier.
            obj['uuid'] = str(assert_obj.uuid)
            obj['subject_id'] = str(assert_obj.subject.uuid)
            obj['observation_id'] = str(assert_obj.observation.uuid)
            obj['observation__label'] = assert_obj.observation.label
            obj['event_id'] = str(assert_obj.event.uuid)
            obj['event__label'] = assert_obj.event.label
            obj['attribute_group_id'] = str(assert_obj.attribute_group.uuid)
            obj['attribute_group__label'] = assert_obj.attribute_group.label
            obj['predicate__label'] = predicate.label
            obj['predicate_id'] = str(predicate.uuid)
            obj['predicate__label'] = predicate.label
            obj['predicate__data_type'] = predicate.data_type
            obj['predicate__item_class_id'] = str(predicate.item_class.uuid)
            obj['predicate__item_class__label'] = predicate.item_class.label
            obj['predicate__uri'] = predicate.uri
            obj['predicate__context_id'] = str(predicate.context.uuid)
            obj['predicate__context__item_type'] = predicate.context.item_type
            obj['predicate__context__label'] = predicate.context.label
            obj['predicate__context__uri'] = predicate.context.uri
            obj['language_id'] = str(assert_obj.language.uuid)
            obj['language__label'] = assert_obj.language.label
            obj['sort'] = assert_obj.sort
            obj['created'] = assert_obj.created.isoformat()
            obj['updated'] = assert_obj.updated.isoformat()

        if obj in pred_objects:
            # We already have this object, so don't add it. We face this circumstance
            # when want to add objects to from different predicates that we
            # determined to be equivalent.
            continue
        pred_objects.append(obj)
    return pred_objects


def add_predicates_assertions_to_dict(
    pred_keyed_assert_objs, 
    act_dict=None, 
    add_objs_to_existing_pred=True,
    for_edit=False,
    for_html=False
):
    """Adds predicates with their grouped objects to a dictionary, keyed by each pred
    
    :param dict pred_keyed_assert_objs: A dictionary, keyed by a manifest predicate
        object that has a list of assertion objects related to that represent the
        objects of that predicate's description.
    :param dict act_dict: A dictionary that gets the predicate object list
    :param bool for_edit: Do we want an output with additional identifiers
        useful for editing.
    :param bool for_html: Do we want an output with additional attributes
        useful for HTML templating.
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
        pred_objects = make_predicate_objects_list(
            predicate,
            assert_objs, 
            for_edit=for_edit,
            for_html=for_html,
        )
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