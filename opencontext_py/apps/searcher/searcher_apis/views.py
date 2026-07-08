import copy
import json

from django.conf import settings
from django.core.cache import caches
from django.http import HttpResponse, HttpResponseRedirect
from django.http import HttpResponse, Http404
from django.shortcuts import redirect

from django.template import loader
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation

from opencontext_py.apps.all_items.editorial import api as editorial_api

from opencontext_py.apps.searcher.new_solrsearcher import db_entities
from opencontext_py.apps.all_items import hierarchy


from django.views.decorators.cache import cache_control
from django.utils.cache import patch_vary_headers, get_cache_key
from django.utils.http import urlencode


if settings.DEBUG:
    SEARCH_CACHE_TIMEOUT = 60 # 1 minute
else:
    SEARCH_CACHE_TIMEOUT = 60 * 60 * 24 * 7 # 1 week


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
    cache = caches['default']
    cache_key = get_cache_key(request, cache=cache)
    print(f'Cache key: "{cache_key}" for "{request.path}"')
    response = HttpResponse(
        json_output,
        content_type=req_neg.use_response_type + "; charset=utf8"
    )
    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
    return response


def item_children_json(request, identifier):
    req_neg = RequestNegotiation('application/json')
    item_man_obj = db_entities.get_cache_man_obj_by_any_id(identifier)
    if not item_man_obj:
        response = HttpResponse(
            {
                'error': 'No object found',
                'identifier': identifier,
            },
            content_type=req_neg.use_response_type + "; charset=utf8",
            status=404,
        )
        patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
        return response
    all_children = hierarchy.get_next_children_w_alt_labels_by_item_type(
        item_man_obj=item_man_obj,
        use_cache=False,
    )
    rep_dict = [editorial_api.manifest_obj_to_json_safe_dict(m) for m in all_children]
    json_output = json.dumps(
        rep_dict,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )



def query_json(request, spatial_context=None):
    """ API for searching Open Context """

    request_dict = utilities.make_request_obj_dict(
        request, spatial_context=spatial_context
    )
    response_dict = main_search.process_solr_query(request_dict.copy())

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

