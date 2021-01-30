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
RESOURCE_ATTRIBUTES_UPDATE_CONFIG = [
    ('project_id', 'Changed item parent project',),
    ('source_id', 'Changed item data source id',),
    ('item_id', 'Changed item association'),
    ('resourcetype_id', 'Changed resource type'),
    ('mediatype_id', 'Changed media type',),
    ('uri', 'Changed file URI',),
    ('filesize', 'Changed file size',),
    ('rank', 'Changed rank',),
    ('is_static', 'Changed static',),
    ('meta_json', 'Changed item admministrative metadata',),
]

RESOURCE_ATTRIBUTES_UPDATE_ALLOWED = [a_a for a_a, _ in RESOURCE_ATTRIBUTES_UPDATE_CONFIG]


# The source id to use for adding new resource if not provided
DEFAULT_SOURCE_ID = 'ui-added'


def make_resource_note_string(resource_obj):
    """Makes a resource note string """
    if not resource_obj:
        return None
    note = (
        f'Resource {resource_obj.resourcetype.label} record {str(resource_obj.uuid)} '
        f'at {resource_obj.uri}'
    )
    return note


def update_resource_fields(request_json):
    """Updates AllResource fields based on listed attributes in client request JSON"""
    errors = []
    
    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to update')
        return [], errors

    # Make a dict to look up the edit notes associated with different attributes.
    edit_note_dict = {k:v for k, v in RESOURCE_ATTRIBUTES_UPDATE_CONFIG}

    updated = []
    for item_update in request_json:
        uuid = item_update.get('uuid')
        if not uuid:
            errors.append('Must have "uuid" attribute.')
            continue
        resource_obj = AllResource.objects.filter(uuid=uuid).first()
        if not resource_obj:
            errors.append(f'Cannot find resource object for {uuid}')
            continue

        # Get the item manifest object for this resource object. This
        # will be used for history tracking.
        man_obj = AllManifest.objects.filter(
            uuid=resource_obj.item.uuid
        ).first()
    
        # Update if the item_update has attributes that we allow to update.
        update_dict = {
            k:item_update.get(k) 
            for k in RESOURCE_ATTRIBUTES_UPDATE_ALLOWED 
            if item_update.get(k) is not None and str(getattr(resource_obj, k)) != str(item_update.get(k))
        }
        
        if not len(update_dict):
            print('Nothing to update')
            continue

         # Keep a copy of the old state before saving it.
        prior_to_edit_model_dict = updater_general.make_models_dict(item_obj=resource_obj)

        edits = []
        for attr, value in update_dict.items():
            old_edited_obj = None
            new_edited_obj = None
            if attr.endswith('_id') and attr != 'source_id':
                # Get the label for the attribute that we're changing.
                edited_obj_attrib = attr.replace('_id', '')
                old_edited_obj = getattr(spt_obj, edited_obj_attrib)
                new_edited_obj = AllManifest.objects.filter(uuid=value).first()

            attribute_edit_note = edit_note_dict.get(attr)
            if old_edited_obj and new_edited_obj and attribute_edit_note:
                attribute_edit_note += f' from "{old_edited_obj.label}" to "{new_edited_obj.label}"'
            
            if attribute_edit_note:
                edits.append(attribute_edit_note)
            setattr(resource_obj, attr, value)

        try:
            resource_obj.save()
            ok = True
        except Exception as e:
            ok = False
            if hasattr(e, 'message'):
                error = e.message
            else:
                error = str(e)
            errors.append(f'Resource item {uuid} update error: {error}')
        if not ok:
            continue

        # Make a copy of the new state of your model.
        after_edit_model_dict = updater_general.make_models_dict(item_obj=resource_obj)

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


