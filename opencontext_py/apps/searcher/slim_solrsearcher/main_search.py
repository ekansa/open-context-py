import copy
import logging
import time

from django.conf import settings
from django.core.cache import caches

from opencontext_py.libs.rootpath import RootPath


from opencontext_py.apps.searcher.slim_solrsearcher.searchsolr import SearchSolrSlim
from opencontext_py.apps.searcher.new_solrsearcher.resultmaker import ResultMaker

from opencontext_py.apps.indexer.embeddings import (
    make_vectorized_embedding_query_str
)
from opencontext_py.apps.indexer.solrdocument_slim_schema import (
    EMBEDDING_FIELD_SOLR,
)

from opencontext_py.libs.queue_utilities import make_hash_id_from_args

logger = logging.getLogger(__name__)




if settings.DEBUG:
    SEARCH_CACHE_TIMEOUT = 60 # 1 minute
else:
    SEARCH_CACHE_TIMEOUT = 60 * 60 * 24 * 7 # 1 week




def process_solr_query_via_solr_and_db(request_dict, base_search_url='/lm-query/'):
    """Processes a request dict to formulate a solr query and process a
       response from solr

    :param dict request_dict: Dictionary derived from a solr
        request object with client GET request parameters.
    """
    start_time = time.time()
    search_solr = SearchSolrSlim()
    search_solr.add_initial_facet_fields(request_dict)
    search_solr.init_facet_fields.append('item_type')
    query = search_solr.compose_query(request_dict)
    query = search_solr.update_query_with_stats_prequery(
        query
    )
    if request_dict.get('oai-pmh'):
        # Empty this!
        query['facet.field'] = []
    prep_solr_query_time = time.time()
    solr_response = search_solr.query_solr(query)
    solr_response_time = time.time()
    result_maker = ResultMaker(
        request_dict=request_dict,
        facet_fields_to_client_request=copy.deepcopy(search_solr.facet_fields_to_client_request),
        slugs_for_config_facets=copy.deepcopy(search_solr.slugs_for_config_facets),
        base_search_url=base_search_url,
    )
    result_maker.create_result(
        solr_json=solr_response
    )
    solr_end_time = time.time()
    if isinstance(result_maker.result, list):
        # Case of a list response.
        return result_maker.result
    if not isinstance(result_maker.result, dict):
        return {}
    result_maker.result['query'] = query
    if 'no-docs' in request_dict.get('solr', []):
        solr_response['response'].pop('docs')
        result_maker.result = solr_response
    if settings.DEBUG:
        result_maker.result['prep_solr_query_time'] = (prep_solr_query_time - start_time) * 10**3
        result_maker.result['solr_response_time'] = (solr_response_time - prep_solr_query_time) * 10**3
        result_maker.result['process_solr_result_time'] = (solr_end_time - solr_response_time) * 10**3
    if not settings.DEBUG and not request_dict.get('solr') and result_maker.result.get('query'):
        # Get rid of the solr query if we're not in debug mode and did not specifically
        # ask for it.
        result_maker.result.pop('query')
    result_maker.result['Qtime'] = solr_response.get('responseHeader', {}).get('QTime')
    return result_maker.result
