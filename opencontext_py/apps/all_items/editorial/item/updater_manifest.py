import copy

import reversion


from django.db.models import Q
from django.utils import timezone


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.defaults import (
    DEFAULT_MANIFESTS,
)
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

from opencontext_py.apps.all_items import permissions
from opencontext_py.apps.all_items.editorial.item import updater_general
from opencontext_py.apps.all_items.editorial.item import item_validation
from opencontext_py.apps.all_items.editorial.item.edit_configs import (
    MANIFEST_ADD_EDIT_CONFIGS,
    TABLES_ADD_EDIT_CONFIG,
    EDIT_GROUP_USER_ALLOWED_REINDEX_TYPES,
)

from opencontext_py.apps.all_items.editorial.tables import cloud_utilities
from opencontext_py.apps.all_items.editorial.tables import metadata as tables_metadata

from opencontext_py.libs.models import (
    make_model_object_json_safe_dict
)

from opencontext_py.apps.indexer import index_new_schema as new_ind

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

# Attributes OK when adding OC_ITEM_TYPES
OC_ITEM_TYPES_ADD_OK_ATTRIBUTES = [
    'uuid',
    'slug',
]

# Attributes OK when adding NODE_ITEM_TYPES
NODE_ITEM_TYPES_ADD_OK_ATTRUBUTES = OC_ITEM_TYPES_ADD_OK_ATTRIBUTES.copy()

# Attributes OK when adding URI_ITEM_TYPES
URI_ITEM_TYPES_ADD_OK_ATTRIBUTES = [
    'slug',
    'uri',
    'item_key',
]

# The source id to use for adding new resource if not provided
DEFAULT_SOURCE_ID = 'ui-added'

# Make a list of default Manifest objects for which we prohibit
# edits.
EDIT_EXCLUDE_UUIDS = [m.get('uuid') for m in DEFAULT_MANIFESTS if m.get('uuid')]


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


def update_manifest_objs(request_json, request=None):
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

        _, ok_edit = permissions.get_request_user_permissions(
            request,
            man_obj,
            null_request_ok=True
        )
        if not ok_edit:
            errors.append(f'Need permission to edit manifest object {man_obj}')
            continue

        if uuid in EDIT_EXCLUDE_UUIDS:
            errors.append(f'Edits prohibited on required item {man_obj}')
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

        # Do some update validations.
        if update_dict.get('label'):
            update_dict['label'] = str(update_dict['label']).strip()
            report = item_validation.validate_label(
                update_dict['label'],
                filter_args={
                    'item_type': man_obj.item_type,
                    'project_id': man_obj.project_id,
                    'context_id': man_obj.context_id,
                },
                exclude_uuid=man_obj.uuid
            )
            if not report.get('is_valid'):
                errors.append(f'Label "{update_dict["label"]}" invalid.')
                continue

        if update_dict.get('slug'):
            update_dict['slug'] = str(update_dict['slug']).strip()
            report = item_validation.validate_slug(
                update_dict['slug'],
                exclude_uuid=man_obj.uuid
            )
            if not report.get('is_valid'):
                errors.append(f'Slug "{update_dict["slug"]}" invalid.')
                continue

        if update_dict.get('item_key'):
            update_dict['item_key'] = str(update_dict['item_key']).strip()
            report = item_validation.validate_item_key(
                update_dict['item_key'],
                exclude_uuid=man_obj.uuid
            )
            if not report.get('is_valid'):
                errors.append(f'Item key "{update_dict["item_key"]}" invalid.')
                continue

        if update_dict.get('uri'):
            update_dict['uri'] = str(update_dict['uri']).strip()
            report = item_validation.validate_uri(
                update_dict['uri'],
                exclude_uuid=man_obj.uuid
            )
            if not report.get('is_valid'):
                errors.append(f'URI "{update_dict["uri"]}" invalid.')
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

            if attr == 'meta_json' and isinstance(value, dict):
                for key, new_key_value in value.items():
                    old_key_value = man_obj.meta_json.get(key)
                    if old_key_value == new_key_value:
                        continue
                    old_key_value = str(old_key_value)[:20]
                    new_key_value = str(new_key_value)[:20]
                    attribute_edit_note += (
                        f' {key} from "{old_key_value}" to "{new_key_value}"'
                    )
            elif attribute_edit_note and not attr.endswith('_id'):
                old_value = getattr(man_obj, attr)
                attribute_edit_note += f' from "{str(old_value)[:120]}" to "{str(value)[:120]}"'

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


