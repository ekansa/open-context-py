import logging
import hashlib

from django.conf import settings
from django.core.cache import caches
from django.db.models import Q, OuterRef, Subquery, Prefetch

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllResource,
    AllSpaceTime,
)
from opencontext_py.apps.all_items.editorial import api as editorial_api
from opencontext_py.apps.all_items import hierarchy


logger = logging.getLogger(__name__)


def check_off_world(path):
    """Checks if a path has an off world item"""
    if not path:
        return False
    if path in ['Off World', 'Off+World']:
        return True
    return False


def db_get_manifest_item_by_path(path, filter_args):
    """Gets a manifest item by an item path

    :param str path: A string path values

    :return AllManifest or None
    """
    if check_off_world(path):
        man_obj_qs = AllManifest.objects.filter(
            Q(path=path)
            | Q(
                item_type='subjects',
                label=path,
                project_id=configs.OPEN_CONTEXT_PROJ_UUID,
            )
        )
    else:
        man_obj_qs = AllManifest.objects.filter(path=path)
    if filter_args:
        man_obj_qs = man_obj_qs.filter(**filter_args)
    return man_obj_qs.first()


def db_get_manifest_items_by_path(paths_list, filter_args):
    """Gets a manifest queryset filtered by a list of paths

    :param list paths_list: A list of string path values

    :return QuerySet of AllManifest items.
    """
    has_off_world = False
    for path in paths_list:
        if check_off_world(path):
            has_off_world = True
    if has_off_world:
        man_obj_qs = AllManifest.objects.filter(
            Q(path__in=paths_list)
            | Q(
                item_type='subjects',
                label__in=paths_list,
                project_id=configs.OPEN_CONTEXT_PROJ_UUID,
            )
        )
    else:
        man_obj_qs = AllManifest.objects.filter(path__in=paths_list)
    if filter_args:
        man_obj_qs = man_obj_qs.filter(**filter_args)
    man_obj_qs = man_obj_qs.select_related('context')
    return man_obj_qs


def make_path_manifest_item_cache_key(path, filter_args):
    """Makes a cache key for looking up a manifest item by path"""
    hash_obj = hashlib.sha1()
    path_item_str = f'context: {path} {str(filter_args)}'
    hash_obj.update(path_item_str.encode('utf-8'))
    id = hash_obj.hexdigest()
    return f'{settings.CACHE_PREFIX_SEARCH}{str(id)}'


def make_id_manifest_item_cache_key(identifier):
    """Makes a cache key for looking up a manifest item by any id"""
    hash_obj = hashlib.sha1()
    id_item_str = f'id: {identifier}'
    hash_obj.update(id_item_str.encode('utf-8'))
    id = hash_obj.hexdigest()
    return f'{settings.CACHE_PREFIX_SEARCH}{str(id)}'


def make_slug_manifest_children_cache_key(parent_slug):
    """Makes a cache key for looking up children of manifest item by a slug"""
    hash_obj = hashlib.sha1()
    id_item_str = f'children-of-slug: {parent_slug}'
    hash_obj.update(id_item_str.encode('utf-8'))
    id = hash_obj.hexdigest()
    return f'{settings.CACHE_PREFIX_SEARCH}{str(id)}'


def get_cache_manifest_item_by_path(
    path,
    filter_args={'item_type': 'subjects'},
    use_cache=True,
):
    """Gets a manifest object filtered by a context path

    :param list paths_list: A list of string path values

    :return AllManifest items.
    """
    if not use_cache:
        return db_get_manifest_item_by_path(
            path,
            filter_args=filter_args
        )

    cache = caches['redis_search']
    cache_key = make_path_manifest_item_cache_key(path, filter_args)
    man_obj = cache.get(cache_key)
    if man_obj:
        return man_obj

    # Didn't find it in the cache, so do a DB query
    man_obj = db_get_manifest_item_by_path(
        path,
        filter_args=filter_args
    )
    if not man_obj:
        return None
    try:
        cache.set(cache_key, man_obj)
    except:
        pass
    return man_obj


