
import copy

from django.db.models import OuterRef, Subquery

from opencontext_py.libs.general import LastUpdatedOrderedDict

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllResource,
    AllIdentifier,
)

from opencontext_py.apps.all_items.representations import geojson
from opencontext_py.apps.all_items.representations import metadata
from opencontext_py.apps.all_items.representations import equivalent_ld
from opencontext_py.apps.all_items.representations import rep_utils
from opencontext_py.apps.all_items.representations import table



def add_select_related_contexts_to_qs(
    qs,
    context_prefix='',
    depth=7,
    more_related_objs=['item_class']
):
    """Adds select_related contexts to a queryset

    :param QuerySet qs: The queryset that we will modify by adding
        select_related to AllManifest objects.
    :param str context_prefix: A prefix to identify which of the
        queryset manifest objects we want use for select_related
    :param int depth: The depth of how many steps of select_related
        contexts we want to de-reference. We default to 7 which is
        enough to go up 7 levels of context hierarchy.
    :param list more_related_objs: A list of additional related
        AllManifest objects related to the context objects that
        we want to dereference.
    """
    # NOTE: This is all about reducing the number of queries we send to the
    # database. This most important use case for this is to look up parent
    # context paths of manifest "subjects" item_types.
    act_path = context_prefix
    next_context = 'context'
    for _ in range(depth):
        act_path += next_context
        next_context = '__context'
        qs = qs.select_related(act_path)
        for rel_obj in more_related_objs:
            qs = qs.select_related(f'{act_path}__{rel_obj}')
    return qs


def make_grouped_by_dict_from_queryset(qs, index_list):
    """Makes a dictionary, grouped by attributes of query set objects

    :param list index_list: List of attributes in objects of the
       query set we want to use as group-by criteria.
    """
    keyed_objects = LastUpdatedOrderedDict()
    for obj in qs:
        key = tuple(getattr(obj, act_attrib) for act_attrib in index_list)
        keyed_objects.setdefault(key, []).append(obj)
    return keyed_objects


def get_dict_path_value(path_keys_list, dict_obj, default=None):
    """Get a value from a dictionary object by a list of keys

    :param list path_keys_list: A list of hierarchically organized
       keys to select within the tree of a dict_obj
    :param dict dict_obj: A dictionary object that is the source
       of the value we want to select with the path_key_list.
    :param (any) default: A default value to return if the
       path_keys_list can't be found.
    """
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


def get_item_assertions(
        subject_id,
        select_related_object_contexts=False,
        get_geo_overlays=False,
    ):
    """Gets an assertion queryset about an item"""

    # Limit this subquery to only 1 result, the first.
    thumbs_qs = AllResource.objects.filter(
        item=OuterRef('object'),
        resourcetype_id=configs.OC_RESOURCE_THUMBNAIL_UUID,
    ).order_by().values('uri')[:1]

    class_icon_qs = AllResource.objects.filter(
        item=OuterRef('object__item_class'),
        resourcetype_id=configs.OC_RESOURCE_ICON_UUID,
    ).order_by().values('uri')[:1]

    # ORCID IDs for project creators and contributors
    orcid_id_qs = AllIdentifier.objects.filter(
        item=OuterRef('object'),
        scheme='orcid',
    ).order_by().values('id')[:1]

    # DC-Creator equivalent predicate
    dc_creator_qs = AllAssertion.objects.filter(
        subject=OuterRef('predicate'),
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        object_id=configs.PREDICATE_DCTERMS_CREATOR_UUID,
        visible=True,
    ).order_by().values('object')[:1]

    # DC-Contributor equivalent predicate
    dc_contributor_qs = AllAssertion.objects.filter(
        subject=OuterRef('predicate'),
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        object_id=configs.PREDICATE_DCTERMS_CONTRIBUTOR_UUID,
        visible=True,
    ).order_by().values('object')[:1]

    qs = AllAssertion.objects.filter(
        subject_id=subject_id,
        visible=True,
    ).exclude(
        # NOTE: Keep this for debugging. Sometimes vue won't render a
        # string with bad characters. We had trouble with
        # <http://blah.org> (not valid HTML) in the string.
        # predicate__data_type__in=['xsd:string',]
        # predicate__slug__in=['40-bibliography-references-cited-and-others'],
    ).select_related(
        'subject'
    ).select_related(
        'observation'
    ).select_related(
        'event'
    ).select_related(
        'attribute_group'
    ).select_related(
        'predicate'
    ).select_related(
        'predicate__item_class'
    ).select_related(
        'predicate__context'
    ).select_related(
        'language'
    ).select_related(
        'object'
    ).select_related(
        'object__item_class'
    ).select_related(
        'object__context'
    ).order_by(
        'obs_sort',
        'event_sort',
        'attribute_group_sort',
        'attribute_group__sort',
        'sort',
        'object__item_class__label',
        'object__sort',
    ).annotate(
        object_thumbnail=Subquery(thumbs_qs)
    ).annotate(
        object_class_icon=Subquery(class_icon_qs)
    ).annotate(
        object_orcid=Subquery(orcid_id_qs)
    ).annotate(
        # This will indicate if a predicate is equivalent to a
        # dublin core creator.
        predicate_dc_creator=Subquery(dc_creator_qs)
    ).annotate(
        # This will indicate if a predicate is equivalent to a
        # dublin core contributor.
        predicate_dc_contributor=Subquery(dc_contributor_qs)
    )
    if select_related_object_contexts:
        # Get the context hierarchy for related objects. We typically
        # only do this for media and documents.
        qs =  add_select_related_contexts_to_qs(
            qs,
            context_prefix='object__'
        )
    return qs


