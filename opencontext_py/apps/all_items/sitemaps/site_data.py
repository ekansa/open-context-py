import datetime
from calendar import c
import copy
import hashlib
import logging

from django.conf import settings

from django.core.cache import caches

from opencontext_py.libs.queue_utilities import (
    wrap_func_for_rq,
)

from django.db.models import Q, Count, OuterRef, Subquery
from django.db.models.functions import Length


from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
)

from opencontext_py.apps.searcher.new_solrsearcher.searchsolr import SearchSolr
from opencontext_py.apps.searcher.new_solrsearcher.resultmaker import ResultMaker

from opencontext_py.apps.all_items.sitemaps import db_site_data
"""
# testing

import importlib
from opencontext_py.apps.all_items.models import (
    AllManifest,
)
from opencontext_py.apps.all_items.sitemaps import site_data
importlib.reload(site_data)

site_data.warm_sitemap_representative_items()


pqs = AllManifest.objects.filter(item_type='projects')
for p in pqs:
    if not p.meta_json.get('sitemap_index_id'):
        continue
    p.meta_json['sitemap_index_id'] = None
    print(f'update: {p.slug}')
    p.save()

proj_obj = AllManifest.objects.get(uuid='a52bd40a-9ac8-4160-a9b0-bd2795079203')
r = site_data.get_cache_project_representative_sample(proj_obj)
"""

MAX_SITEMAP_ITEMS = 25000 # It's really 50K, but let's be conservative

SITEMAP_ITEMS_CACHE_LIFE = 60 * 60 * 24 * 365 # A 1 year cache
MIN_SIZE_SOLR_INDEX = 15
SKIP_PROJECT_SLUGS = [
    'open-context'
]


MISC_SITEMAP_ITEM_TYPE = 'other'
DEFAULT_ITEM_TYPE_PRIORITY = 0.33

SITEMAP_ITEM_TYPES_AND_PRIORITY = [
    ('projects', 1.0,),
    ('media', 0.9,),
    ('documents', 0.8,),
    ('subjects', 0.5,),
    (MISC_SITEMAP_ITEM_TYPE, DEFAULT_ITEM_TYPE_PRIORITY,),
]
ITEM_TYPES_PRIORITY_DICT = {k:v for k,v in SITEMAP_ITEM_TYPES_AND_PRIORITY}

rp = RootPath()
BASE_URL = rp.get_baseurl()


logger = logging.getLogger("site-map-items")

def make_cache_key_proj_rep(proj_obj):
    key = f'sitemap-proj-{str(proj_obj.uuid)}'
    return key


def get_solr_indexed_project_slugs():
    request_dict = {
        'rows': 1,
        'response': 'metadata,prop-facet',
    }
    search_solr = SearchSolr()
    query = search_solr.compose_sitemap_query()
    solr_response = search_solr.query_solr(query)
    result_maker = ResultMaker(
        request_dict=request_dict,
        facet_fields_to_client_request=copy.deepcopy(search_solr.facet_fields_to_client_request),
        slugs_for_config_facets=copy.deepcopy(search_solr.slugs_for_config_facets),
        base_search_url='/query/',
    )
    # Make sure we tell the results generator to look for sitemap facets
    result_maker.sitemap_facets = True
    result_maker.create_result(
        solr_json=solr_response
    )
    max_count = 0
    project_slug_counts = []
    for facet in result_maker.result.get('oc-api:has-facets', []):
        for option in facet.get('oc-api:has-id-options', []):
            proj_slug = option.get('slug')
            if not proj_slug:
                continue
            if proj_slug in SKIP_PROJECT_SLUGS:
                continue
            count_size = option.get('count', 0)
            if count_size < MIN_SIZE_SOLR_INDEX:
                # Not enough items indexed in project to include in the site map
                continue
            if count_size > max_count:
                max_count = count_size
            project_slug_counts.append(
                (proj_slug, count_size,)
            )
    return project_slug_counts, max_count


def get_cache_solr_indexed_project_slugs(reset_cache=False):
    cache = caches['redis']
    cache_key = 'sitemap-proj-slug-counts'
    project_slug_counts = None
    max_count = None
    if not reset_cache:
        tup = cache.get(cache_key)
        if isinstance(tup, tuple):
            project_slug_counts, max_count = tup
    if project_slug_counts and max_count:
        return project_slug_counts, max_count
    project_slug_counts, max_count = get_solr_indexed_project_slugs()
    if project_slug_counts:
        tup = (project_slug_counts, max_count,)
        try:
            cache.set(cache_key, tup, timeout=SITEMAP_ITEMS_CACHE_LIFE)
        except:
            logger.info(f'Cache failure with: {cache_key}')
            print(f'Cache failure with: {cache_key}')
    return project_slug_counts, max_count


