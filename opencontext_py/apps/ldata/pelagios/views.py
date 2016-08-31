import json
import mimetypes
import requests
import logging
from django.http import HttpResponse, Http404
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.pelagios.graph import PelagiosGraph
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


# These views display an HTML form for classifying import fields,
# and handles AJAX requests / responses to change classifications
def index(request):
    return HttpResponse("Hello, world. You're at the entities index.")


@cache_control(no_cache=True)
@never_cache
def project_annotations(request, identifier):
    """ Returns JSON data for an identifier in its hierarchy """
    ent = Entity()
    found = ent.dereference(identifier)
    if found:
        if ent.item_type == 'projects':
            pelagios = PelagiosGraph()
            pelagios.project_uuids = [ent.uuid]
            pelagios.test_limit = None
            pelagios.make_graph()
            output = pelagios.g.serialize(format='turtle')
            return HttpResponse(output,
                                content_type='text/turtle; charset=utf8')
        else:
            found = False
    if found is False:
        raise Http404