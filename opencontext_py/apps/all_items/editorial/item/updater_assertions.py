import copy

import reversion

from django.core.cache import caches

from django.db.models import Q
from django.utils import timezone


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)

from opencontext_py.apps.all_items import permissions
from opencontext_py.apps.all_items.editorial.item import updater_general



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
    ('meta_json', 'Changed assertion administrative metadata',),
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

# The source id to use for adding new assertions if not provided
DEFAULT_SOURCE_ID = 'ui-added'

PREDICATE_OBJECT_SORT_INCREMENT = 0.001

# By default, exclude assertions where subjects have these
# item types from sorting.
SORT_EXCLUDE_SUBJ_ITEM_TYPES = [
    'projects',
    'tables',
]

# By default, exclude assertions where predicates have these
# contexts from sorting.
SORT_EXCLUDE_PREDICATE_CONTEXT_IDS = [
    configs.SKOS_VOCAB_UUID,
    configs.DCTERMS_VOCAB_UUID,
    configs.BIBO_VOCAB_UUID,
]

# By default, exclude assertions where objects have these
# item types from sorting.
SORT_EXCLUDE_OBJ_ITEM_TYPES = [
    'types',  # These usually come in order determined by import.
    'persons', # These are usually significant for authorship
    'tables',
    'class',
    'uri',
]

PROJECT_SORT_CACHE_LIFE = 60 * 60  # 60 minutes (1 hour)
PROJECT_SORT_CHUNK_SIZE = 20


def get_assert_related_qs(assert_obj):
    """Gets a queryset of assertions in the same node as assert_obj"""
    node_assert_qs = AllAssertion.objects.filter(
        subject=assert_obj.subject,
        observation=assert_obj.observation,
        event=assert_obj.event,
        attribute_group=assert_obj.attribute_group,
        predicate=assert_obj.predicate,
    ).order_by('sort')
    return node_assert_qs


def get_clean_sort_related_assert_qs(assert_obj, increment=PREDICATE_OBJECT_SORT_INCREMENT):
    """Get a queryset node-related to assert_obj, cleaning sorts if needed"""
    node_assert_qs = get_assert_related_qs(assert_obj)
    len_qs = len(node_assert_qs)
    if len_qs < 1:
        return None

    qs_change_needed = False
    sort_values = []
    for i, other_assert in enumerate(node_assert_qs):
        if other_assert.sort is None or other_assert.sort == 0:
            qs_change_needed = True
            continue
        if other_assert.sort in sort_values:
            qs_change_needed = True
        sort_values.append(other_assert.sort)

    if not qs_change_needed:
        # Return the queryset, it doesn't need to be updated
        # to fix problematic sorts.
        return node_assert_qs

    # This will change the sort values to make them all 
    # unique, but keep the order as given in the node_assert_qs
    min_sort = 1
    if len(sort_values):
        min_sort = min(sort_values)
    for i, other_assert in enumerate(node_assert_qs):
        other_assert.sort = min_sort + (i * increment) 
        other_assert.save()
    
    # The query set changed, so refetch it.
    return get_assert_related_qs(assert_obj)


def move_sort_placement(assert_obj, move_sort, increment=PREDICATE_OBJECT_SORT_INCREMENT):
    """Changes a sort placement for an assertion object within it's node context"""
    node_assert_qs = get_clean_sort_related_assert_qs(
        assert_obj, 
        increment=increment
    )
    # get_clean_sort_related_assert_qs can change the assert_obj
    # so go fetch it again.
    assert_obj = AllAssertion.objects.get(uuid=assert_obj.uuid)

    node_assert_qs = node_assert_qs.exclude(
        uuid=assert_obj.uuid
    ).order_by('sort')
    if not node_assert_qs:
        return assert_obj
    
    prev_assert = None
    next_assert = None
    for other_assert in node_assert_qs:
        if other_assert.sort < assert_obj.sort:
            prev_assert = other_assert
        if next_assert is None and other_assert.sort > assert_obj.sort:
            # will be set by the first other assert that has a sort
            # value greater than 
            next_assert = other_assert
    
    store_sort = assert_obj.sort
    if move_sort == 'up' and prev_assert:
        assert_obj.sort = prev_assert.sort
        prev_assert.sort = store_sort
        assert_obj.save()
        prev_assert.save()
    
    if move_sort == 'down' and next_assert:
        assert_obj.sort = next_assert.sort
        next_assert.sort = store_sort
        assert_obj.save()
        next_assert.save()
    
    return assert_obj
    

