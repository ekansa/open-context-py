import copy
import logging

from django.conf import settings
from django.core.cache import caches

from opencontext_py.libs.rootpath import RootPath


from opencontext_py.apps.searcher.new_solrsearcher.searchsolr import SearchSolr
from opencontext_py.apps.searcher.new_solrsearcher.resultmaker import ResultMaker

from opencontext_py.libs.queue_utilities import make_hash_id_from_args

logger = logging.getLogger(__name__)



if settings.DEBUG:
    SEARCH_CACHE_TIMEOUT = 60 # 1 minute
else:
    SEARCH_CACHE_TIMEOUT = 60 * 60 * 24 * 7 # 1 week


# --------------------------------------------------------------------
# NOTE: These functions provide a simple general purpose means to search
# Solr and cache search results.
# --------------------------------------------------------------------


def process_solr_query_via_solr_and_db(request_dict, base_search_url='/query/'):
    """Processes a request dict to formulate a solr query and process a
       response from solr

    :param dict request_dict: Dictionary derived from a solr
        request object with client GET request parameters.
    """
    search_solr = SearchSolr()
    search_solr.add_initial_facet_fields(request_dict)
    search_solr.init_facet_fields.append('item_type')
    query = search_solr.compose_query(request_dict)
    query = search_solr.update_query_with_stats_prequery(
        query
    )
    solr_response = search_solr.query_solr(query)
    result_maker = ResultMaker(
        request_dict=request_dict,
        facet_fields_to_client_request=copy.deepcopy(search_solr.facet_fields_to_client_request),
        slugs_for_config_facets=copy.deepcopy(search_solr.slugs_for_config_facets),
        base_search_url=base_search_url,
    )
    result_maker.create_result(
        solr_json=solr_response
    )
    if isinstance(result_maker.result, dict):
        result_maker.result['query'] = query
    if 'no-docs' in request_dict.get('solr', []):
        solr_response['response'].pop('docs')
        result_maker.result = solr_response
    if False and not settings.DEBUG and not request_dict.get('solr') and result_maker.result.get('query'):
        # Get rid of the solr query if we're not in debug mode and did not specifically
        # ask for it.
        result_maker.result.pop('query')
    return result_maker.result


def process_solr_query(request_dict, base_search_url='/query/'):
    """Processes a request dict to formulate a solr query and process a
       response from solr

    :param dict request_dict: Dictionary derived from a solr
        request object with client GET request parameters.
    """
    reset_cache = False
    if request_dict.get('reset_cache'):
        reset_cache = True
        request_dict.pop('reset_cache')
        print(f'Resetting cache for {request_dict}')
    cache = caches['redis']
    cache_key = make_hash_id_from_args(
        args=request_dict
    )
    result = None
    if not reset_cache:
        result = cache.get(cache_key)
    if result:
        # We have a result from the cache, so return it.
        print(f'Solr query result from cache {cache_key}')
        return result
    # Do the hard work of computing the result from scratch
    result = process_solr_query_via_solr_and_db(
        request_dict,
        base_search_url=base_search_url,
    )
    try:
        cache.set(cache_key, result, timeout=SEARCH_CACHE_TIMEOUT)
    except:
        pass
    return result