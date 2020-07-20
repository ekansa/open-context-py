import json
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponse, Http404

from django.template import RequestContext, loader
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.requestnegotiation import RequestNegotiation

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.template_prep import SearchTemplate
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
        facet_fields_to_client_request=search_solr.facet_fields_to_client_request,
        base_search_url='/query/',
    )
    result_maker.create_result(
        solr_json=solr_response
    )
    result_maker.result['query'] = query
    return result_maker.result


def make_json_response(request, req_neg, response_dict):
    """Makes a JSON response with content negotiation"""
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
    
    return make_json_response(request, req_neg, response_dict)


@cache_control(no_cache=True)
def query_html(request, spatial_context=None):
    """HTML representation for searching Open Context """
    
    request_dict = utilities.make_request_obj_dict(
        request, spatial_context=spatial_context
    )
    response_dict = process_solr_query(request_dict.copy())
    
    req_neg = RequestNegotiation('text/html')
    req_neg.supported_types = [
        'application/json',
        'application/ld+json',
    ]
    
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
    
    if req_neg.use_response_type.endswith('json'):
        return make_json_response(request, req_neg, response_dict)

    rp = RootPath()
    # Disable the search template and just use vue with the JSON
    # API.
    # search_temp = SearchTemplate(response_dict.copy())
    context = {
        'st': response_dict.copy(),
        'base_url': rp.get_baseurl(),
        'api_url': response_dict.get('id'),
        'configs': configs,
    }
    template = loader.get_template('search_vue/view.html')
    response = HttpResponse(template.render(context, request))
    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
    return response