import json
from django.conf import settings
from django.http import HttpResponse, Http404
from django.template import RequestContext, loader
from opencontext_py.libs.general import LastUpdatedOrderedDict
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


def index(request, spatial_context=None):
    return HttpResponse("Hello, world. You're at the archive index.")