def get_item_type_req_attribs_dict():
    """Gets a dict keyed by item_type for attributes required to add manifest obj"""
    item_type_req_attribs = {
        'tables': TABLES_ADD_EDIT_CONFIG.get(
            'add_required_attributes',
            []
        ),
    }
    for group in MANIFEST_ADD_EDIT_CONFIGS:
        for i_type_config in group.get('item_types', []):
            item_type = i_type_config.get('item_type')
            item_type_req_attribs[item_type] = i_type_config.get(
                'add_required_attributes',
                []
            )
    return item_type_req_attribs


def get_item_type_ok_attribs_dict():
    """Gets a dict keyed by item_type for attributes ALLOWED in creating a manifest obj"""
    item_type_req_attribs = get_item_type_req_attribs_dict()
    item_type_ok_attribs = {}
    for item_type_key, _ in item_type_req_attribs.items():
        item_type_ok_attribs[item_type_key] = MANIFEST_ATTRIBUTES_UPDATE_ALLOWED
        if item_type_key in configs.OC_ITEM_TYPES:
            item_type_ok_attribs[item_type_key] += OC_ITEM_TYPES_ADD_OK_ATTRIBUTES
        elif item_type_key in configs.NODE_ITEM_TYPES:
            item_type_ok_attribs[item_type_key] += NODE_ITEM_TYPES_ADD_OK_ATTRUBUTES
        elif item_type_key in configs.URI_ITEM_TYPES:
            item_type_ok_attribs[item_type_key] += URI_ITEM_TYPES_ADD_OK_ATTRIBUTES
        else:
            pass
    return item_type_ok_attribs