def update_attribute_objs(request_json, request=None):
    """Updates AllAssertion fields based on listed attributes in client request JSON"""
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

        # Get the subject of the assertion's manifest object. This
        # will be used for history tracking. We also need to check permissions for
        # making an edit.
        man_obj = AllManifest.objects.filter(
            uuid=assert_obj.subject.uuid
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
            for k in ASSERTION_ATTRIBUTES_UPDATE_ALLOWED
            if item_update.get(k) is not None and str(getattr(assert_obj, k)) != str(item_update.get(k))
        }
        
        if update_dict.get('predicate_id') == str(configs.PREDICATE_CONTAINS_UUID):
            # Don't allow modification of spatial containment, because that
            # has wider implications on manifest object records.
            errors.append(f'Cannot change (spatial) containment with this method')
            continue

        move_sort = item_update.get('move_sort')
        if not len(update_dict) and not move_sort:
            print('Nothing to update')
            continue

        edits = []

        if not move_sort:
            # Change assertion attributes, not sort placement.
            update_assert_obj = copy.deepcopy(assert_obj)
            update_assert_obj.uuid = None
            update_assert_obj.pk = None
        elif len(update_dict) and move_sort:
            errors.append(f'Cannot change sort placement along with other changes')
            continue
        else:
            # we're changing the sort for this item.
            edits.append(f'Changed "{assert_obj.predicate.label}" assertion object sorting')
            update_assert_obj = move_sort_placement(assert_obj, move_sort)


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
                    attribute_edit_note += f' from "{str(old_value)[:120]}" to "{str(value)[:120]}"'

            if old_edited_obj and new_edited_obj and attribute_edit_note:
                attribute_edit_note += f' from "{old_edited_obj.label}" to "{new_edited_obj.label}"'
            
            if attribute_edit_note:
                edits.append(attribute_edit_note)
            setattr(update_assert_obj, attr, value)


        # Keep a copy of the old state before saving it.
        prior_to_edit_model_dict = updater_general.make_models_dict(item_obj=assert_obj)

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

        if not move_sort:
            # Delete the assertion that we just changed. The UUID will be different.
            assert_obj.delete()

        # Make a copy of the new state of your model.
        after_edit_model_dict = updater_general.make_models_dict(item_obj=update_assert_obj)

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


