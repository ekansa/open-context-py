import json
from django.conf import settings
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker


# This class is used to dereference URIs or prefixed URIs
# to get useful information about the entity
class SolrSearch():

    DEFAULT_FACET_FIELDS = [SolrDocument.ROOT_PREDICATE_SOLR,
                            SolrDocument.ROOT_LINK_DATA_SOLR,
                            SolrDocument.ROOT_PROJECT_SOLR,
                            'item_type']

    def __init__(self):
        self.solr = False
        self.solr_connect()
        self.solr_response = False
        self.json_ld = False
        self.entities = {}  # entities involved in a search request
        self.facet_fields = self.DEFAULT_FACET_FIELDS

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
        if 'path' in request_dict:
            self.remove_from_default_facet_fields(SolrDocument.ROOT_CONTEXT_SOLR)
            context = qm._process_spatial_context(request_dict['path'])
            query['fq'].append(context['fq'])
            query['facet.field'] += context['facet.field']  # context facet fields, always a list
            # Properties and Linked Data
        props = self.get_request_param(request_dict,
                                       'prop',
                                       False,
                                       True)
        if props is not False:
            for act_prop in props:
                # process each prop independently.
                prop_query = qm.process_prop(act_prop)
                query['fq'] += prop_query['fq']
                query['facet.field'] += prop_query['facet.field']
                query['stats.field'] += prop_query['stats.field']
                query['facet.range'] = prop_query['facet.range']
                if 'ranges' in prop_query:
                    for key, value in prop_query['ranges'].items():
                        print('Key: ' + key + ' val: ' + str(value))
                        query[key] = value
        # Project
        proj = self.get_request_param(request_dict,
                                      'proj',
                                      False)
        if proj is not False:
            # remove the facet field, since we're already filtering with it
            self.remove_from_default_facet_fields(SolrDocument.ROOT_PROJECT_SOLR)
            proj_query = qm.process_proj(proj)
            query['fq'] += proj_query['fq']
            query['facet.field'] += proj_query['facet.field']
        # item-types
        item_type = self.get_request_param(request_dict,
                                           'type',
                                           False,
                                           False)
        if item_type is not False:
            # remove the facet field, since we're already filtering with it
            self.remove_from_default_facet_fields('item_type')
            it_query = qm.process_item_type(item_type)
            query['fq'] += it_query['fq']
            query['facet.field'] += it_query['facet.field']
        # Now add default facet fields
        query = self.add_default_facet_fields(query)
        # Now set aside entities used as search filters
        self.gather_entities(qm.entities)
        return query

    def remove_from_default_facet_fields(self, field):
        """ removes a field from the default facet fields """
        if isinstance(self.facet_fields, list):
            if field in self.facet_fields:
                self.facet_fields.remove(field)

    def add_default_facet_fields(self, query):
        """ adds additional facet fields to query """
        if isinstance(self.facet_fields, list):
            for default_field in self.facet_fields:
                if default_field not in query['facet.field']:
                    query['facet.field'].append(default_field)
        return query

    def gather_entities(self, entities_dict):
        """ Gathers and stores entites found in
            the query maker object.
            These entities can be used in indicating
            filters applied in a search
        """
        for search_key, entity in entities_dict.items():
            if search_key not in self.entities:
                self.entities[search_key] = entity

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
                    output = default
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