def add_manifest_objs(request_json, source_id=DEFAULT_SOURCE_ID):
    """Adds AllManifest objects from attributes given in client request JSON"""
    errors = []

    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to add')
        return [], errors

    # This makes a dict keyed by item_type for attributes we REQUIRE
    # to create a new manifest item.
    item_type_req_attribs = get_item_type_req_attribs_dict()

    # This makes a dict keyed by item_type for attributes we ALLOW
    # to create a new manifest item.
    item_type_ok_attribs = get_item_type_ok_attribs_dict()

    added = []
    for item_add in request_json:
        item_type = item_add.get('item_type')
        if not item_type or not item_type_req_attribs.get(item_type):
            errors.append('Missing or unrecognized item_type')
            continue

        # Check to make sure we have all of our required attributes
        # for this item-type
        for req_attrib in item_type_req_attribs.get(item_type):
            if item_add.get(req_attrib):
                continue
            errors.append(f'Missing the required attribute "{req_attrib}"')
        if len(errors):
            continue

        if item_type in configs.URI_CONTEXT_PREFIX_ITEM_TYPES:
            # The context (vocabulary) will be the object that will
            # get an edit history
            edited_obj = AllManifest.objects.filter(uuid=item_add.get('context_id')).first()
        else:
            edited_obj = AllManifest.objects.filter(uuid=item_add.get('project_id')).first()

        if not edited_obj:
            errors.append(f'Missing project or context to add into: {str(item_add)}')
            continue

        ok_attributes = item_type_ok_attribs.get(item_type)
        if not ok_attributes:
            errors.append(f'Allowed add config missing for: {str(item_type)}')
            continue

        # Make an add dictionary limited to attributes allowed for adding
        # for this item type
        add_dict = {k:item_add.get(k) for k in ok_attributes if item_add.get(k)}
        # make sure the item_type is part of the add_dict.
        add_dict['item_type'] = item_type
        if not add_dict.get('source_id'):
            add_dict['source_id'] = source_id
        if not add_dict.get('meta_json'):
            add_dict['meta_json'] = {}

        valid_ok, valid_errors = item_validation.validate_manifest_dict(add_dict)
        if not valid_ok:
            errors.append(f'Attribute validation errors: {str(valid_errors)}')
            continue

        # NOTE: We will want to save a table export CSV data to cloud storage
        # before we go on to make the item.
        full_cloud_obj = None
        preview_cloud_obj = None
        export_id = None
        if item_add.get('export_id') and item_type == 'tables':
            # Get the export table uuid, if set. At this point, we know
            # it will be valid (if set).
            export_id = item_add.get('export_id')
            uuid, full_cloud_obj = cloud_utilities.cloud_store_csv_from_cached_export(
                export_id=export_id,
                uuid=add_dict.get('uuid'),
            )
            if not uuid or not full_cloud_obj:
                errors.append(f'Cloud storage failure for full csv: {export_id}')
                if not uuid:
                    errors.append(f'Missing uuid')
                if not full_cloud_obj:
                    errors.append(f'Missing full_cloud_obj')
                continue

            # Make sure the uuid is synced so the preview has the correct key / object name
            add_dict['uuid'] = uuid
            uuid, preview_cloud_obj = cloud_utilities.cloud_store_csv_from_cached_export(
                export_id=export_id,
                uuid=add_dict.get('uuid'),
                preview_rows=cloud_utilities.DEFAULT_PREVIEW_ROW_SIZE,
            )
            if not uuid or not preview_cloud_obj:
                errors.append(f'Cloud storage failure for preview csv: {export_id}')
                if not uuid:
                    errors.append(f'Missing uuid')
                if not full_cloud_obj:
                    errors.append(f'Missing preview_cloud_obj')
                continue

        # Check to make sure we can de-reference identified items.
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

        if len(errors):
            continue

        print(f'add dict is: {str(add_dict)}')

        try:
            man_obj = AllManifest(**add_dict)
            man_obj.revised = timezone.now()
            man_obj.save()
            ok = True
        except Exception as e:
            ok = False
            if hasattr(e, 'message'):
                error = e.message
            else:
                error = str(e)
            errors.append(f'Manifest item add error: {error}')
        if not ok:
            continue

        if full_cloud_obj and preview_cloud_obj and man_obj.item_type == 'tables':
            # We succeeded in making a table and have a cloud_obj
            # so, time to add some related resources.
            tables_metadata.add_table_metadata_and_resources(
                man_obj,
                export_id,
                full_cloud_obj=full_cloud_obj,
                preview_cloud_obj=preview_cloud_obj,
            )

        # Make a copy of the new state of your model.
        after_edit_model_dict = updater_general.make_models_dict(item_obj=man_obj)
        edit_note = (
            f'Added: {man_obj}'
        )

        history_obj = updater_general.record_edit_history(
            edited_obj,
            edit_note=edit_note,
            prior_to_edit_model_dict={},
            after_edit_model_dict=after_edit_model_dict,
        )

        # Make an added dict with the manifest item.
        final_added = make_model_object_json_safe_dict(man_obj)
        final_added['history_id'] = str(history_obj.uuid)
        added.append(final_added)

    return added, errors


