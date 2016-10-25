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
from opencontext_py.apps.entities.entity.templating import EntityTemplate
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


# These views display an HTML form for classifying import fields,
# and handles AJAX requests / responses to change classifications
def index(request):
    return HttpResponse("Hello, world. You're at the entities index.")
