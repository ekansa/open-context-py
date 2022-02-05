
import reversion


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

from opencontext_py.apps.all_items import permissions
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
SPACETIME_ATTRIBUTES_UPDATE_CONFIG = [
    ('project_id', 'Changed item parent project',),
    ('publisher_id', 'Changed item publisher',),
    ('source_id', 'Changed item data source id',),
    ('item_id', 'Changed item association'),
    ('event_id', 'Changed event item'),
    ('feature_id', 'Changed feature number',),
    ('earliest', 'Changed earliest date',),
    ('start', 'Changed early/start date',),
    ('stop', 'Changed end/stop date',),
    ('latest', 'Changed latest date',),
    ('geometry_type', 'Changed geometry type'),
    ('latitude', 'Changed latitude'),
    ('longitude', 'Changed longitude'),
    ('geo_specificity', 'Changed location specificity'),
    ('geometry', 'Changed geometry'),
    ('meta_json', 'Changed item administrative metadata',),
]

SPACETIME_ATTRIBUTES_UPDATE_ALLOWED = [a_a for a_a, _ in SPACETIME_ATTRIBUTES_UPDATE_CONFIG]


# The source id to use for adding new spacetime if not provided
DEFAULT_SOURCE_ID = 'ui-added'

def fix_date_ranges(space_time_dict):
    """Fix date ranges in a space time dict"""
    pairs = [
        ('earliest', 'start',),
        ('start', 'earliest',),
        ('latest', 'stop',),
        ('stop', 'latest',),
    ]
    for a, b in pairs:
        if space_time_dict.get(a) and not space_time_dict.get(b):
            space_time_dict[b] = space_time_dict.get(a)
    return space_time_dict


def fix_point_geometry(space_time_dict):
    """Fix date ranges in a space time dict"""
    if not space_time_dict.get('geometry'):
        return space_time_dict
    if space_time_dict['geometry'].get('type') != 'Point':
        return space_time_dict
    if len(space_time_dict['geometry'].get('coordinates', [])) < 2:
        # We have the wrong coordinates
        return space_time_dict
      
    # Remember GeoJSON coordinate order (lon/lat)
    space_time_dict['longitude'] = float(space_time_dict['geometry']['coordinates'][0])
    space_time_dict['latitude'] = float(space_time_dict['geometry']['coordinates'][1])
    return space_time_dict


def make_spacetime_note_string(spacetime_obj):
    """Makes a spacetime note string """
    if not spacetime_obj:
        return None
    note = (
        f'Space-time {spacetime_obj.event.label} record {str(spacetime_obj.uuid)}'
    )
    if spacetime_obj.start is not None:
        note += f' Time: {spacetime_obj.earliest} to {spacetime_obj.latest}'
    if spacetime_obj.geometry_type is not None:
        note += (
            f'; a {spacetime_obj.geometry_type} at '
            f'Lat: {spacetime_obj.latitude}, Lon: {spacetime_obj.longitude}'
        )
    return note


def update_spacetime_objs(request_json, request=None):
    """Updates AllSpaceTime fields based on listed attributes in client request JSON"""
    errors = []
    
    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to update')
        return [], errors

    # Make a dict to look up the edit notes associated with different attributes.
    edit_note_dict = {k:v for k, v in SPACETIME_ATTRIBUTES_UPDATE_CONFIG}

    updated = []
    for item_update in request_json:
        uuid = item_update.get('uuid')
        if not uuid:
            errors.append('Must have "uuid" attribute.')
            continue
        spt_obj = AllSpaceTime.objects.filter(uuid=uuid).first()
        if not spt_obj:
            errors.append(f'Cannot find spacetime object for {uuid}')
            continue

        # Get the item manifest object for this spacetime object. This
        # will be used for history tracking.
        man_obj = AllManifest.objects.filter(
            uuid=spt_obj.item.uuid
        ).first()
        
        _, ok_edit = permissions.get_request_user_permissions(
            request, 
            man_obj, 
            null_request_ok=True
        )
        if not ok_edit:
            errors.append(f'Need permission to edit manifest object {man_obj}')
            continue
    
        # Update if the item_update has attributes that we allow to update.
        update_dict = {
            k:item_update.get(k) 
            for k in SPACETIME_ATTRIBUTES_UPDATE_ALLOWED  
            if item_update.get(k) is not None and str(getattr(spt_obj, k)) != str(item_update.get(k))
        }
        
        if not len(update_dict):
            print('Nothing to update')
            continue

        # Make sure date information is fully set.
        update_dict = fix_date_ranges(update_dict)
        # Update lat/lon if a point geometry object was provided
        update_dict = fix_point_geometry(update_dict)

         # Keep a copy of the old state before saving it.
        prior_to_edit_model_dict = updater_general.make_models_dict(item_obj=spt_obj)

        edits = []
        for attr, value in update_dict.items():
            if attr == 'event_id' and value is False:
                # We're removing an item class, so set it back to the default
                value = configs.DEFAULT_EVENT_UUID

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
            setattr(spt_obj, attr, value)

        try:
            spt_obj.save()
            ok = True
        except Exception as e:
            ok = False
            if hasattr(e, 'message'):
                error = e.message
            else:
                error = str(e)
            errors.append(f'Spacetime item {uuid} update error: {error}')
        if not ok:
            continue

        # Make a copy of the new state of your model.
        after_edit_model_dict = updater_general.make_models_dict(item_obj=spt_obj)

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



