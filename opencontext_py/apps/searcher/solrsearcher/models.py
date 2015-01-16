import json
from django.conf import settings
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker


# This class is used to dereference URIs or prefixed URIs
# to get useful information about the entity
class SolrSearch():

    def __init__(self):
        self.solr = False
        self.solr_connect()
        self.solr_response = False
        self.json_ld = False

    def solr_connect(self):
        """ connects to solr """
        self.solr = SolrConnection().connection

    def search_solr(self, request_dict):
        """searches solr to get raw solr search results"""
        # Start building solr query
        query = self.compose_query(request_dict)
        return self.solr.search(**query)

    def compose_query(self, request_dict):
        """ composes the search query based on the request_dict """
        qm = QueryMaker()
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
        query['stats.field'] = ['updated', 'published']
        # If the user does not provide a search term, search for everything
        query['q'] = self.get_request_param(request_dict,
                                            'q',
                                            '*:*')
        query['start'] = self.get_request_param(request_dict,
                                                'start',
                                                '0')
         # Spatial Context
        context = qm._process_spatial_context(request_dict['path'])
        query['fq'].append(context['fq'])
        query['facet.field'] += context['facet.field']  # context facet fields, always a list
        # Descriptive Properties
        prop_list = self.get_request_param(request_dict,
                                           'prop',
                                           False,
                                           True)
        if prop_list:
            props = qm._process_prop_list(prop_list)
            for prop in props:
                if prop['fq'] not in query['fq']:
                    query['fq'].append(prop['fq'])
                if prop['facet.field'] not in query['facet.field']:
                    query['facet.field'].append(prop['facet.field'])
        query = self.add_default_facet_fields(query)
        return query

    def add_default_facet_fields(self, query):
        """ adds additional facet fields to query """
        default_list = [SolrDocument.ROOT_PREDICATE_SOLR,
                        SolrDocument.ROOT_LINK_DATA_SOLR,
                        SolrDocument.ROOT_PROJECT_SOLR]
        for default_field in default_list:
            if default_field not in query['facet.field']:
                query['facet.field'].append(default_field)
        return query

    def get_request_param(self, request_dict, param, default, as_list=False):
        """ get a string or list to use in queries from either
            the request object or the internal_request object
            so we have flexibility in doing searches without
            having to go through HTTP
        """
        if request_dict is not False:
            if as_list:
                if param in request_dict:
                    param_obj = request_dict[param]
                    if isinstance(param_obj, list):
                        output = param_obj
                    else:
                        output = [param_obj]
            else:
                if param in request_dict:
                    output = request_dict[param]
                else:
                    output = default
        else:
            output = False
        return output

    def make_request_obj_dict(self, request, spatial_context):
        """ makes the Django request object into a dictionary obj """
        new_request = LastUpdatedOrderedDict()
        if spatial_context is not None:
            new_request['path'] = spatial_context
        else:
            new_request['path'] = False
        if request is not False:
            for key, key_val in request.GET.items():  # "for key in request.GET" works too.
                new_request[key] = request.GET.getlist(key)
        return new_request