def get_related_subjects_item_from_object_id(object_id):
    """Gets a Query Set of subjects items related to an assertion object_id"""
    # NOTE: Some media and documents items are only related to
    # an item_type subject via an assertion where the media and
    # documents items is the object of a assertion relationship.
    # Since an item_type = 'subjects' is needed to establish the
    # full context of a media or document item, and we won't necessarily
    # get a relationship to an item_type = 'subjects' item from
    # the get_item_assertions function, we will often need to
    # do this additional query.
    rel_subj_item_assetion_qs = AllAssertion.objects.filter(
        object_id=object_id,
        subject__item_type='subjects',
        visible=True,
    ).select_related(
        'subject'
    ).select_related(
        'subject__item_class'
    ).select_related(
        'subject__context'
    )
    rel_subj_item_assetion_qs = add_select_related_contexts_to_qs(
        rel_subj_item_assetion_qs,
        context_prefix='subject__'
    )
    return rel_subj_item_assetion_qs.first()


def get_related_subjects_item_assertion(item_man_obj, assert_qs):
    """Gets the related subject item for a media or documents subject item"""
    if item_man_obj.item_type not in ['media', 'documents', 'tables',]:
        return None

    for assert_obj in assert_qs:
        if assert_obj.object.item_type == 'subjects':
            return assert_obj.object

    # An manifest item_type='subjects' is not the object of any of
    # the assert_qs assertions, so we need to do another database pull
    # to check for manifest item_type 'subjects' items that are the
    # subject of an assertion.
    rel_subj_item_assetion = get_related_subjects_item_from_object_id(
        object_id=item_man_obj.uuid
    )
    if not rel_subj_item_assetion:
        return None
    return rel_subj_item_assetion.subject


