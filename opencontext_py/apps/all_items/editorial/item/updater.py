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

from opencontext_py.libs.models import (
    make_dict_json_safe, 
    make_model_object_json_safe_dict
)


#----------------------------------------------------------------------
# NOTE: These are methods for handling requests to change individual 
# items.
# ---------------------------------------------------------------------
MANIFEST_ATTRIBUTES_UPDATE_CONFIG = [
    ('label', 'Changed item label',),
    ('data_type', 'Changed item data-type',),
    ('item_class_id', 'Changed item classification',),
    ('context_id', 'Changed item context',),
    ('project_id', 'Changed item parent project',),
    ('publisher_id', 'Changed item publisher',),
    ('item_key', 'Changed item key identifier',),
    ('source_id', 'Changed item data source id',),
    ('meta_json', 'Changed item admministrative metadata',),
]

MANIFEST_ATTRIBUTES_UPDATE_ALLOWED = [m_a for m_a, _ in MANIFEST_ATTRIBUTES_UPDATE_CONFIG]

ASSERTION_ATTRIBUTES_UPDATE_CONFIG = [
    ('project_id', 'Changed assertion project',),
    ('publisher_id', 'Changed assertion publisher',),
    ('subject_id', 'Changed item attribute or relationships',),
    ('observation_id', 'Changed observation group',),
    ('event_id', 'Changed geospatial/chronology specific description',),
    ('attribute_group_id', 'Changed attribute group',),
    ('predicate_id', 'Changed attribute/relationship predicate',),
    ('language_id', 'Changed assertion language',),
    ('sort', 'Changed assertion sorting',),
    ('visible', 'Changed assertion visibility',),
    ('certainty', 'Changed assertion certainty',),
    ('object_id', 'Changed attribute/relationship object item',),
    ('obj_string', 'Changed attribute value',),
    ('obj_boolean', 'Changed attribute value',),
    ('obj_integer', 'Changed attribute value',),
    ('obj_double', 'Changed attribute value',),
    ('obj_datetime', 'Changed attribute value',),
    ('meta_json', 'Changed assertion admministrative metadata',),
]

ASSERTION_DEFAULT_NODE_IDS = {
    'observation_id': configs.DEFAULT_OBS_UUID,
    'event_id': configs.DEFAULT_EVENT_UUID,
    'attribute_group_id': configs.DEFAULT_ATTRIBUTE_GROUP_UUID,
    'language_id':  configs.DEFAULT_LANG_UUID,
}

ASSERTION_ATTRIBUTES_UPDATE_ALLOWED = [
    a_a 
    for a_a, _ in ASSERTION_ATTRIBUTES_UPDATE_CONFIG
]

def make_models_dict(models_dict=None, item_obj=None, obj_qs=None):
    """Makes an edit history dict, keyed by the model label"""
    if not item_obj and not obj_qs:
        return None
    if not models_dict:
        models_dict = {}
    items = []
    if item_obj:
        items.append(item_obj)
    if obj_qs:
        items += [m for m in obj_qs]
    for act_model in items:
        models_dict.setdefault(act_model._meta.label, [])
        models_dict[act_model._meta.label].append(
            make_model_object_json_safe_dict(act_model)
        )
    return models_dict


def create_edit_history_meta_json(
    edit_note,
    edit_dict=None,
    prior_to_edit_model_objs=None,
    prior_to_edit_model_dict=None,
    after_edit_model_objs=None,
    after_edit_model_dict=None,
):
    """Adds an edit history item to the meta_json of an object"""
    if not edit_dict:
        edit_dict = {}
    
    edit_dict['edit_note'] = edit_note
    edit_dict['edit_time'] = timezone.now().isoformat()

    if not prior_to_edit_model_dict and prior_to_edit_model_objs:
        prior_to_edit_model_dict = {}

    if prior_to_edit_model_objs:
        prior_to_edit_model_dict = make_models_dict(
            models_dict=prior_to_edit_model_dict, 
            obj_qs=prior_to_edit_model_objs
        )

    if not after_edit_model_dict and after_edit_model_objs:
        after_edit_model_dict = {}
    
    if after_edit_model_objs:
        after_edit_model_dict = make_models_dict(
            models_dict=after_edit_model_dict, 
            obj_qs=after_edit_model_objs
        )

    if not prior_to_edit_model_dict or not after_edit_model_dict:
        return None

    edit_dict['prior_to_edit'] = prior_to_edit_model_dict
    edit_dict['after_edit'] = after_edit_model_dict
    return edit_dict