def get_cache_manifest_items_by_path(
    paths_list,
    filter_args={'item_type': 'subjects'},
    use_cache=True,
):
    """Gets and caches manifest items by their path

    :param list paths_list: A list of string path values

    :return list of AllManifest objects
    """
    if not use_cache:
        return db_get_manifest_items_by_path(
            paths_list,
            filter_args=filter_args
        )

    cache = caches['redis_search']
    output = []
    db_query_paths = []
    for path in paths_list:
        cache_key = make_path_manifest_item_cache_key(path, filter_args)
        man_obj = cache.get(cache_key)
        if man_obj:
            # We found the manifest object in the cache
            output.append(man_obj)
            continue
        # We still need to look up this path in the database.
        db_query_paths.append(path)

    if not db_query_paths:
        return output

    # We didn't find some paths in the cache, so do a DB query.
    for man_obj in db_get_manifest_items_by_path(
        db_query_paths,
        filter_args=filter_args
    ):
        output.append(man_obj)
        cache_key = make_path_manifest_item_cache_key(
            man_obj.path,
            filter_args
        )
        try:
            cache.set(cache_key, man_obj)
        except:
            pass
    return output


def get_cache_item_key_list():
    """Gets a list of item_keys that are actually in use."""
    # This should limit expensive queries on a field that is rarely used.
    cache = caches['redis_search']
    cache_key = 'manifest_item_keys_list'
    item_key_list = cache.get(cache_key)
    if item_key_list:
        # Item is already in the cache, so return it
        return item_key_list
    m_qs = AllManifest.objects.filter(
        item_key__isnull=False,
    ).distinct(
        'item_key'
    ).order_by(
        'item_key'
    ).values_list(
        'item_key', 
        flat=True
    )
    item_key_list = list(m_qs) 
    try:
        cache.set(cache_key, item_key_list)
    except:
        pass
    return item_key_list


def get_cache_man_obj_by_any_id(identifier, use_cache=True):
    """Gets and caches a manifest object by any type of unique id"""
    if not use_cache:
        return editorial_api.get_man_obj_by_any_id(identifier)

    cache = caches['redis_search']
    cache_key = make_id_manifest_item_cache_key(identifier)
    man_obj = cache.get(cache_key)
    if man_obj:
        # Found it in the cache, the fastest, happiest scenario
        return man_obj
    # This should reduce the number of some long queries
    item_key_list = get_cache_item_key_list()
    # Do a database lookup to get the item.
    man_obj = editorial_api.get_man_obj_by_any_id(
        identifier=identifier,
        item_key_list=item_key_list,
    )
    if not man_obj:
        return None
    try:
        cache.set(cache_key, man_obj)
    except:
        pass
    return man_obj


def get_man_obj_parent(man_obj):
    """Gets the parent manifest item for the input manifest item

    :param AllManifest item

    :return AllManifest item (parent)
    """
    hierarchy_paths = hierarchy.get_hierarchy_paths_w_alt_labels_by_item_type(man_obj)
    if not hierarchy_paths:
        return None

    path = hierarchy_paths[0]
    if len(path) < 2:
        # the man_obj is the only thing returned
        return None
    # The last item in the path is the input man_obj, this returns
    # the parent of that item
    return path[-2]


def get_man_obj_children_list(man_obj, use_cache=True):
    """Gets a list of children item dicts for an item entity object

    :param entity item: See the apps/entity/models entity object for a
        definition.
    """
    if not use_cache:
        return editorial_api.get_item_children(
            identifier=None,
            man_obj=man_obj,
            output_child_objs=True
        )

    cache = caches['redis_search']
    cache_key = make_slug_manifest_children_cache_key(man_obj.slug)
    children_objs = cache.get(cache_key)
    if children_objs is not None:
        # Found it in the cache, the fastest, happiest scenario
        return children_objs

    # Do a database lookup to get the item.
    children_objs = editorial_api.get_item_children(
        identifier=None,
        man_obj=man_obj,
        output_child_objs=True
    )
    if children_objs is None:
        return None
    try:
        cache.set(cache_key, children_objs)
    except:
        pass
    return children_objs


def db_get_projects_overlay_qs(project_slugs):
    """Get get a project (image) overlay

    :param str project_slugs: List string slug identifiers for a project
        that may image overlays
    """

    # NOTE: Some projects have digitized raster images
    # georeference and used as an overlay.
    geo_overlay_qs = AllResource.objects.filter(
        item=OuterRef('object'),
        resourcetype_id=configs.OC_RESOURCE_FULLFILE_UUID,
    ).values('uri')[:1]

    qs = AllAssertion.objects.filter(
        subject__slug__in=project_slugs,
        predicate__data_type='id',
        visible=True,
    ).filter(
       predicate_id=configs.PREDICATE_GEO_OVERLAY_UUID
    ).select_related(
        'object'
    ).annotate(
        object_geo_overlay=Subquery(geo_overlay_qs)
    )
    return qs


