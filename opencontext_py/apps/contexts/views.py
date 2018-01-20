import json
from django.conf import settings
from django.http import HttpResponse, Http404
from django.template import RequestContext, loader
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.contexts.models import ItemContext
from opencontext_py.apps.contexts.models import SearchContext
from opencontext_py.apps.contexts.projectcontext import ProjectContext
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


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


@cache_control(no_cache=True)
# @never_cache
def projects_json(request, uuid):
    """ provides a JSON-LD context for
        the predicates used in a project. 
    """
    proj_context = ProjectContext(uuid, request)
    if 'hashes' in request.GET:
        proj_context.assertion_hashes = True
    if proj_context.manifest is not False:
        req_neg = RequestNegotiation('application/json')
        req_neg.supported_types = ['application/ld+json',
                                   'application/vnd.geo+json']
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            json_ld = proj_context.make_context_json_ld()
            json_output = json.dumps(json_ld,
                                     indent=4,
                                     ensure_ascii=False)
            if 'callback' in request.GET:
                funct = request.GET['callback']
                return HttpResponse(funct + '(' + json_output + ');',
                                    content_type='application/javascript' + "; charset=utf8")
            else:
                return HttpResponse(json_output,
                                    content_type=req_neg.use_response_type + "; charset=utf8")
        else:
            # client wanted a mimetype we don't support
            return HttpResponse(req_neg.error_message,
                                content_type=req_neg.use_response_type + "; charset=utf8",
                                status=415)
    else:
        raise Http404


@cache_control(no_cache=True)
# @never_cache
def project_vocabs_json(request, uuid):
    """ provides a JSON-LD context for
        the data in a project. This will include
        a graph object that has annotations
        annotations of predicates and types
    """
    proj_context = ProjectContext(uuid, request)
    if 'hashes' in request.GET:
        proj_context.assertion_hashes = True
    if proj_context.manifest is not False:
        req_neg = RequestNegotiation('application/json')
        req_neg.supported_types = ['application/ld+json',
                                   'application/vnd.geo+json']
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            json_ld = proj_context.make_context_and_vocab_json_ld()
            json_output = json.dumps(json_ld,
                                     indent=4,
                                     ensure_ascii=False)
            if 'callback' in request.GET:
                funct = request.GET['callback']
                return HttpResponse(funct + '(' + json_output + ');',
                                    content_type='application/javascript' + "; charset=utf8")
            else:
                return HttpResponse(json_output,
                                    content_type=req_neg.use_response_type + "; charset=utf8")
        else:
            # client wanted a mimetype we don't support
            return HttpResponse(req_neg.error_message,
                                content_type=req_neg.use_response_type + "; charset=utf8",
                                status=415)
    else:
        raise Http404