def record_edit_history(
    man_obj,
    edit_note,
    edit_dict=None,
    prior_to_edit_model_objs=None,
    prior_to_edit_model_dict=None,
    after_edit_model_objs=None,
    after_edit_model_dict=None,
):
    """Records edit history of a man_obj item"""

    # NOTE: This a record of the history of an edit. The prior state
    # and after edit states are saved in the meta_json of the history object.
    edit_dict = create_edit_history_meta_json(
        edit_note,
        edit_dict=edit_dict,
        prior_to_edit_model_objs=prior_to_edit_model_objs,
        prior_to_edit_model_dict=prior_to_edit_model_dict,
        after_edit_model_objs=after_edit_model_objs,
        after_edit_model_dict=after_edit_model_dict,
    )
    history_obj = AllHistory()
    history_obj.item = man_obj
    history_obj.meta_json = edit_dict
    history_obj.save()
    return history_obj


def validate_label(man_obj, new_label):
    """Validates that a new label is unique in a context"""
    if new_label == man_obj.label:
        # No change, so assume this is valid.
        return True, None
    if not len(new_label):
        return False, f'The label {new_label} cannot be blank'
    check_qs = AllManifest.objects.filter(
        context=man_obj.context,
        item_type=man_obj.item_type,
        item_class=man_obj.item_class,
        data_type=man_obj.data_type,
        label=new_label,
    ).exclude(
        uuid=man_obj.uuid
    ).first()
    if check_qs:
        # new_label is already in use, so it is NOT valid within
        # this context.
        return False, f'The label {new_label} is already in use in this context'
    return True, None


def recursive_subjects_path_update(man_obj):
    """Updates the path attribute of manifest item_type subjects after label changes"""
    if man_obj.item_type != 'subjects':
        # Skip out. ot a subjects item.
        return None

    man_children = AllManifest.objects.filter(
        context=man_obj
    ).exclude(uuid=man_obj.uuid)
    for child_obj in man_children:
        # NOTE: the method save should automatically:
        # make_subjects_path_and_validate()
        child_obj.save()
        # Now go down to the next level and update those paths.
        recursive_subjects_path_update(child_obj)


def update_subjects_context_containment_assertion(man_obj):
    """Updates the context containment assertion for a  manifest item_type subjects item"""
    parent_context = man_obj.context
    old_contain = AllAssertion.objects.filter(
        predicate_id=configs.PREDICATE_CONTAINS_UUID,
        object=man_obj,
    ).exclude(
        subject=parent_context
    ).first()
    if old_contain:
        # Copy the old containment assertion and change the parent.
        new_contain = copy.deepcopy(old_contain)
        new_contain.uuid = None
        new_contain.pk = None
        new_contain.subject = parent_context
        old_contain.delete()
        new_contain.save()
        return new_contain, old_contain

    assert_dict = {
        'uuid': AllAssertion().primary_key_create(
            subject_id=man_obj.context.uuid,
            predicate_id=configs.PREDICATE_CONTAINS_UUID,
            object_id=man_obj.uuid,
        ),
        'project': man_obj.project,
        'publisher': man_obj.publisher,
        'source_id':man_obj.source_id,
        'subject': man_obj.context,
        'predicate_id': configs.PREDICATE_CONTAINS_UUID,
        'object': man_obj,
        'meta_json': {},
    }
    assert_obj = AllAssertion(**assert_dict)
    assert_obj.save()
    return assert_obj, None


