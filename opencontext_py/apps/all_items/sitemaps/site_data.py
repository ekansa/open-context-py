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
    AllAssertion,
    AllResource,
)

from opencontext_py.apps.searcher.new_solrsearcher.searchsolr import SearchSolr
from opencontext_py.apps.searcher.new_solrsearcher.resultmaker import ResultMaker

"""
# testing

import importlib
from opencontext_py.apps.all_items.models import (
    AllManifest,
)
from opencontext_py.apps.all_items.sitemaps import site_data
importlib.reload(site_data)

site_data.warm_sitemap_representative_items()
"""

MAX_SITEMAP_ITEMS = 25000 # It's really 50K, but let's be conservative

BIG_FILE_SAMPLE_SIZE = 100
VERBOSE_TEXT_SAMPLE_SIZE = 15
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


def db_get_proj_items_unique_by_descriptors(proj_obj):
    """Gets a unique representative sample of items from a project that
    have the full range of descriptive attributes, and associated types
    and persons

    :param AllManifest proj_obj: An AllManifest instance of the project
        for which we want a representative set of
    
    returns set(AllManifest objects) where the set includes a representative
        associated with each unique predicate, type (controlled vocab concept),
        person.
    """

    # This sub-query returns the number of media resources associated with
    # each subject. It is useful to promote the best image described items
    # that represent each kind of descriptor.
    media_count_qs = AllAssertion.objects.filter(
        subject=OuterRef('subject'),
        object__item_type='media',
        visible=True,
    ).annotate(
        media_count=Count('object')
    ).values('media_count')[:1]

    pred_qs = AllAssertion.objects.filter(
        subject__project=proj_obj,
        subject__item_type__in=configs.OC_ITEM_TYPES,
        visible=True,
    ).annotate(
        media_count=Subquery(media_count_qs)
    ).select_related(
        'subject'
    ).distinct(
        'predicate',
        'media_count',
    ).order_by(
        '-media_count',
        'predicate',
    )
    unique_by_preds = {act_ass.subject for act_ass in pred_qs}
    # Now items that represent associations with each types and persons item_type
    person_type_qs = AllAssertion.objects.filter(
        subject__project=proj_obj,
        subject__item_type__in=configs.OC_ITEM_TYPES,
        object__item_type__in=['types', 'persons'],
        visible=True,
    ).annotate(
        media_count=Subquery(media_count_qs)
    ).select_related(
        'subject'
    ).distinct(
        'object',
        'media_count',
    ).order_by(
        '-media_count',
        'object',
        'subject',
    )
    unique_by_t_p = {act_ass.subject for act_ass in person_type_qs}
    rep_man_objs = unique_by_preds.union(
        unique_by_t_p
    )
    return rep_man_objs


def db_get_proj_items_biggest_files(proj_obj):
    """Gets a unique sample of items associated with a project that have
    the largest file sizes for different media types

    :param AllManifest proj_obj: An AllManifest instance of the project
        for which we want a representative set of
    
    returns set(AllManifest objects) that have the biggest file sizes for
        different media types
    """
    # Now items that represent each mediatype
    media_type_qs = AllResource.objects.filter(
        item__project=proj_obj,
        resourcetype_id__in=configs.OC_RESOURCE_TYPES_MAIN_UUIDS,
    ).select_related(
        'item'
    ).distinct(
        'mediatype',
    ).order_by(
        'mediatype',
        '-filesize',
    )
    # Now get items with the biggest filesizes associated with each media type
    # in the dataset.
    big_media = set()
    for act_res in media_type_qs:
        big_qs = AllResource.objects.filter(
            item__project=proj_obj,
            resourcetype_id__in=configs.OC_RESOURCE_TYPES_MAIN_UUIDS,
            mediatype=act_res.mediatype,
        ).select_related(
            'item'
        ).order_by(
            '-filesize',
        )[:BIG_FILE_SAMPLE_SIZE]
        act_set = {act_res.item for act_res in big_qs}
        big_media.update(act_set)
    return big_media