def add_spacetime_objs(request_json, request=None, source_id=DEFAULT_SOURCE_ID):
    """Add AllSpaceTime and from a client request JSON"""
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
            errors.append(f'Cannot find manifest object for location/chronology {str(item_add)}')
            continue

        _, ok_edit = permissions.get_request_user_permissions(
            request, 
            man_obj, 
            null_request_ok=True
        )
        if not ok_edit:
            errors.append(f'Need permission to edit manifest object {man_obj}')
            continue

        # Update if the item_update has attributes that we allow to update.
        add_dict = {
            k:item_add.get(k) 
            for k in SPACETIME_ATTRIBUTES_UPDATE_ALLOWED
            if k != 'uuid' and item_add.get(k) is not None
        }

        if not add_dict.get('event_id'):
            add_dict['event_id'] = configs.DEFAULT_EVENT_UUID
        
        item_event_sp = AllSpaceTime.objects.filter(
            item=man_obj,
            event_id=add_dict.get('event_id'),
        ).first()
        if item_event_sp:
            errors.append(
                f'Item {man_obj.label} ({str(man_obj.uuid)}) already has a location/chronology '
                f'record for {item_event_sp.event.label} ({str(item_event_sp.event.uuid)})'
            )
            continue

        if not len(add_dict):
            print('Nothing to update')
            continue

        # Make sure date information is fully set.
        add_dict = fix_date_ranges(add_dict)
        # Update lat/lon if a point geometry object was provided
        add_dict = fix_point_geometry(add_dict)

        # Fill in some of the blanks that the client may not usually send
        add_dict['item_id'] = man_obj.uuid
        if not add_dict.get('project_id'):
            add_dict['project_id'] = man_obj.project.uuid
        if not add_dict.get('publisher_id'):
            add_dict['publisher_id'] = man_obj.publisher.uuid
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
            spacetime_obj = AllSpaceTime(**add_dict)
            spacetime_obj.uuid = spacetime_obj.primary_key_create_for_self()
            spacetime_obj.validate_times_for_self()
            spacetime_obj.created = timezone.now()
            spacetime_obj.save()
            ok = True
        except Exception as e:
            ok = False
            if hasattr(e, 'message'):
                error = e.message
            else:
                error = str(e)
            errors.append(f'Spacetime item add error: {error}')
        if not ok:
            continue

        # Make a copy of the new state of your model.
        after_edit_model_dict = updater_general.make_models_dict(item_obj=spacetime_obj)

        sp_note = make_spacetime_note_string(spacetime_obj)
        edit_note = (
            f'Added {sp_note}'
        )

        history_obj = updater_general.record_edit_history(
            man_obj,
            edit_note=edit_note,
            prior_to_edit_model_dict={},
            after_edit_model_dict=after_edit_model_dict,
        )
        item_add['history_id'] = str(history_obj.uuid)
        item_add['uuid'] = str(spacetime_obj.uuid)
        added.append(item_add)

    return added, errors


def delete_spacetime_objs(request_json, request=None):
    """Deletes a list of spacetime objects"""
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
        to_delete_spt_obj = AllSpaceTime.objects.filter(uuid=uuid).first()
        if not to_delete_spt_obj:
            errors.append(f'Cannot find spacetime object for {uuid}')
            continue
        
        # Get the item manifest object for this spacetime object. This
        # will be used for history tracking.
        man_obj = AllManifest.objects.filter(
            uuid=to_delete_spt_obj.item.uuid
        ).first()

        _, ok_edit = permissions.get_request_user_permissions(
            request, 
            man_obj, 
            null_request_ok=True
        )
        if not ok_edit:
            errors.append(f'Need permission to edit manifest object {man_obj}')
            continue

        # Keep a copy of the old state before saving it.
        prior_to_edit_model_dict = updater_general.make_models_dict(item_obj=to_delete_spt_obj)
        sp_note = make_spacetime_note_string(to_delete_spt_obj)
        edit_note = (
            f'Deleted {sp_note}'
        )
         # Delete the spacetime object.
        to_delete_spt_obj.delete()

        history_obj = updater_general.record_edit_history(
            man_obj,
            edit_note=edit_note,
            prior_to_edit_model_dict=prior_to_edit_model_dict,
            after_edit_model_dict={},
        )
        item_delete['history_id'] = str(history_obj.uuid)
        deleted.append(item_delete)

    return deleted, errors