def get_cache_project_representative_sample(proj_obj, reset_proj_item_index=False):
    """Gets a representative sample of a project. Uses a sitemap index id to
    find items in the meta_json for the manifest.
    """
    rep_man_objs = None
    if not reset_proj_item_index and proj_obj.meta_json.get('sitemap_index_id'):
        rep_man_objs = AllManifest.objects.filter(
            project=proj_obj,
            meta_json__sitemap_index_id=proj_obj.meta_json.get('sitemap_index_id')
        )
        if len(rep_man_objs) > 1:
            return rep_man_objs
    job_done = False
    dt_obj = datetime.datetime.now()
    index_id = dt_obj.strftime('%Y-%m-%d')
    job_id = None
    if proj_obj.meta_json.get('sitemap_job_ids'):
        job_id = proj_obj.meta_json.get('sitemap_job_ids').get(index_id)

    # Do a queued request to get all of the representative items for the project
    job_id, job_done, rep_man_objs = wrap_func_for_rq(
        func=db_site_data.db_get_project_representative_sample,
        kwargs={
            'proj_obj': proj_obj,
        },
        job_id=job_id,
    )

    if job_id and not job_done:
        proj_obj.meta_json['sitemap_job_ids'] = {
            index_id: job_id,
        }
        proj_obj.save()
    if rep_man_objs and job_done:
        print(f'Marking {len(rep_man_objs)} representative items of {proj_obj.slug} with sitemap index id {index_id}')
        for man_obj in rep_man_objs:
            man_obj.meta_json['sitemap_index_id'] = index_id
            man_obj.save()
        # Remove the worker job id, since it is done.
        proj_obj.meta_json['sitemap_job_ids'] = {}
        proj_obj.meta_json['sitemap_index_id'] = index_id
        proj_obj.save()
    if not job_done:
        return []
    if not rep_man_objs:
        return []
    return rep_man_objs


def compute_sitemap_priority(item_type, proj_count, max_count):
    """Computes the sitemap priority for a given item_type and proj_count
    """
    # NOTE: We're going to give the most influence in calculating
    # the priority score to the item type, with a smaller influence
    # based on the size of a project in the solr index. Bigger
    # projects are more "significant" to Open Context and should
    # get relatively more search engine priority
    item_type_priority = ITEM_TYPES_PRIORITY_DICT.get(
        item_type,
        DEFAULT_ITEM_TYPE_PRIORITY
    )
    if max_count < 1:
        return item_type_priority
    priority = (
        (item_type_priority * 3)
        + (item_type_priority * proj_count/max_count)
    ) / 4
    if priority < 0:
        priority = 0.001
    return round(priority, 3)


def compute_sitemap_url(man_obj):
    """Computes the sitemap priority for a given item_type and proj_count
    """
    # return f'{BASE_URL}/{man_obj.item_type}/{str(man_obj.uuid)}'
    return f'/{man_obj.item_type}/{str(man_obj.uuid)}'


def get_sitemap_items_dict_for_proj_slug(
    proj_slug,
    proj_count,
    max_count,
    reset_proj_item_index=False):
    # Check solr for projects that are actually indexed. This
    # is a signal that the project data is ready to fully
    # publicize with search engines.
    all_items = {k:[] for k,_ in SITEMAP_ITEM_TYPES_AND_PRIORITY}
    # Use a get to fail loudly here!
    proj_obj = AllManifest.objects.filter(
        slug=proj_slug,
        item_type='projects'
    ).first()
    if not proj_obj:
        return all_items
    # Add the sitemap priority to the project item.
    proj_obj.sitemap_priority = compute_sitemap_priority(
        item_type=proj_obj.item_type,
        proj_count=proj_count,
        max_count=max_count,
    )
    proj_obj.url = compute_sitemap_url(proj_obj)
    # Get representative content for the project.
    rep_man_objs = get_cache_project_representative_sample(
        proj_obj,
        reset_proj_item_index=reset_proj_item_index,
    )
    for man_obj in rep_man_objs:
        man_obj.sitemap_priority = compute_sitemap_priority(
            item_type=man_obj.item_type,
            proj_count=proj_count,
            max_count=max_count,
        )
        man_obj.url = compute_sitemap_url(man_obj)
        # Now put this item type in the appropriate
        # list.
        if man_obj.item_type in all_items:
            sitemap_key = man_obj.item_type
        else:
            sitemap_key = MISC_SITEMAP_ITEM_TYPE
        all_items[sitemap_key].append(man_obj)
    # Make sure the project item itself is in the
    # output dict.
    if not proj_obj in all_items['projects']:
        all_items['projects'].append(proj_obj)
    return all_items


def get_index_sitemap_item_for_proj_slug(
    proj_slug,
    proj_count,
    max_count,
):

    proj_obj = AllManifest.objects.filter(
        slug=proj_slug,
        item_type='projects'
    ).first()
    if not proj_obj:
        return None
    # Add the sitemap priority to the project item.
    proj_obj.sitemap_priority = compute_sitemap_priority(
        item_type=proj_obj.item_type,
        proj_count=proj_count,
        max_count=max_count,
    )
    proj_obj.url = compute_sitemap_url(proj_obj)
    return proj_obj


def get_sitemap_items_for_proj_slug(
    proj_slug,
    proj_count,
    max_count,
    reset_proj_item_index=False
):
    # Check solr for projects that are actually indexed. This
    # is a signal that the project data is ready to fully
    # publicize with search engines.
    all_item_list = []
    all_items = get_sitemap_items_dict_for_proj_slug(
        proj_slug=proj_slug,
        proj_count=proj_count,
        max_count=max_count,
        reset_proj_item_index=reset_proj_item_index

    )
    for key, _ in SITEMAP_ITEM_TYPES_AND_PRIORITY:
        all_item_list += all_items.get(key, [])
    if len(all_item_list) > MAX_SITEMAP_ITEMS:
        return all_item_list[:MAX_SITEMAP_ITEMS]
    return all_item_list


def warm_sitemap_representative_items():
    project_slug_counts, max_count = get_cache_solr_indexed_project_slugs(
        reset_cache=True
    )
    for proj_slug, proj_count in project_slug_counts:
        rep_man_objs = get_sitemap_items_for_proj_slug(
            proj_slug=proj_slug,
            proj_count=proj_count,
            max_count=max_count,
            reset_proj_item_index=True,
        )
        print(f'Warmed {len(rep_man_objs)} rep items for {proj_slug}')