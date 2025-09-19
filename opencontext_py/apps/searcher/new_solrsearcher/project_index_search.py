import logging

from scipy import stats

from django.core.cache import caches
from django.template.defaultfilters import slugify

from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import main_search
from opencontext_py.apps.searcher.new_solrsearcher.resultmaker import ResultMaker
from opencontext_py.apps.searcher.new_solrsearcher.sorting import SortingOptions
from opencontext_py.apps.searcher.new_solrsearcher import utilities

from opencontext_py.libs.queue_utilities import make_hash_id_from_args

logger = logging.getLogger(__name__)



PROJ_ITEM_ATTRIBUTES = [
    'dc-terms-creator',
    'dc-terms-description',
    'dc-terms-license',
    'dc-terms-subject',
    'dc-terms-spatial',
    'dc-terms-coverage',
    'dc-terms-contributor',
    'dc-terms-temporal',
    'dc-terms-is-referenced-by',
    'dc-terms-references',
]

PROJ_ITEM_REQUEST_DICT = {
    'response': 'geo-record',
    'rows': 1000,
    'start': 0,
    'type': 'projects',
    'proj-index': 1,
    'attributes': ','.join(PROJ_ITEM_ATTRIBUTES),
}

UPDATE_PAGE_LINK_KEYS = [
    'first',
    'first-json',
    'previous',
    'previous-json',
    'next',
    'next-json',
    'last',
    'last-json',
    'oc-api:has-sorting',
    'oc-api:active-filters',
    'oc-api:has-text-search',
]

def get_uuid_from_proj_uri(uri):
    """Gets the UUID form a project URI"""
    if not uri or not '/' in uri:
        return None
    uri_ex = uri.split('/')
    return uri_ex[-1]


def get_cache_all_projects_items_geojson(reset_cache=False):
    """Gets and caches project index geojson records for all projects"""
    cache = caches['redis']
    cache_key = make_hash_id_from_args(
        args=PROJ_ITEM_REQUEST_DICT
    )
    cache_key = f'allprjgeo-{cache_key}'
    features = None
    if not reset_cache:
        features = cache.get(cache_key)
    if features:
        # We have a result from the cache, so return it.
        print(f'Solr query result from cache {cache_key}')
        return features
    response_dict = main_search.process_solr_query_via_solr_and_db(
        PROJ_ITEM_REQUEST_DICT,
        base_search_url='/projects-index/',
    )
    # Now we will calculate the absolute descriptiveness percentile
    # ranking for ALL of the projects. This will be cached because
    # we want the rankings to be stable, no matter how the list of
    # projects get filtered.
    interest_scores = []
    features = []
    # print(f"solr project index response with feature count: {len(response_dict.get('features', []))}")
    for feature in response_dict.get('features', []):
        if not feature.get('oc-api:descriptiveness'):
            print('no descriptivness')
            continue
        interest_scores.append(feature.get('oc-api:descriptiveness'))
        features.append(feature)
    interest_scores.sort()
    features_uri_dict = {}
    # print(f'here we have {len(features)} project features')
    for feature in features:
        feature['oc-api:descriptiveness-percentile'] = stats.percentileofscore(
            interest_scores,
            feature.get('oc-api:descriptiveness'),
            'rank',
        )
    try:
        cache.set(cache_key, features, timeout=main_search.SEARCH_CACHE_TIMEOUT)
    except:
        pass
    return features


def get_project_facet_options(response_dict):
    """Gets the project index (site map) facet options from a search response dict"""
    for facet in response_dict.get('oc-api:has-facets', []):
        if facet.get('type') != 'oc-api:sitemap-facet-project':
            continue
        if not facet.get('oc-api:has-id-options'):
            continue
        return facet.get('oc-api:has-id-options')
    return None


def validate_update_item_feature_from_proj_opts(proj_opts, feature):
    """Validates and updates a project item feature based on proj_objs list"""
    if not proj_opts:
        return None
    feature_uuid = get_uuid_from_proj_uri(feature.get('rdfs:isDefinedBy'))
    if not feature_uuid:
        # print('No feature_uuid')
        return None
    for proj_opt in proj_opts:
        proj_opt_uuid = get_uuid_from_proj_uri(proj_opt.get('rdfs:isDefinedBy'))
        if proj_opt_uuid != feature_uuid:
            continue
        feature['oc-api:project-contents-count'] = proj_opt.get('count')
        return feature
    return None


def validate_update_item_features_from_proj_opts(proj_opts, features):
    """Validates and updates a project item feature based on proj_objs list"""
    if not proj_opts:
        return None
    if not features:
        return None
    valid_features = []
    for feature in features:
        ok_feature = validate_update_item_feature_from_proj_opts(proj_opts, feature)
        if ok_feature:
            valid_features.append(ok_feature)
    return valid_features


def validate_sort_uuids_from_proj_opts(proj_opts, sort_uuids):
    """Validates and updates a project item feature based on proj_objs list"""
    if not proj_opts:
        return None
    if not sort_uuids:
        return None
    proj_opt_uuids = [
        get_uuid_from_proj_uri(opt.get('rdfs:isDefinedBy'))
        for opt in proj_opts
    ]
    valid_sort_uuids = [uuid for uuid in sort_uuids if uuid in proj_opt_uuids]
    return valid_sort_uuids