def get_project_overlay_qs(
    projects=None,
    project_slugs=None,
    use_cache=True
):
    """Get get a project (image) overlay via the cache"""
    if not project_slugs and projects:
        project_slugs = [p.slug for p in projects]
    if not len(project_slugs):
        return None

    # Sort the slugs generating a consistent cache key
    project_slugs.sort()
    if not use_cache:
        # Skip the case, just use the database.
        return db_get_projects_overlay_qs(project_slugs)

    hash_obj = hashlib.sha1()
    path_item_str = f'projects-overlay: {project_slugs}'
    hash_obj.update(path_item_str.encode('utf-8'))
    cache_key = f'{settings.CACHE_PREFIX_PROJ_META}ov_{str(hash_obj.hexdigest())}'
    cache = caches['redis_search']
    proj_overlay_qs = cache.get(cache_key)
    if proj_overlay_qs is not None:
        # We've already cached this, so returned the cached queryset
        return proj_overlay_qs
    proj_overlay_qs = db_get_projects_overlay_qs(project_slugs)
    # Evaluate the queryset (lazy load, so it caches evaluated)
    proj_overlay_qs.count()
    try:
        cache.set(cache_key, proj_overlay_qs)
    except:
        pass
    return proj_overlay_qs


def db_get_unique_project_item_class_list(
    project_slugs
):
    m_qs = AllManifest.objects.filter(
        project__slug__in=project_slugs
    ).exclude(
        item_class_id=configs.DEFAULT_CLASS_UUID,
    ).distinct(
        'item_type', 'item_class'
    ).select_related(
        'item_class'
    ).order_by(
        'item_type', 'item_class'
    ).values(
        'item_type',
        'item_class_id',
        'item_class__slug',
        'item_class__label',
        'item_class__uri',
    )
    proj_class_sum_list = [m for m in m_qs]
    return proj_class_sum_list


def get_unique_project_item_class_list(
    projects=None,
    project_slugs=None,
    use_cache=True
):
    if not project_slugs and projects:
        project_slugs = [p.slug for p in projects]
    if not len(project_slugs):
        return None
    # Sort the slugs generating a consistent cache key
    project_slugs.sort()
    if not use_cache:
        # Skip the case, just use the database.
        return  db_get_unique_project_item_class_list(project_slugs)

    hash_obj = hashlib.sha1()
    path_item_str = f'projects-item-class-summary: {project_slugs}'
    hash_obj.update(path_item_str.encode('utf-8'))
    cache_key = f'{settings.CACHE_PREFIX_PROJ_META}cl_{str(hash_obj.hexdigest())}'
    cache = caches['redis_search']
    proj_class_sum_list = cache.get(cache_key)
    if proj_class_sum_list is not None:
        # We've already cached this, so returned the cached list
        return proj_class_sum_list
    proj_class_sum_list = db_get_unique_project_item_class_list(project_slugs)
    try:
        cache.set(cache_key, proj_class_sum_list)
    except:
        pass
    return proj_class_sum_list


def db_get_proj_geo_qs_by_slugs(slugs):
    """Get get manifest_qs by slugs

    :param list(str) slugs: List string slug identifiers for objects
        in the AllManifest table
    """
    description_qs = AllAssertion.objects.filter(
        subject=OuterRef('item'),
        predicate_id=configs.PREDICATE_DCTERMS_DESCRIPTION_UUID,
        visible=True,
    ).order_by(
        'sort'
    ).values(
        'obj_string'
    )[:1]
    act_qs = AllSpaceTime.objects.filter(
        item__slug__in=slugs,
        item__item_type='projects'
    ).exclude(
        geometry_type__isnull=True
    ).select_related(
        'item'
    ).select_related(
        'item__project'
    ).select_related(
        'item__context'
    ).annotate(
        description=Subquery(description_qs)
    ).distinct(
        'item'
    ).order_by(
        'item',
        'feature_id',
    )
    return act_qs