def add_assertions(request_json, request=None, source_id=DEFAULT_SOURCE_ID):
    """Add AllAssertions and from a client request JSON"""
    errors = []
    
    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to add')
        return [], errors

    added = []
    for item_add in request_json:
        subj_man_obj = None
        if item_add.get('subject_id'):
            subj_man_obj = AllManifest.objects.filter(
                uuid=item_add.get('subject_id')
            ).first()

        if not subj_man_obj:
            errors.append(f'Cannot find subject for assertion {str(item_add)}')
            continue

        _, ok_edit = permissions.get_request_user_permissions(
            request, 
            subj_man_obj, 
            null_request_ok=True
        )
        if not ok_edit:
            errors.append(f'Need permission to edit manifest object {subj_man_obj}')
            continue

        # Update if the item_update has attributes that we allow to update.
        add_dict = {
            k:item_add.get(k) 
            for k in ASSERTION_ATTRIBUTES_UPDATE_ALLOWED
            if k != 'uuid' and item_add.get(k) is not None
        }
        
        if add_dict.get('predicate_id') == str(configs.PREDICATE_CONTAINS_UUID):
            # Don't allow modification of spatial containment, because that
            # has wider implications on manifest object records.
            errors.append(f'Cannot add (spatial) containment with this method')
            continue

        if not add_dict.get('predicate_id'):
            errors.append(f'Assertion must have a predicate')
            continue

        if not len(add_dict):
            print('Nothing to update')
            continue

        # Fill in some of the blanks that the client may not usually send
        add_dict['subject_id'] = subj_man_obj.uuid
        if not add_dict.get('project_id'):
            add_dict['project_id'] = subj_man_obj.project.uuid
        if not add_dict.get('publisher_id'):
            add_dict['publisher_id'] = subj_man_obj.publisher.uuid
        if not add_dict.get('source_id'):
            add_dict['source_id'] = source_id
        if not add_dict.get('meta_json'):
            add_dict['meta_json'] = {}


        # NOTE: The sorting for the new assertion can be determined if not
        # already specified by the client in the add_dict. The following
        # steps should add the new assertion record with an expected sort
        # value.
        if not add_dict.get('sort'):
            sort_assert = AllAssertion.objects.filter(
                subject=subj_man_obj,
                predicate_id=add_dict.get('predicate_id')
            ).order_by('-sort').first()
            if sort_assert:
                # This subject already has assertion(s) with this predicate,
                # so add a small value to the sort of the new assertion.
                add_dict['sort'] = sort_assert.sort + PREDICATE_OBJECT_SORT_INCREMENT

        if not add_dict.get('sort'):
            pred_obj = AllManifest.objects.filter(
                uuid=add_dict.get('predicate_id')
            ).first()
            if pred_obj and pred_obj.meta_json.get('sort'):
                # The predicate object has a default sort value, so use it
                add_dict['sort'] = pred_obj.meta_json.get('sort')
        
        if not add_dict.get('sort'):
            sort_assert = AllAssertion.objects.filter(
                subject=subj_man_obj,
            ).order_by('-sort').first()
            if sort_assert:
                # This subject does not have any assertions with the new
                # predicate, so add larger sort value to the new assertion
                add_dict['sort'] = sort_assert.sort + 1


        for attr, value in add_dict.items():
            if value is False and ASSERTION_DEFAULT_NODE_IDS.get(attr):
                # We're removing an an assertion node, so set it back to the default
                value = ASSERTION_DEFAULT_NODE_IDS.get(attr)

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
            assert_obj = AllAssertion(**add_dict)
            assert_obj.created = timezone.now()
            assert_obj.save()
            ok = True
        except Exception as e:
            ok = False
            if hasattr(e, 'message'):
                error = e.message
            else:
                error = str(e)
            errors.append(f'Assertion item add error: {error}')
        if not ok:
            continue

        # Make a copy of the new state of your model.
        after_edit_model_dict = updater_general.make_models_dict(item_obj=assert_obj)

        display_obj = assert_obj.get_display_object()
        edit_note = (
            f'Added assertion: {assert_obj.predicate.label} -> {display_obj}'
        )

        history_obj = updater_general.record_edit_history(
            subj_man_obj,
            edit_note=edit_note,
            prior_to_edit_model_dict={},
            after_edit_model_dict=after_edit_model_dict,
        )
        item_add['history_id'] = str(history_obj.uuid)
        item_add['uuid'] = str(assert_obj.uuid)
        added.append(item_add)

    return added, errors


def delete_assertions(request_json, request=None):
    """Delete AllAssertions and from a client request JSON"""
    deleted = []
    errors = []
    
    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to update')
        return deleted, errors

    for item_delete in request_json:
        uuid = item_delete.get('uuid')
        if not uuid:
            errors.append('Must have "uuid" attribute.')
            continue
        assert_obj = AllAssertion.objects.filter(uuid=uuid).first()
        if not assert_obj:
            errors.append(f'Cannot find assertion object for {uuid}')
            continue

        # Get the subject of the assertion's manifest object. This
        # will be used for history tracking.
        subj_man_obj = AllManifest.objects.filter(
            uuid=assert_obj.subject.uuid
        ).first()

        _, ok_edit = permissions.get_request_user_permissions(
            request, 
            subj_man_obj, 
            null_request_ok=True
        )
        if not ok_edit:
            errors.append(f'Need permission to edit manifest object {subj_man_obj}')
            continue

        # Keep a copy of the old state before saving it.
        prior_to_edit_model_dict = updater_general.make_models_dict(item_obj=assert_obj)

        display_obj = assert_obj.get_display_object()
        edit_note = (
            f'Deleted assertion: {assert_obj.predicate.label} -> {display_obj}'
        )

        # Delete the assertion.
        assert_obj.delete()

        history_obj = updater_general.record_edit_history(
            subj_man_obj,
            edit_note=edit_note,
            prior_to_edit_model_dict=prior_to_edit_model_dict,
            after_edit_model_dict={},
        )
        item_delete['history_id'] = str(history_obj.uuid)
        deleted.append(item_delete)

    return deleted, errors



