
import copy

from django.conf import settings
from django.core.cache import caches

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)
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
    print(f'{child_obj.label} has {len(parent_objs)} parents')
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
    cache = caches['memory']
    path = cache.get(cache_key)
    if path:
        return path
    path = get_project_hierarchy_db(proj_man_obj)
    try:
        cache.set(cache_key, path)
    except:
        pass
    return path
    
