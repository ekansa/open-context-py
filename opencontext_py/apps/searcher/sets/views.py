import json
from django.conf import settings
from django.http import HttpResponse
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs import viewutilities
from opencontext_py.libs.general import LastUpdatedOrderedDict


def index(request, spatial_context=None):
    return HttpResponse("Hello, world. You're at the sets index.")


def html_view(request, spatial_context=None):
    return HttpResponse("Hello, world. You are trying to browse sets.")


def json_view(request, spatial_context=None):

    # Connect to Solr
    solr = SolrConnection().connection

    # Start building solr query
    query = {}
    # TODO field list (fl)
    #query['fl'] = ['uuid', 'label']
    query['facet'] = 'true'
    query['facet.mincount'] = 1
    query['rows'] = 10
    query['start'] = 0
    query['debugQuery'] = 'true'
    query['fq'] = []
    query['facet.field'] = []
    query['stats'] = 'true'
    query['stats.field'] = 'updated'

    # If the user does not provide a search term, search for everything
    query['q'] = request.GET.get('q', default='*:*')
    query['start'] = request.GET.get('start', default='0')

    # Spatial Context
    context = viewutilities._process_spatial_context(spatial_context)
    query['fq'].append(context['fq'])
    query['facet.field'].append(context['facet.field'])

    # Descriptive Properties
    prop_list = request.GET.getlist('prop')
    if prop_list:
        props = viewutilities._process_prop_list(prop_list)
        for prop in props:
            if prop['fq'] not in query['fq']:
                query['fq'].append(prop['fq'])
            if prop['facet.field'] not in query['facet.field']:
                query['facet.field'].append(prop['facet.field'])

    response = solr.search(**query)

    json_ld = LastUpdatedOrderedDict()
    json_ld['@context'] = LastUpdatedOrderedDict()

    # add @context

    # add id
    host = settings.CANONICAL_HOST
    full_path = request.get_full_path()
    id = host + full_path
    json_ld['id'] = id

    # Add label
    json_ld['label'] = 'Open Context Query Results'
    # TODO Get the the number of results
    # <opensearch:totalResults>4230000</opensearch:totalResults>
    # <opensearch:startIndex>21</opensearch:startIndex>
    # <opensearch:itemsPerPage>10</opensearch:itemsPerPage>

    #return HttpResponse(json.dumps(json_ld, ensure_ascii=False, indent=4),
    #
    #                    content_type="application/json; charset=utf8")

    #return HttpResponse(json.dumps(response.facets['facet_fields'],
    #                    ensure_ascii=False, indent=4),
    #                    content_type="application/json; charset=utf8")
    return HttpResponse(json.dumps(response.raw_content,
                        ensure_ascii=False, indent=4),
                        content_type="application/json; charset=utf8")
