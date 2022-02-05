
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