# ---------------------------------------------------------------------
# NOTE: Below are functions for mass sorting of assertions for
# individual items (as subjects of assertions) and for 
# items from entire projects
# ---------------------------------------------------------------------
def resort_assertion_objects_for_subject_uuids(
    subject_uuids,
    predicate_uuids=None,
    force_reset=True,
    predicate_sorts=None,
    exclude_subj_item_types=SORT_EXCLUDE_SUBJ_ITEM_TYPES,
    exclude_pred_context_ids=SORT_EXCLUDE_PREDICATE_CONTEXT_IDS,
    exclude_obj_item_types=SORT_EXCLUDE_OBJ_ITEM_TYPES,
):
    """Resorts objects of assertions for a given subject and predicate

    :params AllManifest subject: The subject of the assertions.
    :params bool force_reset: If True, resort objects for this
        subject and predicate according to their Manifest table sort order,
        even if these objects are already sorted.
    :params dict predicate_sorts: A dict keyed by a string predicate uuid
        that has starting sort value for a predicate.
        This sort ranking for all predicates of a given subject. It'll have
        a bigger magnitude than the sort rankings for objects of this predicate.
    :params list exclude_subj_item_types: List of item_types of subjects that
        we EXCLUDE from sorting
    :params list exclude_pred_context_ids: List of context (vocabulary) uuids
        that we EXCLUDE from sorting
    :params list exclude_obj_item_types: List of item_types of objects that we
        EXCLUDE from sorting.
    """
    
    assert_qs = AllAssertion.objects.filter(
        subject_id__in=subject_uuids,
        predicate__data_type='id',
    )
    if predicate_uuids:
        # Add optiona predicate filtering.
        assert_qs = assert_qs.filter(predicate_id__in=predicate_uuids)

    if exclude_subj_item_types:
        # Skip excluded subject item types
        assert_qs = assert_qs.exclude(
            subject__item_type__in=exclude_subj_item_types
        )
    if exclude_pred_context_ids:
        # Skip predicates from excluded vocabularies.
        assert_qs = assert_qs.exclude(
            predicate__context_id__in=exclude_pred_context_ids
        )
    
    if exclude_obj_item_types:
        # Limit by object item types
        assert_qs = assert_qs.exclude(
            object__item_type__in=exclude_obj_item_types
        )

    assert_qs = assert_qs.select_related(
        'predicate'
    )
    assert_qs = assert_qs.order_by(
        'subject', 'predicate', 'object__sort', 'object__label'
    )


    if predicate_sorts is None:
        predicate_sorts = {}

    count_updated = 0
    sub_pred_obj_ranks = {}
    for act_assert in assert_qs:
        subj_uuid = str(act_assert.subject.uuid)
        pred_uuid = str(act_assert.predicate.uuid)
        
        if not predicate_sorts.get(pred_uuid):
            predicate_sorts[pred_uuid] = act_assert.predicate.meta_json.get(
                'sort', 
                len(predicate_sorts)
            )
        predicate_sort = predicate_sorts.get(
            pred_uuid, 
            len(predicate_sorts)
        )
        obj_rank_key = (subj_uuid, pred_uuid,)
        if sub_pred_obj_ranks.get(obj_rank_key) is None:
            sub_pred_obj_ranks[obj_rank_key] = 0
        sub_pred_obj_ranks[obj_rank_key] += 1

        new_sort = (
            float(predicate_sort) 
            + (sub_pred_obj_ranks[obj_rank_key] * PREDICATE_OBJECT_SORT_INCREMENT)
        )
        if new_sort == act_assert.sort:
            # Nothing changed, so continue....
            continue
        # Do this as update without triggering a save, which has lots of slow
        # validation logic.
        AllAssertion.objects.filter(
            uuid=act_assert.uuid
        ).update(
            sort=new_sort
        )
        count_updated += 1

    return count_updated


