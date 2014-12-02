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

    # If the user does not provide a spatial context, start at the root context
    if spatial_context is None:
        context_facet_request_field = 'root___context_id'
    # Otherwise, process the context path
    else:
        context_list = []
        context_depth = viewutilities._get_context_depth(spatial_context)

        # Prepare to resolve spatial entities
        entity = Entity()

        context_list = viewutilities._get_context_paths(spatial_context)
        context_slugs = viewutilities._get_valid_context_slugs(context_list)
        # TODO: Stopped above but still testing here
        # return HttpResponse(context_slugs)

        # found = entity.context_dereference(
        #    http.urlunquote_plus(spatial_context))
        # if found:
        #    current_slug = entity.slug
        #    context_facet_request_field = current_slug.replace(
        #        '-', '_') + '___context_id'
        # else:
        #    raise Http404
        # Get the solr field name
        # if context_depth == 1:
        #     # set fq as the root___context_id:<current context slug>
        #    fq_request_field = 'root___context_id_fq:' + current_slug
        # else:
        #    #  We need the parent slug so we can generate the solr field name
        #    # for fq requests
        #
        #    # Removes the last part of the path
        #    parent_path = '/'.join(spatial_context.split('/')[:-1])
        #    # Use parent_path to get the parent slug
        #    parent_found = entity.context_dereference(
        #        http.urlunquote_plus(parent_path))
        #    if parent_found:
        #        parent_slug = entity.slug
        #        parent_field_name = parent_slug.replace(
        #            '-', '_') + '___context_id'
        #        fq_request_field = parent_field_name + '_fq' + ':' + \
        #            current_slug    # + '___*'
        #    else:
        #       # for debugging pursposes only
        #        pass
                #return HttpResponse(str(context_depth) + ' ' + \
                    #str(parent_found) + ' ' + str(parent_slug))
        #context_data['solr_field_name'] = solr_field_name

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
    return HttpResponse(json.dumps(response.facets['facet_fields'],
                        ensure_ascii=False, indent=4),
                        content_type="application/json; charset=utf8")
    #return HttpResponse(json.dumps(response.raw_content,
    #                    ensure_ascii=False, indent=4),
    #                    content_type="application/json")
