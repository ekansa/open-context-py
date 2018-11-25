import json
from django.conf import settings
from django.http import HttpResponse, Http404
from django.template import RequestContext, loader
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.graph import (
    RDF_SERIALIZATIONS,
    graph_serialize
)
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.contexts.models import ItemContext
from opencontext_py.apps.contexts.models import SearchContext
from opencontext_py.apps.contexts.projectcontext import ProjectContext
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.utils.cache import patch_vary_headers


def index(request):
    return HttpResponse("Hello, world. You're at the contexts index.")


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
def projects_json(request, uuid):
    """ provides a JSON-LD context for
        the predicates used in a project.
        
        DEPRECATE THIS!
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



def project_vocabs(request, uuid, return_media=None):
    """ Provides a RDF serialization, defaulting to a
        JSON-LD context for
        the data in a project. This will include
        a graph object that has annotations
        annotations of predicates and types
    """
    proj_context = ProjectContext(uuid, request)
    if 'hashes' in request.GET:
        proj_context.assertion_hashes = True
    if not proj_context.manifest:
        raise Http404
    req_neg = RequestNegotiation('application/json')
    req_neg.supported_types = ['application/ld+json']
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
    json_ld = proj_context.make_context_and_vocab_json_ld()
    # Check first if the output is requested to be an RDF format
    graph_output = graph_serialize(req_neg.use_response_type,
                                   json_ld)
    if graph_output:
        # Return with some sort of graph output
        response = HttpResponse(graph_output,
                                content_type=req_neg.use_response_type + "; charset=utf8")
        patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
        return response
    # We're outputing JSON
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

def project_vocabs_json(request, uuid):
    """Returns a JSON media response for a project context, vocab"""
    return project_vocabs(request, uuid, return_media='application/json')

def project_vocabs_jsonld(request, uuid):
    """Returns a JSON-LD media response for a project context, vocab"""
    return project_vocabs(request, uuid, return_media='application/ld+json')

def project_vocabs_nquads(request, uuid):
    """Returns a N-Quads media response for a project context, vocab"""
    return project_vocabs(request, uuid, return_media='application/n-quads')

def project_vocabs_ntrpls(request, uuid):
    """Returns a N-Triples media response for a project context, vocab"""
    return project_vocabs(request, uuid, return_media='application/n-triples')

def project_vocabs_rdf(request, uuid):
    """Returns a RDF/XML media response for a project context, vocab"""
    return project_vocabs(request, uuid, return_media='application/rdf+xml')

def project_vocabs_turtle(request, uuid):
    """Returns a Turtle media response for a project context, vocab"""
    return project_vocabs(request, uuid, return_media='text/turtle')