def db_get_proj_items_verbose_text(proj_obj):
    """Gets a unique sample of items associated with a project by distinct
    item_type and item_class that have the most verbose text associated

    :param AllManifest proj_obj: An AllManifest instance of the project
        for which we want a representative set of
    
    returns set(AllManifest objects) that have the biggest file sizes for
        different media types
    """
    # Now get a representative list of each distinct item_type and item_class
    m_qs = AllManifest.objects.filter(
        project=proj_obj,
        item_type__in=configs.OC_ITEM_TYPES,
    ).distinct(
        'item_type',
        'item_class'
    ).order_by(
        'item_type',
        'item_class'
    )
    item_type_class = {man_obj for man_obj in m_qs}
    # Now get the most verbosely described items.
    wordy_items = set()
    for man_obj in m_qs:
        wordy_qs = AllAssertion.objects.filter(
            subject__project=proj_obj,
            subject__item_type=man_obj.item_type,
            subject__item_class=man_obj.item_class,
            predicate__data_type='xsd:string',
            visible=True,
        ).annotate(
            text_len=Length('obj_string')
        ).distinct(
            'text_len',
            'subject'
        ).order_by(
            '-text_len',
            'subject',
        )[:VERBOSE_TEXT_SAMPLE_SIZE]
        act_set = {act_ass.subject for act_ass in wordy_qs}
        wordy_items.update(act_set)
    # Combine the two sets
    rep_man_objs = item_type_class.union(
        wordy_items
    )
    return rep_man_objs


def db_get_project_representative_sample(proj_obj, index_id=None):
    """Gets a unique representative sample of resources from a project
    
    :param AllManifest proj_obj: An AllManifest instance of the project
        for which we want a representative set of
    
    returns set(AllManifest objects) where the set includes a representative
        associated with each unique predicate, type (controlled vocab concept),
        person, item_type, and item_class in the project. This sampling method
        should ensure that search engines have links to a good representation
        of the full diversity of content within a project.
    """
    # NOTE: This seems to work well to greatly reduce the number of links
    # we need to include in a sitemap. For Poggio Civitate, we can make a
    # representative sample of Web resources from only 2% of the total
    # number of records (because so much data is pretty repetitive)
    proj_count = AllManifest.objects.filter(project=proj_obj).count()
    print_prefix = f'{proj_obj.label} ({str(proj_obj.uuid)}) [Total: {proj_count}]'
    
    unique_by_des = db_get_proj_items_unique_by_descriptors(proj_obj)
    print(f'{print_prefix}; items for distinct descriptors: {len(unique_by_des)}')

    big_files = db_get_proj_items_biggest_files(proj_obj)
    print(f'{print_prefix}; items representing large media: {len(big_files)}')

    wordy_items = db_get_proj_items_verbose_text(proj_obj)
    print(f'{print_prefix}; wordy items for each distinct item_type, item_class: {len(wordy_items)}')

    rep_man_objs = unique_by_des.union(
        big_files
    ).union(
        wordy_items
    )
    rep_len = len(rep_man_objs)
    print(f'{print_prefix}; all representative items: {rep_len}, or {round(((rep_len/proj_count) * 100), 2)} %')
    if index_id:
        proj_obj.meta_json['sitemap_index_id'] = index_id
        proj_obj.save()
        for man_obj in rep_man_objs:
            man_obj.meta_json['sitemap_index_id'] = index_id
            man_obj.save()
    return rep_man_objs


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
    try:
        job_id, job_done, rep_man_objs = wrap_func_for_rq(
            func=db_get_project_representative_sample,
            kwargs={
                'proj_obj': proj_obj,
                'index_id': index_id,
            },
            job_id=job_id,
        )
    except Exception as e:
        print(f'Sitemap {proj_obj.slug} queue problem: {str(e)}')
        rep_man_objs = []
    if job_id and not job_done:
        proj_obj.meta_json['sitemap_job_ids'] = {
            index_id: job_id,
        }
        proj_obj.save()
    if job_done:
        # Remove the worker job id, since it is done.
        proj_obj.meta_json['sitemap_job_ids'] = {}
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