def get_observations_attributes_from_assertion_qs(
    assert_qs,
    for_edit=False,
    for_solr_or_html=False
):
    """Gets observations and attributes in observations

    :param QuerySet assert_qs: A query set of assertions made on the item
    :param bool for_edit: Do we want an output with additional identifiers
        useful for editing.
    """
    grp_index_attribs = ['observation', 'event', 'attribute_group', 'predicate']
    grouped_asserts = make_tree_dict_from_grouped_qs(
        qs=assert_qs,
        index_list=grp_index_attribs
    )
    observations = []
    for observation, events in grouped_asserts.items():
        act_obs = LastUpdatedOrderedDict()
        act_obs['id'] = f'#obs-{observation.slug}'
        act_obs['label'] = observation.label
        if for_solr_or_html:
            # Let our template know we've got a default observation
            act_obs['default'] = (str(observation.uuid) == configs.DEFAULT_OBS_UUID)
        # NOTE: we've added act_obs to the observations list, but
        # we are continuing to modify it, even though it is part this
        # observations list already.
        observations.append(act_obs)
        for event, attrib_groups in events.items():
            if not for_solr_or_html and str(event.uuid) == configs.DEFAULT_EVENT_UUID:
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
                act_event['id'] = f'#event-{event.slug}'
                act_event['label'] = event.label
                act_event['type'] = 'oc-gen:events'
                if for_solr_or_html:
                    # Let our template know we've got a default event.
                    act_event['default'] = (str(event.uuid) == configs.DEFAULT_EVENT_UUID)
                act_obs.setdefault('oc-gen:has-events', [])
                act_obs['oc-gen:has-events'].append(act_event)
            for attrib_group, preds in attrib_groups.items():
                if not for_solr_or_html and str(attrib_group.uuid) == configs.DEFAULT_ATTRIBUTE_GROUP_UUID:
                    # NOTE: no attribute group node is specified here, so all
                    # the predicates will be added to the act_event dictionary.
                    #
                    # How? The beauty of mutable dicts! Again, the act_attrib_grp
                    # will be the same object as the act_event.
                    act_attrib_grp = act_event
                else:
                    act_attrib_grp = LastUpdatedOrderedDict()
                    act_attrib_grp['id'] = f'#attribute-group-{attrib_group.slug}'
                    act_attrib_grp['label'] = attrib_group.label
                    act_attrib_grp['type'] = 'oc-gen:attribute-groups'
                    if for_solr_or_html:
                        # Let our template know we've got a default attribute group
                         act_attrib_grp['default'] = (
                            str(attrib_group.uuid) == configs.DEFAULT_ATTRIBUTE_GROUP_UUID
                        )
                    act_event.setdefault('oc-gen:has-attribute-groups', [])
                    act_event['oc-gen:has-attribute-groups'].append(act_attrib_grp)
                # Now add the predicate keys and their assertion objects to
                # the act_attrib_grp
                act_attrib_grp = rep_utils.add_predicates_assertions_to_dict(
                    pred_keyed_assert_objs=preds,
                    act_dict=act_attrib_grp,
                    for_edit=for_edit,
                    for_solr_or_html=for_solr_or_html,
                )

    return observations


def get_related_media_resources(item_man_obj):
    """Gets related media resources for a media subject"""
    if item_man_obj.item_type not in ['media', 'projects']:
        return None
    resource_qs = AllResource.objects.filter(
        item=item_man_obj,
    ).select_related(
        'resourcetype'
    ).select_related(
        'mediatype'
    ).select_related(
        'mediatype__context'
    )
    return resource_qs


def add_related_media_files_dicts(item_man_obj, act_dict=None):
    resource_qs = get_related_media_resources(item_man_obj)
    if not resource_qs:
        return act_dict
    if not act_dict:
        act_dict = LastUpdatedOrderedDict()
    act_dict["oc-gen:has-files"] = []
    for res_obj in resource_qs:
        res_dict = LastUpdatedOrderedDict()
        res_dict['id'] = rep_utils.make_web_url(res_obj)
        res_dict['type'] = rep_utils.get_item_key_or_uri_value(res_obj.resourcetype)
        if res_obj.mediatype:
            res_dict['dc-terms:hasFormat'] = rep_utils.make_web_url(res_obj.mediatype)
        if res_obj.filesize and res_obj.filesize > 1:
            res_dict['dcat:size'] = int(res_obj.filesize)
        act_dict["oc-gen:has-files"].append(res_dict)
    return act_dict


def add_to_parent_context_list(manifest_obj, context_list=None, for_solr_or_html=False):
    """Recursively add to a list of parent contexts

    :param AllManifest manifest_obj: Instance of the AllManifest model that
        we want to see context information
    :param list context_list: A list context dictionaries that gets extended
        by this function
    :param bool for_solr_or_html: A boolean flag, if True add additional keys useful
        for HTML tempating
    """
    if context_list is None:
        context_list = []
    if manifest_obj.item_type != 'subjects':
        return context_list
    item_dict = LastUpdatedOrderedDict()
    item_dict['id'] = rep_utils.make_web_url(manifest_obj)
    item_dict['slug'] = manifest_obj.slug
    item_dict['label'] = manifest_obj.label
    item_dict['type'] = rep_utils.get_item_key_or_uri_value(manifest_obj.item_class)
    if for_solr_or_html:
        item_dict['object_id'] = str(manifest_obj.uuid)
        item_dict['object__item_type'] = manifest_obj.item_type
        item_dict['item_class_id'] = str(manifest_obj.item_class.uuid)
        item_dict['item_class__label'] = manifest_obj.item_class.label
    context_list.append(item_dict)
    if (manifest_obj.context.item_type == 'subjects'
       and str(manifest_obj.context.uuid) != configs.DEFAULT_SUBJECTS_ROOT_UUID):
        context_list = add_to_parent_context_list(
            manifest_obj.context,
            context_list=context_list,
            for_solr_or_html=for_solr_or_html,
        )
    return context_list


