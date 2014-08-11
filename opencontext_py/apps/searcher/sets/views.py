import json
from django.http import HttpResponse, Http404
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.libs.general import LastUpdatedOrderedDict
#from django.template import RequestContext, loader
#from django.shortcuts import render


def index(request):
    return HttpResponse("Hello, world. You're at the sets index.")


def html_view(request, spatial_context=None):
    context_depth = len(spatial_context.rstrip('/').split(
        '/sets/')[0].split('/'))
    if spatial_context is None:
        return HttpResponse("Hello, world. You are trying to browse sets.")
    else:
        return HttpResponse(str(context_depth) +
                            " Hello, the context is: " + spatial_context)


def json_view(request, spatial_context=None):
    # Gather context-related information
    context_data = LastUpdatedOrderedDict()
    if spatial_context is not None:
        entity = Entity()
        found = entity.context_dereference(spatial_context)
        if found:
            context_data['slug'] = entity.slug
            context_data['id'] = entity.uri
            context_data['label'] = entity.label
            context_depth = len(spatial_context.rstrip('/').split(
                '/sets/')[0].split('/'))
        else:
            raise Http404
        if context_depth == 1:
            solr_field_name = 'root___context_id'
        else:
            solr_field_name = entity.slug.replace('-', '_') + '___context_id'
        context_data['solr_field_name'] = solr_field_name
        return HttpResponse(json.dumps(context_data, ensure_ascii=False),
                            content_type="application/json")
