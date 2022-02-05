


from opencontext_py.apps.all_items import configs

from opencontext_py.apps.etl.importer.models import (
    DataSourceField,
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
        if not ds_field:
            errors.append(f'Cannot find ds_field for {uuid}')
            continue

        orig_item_type = ds_field.item_type

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


def add_single_annotation(request_item_dict, errors=None):
    """Adds a DataSourceAnnotation based on request_json"""
    if errors is None:
        errors = []

    created = None
    subject_field_id = request_item_dict.get('subject_field_id')
    if not subject_field_id:
        errors.append('subject_field_id')
        return None, errors

    ds_subj_field = DataSourceField.objects.filter(
        uuid=subject_field_id
    ).first()
    if not ds_subj_field:
        errors.append(f'Cannot find field {ds_subj_field}')
        return None, errors
    
    object_field_id = request_item_dict.get('object_field_id')
    predicate_id = request_item_dict.get('predicate_id')
    if object_field_id and predicate_id == configs.PREDICATE_OC_ETL_DESCRIBED_BY:
        # Delete annotations where the object_field_id is already an
        # described-by object in another annotation
        DataSourceAnnotation.objects.filter(
            object_field_id=object_field_id,
            predicate_id=predicate_id,
        ).delete()

    create_dict = {
        'data_source': ds_subj_field.data_source,
        'subject_field': ds_subj_field,
    }
    skip_keys = ['data_source', 'data_source_id', 'subject_field', 'subject_field_id']
    for key, value in request_item_dict.items():
        if key in skip_keys:
            continue
        create_dict[key] = value
    
    ds_anno = DataSourceAnnotation(**create_dict)
    try:
        ds_anno.save()
        created = str(ds_anno.uuid)
    except Exception as e:
        created = None
        if hasattr(e, 'message'):
            error = e.message
        else:
            error = str(e)
        errors.append(error)
    return created, errors


def add_annotations(request_json):
    """Adds annotation items from a request_json list"""
    if not request_json:
        return [], ['Empty request']
    
    all_created = []
    errors = None
    for request_item_dict in request_json:
        created, errors = add_single_annotation(request_item_dict, errors=errors)
        print(f'NEW created: {created}, errors: {errors}')
        all_created.append(created)
    
    print(f'Created: {all_created}, errors: {errors}')
    return all_created,  errors