def resort_assertion_objects_for_project_subjects(
    proj_context, 
    force_reset=True,
    predicate_sorts=None,
    exclude_subj_item_types=SORT_EXCLUDE_SUBJ_ITEM_TYPES,
    exclude_pred_context_ids=SORT_EXCLUDE_PREDICATE_CONTEXT_IDS,
    exclude_obj_item_types=SORT_EXCLUDE_OBJ_ITEM_TYPES,
):
    """Resorts objects of assertions for a given subject and predicate

    :params AllManifest proj_context: A project or context in which to
        select uuids for sorting.
    :params bool force_reset: If True, resort objects for this
        subject and predicate according to their Manifest table sort order,
        even if these objects are already sorted.
    :params dict predicate_sorts: A dict keyed by a string predicate uuid
        that has starting sort value for a predicate.
        This sort ranking for all predicates of a given subject. It'll have
        a bigger magnitude than the sort rankings for objects of this predicate.
    :params list exclude_subj_item_types: List of item_types of subjects that
        we EXCLUDE from sorting
    :params list exclude_pred_context_ids: List of context (vocabulary) uuids
        that we EXCLUDE from sorting
    :params list exclude_obj_item_types: List of item_types of objects that we
        EXCLUDE from sorting.
    """

    if predicate_sorts is None:
        predicate_sorts = {}

    uuid_qs = AllAssertion.objects.filter(
        Q(project=proj_context)
        |Q(subject__project=proj_context)
        |Q(subject__context=proj_context)
    ).filter(
        predicate__data_type='id',
    )

    if exclude_subj_item_types:
        # The subject item type is in a lit of excluded item types
        uuid_qs = uuid_qs.exclude(
            subject__item_type__in=exclude_subj_item_types
        )
    
    if exclude_pred_context_ids:
        # The subject item type is in a lit of excluded item types
        uuid_qs = uuid_qs.exclude(
            predicate__context_id__in=exclude_pred_context_ids
        )
    
    uuids = [str(u) for u in uuid_qs]
    uuids = list(set(uuids))
    chunk_uuids = [chunk for chunk in chunk_list(uuids)]

    count_updated = 0
    for chunk in chunk_uuids:
        count_updated += resort_assertion_objects_for_subject_uuids(
            subject_uuids=chunk, 
            force_reset=force_reset,
            predicate_sorts=predicate_sorts,
            exclude_subj_item_types=exclude_subj_item_types,
            exclude_pred_context_ids=exclude_pred_context_ids,
            exclude_obj_item_types=exclude_obj_item_types,
        )
    return count_updated


def sort_item_assertions(request_json, request=None):
    """Sort AllAssertions objects for items listed in a client request JSON"""
    count_updated = 0
    errors = []
    
    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to update')
        return count_updated, errors

    for item_sort in request_json:
        uuid = item_sort.get('uuid')
        if not uuid:
            errors.append('Must have "uuid" attribute.')
            continue
        subject = AllManifest.objects.filter(
            uuid=uuid
        ).first()
        if not subject:
            errors.append(f'Cannot find {uuid} in the manifest.')
            continue

        _, ok_edit = permissions.get_request_user_permissions(
            request, 
            subject, 
            null_request_ok=True
        )
        if not ok_edit:
            errors.append(f'Need permission to edit manifest object {subject}')
            continue

        count_updated += resort_assertion_objects_for_subject_uuids(
            subject_uuids=[uuid], 
            force_reset=True,
            predicate_sorts=None,
        )

    return count_updated, errors


def chunk_list(list_name, n=PROJECT_SORT_CHUNK_SIZE):
    """Breaks a long list into chunks of size n"""
    for i in range(0, len(list_name), n):
        yield list_name[i:i + n]


