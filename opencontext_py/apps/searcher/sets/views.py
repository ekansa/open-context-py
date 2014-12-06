import json
from django.http import HttpResponse
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
    # TODO field list (fl)
    #query['fl'] = ['uuid']
    query['facet'] = 'true'
    query['facet.mincount'] = 1
    query['fq'] = []
    query['facet.field'] = []
    query['rows'] = 10
    query['start'] = 0
    query['debugQuery'] = 'true'

    # If the user does not provide a search term, search for everything
    query['q'] = request.GET.get('q', default='*:*')

    # Spatial Context
    context = viewutilities._process_spatial_context(spatial_context)
    query['fq'].append(context['fq'])
    query['facet.field'].append(context['facet.field'])

    # Descriptive Properties
    prop_list = request.GET.getlist('prop')
    props = viewutilities._process_prop_list(prop_list)
    if props:
        for prop in props:
            if prop['fq'] not in query['fq']:
                query['fq'].append(prop['fq'])
            if prop['facet.field'] not in query['facet.field']:
                query['facet.field'].append(prop['facet.field'])
    response = solr.search(**query)
    #return HttpResponse(json.dumps(response.facets['facet_fields'],
    #                    ensure_ascii=False, indent=4),
    #                    content_type="application/json; charset=utf8")
    return HttpResponse(json.dumps(response.raw_content,
                        ensure_ascii=False, indent=4),
                        content_type="application/json")