def make_sort_uuids_from_project_opts_labels(proj_opts, reverse=False):
    """Makes sort_uuids list from labels"""
    tups = [
        (
            get_uuid_from_proj_uri(opt.get('rdfs:isDefinedBy')),
            slugify(opt.get('label')),
        )
        for opt in proj_opts
    ]
    tups.sort(key=lambda t: t[1], reverse=reverse)
    sort_uuids = [uuid for uuid, _ in tups]
    return sort_uuids


def get_sort_uuids(request_dict, proj_opts):
    """Gets sort uuids either from the proj_opts or a new request"""
    sort_opts = SortingOptions()
    sort_list = sort_opts.make_current_sorting_list(request_dict)
    if sort_list:
        for sort_obj in sort_list:
            if sort_obj['type'] != 'oc-api:sort-project':
                continue
            reverse = (sort_obj['oc-api:sort-order'] == 'descending')
            return make_sort_uuids_from_project_opts_labels(proj_opts, reverse=reverse)
    item_search_dict = {
        'type': 'projects',
        'response': 'uuid',
        'rows': 1000,
        'start': 0,
    }
    if 'sort' in request_dict:
        item_search_dict['sort'] = request_dict.get('sort')
    sort_uuids = main_search.process_solr_query_via_solr_and_db(
        item_search_dict,
        base_search_url='/projects-index/',
    )
    sort_uuids = validate_sort_uuids_from_proj_opts(proj_opts, sort_uuids)
    return sort_uuids


def get_cache_project_index_filtered_summary_and_items(request, spatial_context=None):
    """Gets the project index with optional filters result and project items"""
    cache = caches['redis']
    request_dict = utilities.make_request_obj_dict(
        request, spatial_context=spatial_context
    )
    if not request_dict.get('rows'):
        request_dict['rows'] = 20
    request_dict['proj-index'] = 1
    request_dict['response'] = ','.join(
        [
            'metadata',
            'prop-facet',
        ]
    )
    reset_cache = False
    if request_dict.get('reset_cache'):
        reset_cache = True
    cache_key = make_hash_id_from_args(
        args=request_dict
    )
    cache_key = f'allprjindex-{cache_key}'
    result = None
    if not reset_cache:
        result = cache.get(cache_key)
    if result:
        # We have a result from the cache, so return it.
        print(f'Solr query result from cache {cache_key}')
        return result
    response_dict = main_search.process_solr_query_via_solr_and_db(
        request_dict,
        base_search_url='/projects-index/',
    )
    proj_opts = get_project_facet_options(response_dict)
    if not proj_opts:
        return response_dict
    # print(f'Project index search has {len(proj_opts)} proj facets for {cache_key}')
    # Now get sort uuids, either with a new request or by sorting the project
    # facet options.
    sort_uuids = get_sort_uuids(request_dict, proj_opts)
    all_features = get_cache_all_projects_items_geojson(reset_cache)
    valid_features = validate_update_item_features_from_proj_opts(proj_opts, all_features)
    # print(f'count valid features {len(valid_features)}')
    # print(proj_opts)
    sorted_valid_features = []
    for sort_uuid in sort_uuids:
        for feature in valid_features:
            feature_uuid = get_uuid_from_proj_uri(feature.get('rdfs:isDefinedBy'))
            if feature_uuid != sort_uuid:
                continue
            sorted_valid_features.append(feature)
    # We need to update the paging with the actual number of projects that
    # we are returning from our search.
    start_pos = utilities.get_request_param_value(
        request_dict,
        param='start',
        default=0,
        as_list=False,
        solr_escape=False,
        require_int=True,
    )
    rows = utilities.get_request_param_value(
        request_dict,
        param='rows',
        default=50,
        as_list=False,
        solr_escape=False,
        require_int=True,
    )
    rev_request_dict = {
        k:v for k,v in request_dict.items()
        if k not in ['proj-index', 'response']
    }
    result_maker = ResultMaker(
        request_dict=rev_request_dict,
        base_search_url='/projects-index/',
    )
    # Update the result id so it has cleaner parameters
    result_maker.make_response_id()
    response_dict['id'] = result_maker.id

    response_dict['totalResults'] = len(sorted_valid_features)
    result_maker.total_found = response_dict['totalResults']
    result_maker.start = start_pos
    result_maker.rows = rows
    result_maker.make_response_id()
    result_maker.add_paging_json({})
    result_maker.add_sorting_json()
    result_maker.add_filters_json()
    result_maker.add_text_fields()
    for link_key in UPDATE_PAGE_LINK_KEYS:
        link_val = result_maker.result.get(link_key)
        if link_val:
            response_dict[link_key] = link_val
        elif response_dict.get(link_key):
            response_dict.pop(link_key)
    response_dict['features'] = sorted_valid_features[start_pos:(start_pos + rows)]
    try:
        cache.set(cache_key, response_dict, timeout=main_search.SEARCH_CACHE_TIMEOUT)
    except:
        pass
    return response_dict