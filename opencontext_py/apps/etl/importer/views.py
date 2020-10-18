import json
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponse, Http404

from django.template import RequestContext, loader
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities


from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.views.decorators.cache import cache_page
from django.utils.cache import patch_vary_headers





@never_cache
def test_a(request):
    """Does Nothing. Yet..."""
    return None


@never_cache
def test_b(request):
    """Does Nothing. Yet..."""
    return None