def delete_manifest_obj(to_delete_man_obj, context_recursive=False, note=None, deleted=None, errors=None):
    """Deletes a manifest object, optionally recursively for items that use it as context"""
    if note is None:
        note = ''
    if deleted == None:
        deleted = []
    if errors == None:
        errors = []
    if str(to_delete_man_obj.uuid) in EDIT_EXCLUDE_UUIDS:
        errors.append(f'Edits prohibited on required item {to_delete_man_obj}')
        return deleted, errors
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
                note=note,
                deleted=deleted,
                errors=errors
            )

    if len(errors):
        # Stop if there was a problem in deleting child items.
        return deleted, errors

    if to_delete_man_obj.item_type in configs.URI_CONTEXT_PREFIX_ITEM_TYPES:
        # The context (vocabulary) will be the object that will
        # get an edit history
        edited_obj = AllManifest.objects.filter(
            uuid=to_delete_man_obj.context.uuid
        ).first()
    else:
        edited_obj = AllManifest.objects.filter(
            uuid=to_delete_man_obj.project.uuid
        ).first()


    # Keep a copy of the old state before saving it.
    prior_to_edit_model_dict = updater_general.make_models_dict(item_obj=to_delete_man_obj)

    # Get querysets for objects related to / associated with the item we
    # are deleting.
    qs_list = []
    qs_list.append(
        AllAssertion.objects.filter(
            Q(subject=to_delete_man_obj)
            | Q(publisher=to_delete_man_obj)
            | Q(project=to_delete_man_obj)
            | Q(observation=to_delete_man_obj)
            | Q(event=to_delete_man_obj)
            | Q(attribute_group=to_delete_man_obj)
            | Q(predicate=to_delete_man_obj)
            | Q(object=to_delete_man_obj)
            | Q(language=to_delete_man_obj)
        )
    )
    qs_list.append(
        AllSpaceTime.objects.filter(
            Q(item=to_delete_man_obj)
            | Q(publisher=to_delete_man_obj)
            | Q(project=to_delete_man_obj)
            | Q(event=to_delete_man_obj)
        )
    )
    qs_list.append(
        AllResource.objects.filter(
            Q(item=to_delete_man_obj)
            | Q(resourcetype=to_delete_man_obj)
            | Q(mediatype=to_delete_man_obj)
        )
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
        f'and {total_objects} associated records. {note}'
    )
    # Save the edit note to the meta_json for the project. This makes sure the
    # hash updates for the project so we can save the history of the edit.
    edited_obj.meta_json.setdefault('deleted', [])
    edited_obj.meta_json['deleted'].append(edit_note)
    edited_obj.save()

    delete_uuid = str(to_delete_man_obj.uuid)

    # Now do the actual delete of the item we want to delete.
    to_delete_man_obj.delete()

    history_obj = updater_general.record_edit_history(
        edited_obj,
        edit_note=edit_note,
        prior_to_edit_model_dict=prior_to_edit_model_dict,
        after_edit_model_dict={},
    )
    delete_dict = {
        'history_id': str(history_obj.uuid),
        'deleted_id': delete_uuid,
    }
    deleted.append(delete_dict)
    # Now delete the item from the solr index.
    new_ind.delete_solr_documents(uuids=[delete_uuid])
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
        note = item_delete.get('note')
        if not uuid:
            errors.append('Must have "uuid" attribute.')
            continue
        to_delete_man_obj = AllManifest.objects.filter(uuid=uuid).first()
        if not to_delete_man_obj:
            errors.append(f'Cannot find manifest object for {uuid}')
            continue
        if uuid in EDIT_EXCLUDE_UUIDS:
            errors.append(f'Edits prohibited on required item {man_obj}')
            continue
        deleted, errors = delete_manifest_obj(
            to_delete_man_obj=to_delete_man_obj,
            context_recursive=item_delete.get('context_recursive', False),
            note=note,
            deleted=deleted,
            errors=errors,
        )
    return deleted, errors


def get_rank(keep_man_obj, legacy_obj, model):
    """Gets a ranking value for the legacy_obj for models that use ranking"""
    models_with_rank = {
        AllResource: ['resourcetype',],
        AllIdentifier: ['scheme',],
    }
    if not models_with_rank.get(model):
        return None
    check_args = {
        'item': keep_man_obj,
    }
    for attrib in models_with_rank.get(model):
        if not getattr(legacy_obj, attrib, None):
            continue
        check_args[attrib] = getattr(legacy_obj, attrib)
    rank_qs = model.objects.filter(**check_args)
    rank = len(rank_qs)
    return rank


