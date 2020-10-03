
import copy
import hashlib
import uuid as GenUUID

from django.db.models import OuterRef, Subquery

from opencontext_py.libs.general import LastUpdatedOrderedDict

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities
from opencontext_py.apps.all_items.representations import metadata


# This provides a mappig between a predicate.data_type and
# the attribute of an assertion object for the object of that
# assertion.
ASSERTION_DATA_TYPE_LITERAL_MAPPINGS = {
    'xsd:string': 'obj_string',
    'xsd:boolean': 'obj_boolean',
    'xsd:integer': 'obj_integer',
    'xsd:double': 'obj_double',
    'xsd:date': 'obj_datetime',
}


def make_grouped_by_dict_from_queryset(qs, index_list):
    """Makes a dictionary, grouped by attributes of query set objects"""
    keyed_objects = LastUpdatedOrderedDict()
    for obj in qs:
        key = tuple(getattr(obj, act_attrib) for act_attrib in index_list)
        keyed_objects.setdefault(key, []).append(obj)
    return keyed_objects


def get_dict_path_value(path_keys_list, dict_obj, default=None):
    """Get a value from a dictionary object by a list of keys """
    if not isinstance(dict_obj, dict):
        return None
    act_obj = copy.deepcopy(dict_obj)
    for key in path_keys_list:
        act_obj = act_obj.get(key, default)
        if not isinstance(act_obj, dict):
            return act_obj
    return act_obj


def make_tree_dict_from_grouped_qs(qs, index_list):
    """Groups a queryset according to index list of attributes to
    make hierarchically organized lists of dicts
    """
    # NOTE: This works because it relies on mutating a dictionary
    # tree_dict. It's a little hard to understand, which is why
    # there's a debugging function _print_tree_dict to show the
    # outputs.
    grouped_qs_objs = make_grouped_by_dict_from_queryset(qs, index_list)
    tree_dict = LastUpdatedOrderedDict()
    for group_tup_key, obj_list in grouped_qs_objs.items():
        level_dict = tree_dict
        for key in group_tup_key:
            if key != group_tup_key[-1]:
                level_dict.setdefault(key, LastUpdatedOrderedDict())
                level_dict = level_dict[key]
            else:
                level_dict[key] = obj_list
    return tree_dict


def _print_tree_dict(tree_dict, level=0):
    """Debugging print of a tree dict for assertions"""
    indent = level * 4
    for key, vals in tree_dict.items():
        print(
            '-'*indent +
            f'Key: {key.uuid} {key.label}'
        )
        if isinstance(vals, dict):
            _print_tree_dict(vals, level=(level + 1))
        else:
            for ass_obj in vals:
                obj_str = ass_obj.obj_string
                if obj_str is None:
                    obj_str = ''
                obj_str = obj_str[:20]
                print(
                    '-'*indent +
                    '----' +
                    f'Assertion {ass_obj.uuid}: '
                    f'is {ass_obj.subject.label} [{ass_obj.subject.uuid}]'
                    f'-> {ass_obj.predicate.label} [{ass_obj.predicate.uuid}]'
                    f'-> {ass_obj.object.label} [{ass_obj.object.uuid}] '
                    f'Str: {obj_str} '
                    f'Bool: {ass_obj.obj_boolean} '
                    f'Int: {ass_obj.obj_integer} '
                    f'Double: {ass_obj.obj_double} '
                    f'Date: {ass_obj.obj_datetime}'
                )


def get_item_assertions(subject_id):
    """Gets an assertion queryset about an item"""
    thumbs_qs = AllResource.objects.filter(
        item=OuterRef('object'),
        resourcetype_id=configs.OC_RESOURCE_THUMBNAIL_UUID,
    ).values('uri')

    qs = AllAssertion.objects.filter(
        subject_id=subject_id,
        visible=True,
    ).select_related(
        'observation'
    ).select_related(
        'event'
    ).select_related( 
        'attribute_group'
    ).select_related(
        'predicate'
    ).select_related(
        'language'
    ).select_related( 
        'object'
    ).select_related( 
        'object__item_class'
    ).annotate(
        object_thumbnail=Subquery(thumbs_qs)
    )
    return qs


def make_predicate_objects_list(predicate, assert_objs):
    """Makes a list of assertion objects for a predicate"""
    # NOTE: Predicates of different data-types will hae different values
    # for different 
    pred_objects = []
    for assert_obj in assert_objs:
        if predicate.data_type == 'id':
            obj = LastUpdatedOrderedDict()
            obj['id'] = f'https://{assert_obj.object.uri}'
            obj['slug'] = assert_obj.object.slug
            obj['label'] = assert_obj.object.label
            if str(assert_obj.object.item_class.uuid) != configs.DEFAULT_CLASS_UUID:
                if assert_obj.object.item_class.item_key:
                    obj['type'] = assert_obj.object.item_class.item_key
                else:
                    obj['type'] = f'https://{assert_obj.object.item_class.uri}'
            if getattr(assert_obj, 'object_thumbnail'):
                obj['oc-gen:thumbnail-uri'] = f'https://{assert_obj.object_thumbnail}'
        elif predicate.data_type == 'xsd:string':
            obj = {
                f'@{assert_obj.language.item_key}': assert_obj.obj_string
            }
        else:
            act_attrib = ASSERTION_DATA_TYPE_LITERAL_MAPPINGS.get(
                predicate.data_type
            )
            obj = getattr(assert_obj, act_attrib)
            if predicate.data_type == 'xsd:date':
                obj = obj.date().isoformat()
        pred_objects.append(obj)
    return pred_objects


