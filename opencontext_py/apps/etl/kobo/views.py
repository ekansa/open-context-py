import json
from django.shortcuts import redirect
from django.http import HttpResponse, Http404

from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


@cache_control(no_cache=True)
@never_cache
def submissions_kobo_proxy(request):
    """This does nothing for now"""
    return None
