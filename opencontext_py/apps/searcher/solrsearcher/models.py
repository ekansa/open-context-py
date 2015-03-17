import re
import json
from django.conf import settings
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker
from opencontext_py.apps.searcher.solrsearcher.specialized import SpecialSearches


# This class is used to dereference URIs or prefixed URIs
# to get useful information about the entity
class SolrSearch():

    DEFAULT_FACET_FIELDS = [SolrDocument.ROOT_LINK_DATA_SOLR,
                            SolrDocument.ROOT_PROJECT_SOLR,
                            'item_type',
                            'image_media_count',
                            'other_binary_media_count',
                            'document_count']

    def __init__(self):
        self.solr = False
        self.solr_connect()
        self.solr_response = False
        self.json_ld = False
        self.entities = {}  # entities involved in a search request
        self.facet_fields = self.DEFAULT_FACET_FIELDS
        self.rows = 20
        self.start = 0
        self.max_rows = 10000

    def solr_connect(self):
        """ connects to solr """
        self.solr = SolrConnection(False).connection

    def search_solr(self, request_dict_json):
        """searches solr to get raw solr search results"""
        # Start building solr query
        request_dict = json.loads(request_dict_json)
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
        query['rows'] = self.rows
        query['start'] = self.start
        query['debugQuery'] = 'false'
        query['fq'] = []
        query['facet.field'] = []
        query['facet.range'] = []
        query['stats'] = 'true'
        query['stats.field'] = ['updated', 'published']
        query['sort'] = 'interest_score desc'
        s_param = self.get_request_param(request_dict,
                                         'sort',
                                         False,
                                         False)
        if s_param is not False:
            # add custom sorting
            query['sort'] = s_param
        # If the user does not provide a search term, search for everything
        query['q'] = '*:*'  # defaul search for all
        q_param = self.get_request_param(request_dict,
                                         'q',
                                         False,
                                         False)
        if q_param is not False:
            escaped_terms = qm.prep_string_search_term(q_param)
            query['q'] = ' '.join(escaped_terms)
            query['q.op'] = 'AND'
            query['hl'] = 'true'
            query['hl.fl'] = 'text'
            query['hl.q'] = ' '.join(escaped_terms)
        start = self.get_request_param(request_dict,
                                       'start',
                                       False,
                                       False)
        if start is not False:
            query['start'] = re.sub(r'[^\d]', r'', start)
        rows = self.get_request_param(request_dict,
                                      'rows',
                                      False,
                                      False)
        if rows is not False:
            rows = re.sub(r'[^\d]', r'', rows)
            rows = int(float(rows))
            if rows > self.max_rows:
                rows = self.max_rows
            elif rows < 0:
                rows = 0
            query['rows'] = rows
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
                query['facet.range'] += prop_query['facet.range']
                if 'ranges' in prop_query:
                    for key, value in prop_query['ranges'].items():
                        query[key] = value
                if 'hl-queries' in prop_query:
                    query['hl'] = 'true'
                    query['hl.fl'] = 'text'
                    # query['hl.snippets'] = 2
                    for q_term in prop_query['hl-queries']:
                        if 'hl.q' in query:
                            query['hl.q'] += ' OR (' + q_term + ')'
                        else:
                            query['hl.q'] = q_term
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
        # Dublin-Core terms
        dc_params = ['dc-subject',
                     'dc-spatial',
                     'dc-coverage']
        for dc_param in dc_params:
            dc_terms = self.get_request_param(request_dict,
                                              dc_param,
                                              False,
                                              True)
            if dc_terms is not False:
                dc_query = qm.process_dc_term(dc_param, dc_terms)
                query['fq'] += dc_query['fq']
                query['facet.field'] += dc_query['facet.field']
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
        # now add discovery geo location
        disc_geo = self.get_request_param(request_dict,
                                          'disc-geotile',
                                          False,
                                          False)
        if disc_geo is not False:
            disc_geo_query = qm.process_discovery_geo(disc_geo)
            query['fq'] += disc_geo_query['fq']
            query['facet.field'] += disc_geo_query['facet.field']
            query['f.discovery_geotile.facet.limit'] = -1
        else:
            # Add default geofacet
            query = self.add_root_discovery_geo(query,
                                                request_dict)
        # now add form-use-life chronology
        form_chrono = self.get_request_param(request_dict,
                                             'form-chronotile',
                                             False,
                                             False)
        if form_chrono is not False:
            # query for form-use-live chronological tile
            form_chrono_query = qm.process_form_use_life_chrono(form_chrono)
            query['fq'] += form_chrono_query['fq']
            query['facet.field'] += form_chrono_query['facet.field']
            query['f.form_use_life_chrono_tile.facet.limit'] = -1
        else:
            # Add default form-use-life chronology
            query = self.add_root_form_use_life_chrono(query,
                                                       request_dict)
        form_start = self.get_request_param(request_dict,
                                            'form-start',
                                            False,
                                            False)
        if form_start is not False:
            # query for form-use-live start date
            form_start_query = qm.process_form_date_chrono(self,
                                                           form_use_life_date,
                                                           'start')
            query['fq'] += form_start_query['fq']
        form_stop = self.get_request_param(request_dict,
                                           'form-stop',
                                           False,
                                           False)
        if form_stop is not False:
            # query for form-use-live stop date
            form_stop_query = qm.process_form_date_chrono(self,
                                                          form_use_life_date,
                                                          'stop')
            query['fq'] += form_stop_query['fq']
        # images
        images = self.get_request_param(request_dict,
                                        'images',
                                        False,
                                        False)
        if images is not False:
            query['fq'] += ['image_media_count:[1 TO *]']
        # other media (not images)
        other_media = self.get_request_param(request_dict,
                                             'other-media',
                                             False,
                                             False)
        if other_media is not False:
            query['fq'] += ['other_binary_media_count:[1 TO *]']
         # other media (not images)
        documents = self.get_request_param(request_dict,
                                           'documents',
                                           False,
                                           False)
        if documents is not False:
            query['fq'] += ['document_count:[1 TO *]']
        # special queries (to simplify access to specific datasets)
        spsearch = SpecialSearches()
        trinomial = self.get_request_param(request_dict,
                                           'trinomial',
                                           False,
                                           False)
        if trinomial is not False:
            query = spsearch.process_trinonial_reconcile(trinomial,
                                                         query)
        # Now add default facet fields
        query = self.add_default_facet_fields(query,
                                              request_dict)
        # Now set aside entities used as search filters
        self.gather_entities(qm.entities)
        return query

    def remove_from_default_facet_fields(self, field):
        """ removes a field from the default facet fields """
        if isinstance(self.facet_fields, list):
            if field in self.facet_fields:
                self.facet_fields.remove(field)

    def add_default_facet_fields(self,
                                 query,
                                 request_dict):
        """ adds additional facet fields to query """
        if isinstance(self.facet_fields, list):
            for default_field in self.facet_fields:
                if default_field not in query['facet.field']:
                    query['facet.field'].append(default_field)
            if 'proj' in request_dict:
                query['facet.field'].append(SolrDocument.ROOT_PREDICATE_SOLR)
            elif SolrDocument.ROOT_PROJECT_SOLR not in query['facet.field']:
                query['facet.field'].append(SolrDocument.ROOT_PROJECT_SOLR)
        return query

    def add_root_discovery_geo(self,
                               query,
                               request_dict):
        """ add base discovery - geo """
        if 'disc-geotile' not in request_dict:
            query['facet.field'].append('discovery_geotile')
            query['f.discovery_geotile.facet.limit'] = -1
        return query

    def add_root_form_use_life_chrono(self,
                                      query,
                                      request_dict):
        """ adds facet field for the most commonly
            used chronology description, when the
            item was created / formed, used, and
            or lived:
            form_use_life_chrono_tile
        """
        if 'form-chronotile' not in request_dict:
            query['facet.field'].append('form_use_life_chrono_tile')
            query['f.form_use_life_chrono_tile.facet.limit'] = -1
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

    def get_request_param(self,
                          request_dict,
                          param,
                          default,
                          as_list=False,
                          solr_escape=False):
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
                        if solr_escape:
                            param_obj = '"' + param_obj + '"'
                        output = [param_obj]
                else:
                    output = default
            else:
                if param in request_dict:
                    output = request_dict[param]
                    if isinstance(output, list):
                        output = output[0]
                    if solr_escape:
                        qm = QueryMaker()
                        if output[0] == '"' and output[-1] == '"':
                            output = qm.escape_solr_arg(output[1:-1])
                            output = '"' + output + '"'
                        else:
                            output = qm.escape_solr_arg(output)
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
