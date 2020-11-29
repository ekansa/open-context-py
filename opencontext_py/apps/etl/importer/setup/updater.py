import json
import uuid as GenUUID
from django.conf import settings

from django.db.models import Q

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items.legacy_all import update_old_id

from opencontext_py.apps.etl.importer.models import (
    DataSource,
    DataSourceField,
    DataSourceRecord,
    DataSourceAnnotation,
)



# This lists DataSourceField attributes that we allow users to update in setting
# up an ETL process.
DS_FIELDS_UPDATE_ALLOWED = [
    'label',
    'item_type',
    'data_type',
    'item_class_id',
    'context_id',
    'value_prefix',
]



def update_fields(request_json):
    """Updates ds_fields based on listed attributes in client request JSON"""
    updated = []
    errors = []
    for item_update in request_json:
        uuid = item_update.get('uuid')
        if not uuid:
            errors.append('Must have "uuid" attribute.')
            continue

        ds_field =  DataSourceField.objects.filter(uuid=uuid).first()
        orig_item_type = ds_field.item_type

        if not ds_field:
            errors.append(f'Cannot find ds_field for {uuid}')
            continue

        # Update if the item_update has attributes that we allow to update.
        update_dict = {
            k:item_update.get(k) 
            for k in DS_FIELDS_UPDATE_ALLOWED if item_update.get(k) is not None
        }

        if not update_dict:
            errors.append(f'Field {uuid}: no attribute allowed for update specified.')
            continue

        for attr, value in update_dict.items():
            if attr == 'item_class_id' and value is False:
                # We're removing an item class, so set it back to the default
                value = configs.DEFAULT_CLASS_UUID
            elif attr == 'context_id' and value is False:
                # We're removing a context, so set it to None.
                value = None
            setattr(ds_field, attr, value)
        
        if orig_item_type != ds_field.item_type:
            # We're changing item_types, which means we should reset other attributes.
            ds_field.data_type = None
            ds_field.item_class_id = configs.DEFAULT_CLASS_UUID
            ds_field.context = None

        try:
            ds_field.save()
            ok = True
        except Exception as e:
            ok = False
            if hasattr(e, 'message'):
                error = e.message
            else:
                error = str(e)
            errors.append(f'Field {uuid} update error: {error}')
        if not ok:
            continue
        update_dict['uuid'] = uuid
        updated.append(update_dict)
    return updated, errors





