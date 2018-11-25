import json
import mimetypes
from django.http import HttpResponse, Http404
from django.conf import settings
from django.shortcuts import redirect
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.libs.graph import (
    RDF_SERIALIZATIONS,
    graph_serialize,
    strip_non_point_features
)
from opencontext_py.apps.entities.redirects.manage import RedirectURL
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from opencontext_py.apps.contexts.manage import consolidate_contexts
from opencontext_py.apps.ocitems.ocitem.generation import OCitem
from django.utils.cache import patch_vary_headers    


def items_graph(request, identifier, return_media=None, item_type=None):
    # The new Open Context OCitem generator
    # that better integrates caching
    oc_item = OCitem()
    if 'hashes' in request.GET:
        oc_item.assertion_hashes = True
    if not oc_item.check_exists(identifier):
        # Did not find a record for the table, check for redirects
        r_ok = False
        if item_type:
            r_url = RedirectURL()
            r_ok = r_url.get_direct_by_type_id(item_type, identifier)
        if r_ok:
            # found a redirect!!
            return redirect(r_url.redirect, permanent=r_url.permanent)
        # raise Http404
        raise Http404
    if item_type and item_type != oc_item.manifest.item_type:
        # We have a rare case where the item_type is wrong, even though we found
        # something in the manifest, so throw an error.
        raise Http404
    oc_item.generate_json_ld()
    req_neg = RequestNegotiation('application/json')
    req_neg.supported_types = ['application/ld+json']
    if (not item_type or
        item_type not in ['persons', 'types', 'predicates', 'tables']):
        # We don't have specified item type, or the item_type is
        # not for a resource that's lacking a geospatial component. Therefore,
        # support GeoJSON as a media type.
        req_neg.supported_types.append('application/vnd.geo+json')
    req_neg.supported_types += RDF_SERIALIZATIONS
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if return_media:
        req_neg.check_request_support(return_media)
        req_neg.use_response_type = return_media
    # Associate the request media type with the request so we can
    # make sure that different representations of this resource get different
    # cache responses.
    request.content_type = req_neg.use_response_type
    if not req_neg.supported:
        # client wanted a mimetype we don't support
        response = HttpResponse(req_neg.error_message,
                                content_type=req_neg.use_response_type + "; charset=utf8",
                                status=415)
        patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
        return response
    # Check first if the output is requested to be an RDF format
    graph_output = None
    if req_neg.use_response_type in RDF_SERIALIZATIONS:
        json_ld = oc_item.json_ld
        # We're making an RDF graph serialization, so consolidate all the
        # context resources so we don't have to make Web requests to generate
        # the graph
        consolidated_contexts = consolidate_contexts(oc_item.json_ld)
        json_ld['@context'] = consolidated_contexts
        # Now make and serialize the graph
        graph_output = graph_serialize(req_neg.use_response_type,
                                       json_ld)
    if graph_output:
        # Return with some sort of graph output
        response = HttpResponse(graph_output,
                                content_type=req_neg.use_response_type + "; charset=utf8")
        patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
        return response
    # We're outputing JSON
    if (req_neg.use_response_type == 'application/ld+json' or
        return_media == 'application/ld+json'):
        # A hack to remove non-point features so JSON-LD will validate.
        json_ld = strip_non_point_features(oc_item.json_ld)
    else:
        json_ld = oc_item.json_ld
    json_output = json.dumps(json_ld,
                             indent=4,
                             ensure_ascii=False)
    if 'callback' in request.GET:
        funct = request.GET['callback']
        response = HttpResponse(funct + '(' + json_output + ');',
                                content_type='application/javascript' + "; charset=utf8")
        patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
        return response
    else:
        response = HttpResponse(json_output,
                                content_type=req_neg.use_response_type + "; charset=utf8")
        patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
        return response