def update_manifest_fields(request_json):
    """Updates AllManifest fields based on listed attributes in client request JSON"""
    errors = []
    
    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to update')
        return [], errors

    # Make a dict to look up the edit notes associated with different attributes.
    edit_note_dict = {k:v for k, v in MANIFEST_ATTRIBUTES_UPDATE_CONFIG}

    updated = []
    for item_update in request_json:
        uuid = item_update.get('uuid')
        if not uuid:
            errors.append('Must have "uuid" attribute.')
            continue
        man_obj = AllManifest.objects.filter(uuid=uuid).first()
        if not man_obj:
            errors.append(f'Cannot find manifest object for {uuid}')
            continue
    
        # Update if the item_update has attributes that we allow to update.
        update_dict = {
            k:item_update.get(k) 
            for k in MANIFEST_ATTRIBUTES_UPDATE_ALLOWED  
            if item_update.get(k) is not None and str(getattr(man_obj, k)) != str(item_update.get(k))
        }
        
        if not len(update_dict):
            print('Nothing to update')
            continue
        
        if update_dict.get('label'):
            label_valid, error_message = validate_label(man_obj, update_dict['label'])
            if not label_valid:
                errors.append(error_message)
                continue
            
        edits = []
        for attr, value in update_dict.items():
            if attr == 'item_class_id' and value is False:
                # We're removing an item class, so set it back to the default
                value = configs.DEFAULT_CLASS_UUID
            elif attr == 'context_id' and value is False:
                # We're removing a context, so set it to the item's project.
                value = man_obj.project

            old_edited_obj = None
            new_edited_obj = None
            if attr.endswith('_id'):
                # Get the label for the attribute that we're changing.
                edited_obj_attrib = attr.replace('_id', '')
                old_edited_obj = getattr(man_obj, edited_obj_attrib)
                new_edited_obj = AllManifest.objects.filter(uuid=value).last()

            attribute_edit_note = edit_note_dict.get(attr)
            if old_edited_obj and new_edited_obj and attribute_edit_note:
                attribute_edit_note += f' from "{old_edited_obj.label}" to "{new_edited_obj.label}"'
            
            if attribute_edit_note:
                edits.append(attribute_edit_note)
            setattr(man_obj, attr, value)

        # Keep a copy of the old state before saving it.
        prior_to_edit_model_dict = make_models_dict(item_obj=man_obj)

        try:
            man_obj.save()
            ok = True
        except Exception as e:
            ok = False
            if hasattr(e, 'message'):
                error = e.message
            else:
                error = str(e)
            errors.append(f'Manifest item {uuid} update error: {error}')
        if not ok:
            continue

        # Make a copy of the new state of your model.
        after_edit_model_dict = make_models_dict(item_obj=man_obj)

        if update_dict.get('label') and man_obj.item_type == 'subjects':
            # We updated a label for a subjects item, so now update the path for all the
            # item children recursively.
            recursive_subjects_path_update(man_obj)
        
        if update_dict.get('context_id') and man_obj.item_type == 'subjects':
            # We updated the context for a subjects item, so now update the path for all the
            # item children recursively.
            new_contain, old_contain = update_subjects_context_containment_assertion(man_obj)
            recursive_subjects_path_update(man_obj)
            if new_contain:
                after_edit_model_dict = make_models_dict(
                    models_dict=after_edit_model_dict,
                    item_obj=new_contain
                )
            if old_contain:
                prior_to_edit_model_dict = make_models_dict(
                    models_dict=prior_to_edit_model_dict,
                    item_obj=old_contain
                )
        
        edit_note = "; ".join(edits)

        history_obj = record_edit_history(
            man_obj,
            edit_note=edit_note,
            prior_to_edit_model_dict=prior_to_edit_model_dict,
            after_edit_model_dict=after_edit_model_dict,
        )
        update_dict['history_id'] = str(history_obj.uuid)
        update_dict['uuid'] = uuid
        updated.append(update_dict)

    return updated, errors