def get_proj_geo_by_slugs(slugs, use_cache=True, reset_cache=False,):
    """Gets a project geo information objects by their slugs"""
    slugs.sort()
    if not use_cache:
        # Skip the case, just use the database.
        return  db_get_proj_geo_qs_by_slugs(slugs)
    hash_obj = hashlib.sha1()
    slug_str = f'proj-geo-slugs: {slugs}'
    hash_obj.update(slug_str.encode('utf-8'))
    cache_key = f'{settings.CACHE_PREFIX_PROJ_META}geo_{str(hash_obj.hexdigest())}'
    cache = caches['redis_search']
    if reset_cache:
        cache.delete(cache_key)
    act_qs = cache.get(cache_key)
    if act_qs is not None:
        # We've already cached this, so returned the cached list
        return act_qs
    act_qs = db_get_proj_geo_qs_by_slugs(slugs)
    # Evaluate the query, before we cache it because query sets
    # are lazy loaded.
    act_qs.count()
    try:
        cache.set(cache_key, act_qs)
    except:
        pass
    return act_qs



def db_get_project_desc_banner_qs(project_slugs, all_projects=False):
    """Get get a project description and (image) banners

    :param str project_slugs: List string slug identifiers for a project
        that may image overlays
    """
    item_description_qs = AllAssertion.objects.filter(
        subject=OuterRef('uuid'),
        predicate_id=configs.PREDICATE_DCTERMS_DESCRIPTION_UUID,
        visible=True,
    ).order_by(
        'sort'
    ).values(
        'obj_string'
    )[:1]

    proj_description_qs = AllAssertion.objects.filter(
        subject=OuterRef('project'),
        predicate_id=configs.PREDICATE_DCTERMS_DESCRIPTION_UUID,
        visible=True,
    ).order_by(
        'sort'
    ).values(
        'obj_string'
    )[:1]

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

    proj_hero_qs = AllManifest.objects.all(
    ).select_related(
        'project'
    ).select_related(
        'project__project'
    ).annotate(
        item_description=Subquery(item_description_qs)
    ).annotate(
        proj_description=Subquery(proj_description_qs)
    ).annotate(
        item_hero_hero=Subquery(item_hero_qs)
    ).annotate(
        proj_hero=Subquery(proj_hero_qs)
    ).annotate(
        proj_proj_hero=Subquery(proj_proj_hero_qs)
    )
    if project_slugs:
        proj_hero_qs = proj_hero_qs.filter(slug__in=project_slugs,)
    if all_projects:
        proj_hero_qs = proj_hero_qs.filter(item_type='projects')
    return proj_hero_qs


def get_project_desc_banner_qs(
    projects=None,
    project_slugs=None,
    use_cache=True,
    all_projects=False,
    reset_cache=False,
):
    """Get get a project (image) banners via the cache"""
    if not project_slugs and projects:
        project_slugs = [p.slug for p in projects]
    if not project_slugs and not all_projects:
        return None

    # Sort the slugs generating a consistent cache key
    if project_slugs:
        project_slugs.sort()
    if not use_cache:
        # Skip the case, just use the database.
        return db_get_project_desc_banner_qs(
            project_slugs,
            all_projects=all_projects
        )
    hash_obj = hashlib.sha1()
    if all_projects:
        path_item_str = f'projects-hero:ALL'
    else:
        path_item_str = f'projects-hero: {project_slugs}'
    hash_obj.update(path_item_str.encode('utf-8'))
    cache_key = f'{settings.CACHE_PREFIX_PROJ_META}hero_{str(hash_obj.hexdigest())}'
    cache = caches['redis_search']
    if reset_cache:
        cache.delete(cache_key)
    proj_desc_banner_qs = cache.get(cache_key)
    if proj_desc_banner_qs is not None:
        # We've already cached this, so returned the cached queryset
        return proj_desc_banner_qs
    proj_desc_banner_qs = db_get_project_desc_banner_qs(
        project_slugs,
        all_projects=all_projects
    )
    proj_desc_banner_qs.count() # evaluate for caching.
    try:
        cache.set(cache_key, proj_desc_banner_qs)
    except:
        pass
    if not proj_desc_banner_qs:
        return []
    return proj_desc_banner_qs