def sort_project_assertions(request_json, request=None):
    """Sort AllAssertions objects for items listed in a client request JSON"""
    sorts_done = None
    updated = []
    errors = []
    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to update')
        return sorts_done, updated, errors

    cache = caches['redis']
    sorts_done = True
    for proj_sort in request_json:
        uuid = proj_sort.get('uuid')
        if not uuid:
            errors.append('Must have "uuid" attribute.')
            continue

        proj_context = AllManifest.objects.filter(
            uuid=uuid,
            item_type__in=['projects', 'vocabularies'],
        ).first()
        if not proj_context:
            errors.append(f'Cannot find {uuid} as a project or vocab in the manifest.')
            continue

        _, ok_edit = permissions.get_request_user_permissions(
            request, 
            proj_context, 
            null_request_ok=True
        )
        if not ok_edit:
            errors.append(f'Need permission to edit manifest object {proj_context}')
            continue
        
        cache_key = f'proj-context-sort-{uuid}'
        proj_context_sort_stage = cache.get(cache_key)
        if proj_context_sort_stage is None or proj_sort.get('reset'):
            # NOTE: We're getting or reseting our sorting process for
            # items in this project. Set up an object to cache that
            # will keep track of the progress in our sorting.
            proj_context_sort_stage = {
                'done': False,
                'total_uuids_count': None,
                'chunk_uuids': None,
                'last_chunk_index': -1,
                'total_chunks': None,
                'count_updated': 0,
            }
            
            # Get a queryset of uuids for this project / context
            uuid_qs = AllAssertion.objects.filter(
                Q(project=proj_context)
                |Q(subject__project=proj_context)
                |Q(subject__context=proj_context)
            ).filter(
                predicate__data_type='id',
            ).exclude(
                subject__item_type__in=SORT_EXCLUDE_SUBJ_ITEM_TYPES,
            ).exclude(
                object__item_type__in=SORT_EXCLUDE_OBJ_ITEM_TYPES,
            ).distinct(
                'subject'
            ).order_by(
                'subject'
            ).values_list('subject', flat=True)

            # Make a list of the UUIDs that we will need to sort
            uuids = [str(u) for u in uuid_qs]
            uuids = list(set(uuids))
            # Because AllAssertion pks are based on subject uuids,
            # this sorting speeds things up!
            uuids.sort()
            proj_context_sort_stage['total_uuids_count'] = len(uuids)
            chunk_uuids = [chunk for chunk in chunk_list(uuids)]
            proj_context_sort_stage['chunk_uuids'] = chunk_uuids
            proj_context_sort_stage['total_chunks'] = len(chunk_uuids)
        
        act_chunk_index = proj_context_sort_stage['last_chunk_index'] + 1
        if act_chunk_index >= proj_context_sort_stage['total_chunks']:
            proj_context_sort_stage['done'] = True

        if proj_context_sort_stage['total_chunks'] < 1:
            proj_context_sort_stage['last_chunk_index'] = 0
            proj_context_sort_stage['done'] = True

        if not proj_context_sort_stage['done']:
            proj_context_sort_stage['count_updated'] += resort_assertion_objects_for_subject_uuids(
                subject_uuids=proj_context_sort_stage['chunk_uuids'][act_chunk_index], 
                force_reset=True,
                predicate_sorts=None,
            )
        
        proj_context_sort_stage['last_chunk_index'] = act_chunk_index
        if proj_context_sort_stage['last_chunk_index'] < proj_context_sort_stage['total_chunks']:
            # We're not done yet.
            sorts_done = False
            proj_context_sort_stage['done'] = False
        else:
            proj_context_sort_stage['done'] = True
        
        cache.set(
            cache_key, 
            proj_context_sort_stage, 
            timeout=PROJECT_SORT_CACHE_LIFE,
        )
        update_dict = {k:v for k,v in proj_context_sort_stage.items() if k != 'chunk_uuids'}
        if update_dict.get('total_chunks', 1) <= 1:
            update_dict['done'] = True
        updated.append(update_dict)

    return sorts_done, updated, errors