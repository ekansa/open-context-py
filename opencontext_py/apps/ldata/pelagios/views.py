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
@never_cache
@cache_control(no_cache=True)
@never_cache
def void(request):
    """ Returns RDF void data describing different datasets for
        Pelagious
    """
    p_void = PelagiosVoid()
    p_void.request = request
    p_void.make_graph()
    output = p_void.g.serialize(format='turtle')
    return HttpResponse(output,
                        content_type='text/turtle; charset=utf8')
    
def void_alt(request):
    """ Returns RDF void data describing different datasets for
        Pelagious
    """
    p_void = PelagiosVoid()
    p_void.request = request
    req_neg = RequestNegotiation('text/turtle')
    req_neg.supported_types = ['text/turtle']
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        if 'turtle' in req_neg.use_response_type:
            output = p_void.g.serialize(format='turtle')
            return HttpResponse(output,
                                content_type='text/turtle; charset=utf8')


@cache_control(no_cache=True)
@never_cache
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
                pelagios.project_uuids = [ent.uuid]
                pelagios.test_limit = None
                pelagios.make_graph()
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