def add_predicates_assertions_to_dict(pred_keyed_assert_objs, act_dict=None):
    """Adds predicates with their grouped objects to a dictionary, keyed by each pred"""
    if not act_dict:
        act_dict = LastUpdatedOrderedDict()
    for predicate, assert_objs in pred_keyed_assert_objs.items():
        pred_objects = make_predicate_objects_list(predicate, assert_objs)
        if predicate.item_type == 'predicates':
            pred_key = f'oc-pred:{predicate.slug}'
        elif predicate.item_key:
            pred_key = predicate.item_key
        else:
            pred_key = f'https://{predicate.uri}'
        act_dict[pred_key] = pred_objects
    return act_dict


def get_observations_attributes_from_assertion_qs(assert_qs):
    """Gets observations and attributes in observations"""
    grp_index_attribs = ['observation', 'event', 'attribute_group', 'predicate']
    grouped_asserts = make_tree_dict_from_grouped_qs(
        qs=assert_qs, 
        index_list=grp_index_attribs
    )
    observations = []
    for observation, events in grouped_asserts.items():
        act_obs = LastUpdatedOrderedDict()
        act_obs['id'] = f'#-obs-{observation.slug}'
        act_obs['label'] = observation.label
        # NOTE: we've added act_obs to the observations list, but
        # we are continuing to modify it, even though it is part this
        # observations list already. 
        observations.append(act_obs)
        for event, attrib_groups in events.items():
            if str(event.uuid) == configs.DEFAULT_EVENT_UUID:
                # NOTE: No event node is specified here, so all the
                # attribute groups and predicates will just be added
                # directly to the act_obs dictionary.
                #
                # How? The beauty of mutable dicts! Below, this will
                # mean that act_obs gets updated as act_event gets
                # updated, since they refer to the same object.
                act_event = act_obs
            else:
                # Make a new act_event dictionary, because we're
                # specifying a new node within this observation.
                act_event = LastUpdatedOrderedDict()
                act_event['id'] = f'#-event-{event.slug}'
                act_event['label'] = event.label
                act_event['type'] = 'oc-gen:events'
                act_obs.setdefault('oc-gen:has-events', [])
                act_obs['oc-gen:has-events'].append(act_event)
            for attrib_group, preds in attrib_groups.items():
                if str(attrib_group.uuid) == configs.DEFAULT_ATTRIBUTE_GROUP_UUID:
                    # NOTE: no attribute group node is specified here, so all
                    # the predicates will be added to the act_event dictionary.
                    #
                    # How? The beauty of mutable dicts! Again, the act_attrib_grp 
                    # will be the same object as the act_event.
                    act_attrib_grp = act_event
                else:
                    act_attrib_grp = LastUpdatedOrderedDict()
                    act_attrib_grp['id'] = f'#-attribute-group-{attrib_group.slug}'
                    act_attrib_grp['label'] = attrib_group.label
                    act_attrib_grp['type'] = 'oc-gen:attribute-groups'
                    act_event.setdefault('oc-gen:has-attribute-groups', [])
                    act_event['oc-gen:has-attribute-groups'].append(act_attrib_grp)
                # Now add the predicate keys and their assertion objects to
                # the act_attrib_grp
                act_attrib_grp = add_predicates_assertions_to_dict(
                    pred_keyed_assert_objs=preds, 
                    act_dict=act_attrib_grp
                )

    return observations


def make_subject_dict(subject):
    output = LastUpdatedOrderedDict()
    output['uuid'] = str(subject.uuid)
    output['slug'] = subject.slug
    output['label'] = subject.label
    if str(subject.item_class.uuid) != configs.DEFAULT_CLASS_UUID:
        if subject.item_class.item_key:
            output['category'] =subject.item_class.item_key
        else:
            output['category'] = f'https://{subject.item_class.uri}'
    return output


def make_representation_dict(subject_id):
    """Makes a representation dict for a subject id"""
    subject = AllManifest.objects.filter(
        uuid=subject_id
    ).select_related(
        'project'
    ).select_related(
        'item_class'
    ).first()
    if not subject:
        return None
    rep_dict = make_subject_dict(subject)
    assert_qs = get_item_assertions(subject_id)
    if not len(assert_qs):
        return rep_dict
    if subject.item_type in ['subjects', 'media', 'documents', 'persons', 'projects']:
        # These types of items have nested nodes of observations, 
        # events, and attribute-groups
        observations = get_observations_attributes_from_assertion_qs(assert_qs)
        rep_dict['oc-gen:has-obs'] = observations
    else:
        # The following is for other types of items that don't have lots
        # of nested observation, event, and attribute nodes.
        pred_keyed_assert_objs = make_tree_dict_from_grouped_qs(
            qs=assert_qs, 
            index_list=['predicate']
        )
        rep_dict = add_predicates_assertions_to_dict(
            pred_keyed_assert_objs, 
            act_dict=rep_dict
        )
    # NOTE: This adds Dublin Core metadata
    rep_dict = metadata.add_dublin_core_literal_metadata(
        subject, 
        assert_qs, 
        act_dict=rep_dict
    )
    # NOTE: This add project Dublin Core metadata.
    proj_metadata_qs = metadata.get_project_metadata_qs(
        project=subject.project
    )
    pred_keyed_assert_objs = make_tree_dict_from_grouped_qs(
        qs=proj_metadata_qs, 
        index_list=['predicate']
    )
    rep_dict = add_predicates_assertions_to_dict(
        pred_keyed_assert_objs, 
        act_dict=rep_dict
    )
    return rep_dict
        