def merge_manifest_objs(
    keep_man_obj,
    to_delete_man_obj,
    note=None,
    merges=None,
    errors=None,
    warnings=None
):
    """Merges manifest objects.

    :param AllManifest keep_man_obj: The manifest object that will be
        retained.
    :param AllManifest to_delete_man_obj: The manifest object that
        will be deleted after merging into the keep_man_obj.
    """
    if note is None:
        note = ''
    if merges is None:
        merges = []
    if errors is None:
        errors = []
    if warnings is None:
        warnings = []

    keep_uuid = str(keep_man_obj.uuid)
    delete_uuid = str(to_delete_man_obj.uuid)
    if keep_uuid == delete_uuid:
        errors.append('Cannot merge an item into itself.')
        return errors
    if delete_uuid in EDIT_EXCLUDE_UUIDS:
        errors.append(f'Edits prohibited on required item {to_delete_man_obj}')
        return errors

    if keep_man_obj.item_type != to_delete_man_obj.item_type:
        errors.append('Cannot merge, mismatched item types.')
        return errors

    if keep_man_obj.data_type != to_delete_man_obj.data_type:
        errors.append('Cannot merge, mismatched data types.')
        return errors

    exclude_keep_attribs = {
        AllManifest: 'uuid',
        AllAssertion: 'subject_id',
    }

    related_models_attribs = [
        (
            AllManifest,
            True,
            [
                'publisher',
                'project',
                'item_class',
                'context',
            ],
        ),
        (
            AllSpaceTime,
            False,
            [
                'publisher',
                'project',
                'item',
                'event',
            ],
        ),
        (
            AllAssertion,
            False,
            [
                'publisher',
                'project',
                'subject',
                'observation',
                'event',
                'attribute_group',
                'predicate',
                'object',
                'language',
            ],
        ),
        (
            AllResource,
            False,
            [
                'project',
                'item',
                'resourcetype',
                'mediatype',
            ],
        ),
        (
            AllIdentifier,
            False,
            ['item',],
        ),
        (
            AllHistory,
            False,
            ['item',],
        ),
    ]

    # Keep a copy of the old state before saving it.
    prior_to_edit_model_dict = updater_general.make_models_dict(item_obj=to_delete_man_obj)

     # Make a copy of the new state of your model.
    after_edit_model_dict = updater_general.make_models_dict(item_obj=keep_man_obj)

    total_objects = 0
    for model, is_manifest, attrib_list in related_models_attribs:
        exclude_attrib = exclude_keep_attribs.get(model)
        for attrib in attrib_list:
            filter_dict = {
                attrib: to_delete_man_obj
            }
            qs = model.objects.filter(**filter_dict)
            if exclude_attrib:
                # This excludes relationships / assertions between the to_delete_man_obj
                # and the keep_man_obj.
                qs = qs.exclude(**{exclude_attrib: keep_man_obj.uuid})

            len_objects = len(qs)
            if len_objects < 1:
                continue
            total_objects += len_objects
            # Record the objects in this query set before we make updates.
            prior_to_edit_model_dict = updater_general.add_queryset_objs_to_models_dict(
                prior_to_edit_model_dict,
                qs
            )
            updated_objs = []
            for legacy_obj in qs:
                if is_manifest:
                    # Special handling for manifest objects. We don't change their
                    # UUID / PKs.
                    setattr(legacy_obj, attrib, keep_man_obj)
                    ok_save = None
                    try:
                        legacy_obj.save()
                        ok_save = True
                    except:
                        ok_save = False
                    if not ok_save:
                        warnings.append(f'Could not update {legacy_obj} {attrib} to {keep_man_obj}')
                        continue
                    updated_objs.append(legacy_obj)
                    continue
                # First check about 'rank', which we use to allow multiple records
                # that should otherwise be unique.
                new_rank = get_rank(keep_man_obj, legacy_obj, model)
                # Make a deep copy to make a new, updated object from the old.
                new_obj = copy.deepcopy(legacy_obj)
                new_obj.uuid = None
                new_obj.pk = None
                if new_rank:
                    new_obj.rank = new_rank
                # Update the attribute to switch the to_delete_man_obj to the
                # keep_man_obj
                setattr(new_obj, attrib, keep_man_obj)
                try:
                    new_obj.save()
                except:
                    new_obj = None
                if not new_obj:
                    warnings.append(f'Could not migrate {legacy_obj} {attrib} to {keep_man_obj}')
                    continue
                updated_objs.append(new_obj)

            after_edit_model_dict = updater_general.add_queryset_objs_to_models_dict(
                after_edit_model_dict,
                updated_objs
            )

    # Update the path for this item and all child items that may have been
    # impacted by the merge.
    recursive_subjects_path_update(keep_man_obj)

    edit_note = f'Merge {to_delete_man_obj} into => {keep_man_obj}. {note}'

    # Now delete the to_delete_man_obj
    _, del_errors = delete_manifest_obj(
        to_delete_man_obj=to_delete_man_obj,
        context_recursive=False,
        note=note,
    )
    errors += del_errors

    history_obj = updater_general.record_edit_history(
        keep_man_obj,
        edit_note=edit_note,
        prior_to_edit_model_dict=prior_to_edit_model_dict,
        after_edit_model_dict=after_edit_model_dict,
    )
    merge_dict = {
        'history_id': str(history_obj.uuid),
        'keep_id': keep_uuid,
        'delete_id': delete_uuid,
    }
    merges.append(merge_dict)
    return merges, errors, warnings


