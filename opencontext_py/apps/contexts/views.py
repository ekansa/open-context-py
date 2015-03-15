import json
from django.conf import settings
from django.http import HttpResponse, Http404
from django.template import RequestContext, loader
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.contexts.models import ItemContext
from opencontext_py.apps.contexts.models import SearchContext


def index(request, spatial_context=None):
    return HttpResponse("Hello, world. You're at the sets index.")


def item_view(request):
    """ Get the item context JSON-LD """
    item_context_obj = ItemContext()
    json_ld = LastUpdatedOrderedDict()
    json_ld['@context'] = item_context_obj.context
    req_neg = RequestNegotiation('application/json')
    req_neg.supported_types = ['application/ld+json']
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        return HttpResponse(json.dumps(json_ld,
                            ensure_ascii=False, indent=4),
                            content_type=req_neg.use_response_type + "; charset=utf8")
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


def search_view(request):
    """ Get the search context JSON-LD """
    search_context_obj = SearchContext()
    json_ld = LastUpdatedOrderedDict()
    json_ld['@context'] = search_context_obj.context
    req_neg = RequestNegotiation('application/json')
    req_neg.supported_types = ['application/ld+json']
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        return HttpResponse(json.dumps(json_ld,
                            ensure_ascii=False, indent=4),
                            content_type=req_neg.use_response_type + "; charset=utf8")
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)

