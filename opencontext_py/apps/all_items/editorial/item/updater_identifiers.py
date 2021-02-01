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
IDENTIFIER_ATTRIBUTES_UPDATE_CONFIG = [
    ('item_id', 'Changed item association'),
    ('scheme', 'Changed identifier scheme'),
    ('rank', 'Changed rank',),
    ('id', 'Changed identifier',),
    ('meta_json', 'Changed item admministrative metadata',),
]

IDENTIFIER_ATTRIBUTES_UPDATE_ALLOWED = [a_a for a_a, _ in IDENTIFIER_ATTRIBUTES_UPDATE_CONFIG]


# The source id to use for adding new resource if not provided
DEFAULT_SOURCE_ID = 'ui-added'


def make_identifier_note_string(id_obj):
    """Makes a identifier note string """
    if not id_obj:
        return None
    note = (
        f'Identifier {id_obj.scheme} "{id_obj.id}" record {str(id_obj.uuid)} '
        f'for {id_obj.item.label}'
    )
    return note


def update_identifier_objs(request_json):
    """Updates AllIdentifier fields based on listed attributes in client request JSON"""
    errors = []
    
    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to update')
        return [], errors

    # Make a dict to look up the edit notes associated with different attributes.
    edit_note_dict = {k:v for k, v in IDENTIFIER_ATTRIBUTES_UPDATE_CONFIG}

    updated = []
    for item_update in request_json:
        uuid = item_update.get('uuid')
        if not uuid:
            errors.append('Must have "uuid" attribute.')
            continue
        id_obj = AllIdentifier.objects.filter(uuid=uuid).first()
        if not id_obj:
            errors.append(f'Cannot find identifier object for {uuid}')
            continue

        # Get the item manifest object for this identifier object. This
        # will be used for history tracking.
        man_obj = AllManifest.objects.filter(
            uuid=id_obj.item.uuid
        ).first()
    
        # Update if the item_update has attributes that we allow to update.
        update_dict = {
            k:item_update.get(k) 
            for k in IDENTIFIER_ATTRIBUTES_UPDATE_ALLOWED 
            if item_update.get(k) is not None and str(getattr(id_obj, k)) != str(item_update.get(k))
        }
        
        if not len(update_dict):
            print('Nothing to update')
            continue

         # Keep a copy of the old state before saving it.
        prior_to_edit_model_dict = updater_general.make_models_dict(item_obj=id_obj)

        edits = []
        for attr, value in update_dict.items():
            old_edited_obj = None
            new_edited_obj = None
            if attr.endswith('_id') and attr != 'source_id':
                # Get the label for the attribute that we're changing.
                edited_obj_attrib = attr.replace('_id', '')
                old_edited_obj = getattr(id_obj, edited_obj_attrib)
                new_edited_obj = AllManifest.objects.filter(uuid=value).first()

            attribute_edit_note = edit_note_dict.get(attr)
            if old_edited_obj and new_edited_obj and attribute_edit_note:
                attribute_edit_note += f' from "{old_edited_obj.label}" to "{new_edited_obj.label}"'
            
            if attribute_edit_note:
                edits.append(attribute_edit_note)
            setattr(id_obj, attr, value)

        try:
            id_obj.save()
            ok = True
        except Exception as e:
            ok = False
            if hasattr(e, 'message'):
                error = e.message
            else:
                error = str(e)
            errors.append(f'Identifier item {uuid} update error: {error}')
        if not ok:
            continue

        # Make a copy of the new state of your model.
        after_edit_model_dict = updater_general.make_models_dict(item_obj=id_obj)

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


def add_identifier_objs(request_json, source_id=DEFAULT_SOURCE_ID):
    """Add AllIdentifier and from a client request JSON"""
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
            errors.append(f'Cannot find manifest object for identifier {str(item_add)}')
            continue

        if not item_add.get('scheme'):
            errors.append(f'Must have a "scheme" for identifier {str(item_add)}')
            continue
    
        if not item_add.get('id') or not len(str(item_add.get('id'))):
            errors.append(f'Must have an "id" for identifier {str(item_add)}')
            continue

        id_obj = None
        # Update if the item_update has attributes that we allow to update.
        add_dict = {
            k:item_add.get(k) 
            for k in IDENTIFIER_ATTRIBUTES_UPDATE_ALLOWED
            if k != 'uuid' and item_add.get(k) is not None
        }

        if not len(add_dict):
            print('Nothing to add')
            continue

        if not add_dict.get('rank'):
            add_dict['rank'] = 0

        item_id_sp = AllIdentifier.objects.filter(
            item=man_obj,
            scheme=item_add.get('scheme'),
            rank=add_dict.get('rank'),
        ).first()
        if item_id_sp:
            errors.append(
                f'Item {man_obj.label} ({str(man_obj.uuid)}) already has '
                f'a rank {item_id_sp.rank} identifier '
                f'record for {item_id_sp.scheme}'
            )
            continue

        # Fill in some of the blanks that the client may not usually send
        add_dict['item_id'] = man_obj.uuid
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
            id_obj = AllResource(**add_dict)
            id_obj.uuid = id_obj.primary_key_create_for_self()
            id_obj.created = timezone.now()
            id_obj.save()
            ok = True
        except Exception as e:
            ok = False
            if hasattr(e, 'message'):
                error = e.message
            else:
                error = str(e)
            errors.append(f'Identifier item add error: {error}')
        if not ok:
            continue

        # Make a copy of the new state of your model.
        after_edit_model_dict = updater_general.make_models_dict(item_obj=id_obj)

        note = make_identifier_note_string(id_obj)
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


def delete_identifier_objs(request_json):
    """Deletes a list of identifier objects"""
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
        to_delete_id_obj = AllIdentifier.objects.filter(uuid=uuid).first()
        if not to_delete_id_obj:
            errors.append(f'Cannot find resource object for {uuid}')
            continue
        
        # Get the item manifest object for this ID object. This
        # will be used for history tracking.
        man_obj = AllManifest.objects.filter(
            uuid=to_delete_id_obj.item.uuid
        ).first()

        # Keep a copy of the old state before saving it.
        prior_to_edit_model_dict = updater_general.make_models_dict(item_obj=to_delete_id_obj)
        note = make_identifier_note_string(to_delete_id_obj)
        edit_note = (
            f'Deleted {note}'
        )
        # Delete the identifier object.
        to_delete_id_obj.delete()

        history_obj = updater_general.record_edit_history(
            man_obj,
            edit_note=edit_note,
            prior_to_edit_model_dict=prior_to_edit_model_dict,
            after_edit_model_dict={},
        )
        item_delete['history_id'] = str(history_obj.uuid)
        deleted.append(item_delete)

    return deleted, errors


