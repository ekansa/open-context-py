
import copy

from django.core.cache import caches

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items import labels
from opencontext_py.apps.all_items import models_utils


""" Recursive functions for hierarchies
import importlib
from opencontext_py.apps.all_items.models import AllManifest
from opencontext_py.apps.all_items import hierarchy

man_obj = AllManifest.objects.filter(
    item_type='class', 
    label__icontains='bos taurus'
).exclude(uri__contains='eol.org').first()

importlib.reload(hierarchy)
paths = hierarchy.get_concept_parent_paths(child_obj=man_obj)
paths = hierarchy.get_concept_hierarchy_paths_containing_item(child_obj=man_obj)

"""


# These item types may be in SKOS or OWL hiearchies.
ITEM_TYPES_FOR_CONCEPT_HIERARCHIES = [
    'predicates',
    'types',
    'class',
    'property',
]
# These item types should have their parent vocabulary as their parent.
ITEM_TYPES_FOR_VOCAB_PARENTS = [
    'units',
    'uri',
]


def get_list_concept_children_recursive(parent_obj, use_cache=True, all_children=None):
    """Gets a list of objects that are children (in some way),
       of a given parent_obj

    :param AllManifest parent_obj: The item that we want to put
            into a list of hierarchy lists.

    return list of child concepts.
    """
    if not all_children:
        all_children = []
    act_children = models_utils.get_immediate_concept_children_objs(
        parent_obj, 
        use_cache=use_cache,
    )
    for act_obj in act_children:
        if act_obj in all_children:
            continue
        all_children.append(act_obj)
        all_children = get_list_concept_children_recursive(
            parent_obj=act_obj,
            use_cache=use_cache,
            all_children=all_children,
        )
    return all_children


def get_concept_parent_paths(child_obj, use_cache=True, paths=None):
    """Makes concept hierarchy paths for child concept. 
    
    A concept may have multiple parents, so this will make multiple
    lists of parents for each independent hierarchy path. Each path
    list goes from small(specific) to big (general).

    Returns a list of lists.
    """
    if paths is None:
        paths = [[child_obj]]
    parent_objs = models_utils.get_immediate_concept_parent_objs(
        child_obj, 
        use_cache=True,
    )
    if not parent_objs:
        return paths
    new_paths = []
    for parent_obj in parent_objs:
        parent_paths = []
        for path in paths:
            new_path = copy.deepcopy(path)
            new_path.append(parent_obj)
            parent_paths.append(new_path)
        new_paths += get_concept_parent_paths(
            parent_obj, 
            use_cache=True, 
            paths=parent_paths
        )
    return new_paths


def get_concept_hierarchy_paths_containing_item(child_obj, use_cache=True):
    """Gets a list of hierarchy paths for a child obj,
       starting from most general to most specific (the child_obj)

    :param AllManifest child_obj: The item that we want to put
            into a list of hierarchy lists.

    return list of hierarchy lists.
    """
    raw_paths = get_concept_parent_paths(child_obj, use_cache=use_cache)
    paths = [list(reversed(p)) for p in raw_paths]
    return paths


def get_project_hierarchy_db(proj_man_obj):
    i = 0
    if proj_man_obj.item_type != 'projects':
        proj_man_obj = proj_man_obj.project
    path = [proj_man_obj]
    i = 0
    last_proj = proj_man_obj
    while i < 10 and str(last_proj.uuid) != configs.OPEN_CONTEXT_PROJ_UUID:
        last_proj = last_proj.project
        if str(last_proj.uuid) == configs.OPEN_CONTEXT_PROJ_UUID:
            break
        path.append(last_proj)
        i += 1
    return list(reversed(path))


def get_project_hierarchy(man_obj, use_cache=True):
    if man_obj.item_type == 'projects':
        proj_man_obj = man_obj
    else:
        proj_man_obj = man_obj.project
    if not use_cache:
        return get_project_hierarchy_db(proj_man_obj)
        
    cache_key = f'parent-projects-{str(proj_man_obj.uuid)}'
    cache = caches['redis']
    path = cache.get(cache_key)
    if path:
        return path
    path = get_project_hierarchy_db(proj_man_obj)
    try:
        cache.set(cache_key, path)
    except:
        pass
    return path


def get_hierarchy_paths_w_alt_labels_by_item_type(item_man_obj, add_alt_label=True, use_cache=True):
    """Get hierarchy paths list of lists for a manifest object

    :param AllManifest item_man_obj: The item that we want to put
        into a list of hierarchy lists.

    return list of hierarchy lists.
    """
    if item_man_obj.item_type in (ITEM_TYPES_FOR_CONCEPT_HIERARCHIES + ITEM_TYPES_FOR_VOCAB_PARENTS):
        # Use database lookups to get concept hierarchies if
        # the item type is relevant to this kind of lookup.
        raw_hierarchy_paths = get_concept_hierarchy_paths_containing_item(
            item_man_obj,
            use_cache=use_cache,
        )
    elif item_man_obj.item_type == 'projects':
        raw_hierarchy_paths = [
            get_project_hierarchy(
                item_man_obj,
                use_cache=use_cache,
            )
        ]
    else:
        raw_hierarchy_paths = [[item_man_obj]]

    if (item_man_obj.item_type in ITEM_TYPES_FOR_VOCAB_PARENTS 
        and str(item_man_obj.context.uuid) != configs.OPEN_CONTEXT_PROJ_UUID):
        raw_raw_hierarchy_paths = copy.deepcopy(raw_hierarchy_paths)
        # Make sure the context of the URI entity item is at the root of all of the
        # hierarchy paths for this item.
        raw_hierarchy_paths = [([item_man_obj.context] + p) for p in raw_raw_hierarchy_paths]

    if not add_alt_label:
        return raw_hierarchy_path
    # Now get the alternative labels if they exist. This step also
    # converts manifest objects into solr doc creation friendly
    # dictionary objects.
    hierarchy_paths = []
    for raw_hierarchy_path in raw_hierarchy_paths:
        hierarchy_path = []
        for item_obj in raw_hierarchy_path:
            other_labels = labels.get_other_labels(item_obj, use_cache=use_cache)
            if other_labels:
                item_obj.alt_label = other_labels[0]
                item_obj.other_labels = other_labels
            hierarchy_path.append(item_obj)
        hierarchy_paths.append(hierarchy_path)
    return hierarchy_paths


