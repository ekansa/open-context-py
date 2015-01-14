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
        self.request = False
        self.internal_request = False
        self.spatial_context = None
        self.solr = False
        self.solr_connect()
        self.solr_response = False
        self.json_ld = False

    def solr_connect(self):
        """ connects to solr """
        self.solr = SolrConnection().connection

    def search_solr(self):
        """searches solr to get raw solr search results"""
        # Start building solr query
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
        query['q'] = self.get_request_param('q', '*:*')
        query['start'] = self.get_request_param('start', '0')
         # Spatial Context
        context = qm._process_spatial_context(self.spatial_context)
        query['fq'].append(context['fq'])
        query['facet.field'] += context['facet.field']  # context facet fields, always a list
        # Descriptive Properties
        prop_list = self.get_request_param('prop', False, True)
        if prop_list:
            props = qm._process_prop_list(prop_list)
            for prop in props:
                if prop['fq'] not in query['fq']:
                    query['fq'].append(prop['fq'])
                if prop['facet.field'] not in query['facet.field']:
                    query['facet.field'].append(prop['facet.field'])
        if SolrDocument.ROOT_PREDICATE_SOLR not in query['facet.field']:
            query['facet.field'].append(SolrDocument.ROOT_PREDICATE_SOLR)
        query['facet.field'].append(SolrDocument.ROOT_LINK_DATA_SOLR)
        query['facet.field'].append(SolrDocument.ROOT_PROJECT_SOLR)
        return self.solr.search(**query)

    def get_request_param(self, param, default, as_list=False):
        """ get a string or list to use in queries from either
            the request object or the internal_request object
            so we have flexibility in doing searches without
            having to go through HTTP
        """
        output = False
        if self.request is not False:
            if as_list:
                output = self.request.GET.getlist(param)
            else:
                output = self.request.GET.get(param, default=default)
        elif self.internal_request is not False:
            if as_list:
                if param in self.internal_request:
                    param_obj = self.internal_request[param]
                    if isinstance(param_obj, list):
                        output = param_obj
                    else:
                        output = [param_obj]
            else:
                if param in self.internal_request:
                    output = self.internal_request[param]
                else:
                    output = default
        else:
            output = False
        return output
