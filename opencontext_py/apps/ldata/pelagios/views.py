import json
import mimetypes
import requests
import logging
from django.http import HttpResponse, Http404
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.pelagios.void import PelagiosVoid
from opencontext_py.apps.ldata.pelagios.graph import PelagiosGraph
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


# These views display an HTML form for classifying import fields,
# and handles AJAX requests / responses to change classifications
def index(request):
    return HttpResponse("Hello, world. You're at the entities index.")


@cache_control(no_cache=True)
def void_ttl(request):
    """ Returns RDF void data describing different datasets for
        Pelagios, in turtle
    """
    p_void = PelagiosVoid()
    p_void.request = request
    p_void.make_graph()
    output = p_void.g.serialize(format='turtle')
    return HttpResponse(output,
                        content_type='text/turtle; charset=utf8')


@cache_control(no_cache=True)
def void(request):
    """ Returns RDF void data describing different datasets for
        Pelagious
    """
    p_void = PelagiosVoid()
    p_void.request = request
    p_void.make_graph()
    req_neg = RequestNegotiation('text/turtle')
    req_neg.supported_types = ['application/rdf+xml',
                               'text/n3',
                               'application/n-triples']
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            content_type = req_neg.use_response_type + '; charset=utf8'
            output = p_void.g.serialize(format=req_neg.use_response_type)
            return HttpResponse(output,
                                content_type=content_type)
        else:
            # client wanted a mimetype we don't support
            return HttpResponse(req_neg.error_message,
                                content_type="text/plain; charset=utf8",
                                status=415)
    else:
        # default to outputting in turtle
        output = p_void.g.serialize(format='turtle')
        return HttpResponse(output,
                            content_type='text/turtle; charset=utf8')


@cache_control(no_cache=True)
def project_annotations(request, identifier):
    """ Returns RDF open annotation assertions conforming to
        Pelagios specifications that link
        Open Context resources with place entities in
        gazetteers
    """
    ent = Entity()
    found = ent.dereference(identifier)
    if found:
        if ent.item_type == 'projects':
            pp = ProjectPermissions(ent.uuid)
            permitted = pp.view_allowed(request)
            if permitted:
                pelagios = PelagiosGraph()
                if 'refresh' in request.GET:
                    # we're going to refresh the cache
                    pelagios.refresh_cache = True
                pelagios.project_uuids = [ent.uuid]
                pelagios.test_limit = None
                pelagios.make_graph()
                req_neg = RequestNegotiation('text/turtle')
                req_neg.supported_types = ['application/rdf+xml',
                                           'text/n3',
                                           'application/n-triples']
                if 'HTTP_ACCEPT' in request.META:
                    req_neg.check_request_support(request.META['HTTP_ACCEPT'])
                    if req_neg.supported:
                        content_type = req_neg.use_response_type + '; charset=utf8'
                        output = pelagios.g.serialize(format=req_neg.use_response_type)
                        return HttpResponse(output,
                                            content_type=content_type)
                    else:
                        # client wanted a mimetype we don't support
                        return HttpResponse(req_neg.error_message,
                                            content_type="text/plain; charset=utf8",
                                            status=415)
                else:
                    # default to outputting in turtle
                    output = pelagios.g.serialize(format='turtle')
                    return HttpResponse(output,
                                        content_type='text/turtle; charset=utf8')
            else:
                return HttpResponse('Not authorized to get this resource',
                                    content_type='text/html; charset=utf8',
                                    status=401)
        else:
            found = False
    if found is False:
        raise Http404


@cache_control(no_cache=True)
def project_annotations_ttl(request, identifier):
    """ Returns RDF open annotation assertions conforming to
        Pelagios specifications that link
        Open Context resources with place entities in
        gazetteers, in the turtle format
    """
    ent = Entity()
    found = ent.dereference(identifier)
    if found:
        if ent.item_type == 'projects':
            pp = ProjectPermissions(ent.uuid)
            permitted = pp.view_allowed(request)
            if permitted:
                pelagios = PelagiosGraph()
                pelagios.project_uuids = [ent.uuid]
                pelagios.test_limit = None
                pelagios.make_graph()
                # default to outputting in turtle
                output = pelagios.g.serialize(format='turtle')
                return HttpResponse(output,
                                    content_type='text/turtle; charset=utf8')
            else:
                return HttpResponse('Not authorized to get this resource',
                                    content_type='text/html; charset=utf8',
                                    status=401)
        else:
            found = False
    if found is False:
        raise Http404