def get_vocabulary_children_objs_db(vocab_man_obj):
    """Get top children items for a given manifest object of a vocabulary"""

    from opencontext_py.apps.all_items.models import (AllManifest, AllAssertion)

    if vocab_man_obj.item_type != 'vocabularies':
        return None
    act_children_qs = AllManifest.objects.filter(
        context=vocab_man_obj,
        item_type='vocabularies',
    )
    if act_children_qs.count() > 0:
        # This is a vocabulary with a child vocabulary. This can happen with Period-O
        act_children = [m_obj for m_obj in act_children_qs]
        return act_children
    # Check for the root concepts of the vocabulary
    subj_super_qs = AllAssertion.objects.filter(
        object__context=vocab_man_obj,
        predicate_id__in=(
            configs.PREDICATE_LIST_SBJ_IS_SUPER_OF_OBJ
            + configs.PREDICTATE_LIST_CONTEXT_SBJ_IS_SUPER_OF_OBJ
        ),
    )
    subj_subord_qs = AllAssertion.objects.filter(
        subject__context=vocab_man_obj,
        predicate_id__in=configs.PREDICATE_LIST_SBJ_IS_SUBORD_OF_OBJ,
    )
    uuids_q_parents = [ass_obj.object.uuid for ass_obj in subj_super_qs]
    uuids_q_parents += [ass_obj.subject.uuid for ass_obj in subj_subord_qs]
    uuids_q_parents = set(uuids_q_parents)
    # Get "root" concepts in a vocabulary, as defined by those items that
    # lack a parent concept in their hierarchy
    act_children_qs = AllManifest.objects.filter(
        context=vocab_man_obj,
    ).exclude(
        uuid__in=uuids_q_parents,
    )
    act_children = [m_obj for m_obj in act_children_qs]
    return act_children


def get_next_children_w_alt_labels_by_item_type_db(item_man_obj, add_alt_label=True, use_cache=False):

    # Import here to avoid circular imports.
    from opencontext_py.apps.all_items.models import (AllManifest, AllAssertion)

    if item_man_obj.item_type in (ITEM_TYPES_FOR_CONCEPT_HIERARCHIES + ITEM_TYPES_FOR_VOCAB_PARENTS):
        # Use database lookups to get concept hierarchies if
        # the item type is relevant to this kind of lookup.
        act_children = models_utils.get_immediate_concept_children_objs(
            item_man_obj, 
            use_cache=use_cache,
        )
    elif item_man_obj.item_type == 'projects' and str(item_man_obj.item_class.uuid) == configs.CLASS_OC_DATA_PUB_UUID:
        act_children_qs = AllManifest.objects.filter(
            item_type='projects', 
            item_class_id=configs.CLASS_OC_DATA_PUB_UUID,
            context=item_man_obj,
        )
        act_children = [m_obj for m_obj in act_children_qs]
    elif item_man_obj.item_type == 'subjects':
        a_qs = AllAssertion.objects.filter(
            subject=item_man_obj,
            predicate_id=configs.PREDICATE_CONTAINS_UUID,
        ).select_related('object')
        act_children = [ass_obj.object for ass_obj in a_qs]
    elif item_man_obj.item_type == 'vocabularies':
        act_children = get_vocabulary_children_objs_db(vocab_man_obj=item_man_obj)
    else:
        return []

    if not add_alt_label:
        return act_children
    labeled_children = []
    for item_obj in act_children:
        other_labels = labels.get_other_labels(item_obj, use_cache=use_cache)
        if other_labels:
            item_obj.alt_label = other_labels[0]
            item_obj.other_labels = other_labels
        else:
            item_obj.alt_label = None
            item_obj.other_labels = None
        labeled_children.append(item_obj)
    return labeled_children
    

def get_next_children_w_alt_labels_by_item_type(item_man_obj, add_alt_label=True, use_cache=True):
    if not use_cache:
        # Return the results with no caching
        return get_next_children_w_alt_labels_by_item_type_db(
            item_man_obj, 
            add_alt_label=add_alt_label, 
            use_cache=False
        )
    cache_key = f'item-children-{str(add_alt_label)}-{str(item_man_obj.uuid)}'
    cache = caches['redis']
    act_children = cache.get(cache_key)
    if isinstance(act_children, list):
        # We have cached results.
        return act_children
    act_children = get_next_children_w_alt_labels_by_item_type_db(
        item_man_obj, 
        add_alt_label=True, 
        use_cache=use_cache,
    )
    if isinstance(act_children, list):
        # set the cache with a good result
        try:
            cache.set(cache_key, act_children)
        except:
            pass
    if not act_children:
        return []
    return act_children
    