def start_item_representation_dict(item_man_obj, for_solr_or_html=False):
    """Start making an item representation dictionary object"""
    rep_dict = LastUpdatedOrderedDict()
    rep_dict["@context"] = [
        "https://opencontext.org/contexts/item.json",
        "http://geojson.org/geojson-ld/geojson-context.jsonld",
    ]
    rep_dict['id'] = rep_utils.make_web_url(item_man_obj)
    rep_dict['uuid'] = str(item_man_obj.uuid)
    rep_dict['slug'] = item_man_obj.slug
    rep_dict['label'] = item_man_obj.label
    if item_man_obj.item_class and str(item_man_obj.item_class.uuid) != configs.DEFAULT_CLASS_UUID:
        if item_man_obj.item_class.item_key:
            rep_dict['category'] = item_man_obj.item_class.item_key
        else:
            rep_dict['category'] = rep_utils.make_web_url(item_man_obj.item_class)
    if for_solr_or_html:
        if item_man_obj.item_class:
            rep_dict['item_class__label'] = item_man_obj.item_class.label
            rep_dict['item_class__slug'] = item_man_obj.item_class.slug
        else:
            rep_dict['item_class__label'] = None
            rep_dict['item_class__slug'] = None
    return rep_dict


def get_annotate_item_manifest_obj(subject_id):
    """Gets an annotated item manifest object and joined objects

    :param str subject_id: UUID or string UUID for the item
    """
    # Limit this subquery to only 1 result, the first.
    item_hero_qs = AllResource.objects.filter(
        item_id=OuterRef('uuid'),
        resourcetype_id=configs.OC_RESOURCE_HERO_UUID,
    ).values('uri')[:1]

    proj_hero_qs = AllResource.objects.filter(
        item_id=OuterRef('project'),
        resourcetype_id=configs.OC_RESOURCE_HERO_UUID,
    ).values('uri')[:1]

    proj_proj_hero_qs = AllResource.objects.filter(
        item_id=OuterRef('project__project'),
        resourcetype_id=configs.OC_RESOURCE_HERO_UUID,
    ).values('uri')[:1]

    # Main persistent identifiers
    ark_qs = AllIdentifier.objects.filter(
        item_id=OuterRef('uuid'),
        scheme='ark',
    ).values('id')[:1]

    doi_qs = AllIdentifier.objects.filter(
        item_id=OuterRef('uuid'),
        scheme='doi',
    ).values('id')[:1]

    orcid_qs = AllIdentifier.objects.filter(
        item_id=OuterRef('uuid'),
        scheme='orcid',
    ).values('id')[:1]

    item_man_obj_qs = AllManifest.objects.filter(
        uuid=subject_id
    ).select_related(
        'project'
    ).select_related(
        'project__project'
    ).select_related(
        'item_class'
    ).select_related(
        'context'
    ).annotate(
        hero=Subquery(item_hero_qs)
    ).annotate(
        proj_hero=Subquery(proj_hero_qs)
    ).annotate(
        proj_proj_hero=Subquery(proj_proj_hero_qs)
    ).annotate(
        ark=Subquery(ark_qs)
    ).annotate(
        doi=Subquery(doi_qs)
    ).annotate(
        orcid=Subquery(orcid_qs)
    )

    item_man_obj_qs = add_select_related_contexts_to_qs(
        item_man_obj_qs
    )

    item_man_obj = item_man_obj_qs.first()
    return item_man_obj