def get_desc_and_banner_url_by_slug(proj_desc_banner_qs, slug, use_cache=True):
    """Gets the project description and banner image url for a slug"""
    if not proj_desc_banner_qs:
        return None, None
    if not slug:
        return None, None
    description = None
    banner_url = None
    cached_tuple = None
    if use_cache:
        hash_obj = hashlib.sha1()
        path_item_str = f'projects-hero-for-slug: {slug}'
        hash_obj.update(path_item_str.encode('utf-8'))
        cache_key = f'{settings.CACHE_PREFIX_PROJ_META}hs_{str(hash_obj.hexdigest())}'
        cache = caches['redis_search']
        cached_tuple = cache.get(cache_key)
    if cached_tuple:
        # return description, banner_url
        return cached_tuple[0], cached_tuple[1]
    for man_obj in proj_desc_banner_qs:
        if man_obj.slug != slug:
            continue
        if man_obj.item_description:
            description = man_obj.item_description
        elif man_obj.proj_description:
            description = man_obj.proj_description
        if man_obj.item_hero_hero:
            banner_url = man_obj.item_hero_hero
        elif man_obj.proj_hero:
            banner_url = man_obj.proj_hero
        elif man_obj.proj_proj_hero:
            banner_url = man_obj.proj_proj_hero
        if description or banner_url:
            break
    if not use_cache:
        return description, banner_url
    try:
        cache.set(cache_key, (description, banner_url))
    except:
        pass
    return description, banner_url


def get_string_attribute_data_for_uuids_qs(
    uuids,
    db_limit_string_attributes=None,
    requested_attrib_slugs=None
):
    """Gets an AllAssertion queryset for string attribute data

    :param list uuids: A list of UUIDs for the subject items
    :param str db_limit_string_attributes: Options to limit the predicates
        retrieved in the query set. Choices are: None (no limits),
        'project' (non-opencontext project attributes only),
        and 'requested_attrib_slugs' (attributes specified by the
        requested_attrib_slugs)
    :param list requested_attrib_slugs: An optional list of predicate
        slugs to limit the query set.

    return AllAssertion queryset
    """
    qs = AllAssertion.objects.filter(
        subject_id__in=uuids,
        predicate__data_type='xsd:string',
    ).select_related(
        'predicate'
    )
    if not db_limit_string_attributes:
        # No further limits on the queryset.
        return qs
    if db_limit_string_attributes == 'project':
        # Exclude the Open Context project from the results
        qs = qs.exclude(predicate__project_id=configs.OPEN_CONTEXT_PROJ_UUID)
        return qs
    # Limit the queryset by attribute slugs requested by the client.
    qs = qs.filter(predicate__slug__in=requested_attrib_slugs)
    return qs


def get_db_uuid_pred_str_dict(
    uuids,
    db_limit_string_attributes=None,
    requested_attrib_slugs=None
):
    """Gets a dictionary of string attribute data for uuids

    :param list uuids: A list of UUIDs for the subject items
    :param str db_limit_string_attributes: Options to limit the predicates
        retrieved in the query set. Choices are: None (no limits),
        'project' (non-opencontext project attributes only),
        and 'requested_attrib_slugs' (attributes specified by the
        requested_attrib_slugs)
    :param list requested_attrib_slugs: An optional list of predicate
        slugs to limit the query set.

    return dict
    """
    qs = get_string_attribute_data_for_uuids_qs(
        uuids,
        db_limit_string_attributes,
        requested_attrib_slugs
    )
    prep_dict = {}
    for ass_obj in qs:
        uuid = str(ass_obj.subject.uuid)
        pred_slug = ass_obj.predicate.slug
        if not uuid in prep_dict:
            prep_dict[uuid] = {}
        if not pred_slug in prep_dict[uuid]:
            prep_dict[uuid][pred_slug] = {
                'label': ass_obj.predicate.label,
                'slug': ass_obj.predicate.slug,
                'uri': ass_obj.predicate.uri,
                'vals_list': [],
            }
        prep_dict[uuid][pred_slug]['vals_list'].append(
            ass_obj.obj_string
        )
    db_uuid_pred_str_dict = {}
    for uuid, a_dict in prep_dict.items():
        db_uuid_pred_str_dict[uuid] = []
        for _, b_dict in a_dict.items():
            pred_dict = {
                'label': b_dict['label'],
                'slug': b_dict['slug'],
                'uri': b_dict['uri'],
            }
            tup = (pred_dict, b_dict['vals_list'])
            db_uuid_pred_str_dict[uuid].append(tup)
    return db_uuid_pred_str_dict