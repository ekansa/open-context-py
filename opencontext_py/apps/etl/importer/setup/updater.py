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
        # Update if the item_update has attributes that we allow to update.
        update_dict = {
            k:item_update.get(k) 
            for k in DS_FIELDS_UPDATE_ALLOWED if item_update.get(k)
        }
        if not update_dict:
            errors.append(f'Field {uuid}: no attribute allowed for update specified.')
            continue
        try:
            ok = DataSourceField.objects.filter(uuid=uuid).update(**update_dict)
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





