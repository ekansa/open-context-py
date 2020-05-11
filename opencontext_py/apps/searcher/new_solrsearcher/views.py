import json
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponse, Http404

from django.template import RequestContext, loader
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.requestnegotiation import RequestNegotiation

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.searchsolr import SearchSolr
from opencontext_py.apps.searcher.new_solrsearcher.resultmaker import ResultMaker
from opencontext_py.apps.searcher.new_solrsearcher import utilities

from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.views.decorators.cache import cache_page
from django.utils.cache import patch_vary_headers


def process_solr_query(request_dict):
    """Processes a request dict to formulate a solr query and process a
       response from solr
    
    :param dict request_dict: Dictionary derived from a solr
        request object with client GET request parmaters.
    """
    
    # NOTE: For inital testing purposes, this only composes a
    # solr query dict, it does not actually do a solr search.
    search_solr = SearchSolr()
    search_solr.add_initial_facet_fields(request_dict)
    query = search_solr.compose_query(request_dict)
    query = search_solr.update_query_with_stats_prequery(
        query
    )
    solr_response = search_solr.query_solr(query)
    result_maker = ResultMaker(
        request_dict=request_dict,
        facet_fields_to_client_request=search_solr.facet_fields_to_client_request,
        base_search_url='/query/',
    )
    result_maker.act_responses = configs.RESPONSE_DEFAULT_TYPES
    result_maker.create_result(
        solr_json=solr_response
    )
    query['facet-fields-to-client'] = result_maker.facet_fields_to_client_request
    query['response'] = result_maker.result
    query['raw-solr-response'] = solr_response
    return query
    

@cache_control(no_cache=True)
def query_json(request, spatial_context=None):
    """ API for searching Open Context """
    
    request_dict = utilities.make_request_obj_dict(
        request, spatial_context=spatial_context
    )
    response_dict = process_solr_query(request_dict)
    
    req_neg = RequestNegotiation('application/json')
    req_neg.supported_types = ['application/ld+json']
    
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])

    # Associate the request media type with the request so we can
    # make sure that different representations of this resource get different
    # cache responses.
    request.content_type = req_neg.use_response_type
    if not req_neg.supported:
        # Client wanted a mimetype we don't support
        response = HttpResponse(
            req_neg.error_message,
            content_type=req_neg.use_response_type + "; charset=utf8",
            status=415
        )
        patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
        return response
    
    json_output = json.dumps(response_dict, indent=4, ensure_ascii=False)
    if 'callback' in request.GET:
        # The JSON-P response
        funct = request.GET['callback']
        response = HttpResponse(
            '{funct}({json_output});'.format(funct=funct,json_output=json_output),
            content_type='application/javascript' + "; charset=utf8"
        )
        patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
        return response

    response = HttpResponse(
        json_output,
        content_type=req_neg.use_response_type + "; charset=utf8"
    )
    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
    return response