def add_persistent_identifiers(item_man_obj, rep_dict):
    """Adds persistent identifiers to a rep_dict

    :param AllManifest item_man_obj: The item's manifest object,
        annotated with ark, doi, and orcid attributes (all of
        which may be None if no persistent id's exist for this
        item)
    """
    if (not item_man_obj.ark
        and not item_man_obj.doi
        and not item_man_obj.orcid):
        return rep_dict
    if not 'dc-terms:identifier' in rep_dict:
        rep_dict['dc-terms:identifier'] = []
    if item_man_obj.doi:
        rep_dict['dc-terms:identifier'].append(
            AllIdentifier().make_id_url('doi', item_man_obj.doi, 'https://')
        )
    if item_man_obj.orcid:
        rep_dict['dc-terms:identifier'].append(
            AllIdentifier().make_id_url('orcid', item_man_obj.orcid, 'https://')
        )
    if item_man_obj.ark:
        rep_dict['dc-terms:identifier'].append(
            AllIdentifier().make_id_url('ark', item_man_obj.ark, 'https://')
        )
    return rep_dict


def make_representation_dict(subject_id, for_solr_or_html=False, for_solr=False):
    """Makes a representation dict for a subject id"""
    # This will most likely get all the context hierarchy in 1 query, thereby
    # limiting the number of times we hit the database.

    if for_solr:
        for_solr_or_html = True

    item_man_obj = get_annotate_item_manifest_obj(subject_id)

    if not item_man_obj:
        return None, None

    rep_dict = start_item_representation_dict(
        item_man_obj,
        for_solr_or_html=for_solr_or_html
    )

    select_related_object_contexts = False
    if item_man_obj.item_type in ['media', 'documents']:
        # We'll want to include the selection of related
        # object contexts to get the spatial hierarchy of related
        # item_type subjects.
        select_related_object_contexts = True

    # Get the assertion query set for this item
    assert_qs = get_item_assertions(
        subject_id=item_man_obj.uuid,
        select_related_object_contexts=select_related_object_contexts,
    )
    # Get the related subjects item (for media and documents)
    # NOTE: rel_subjects_man_obj will be None for all other item types.
    rel_subjects_man_obj = get_related_subjects_item_assertion(
        item_man_obj,
        assert_qs
    )

    # Adds geojson features. This will involve a database query to fetch
    # spacetime objects.
    rep_dict = geojson.add_geojson_features(
        item_man_obj,
        rel_subjects_man_obj=rel_subjects_man_obj,
        act_dict=rep_dict,
        for_solr=for_solr,
    )

    # Add the list of media resources associated with this item if
    # the item has the appropriate item_type.
    rep_dict = add_related_media_files_dicts(item_man_obj, act_dict=rep_dict)

    if item_man_obj.item_type == 'subjects':
        parent_list = add_to_parent_context_list(
            item_man_obj.context,
            for_solr_or_html=for_solr_or_html
        )
        if parent_list:
            # The parent order needs to be reversed to make the most
            # general first, followed by the most specific.
            parent_list.reverse()
            rep_dict['oc-gen:has-contexts'] = parent_list
    elif rel_subjects_man_obj:
        parent_list = add_to_parent_context_list(
            rel_subjects_man_obj,
            for_solr_or_html=for_solr_or_html
        )
        if parent_list:
            # The parent order needs to be reversed to make the most
            # general first, followed by the most specific.
            parent_list.reverse()
            rep_dict['oc-gen:has-linked-contexts'] = parent_list

    if item_man_obj.item_type in ['subjects', 'media', 'documents', 'persons', 'projects']:
        # These types of items have nested nodes of observations,
        # events, and attribute-groups
        obs_assert_qs = [ass for ass in assert_qs if ass.predicate.item_type == 'predicates']

        # Make some linked data assertion analogs based on the obs_assert_qs.
        # If they exist, equiv_assertions are non-database stored objects
        # that have attributes just like normal assertion objects. This
        # commonality allows common processing.
        equiv_assertions = equivalent_ld.make_ld_equivalent_assertions(
            item_man_obj,
            obs_assert_qs,
            for_solr=for_solr,
        )
        if not equiv_assertions:
            equiv_assertions = []
        # Add default equivalent assertions if needed.
        equiv_assertions = equivalent_ld.add_default_ld_equivalent_assertions(
            item_man_obj,
            equiv_assertions,
            for_solr=for_solr,
        )
        if equiv_assertions:
            obs_assert_qs += equiv_assertions

        observations = get_observations_attributes_from_assertion_qs(
            obs_assert_qs,
            for_solr_or_html=for_solr_or_html
        )
        rep_dict['oc-gen:has-obs'] = observations

        # The linked data (non 'predicates' assertions) get associated without
        # nested nodes.
        ld_assert_qs = [ass for ass in assert_qs if ass.predicate.item_type != 'predicates']
        pred_keyed_assert_objs = make_tree_dict_from_grouped_qs(
            qs=ld_assert_qs,
            index_list=['predicate']
        )
        rep_dict = rep_utils.add_predicates_assertions_to_dict(
            pred_keyed_assert_objs,
            act_dict=rep_dict,
            for_edit=for_solr_or_html
        )
        if for_solr:
            # Make sure the assertion objects are easily available for solr.
            rep_dict['for_solr_assert_objs'] = obs_assert_qs + ld_assert_qs
    else:
        # The following is for other types of items that don't have lots
        # of nested observation, event, and attribute nodes.
        pred_keyed_assert_objs = make_tree_dict_from_grouped_qs(
            qs=assert_qs,
            index_list=['predicate']
        )
        rep_dict = rep_utils.add_predicates_assertions_to_dict(
            pred_keyed_assert_objs,
            act_dict=rep_dict,
            for_edit=for_solr_or_html
        )
        if for_solr:
            # Make sure the assertion objects are easily available for solr.
            rep_dict['for_solr_assert_objs'] = assert_qs

    # Get table preview data (if a table, and if successful)
    rep_dict = table.get_preview_csv_data(
        item_man_obj=item_man_obj,
        act_dict=rep_dict,
    )
    # NOTE: This adds Dublin Core metadata
    rep_dict = metadata.add_dublin_core_literal_metadata(
        item_man_obj,
        rel_subjects_man_obj=rel_subjects_man_obj,
        act_dict=rep_dict
    )
    # First add item-specific Dublin Core creators, contributors.
    rep_dict = metadata.add_dc_creator_contributor_equiv_metadata(
        assert_qs,
        act_dict=rep_dict,
        for_solr_or_html=for_solr_or_html
    )
    if item_man_obj.context.item_type == 'vocabularies':
        vocab_meta_qs = metadata.get_vocabulary_metadata_qs(
            vocab=item_man_obj.context
        )
        pred_keyed_vocab_assert_objs = make_tree_dict_from_grouped_qs(
            qs=vocab_meta_qs,
            index_list=['predicate']
        )
        rep_dict = rep_utils.add_predicates_assertions_to_dict(
            pred_keyed_vocab_assert_objs,
            act_dict=rep_dict,
            add_objs_to_existing_pred=False,
            for_edit=for_solr_or_html,
        )
        rep_dict = metadata.check_add_vocabulary(
            vocab=item_man_obj.context,
            act_dict=rep_dict,
        )

    # NOTE: This add project Dublin Core metadata.
    if item_man_obj.item_type == 'projects' and str(item_man_obj.project.uuid) == configs.OPEN_CONTEXT_PROJ_UUID:
        # Get metadata for the current project, then filter only for the geographic overlay
        proj_metadata_qs = metadata.get_project_metadata_qs(
            project=item_man_obj
        )
        # We only want the geo-overlay, since we have a top-level project item.
        # This is for displaying a project's geooverlay should it exist.
        proj_metadata_qs = proj_metadata_qs.filter(
            predicate_id=configs.PREDICATE_GEO_OVERLAY_UUID
        )
    else:
        proj_metadata_qs = metadata.get_project_metadata_qs(
            project=item_man_obj.project
        )
    pred_keyed_assert_objs = make_tree_dict_from_grouped_qs(
        qs=proj_metadata_qs,
        index_list=['predicate']
    )
    # Add project metadata, but only for those predicates that
    # don't already have item-specific object values.
    rep_dict = rep_utils.add_predicates_assertions_to_dict(
        pred_keyed_assert_objs,
        act_dict=rep_dict,
        add_objs_to_existing_pred=False,
        for_edit=for_solr_or_html,
    )
    # Add the project relationship if it is missing
    rep_dict = metadata.check_add_project(
        project=item_man_obj.project,
        act_dict=rep_dict,
    )

    # Adds the default license if a license is still missing.
    rep_dict = metadata.check_add_default_license(
        rep_dict,
        for_solr=for_solr
    )

    # Add any persistent identifiers assigned to this item.
    rep_dict = add_persistent_identifiers(item_man_obj, rep_dict)

    return item_man_obj, rep_dict