def update_attribute_fields(request_json):
    """Updates AllManifest fields based on listed attributes in client request JSON"""
    errors = []
    
    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to update')
        return [], errors

    # Make a dict to look up the edit notes associated with different attributes.
    edit_note_dict = {k:v for k, v in ASSERTION_ATTRIBUTES_UPDATE_CONFIG}

    updated = []
    for item_update in request_json:
        uuid = item_update.get('uuid')
        if not uuid:
            errors.append('Must have "uuid" attribute.')
            continue
        assert_obj = AllAssertion.objects.filter(uuid=uuid).first()
        if not assert_obj:
            errors.append(f'Cannot find assertion object for {uuid}')
            continue

        # Update if the item_update has attributes that we allow to update.
        update_dict = {
            k:item_update.get(k) 
            for k in ASSERTION_ATTRIBUTES_UPDATE_ALLOWED
            if item_update.get(k) is not None and str(getattr(assert_obj, k)) != str(item_update.get(k))
        }
        
        if not len(update_dict):
            print('Nothing to update')
            continue

        # Make a copy for editing purposes.
        update_assert_obj = copy.deepcopy(assert_obj)
        update_assert_obj.uuid = None
        update_assert_obj.pk = None

        edits = []
        for attr, value in update_dict.items():
            if value is False and ASSERTION_DEFAULT_NODE_IDS.get(attr):
                # We're removing an an assertion node, so set it back to the default
                value = ASSERTION_DEFAULT_NODE_IDS.get(attr)

            old_edited_obj = None
            new_edited_obj = None
            if attr.endswith('_id'):
                # Get the label for the attribute that we're changing.
                edited_obj_attrib = attr.replace('_id', '')
                old_edited_obj = getattr(update_assert_obj, edited_obj_attrib)
                new_edited_obj = AllManifest.objects.filter(uuid=value).first()
            else:
                old_value = getattr(update_assert_obj, attr)

            # Compose a note about the edit.
            attribute_edit_note = edit_note_dict.get(attr)
            if attribute_edit_note and attr.startswith('obj'):
                attribute_edit_note += f', "{update_assert_obj.predicate.label}",'
                if not attr.endswith('_id'):
                    attribute_edit_note += f' from {old_value} to {value}'
            if old_edited_obj and new_edited_obj and attribute_edit_note:
                attribute_edit_note += f' from "{old_edited_obj.label}" to "{new_edited_obj.label}"'
            
            if attribute_edit_note:
                edits.append(attribute_edit_note)
            setattr(update_assert_obj, attr, value)


        # Keep a copy of the old state before saving it.
        prior_to_edit_model_dict = make_models_dict(item_obj=assert_obj)

        try:
            update_assert_obj.save()
            ok = True
        except Exception as e:
            ok = False
            if hasattr(e, 'message'):
                error = e.message
            else:
                error = str(e)
            errors.append(f'Assertion item {uuid} update error: {error}')
        if not ok:
            continue

        # Get the subject of the assertion's manifest object. This
        # will be used for history tracking.
        man_obj = AllManifest.objects.filter(
            uuid=assert_obj.subject.uuid
        ).first()
        # Delete the assertion that we just changed. The UUID will be different.
        assert_obj.delete()

        # Make a copy of the new state of your model.
        after_edit_model_dict = make_models_dict(item_obj=update_assert_obj)

        edit_note = "; ".join(edits)

        history_obj = record_edit_history(
            man_obj,
            edit_note=edit_note,
            prior_to_edit_model_dict=prior_to_edit_model_dict,
            after_edit_model_dict=after_edit_model_dict,
        )
        update_dict['history_id'] = str(history_obj.uuid)
        update_dict['uuid'] = uuid
        updated.append(update_dict)

    return updated, errors