import json
from django.http import HttpResponse
#from django.template import RequestContext, loader
#from django.shortcuts import render


def index(request):
    return HttpResponse("Hello, world. You're at the sets index.")


def html_view(request, context=None):
    if context is None:
        return HttpResponse("Hello, world. You are trying to browse sets.")
    else:
        return HttpResponse("Hello, the context is: " + context)


def json_view(request, context=None):
    response_data = {'hello': 'world'}
    return HttpResponse(json.dumps(response_data),
                        content_type="application/json")