def add_resource_objs(request_json, source_id=DEFAULT_SOURCE_ID):
    """Add AllResource and from a client request JSON"""
    errors = []
    
    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to update')
        return [], errors

    added = []
    for item_add in request_json:
        man_obj = None
        if item_add.get('item_id'):
            man_obj = AllManifest.objects.filter(
                uuid=item_add.get('item_id')
            ).first()

        if not man_obj:
            errors.append(f'Cannot find manifest object for resource {str(item_add)}')
            continue
        
        resource_obj = None
        if item_add.get('resourcetype_id'):
            resource_obj = AllManifest.objects.filter(
                uuid=item_add.get('resourcetype_id')
            ).first()
        
        if not resource_obj:
            errors.append(f'Cannot find resource-type object for resource {str(item_add)}')
            continue

        # Update if the item_update has attributes that we allow to update.
        add_dict = {
            k:item_add.get(k) 
            for k in RESOURCE_ATTRIBUTES_UPDATE_ALLOWED
            if k != 'uuid' and item_add.get(k) is not None
        }

        if not len(add_dict):
            print('Nothing to add')
            continue

        if not add_dict.get('rank'):
            add_dict['rank'] = 0

        item_resource_sp = AllResource.objects.filter(
            item=man_obj,
            resourcetype=resource_obj,
            rank=add_dict.get('rank'),
        ).first()
        if item_resource_sp:
            errors.append(
                f'Item {man_obj.label} ({str(man_obj.uuid)}) already has '
                f'a rank {item_resource_sp.rank} resource '
                f'record for {resource_obj.label} ({str(resource_obj.uuid)})'
            )
            continue

        # Fill in some of the blanks that the client may not usually send
        add_dict['item_id'] = man_obj.uuid
        if not add_dict.get('project_id'):
            add_dict['project_id'] = man_obj.project.uuid
        if not add_dict.get('source_id'):
            add_dict['source_id'] = source_id
        if not add_dict.get('meta_json'):
            add_dict['meta_json'] = {}

        for attr, value in add_dict.items():
    
            if not attr.endswith('_id'):
                continue
        
            if attr == 'source_id':
                # Skip this, it's not meant to be a manifest object.
                continue
            
            # Get the label for the attribute that we're changing.
            ref_obj = AllManifest.objects.filter(uuid=value).first()
            if ref_obj:
                continue
            error = f'Cannot find {attr} object {value}'
            errors.append(error)

        try:
            resource_obj = AllResource(**add_dict)
            resource_obj.uri = AllManifest().clean_uri(resource_obj.uri)
            resource_obj.uuid = resource_obj.primary_key_create_for_self()
            resource_obj.created = timezone.now()
            resource_obj.save()
            ok = True
        except Exception as e:
            ok = False
            if hasattr(e, 'message'):
                error = e.message
            else:
                error = str(e)
            errors.append(f'Resource item add error: {error}')
        if not ok:
            continue

        # Make a copy of the new state of your model.
        after_edit_model_dict = updater_general.make_models_dict(item_obj=resource_obj)

        note = make_resource_note_string(resource_obj)
        edit_note = (
            f'Added {note}'
        )

        history_obj = updater_general.record_edit_history(
            man_obj,
            edit_note=edit_note,
            prior_to_edit_model_dict={},
            after_edit_model_dict=after_edit_model_dict,
        )
        item_add['history_id'] = str(history_obj.uuid)
        item_add['uuid'] = str(resource_obj.uuid)
        added.append(item_add)

    return added, errors


def delete_resource_objs(request_json):
    """Deletes a list of resource objects"""
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
        to_delete_res_obj = AllResource.objects.filter(uuid=uuid).first()
        if not to_delete_res_obj:
            errors.append(f'Cannot find resource object for {uuid}')
            continue
        
        # Get the item manifest object for this resource object. This
        # will be used for history tracking.
        man_obj = AllManifest.objects.filter(
            uuid=to_delete_res_obj.item.uuid
        ).first()

        # Keep a copy of the old state before saving it.
        prior_to_edit_model_dict = updater_general.make_models_dict(item_obj=to_delete_res_obj)
        note = make_resource_note_string(to_delete_res_obj)
        edit_note = (
            f'Deleted {note}'
        )
         # Delete the resource object.
        to_delete_res_obj.delete()

        history_obj = updater_general.record_edit_history(
            man_obj,
            edit_note=edit_note,
            prior_to_edit_model_dict=prior_to_edit_model_dict,
            after_edit_model_dict={},
        )
        item_delete['history_id'] = str(history_obj.uuid)
        deleted.append(item_delete)

    return deleted, errors


