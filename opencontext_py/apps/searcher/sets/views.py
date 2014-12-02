import json
from django.http import HttpResponse, Http404
import django.utils.http as http
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs import viewutilities


def index(request):
    return HttpResponse("Hello, world. You're at the sets index.")


def html_view(request, spatial_context=None):
    return HttpResponse("Hello, world. You are trying to browse sets.")


def json_view(request, spatial_context=None):

    # Connect to Solr
    solr = SolrConnection().connection

    # Start building up our solr query
    query = {}

    # If the user does not provide a search term, search for everything
    query['q'] = request.GET.get('q', default='*:*')

    context = viewutilities._process_spatial_context(spatial_context)
    # build solr query
    #query['fl'] = ['uuid', context_facet_request_field]
    #query['facet.field'] = context_facet_request_field
    query['facet'] = 'true'
    query['facet.mincount'] = 1
    query['fq'] = context['fq']
    query['facet.field'] = context['facet.field']
    query['rows'] = 10
    query['start'] = 0
    query['debugQuery'] = 'true'
    response = solr.search(**query)
    # return HttpResponse(query_params.items())
    # return HttpResponse(context_list)
    # return HttpResponse(query['fq'])
    #return HttpResponse(json.dumps(response.facets['facet_fields'],
    #                    ensure_ascii=False, indent=4),
    #                    content_type="application/json; charset=utf8")
    return HttpResponse(json.dumps(response.raw_content,
                        ensure_ascii=False, indent=4),
                        content_type="application/json")
