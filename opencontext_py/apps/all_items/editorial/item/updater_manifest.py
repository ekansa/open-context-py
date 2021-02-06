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
from opencontext_py.apps.all_items.editorial.item import updater_general

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
    ('meta_json', 'Changed item administrative metadata',),
]

MANIFEST_ATTRIBUTES_UPDATE_ALLOWED = [m_a for m_a, _ in MANIFEST_ATTRIBUTES_UPDATE_CONFIG]



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
        # Skip out. not a subjects item.
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


def update_manifest_objs(request_json):
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
            
        # Keep a copy of the old state before saving it.
        prior_to_edit_model_dict = updater_general.make_models_dict(item_obj=man_obj)

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
            if attr.endswith('_id') and attr != 'source_id':
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
        after_edit_model_dict = updater_general.make_models_dict(item_obj=man_obj)

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
                after_edit_model_dict = updater_general.make_models_dict(
                    models_dict=after_edit_model_dict,
                    item_obj=new_contain
                )
            if old_contain:
                prior_to_edit_model_dict = updater_general.make_models_dict(
                    models_dict=prior_to_edit_model_dict,
                    item_obj=old_contain
                )
        
        edit_note = "; ".join(edits)

        history_obj = updater_general.record_edit_history(
            man_obj,
            edit_note=edit_note,
            prior_to_edit_model_dict=prior_to_edit_model_dict,
            after_edit_model_dict=after_edit_model_dict,
        )
        update_dict['history_id'] = str(history_obj.uuid)
        update_dict['uuid'] = uuid
        updated.append(update_dict)

    return updated, errors


def delete_manifest_obj(to_delete_man_obj, context_recursive=False, deleted=None, errors=None):
    """Deletes a manifest object, optionally recursively for items that use it as context"""
    if deleted == None:
        deleted = []
    if errors == None:
        errors = []
    context_qs = AllManifest.objects.filter(
        context=to_delete_man_obj
    )
    if not context_recursive and len(context_qs):
        errors.append(
            f'Not recursively deleting, but manifest obj {to_delete_man_obj.label} ({str(to_delete_man_obj.uuid)}) '
            f'is a context for {len(context_qs)} items'
        )
        return deleted, errors
    if context_recursive and len(context_qs):
        for item_in_context in context_qs:
            deleted, errors = delete_manifest_obj(
                to_delete_man_obj=item_in_context, 
                context_recursive=context_recursive, 
                deleted=deleted, 
                errors=errors
            )
    
    if len(errors):
        # Stop if there was a problem in deleting child items.
        return deleted, errors

    project_obj = AllManifest.objects.get(uuid=to_delete_man_obj.project.uuid)
    # Keep a copy of the old state before saving it.
    prior_to_edit_model_dict = updater_general.make_models_dict(item_obj=to_delete_man_obj)

    # Get querysets for objects related to / associated with the item we
    # are deleting.
    qs_list = []
    qs_list.append(
        AllAssertion.objects.filter(
            Q(subject=to_delete_man_obj)
            | Q(observation=to_delete_man_obj)
            | Q(event=to_delete_man_obj)
            | Q(attribute_group=to_delete_man_obj)
            | Q(predicate=to_delete_man_obj)
            | Q(object=to_delete_man_obj)
        )
    )
    qs_list.append(
        AllSpaceTime.objects.filter(
            Q(item=to_delete_man_obj)
            | Q(event=to_delete_man_obj)
        )
    )
    qs_list.append(
        AllResource.objects.filter(item=to_delete_man_obj)
    )
    qs_list.append(
        AllIdentifier.objects.filter(item=to_delete_man_obj)
    )
    qs_list.append(
        AllHistory.objects.filter(item=to_delete_man_obj)
    )
    total_objects = 0
    for qs in qs_list:
        # Add all the objects from all the querysets associated with this
        # item.
        total_objects += len(qs)
        prior_to_edit_model_dict = updater_general.add_queryset_objs_to_models_dict(
            prior_to_edit_model_dict, 
            qs
        )
        # Delete all the items in these query sets.
        qs.delete()

    edit_note = (
        f'Deleted item: {to_delete_man_obj.label} ({str(to_delete_man_obj.uuid)}) '
        f'and {total_objects} associated records.'
    )
    # Save the edit note to the meta_json for the project. This makes sure the
    # hash updates for the project so we can save the history of the edit.
    project_obj.meta_json.setdefault('deleted', [])
    project_obj.meta_json['deleted'].append(edit_note)
    project_obj.save()

    delete_uuid = str(to_delete_man_obj.uuid)

    # Now do the actual delete of the item we want to delete.
    to_delete_man_obj.delete()

    history_obj = updater_general.record_edit_history(
        project_obj,
        edit_note=edit_note,
        prior_to_edit_model_dict=prior_to_edit_model_dict,
        after_edit_model_dict={},
    )
    delete_dict = {
        'history_id': str(history_obj.uuid),
        'deleted_id': delete_uuid,
    }
    deleted.append(delete_dict)
    return deleted, errors


def delete_manifest_objs(request_json):
    """Deletes a list of manifest objects"""
    errors = []
    deleted = []
    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to update')
        return deleted, errors

    for item_delete in request_json:
        uuid = item_delete.get('uuid')
        if not uuid:
            errors.append('Must have "uuid" attribute.')
            continue
        to_delete_man_obj = AllManifest.objects.filter(uuid=uuid).first()
        if not to_delete_man_obj:
            errors.append(f'Cannot find manifest object for {uuid}')
            continue
        deleted, errors = delete_manifest_obj(
            to_delete_man_obj=to_delete_man_obj, 
            context_recursive=item_delete.get('context_recursive', False), 
            deleted=deleted, 
            errors=errors,
        )
    return deleted, errors