def api_merge_manifest_objs(request_json):
    """Merges manifest objects"""
    merges = []
    errors = []
    warnings = []
    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to update')
        return merges, errors, warnings

    for item_merge in request_json:
        keep_uuid = item_merge.get('keep_id')
        delete_uuid = item_merge.get('delete_id')
        note = item_merge.get('note')
        if not keep_uuid:
            errors.append('Must specify a "keep_id" attribute.')
            continue
        if not delete_uuid:
            errors.append('Must specify a "delete_id" attribute.')
            continue
        if keep_uuid == delete_uuid:
            errors.append('Cannot merge an item into itself.')
            continue
        keep_man_obj = AllManifest.objects.filter(uuid=keep_uuid).first()
        if not keep_man_obj:
            errors.append(f'Cannot find manifest object for {keep_uuid}')
            continue
        to_delete_man_obj = AllManifest.objects.filter(uuid=delete_uuid).first()
        if not to_delete_man_obj:
            errors.append(f'Cannot find manifest object for {delete_uuid}')
            continue
        if delete_uuid in EDIT_EXCLUDE_UUIDS:
            errors.append(f'Edits prohibited on required item {to_delete_man_obj}')
            continue
        merges, errors, warnings = merge_manifest_objs(
            keep_man_obj=keep_man_obj,
            to_delete_man_obj=to_delete_man_obj,
            note=note,
            merges=merges,
            errors=errors,
            warnings=warnings,
        )
    return merges, errors, warnings


def reindex_manifest_objs(request_json, request=None):
    """Reindexes manifest objects"""
    errors = []
    reindex_list = []
    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to update')
        return reindex_list, errors

    for item_reindex in request_json:
        uuid = item_reindex.get('uuid')
        if not uuid:
            errors.append('Must have "uuid" attribute.')
            continue
        to_reindex_man_obj = AllManifest.objects.filter(uuid=uuid).first()
        if not to_reindex_man_obj:
            errors.append(f'Cannot find manifest object for {uuid}')
            continue

        _, ok_edit = permissions.get_request_user_permissions(
            request,
            to_reindex_man_obj,
            null_request_ok=True
        )
        if not ok_edit:
            errors.append(f'Need permission reindex manifest object {man_obj}')
            continue

        if (request and not request.user.is_superuser
            and not to_reindex_man_obj.item_type in EDIT_GROUP_USER_ALLOWED_REINDEX_TYPES):
            errors.append(f'Only super user can reindex item_type: {to_reindex_man_obj.item_type}')
            continue

        if to_reindex_man_obj.meta_json.get('flag_do_not_index'):
            errors.append(f'Item {to_reindex_man_obj.label} ({to_reindex_man_obj.uuid}) has "do_not_index" flag')
            continue

        if to_reindex_man_obj.project.meta_json.get('flag_do_not_index'):
            errors.append(f'Item {to_reindex_man_obj.label} ({to_reindex_man_obj.uuid}) in project with "do_not_index" flag')
            continue

        reindex_list.append(uuid)

    if len(reindex_list) > 0:
        # The assumption here is that our reindex list is small enough
        # to finish indexing before a web request times out.
        new_ind.make_indexed_solr_documents_in_chunks(
            uuids=reindex_list,
            start_clear_caches=False,
        )
    return reindex_list, errors