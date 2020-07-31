import copy
import json
import logging
import time
from datetime import datetime
from django.conf import settings
from mysolr.compat import urljoin, compat_args, parse_response
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities
from opencontext_py.apps.searcher.new_solrsearcher import querymaker
from opencontext_py.apps.searcher.new_solrsearcher import ranges
from opencontext_py.apps.searcher.new_solrsearcher.sorting import SortingOptions


logger = logging.getLogger(__name__)


class SearchSolr():

    def __init__(self):
        self.solr = None
        self.solr_connect()
        self.solr_response = None
        self.json_ld = None
        # Use the copy() method to make sure we don't mutate the configs!
        self.init_facet_fields = configs.DEFAULT_FACET_FIELDS.copy()
        self.init_stats_fields = configs.ALL_TYPES_STATS_FIELDS.copy()
        self.rows = configs.SOLR_DEFAULT_ROW_COUNT
        self.start = 0
        self.max_rows = configs.SOLR_MAX_RESULT_ROW_COUNT
        self.prequery_stats = []
        self.item_type_limit = None  # limit searches to a specific item type
        self.do_context_paths = True  # make sure context paths are in the query
        self.is_bot = False
        self.do_bot_limit = False
        self.solr_debug_query = 'false'
        self.solr_stats_query = 'true'
        # Dictionary of keyed by facet fields that are derived from the
        # raw request paths provided by clients. This dictionary makes
        # it easier to generate links for different facet options.
        self.facet_fields_to_client_request = {}
    
    
    def solr_connect(self):
        """ Connects to solr """
        if self.solr is not None:
            # We are already connected, so skip connecting.
            return None

        if configs.USE_TEST_SOLR_CONNECTION:
            # Connect to the testing solr server
            self.solr = SolrConnection(
                exit_on_error=False,
                solr_host=settings.SOLR_HOST_TEST,
                solr_port=settings.SOLR_PORT_TEST,
                solr_collection=settings.SOLR_COLLECTION_TEST
            ).connection
        else:
            # Connect to the default solr server
            self.solr = SolrConnection(False).connection
    
    def add_initial_facet_fields(self, request_dict):
        """Adds to initial facet field list based on request_dict"""
        if 'proj' in request_dict:
            self.init_facet_fields.append(
                SolrDocument.ROOT_PREDICATE_SOLR
            )

    def _associate_facet_field_with_client_request(
        self, 
        param, 
        raw_path, 
        query_dict
    ):
        """Associates a facet field with a client request."""
        
        # NOTE: Because there's some complex logic in how we determine
        # facet fields from a client request, it is useful to store
        # the associations for later use. The main later use will
        # be the creation of links for different facet search options
        # when we process a raw solr response into a result that we
        # give to a client. This function stores the associations
        # between solr facet fields and the URL parameters and values
        # made by the requesting client.
        
        if not query_dict:
            return None
        for key in ['prequery-stats', 'facet.field']:
            for path_facet_field in query_dict.get(key, []):
                # Associate the facet field for this raw-path with the
                # client request parameter and the raw path from the
                # client. This is also done with solr fields in the
                # prequery-stats key, so as to associate range facets
                # with raw paths. The association is between a
                # solr_field and a param, raw_path tuple.
                self.facet_fields_to_client_request[path_facet_field] = (
                    param, raw_path
                )


    def compose_query(self, request_dict):
        """Composes a solr query by translating a client request_dict
        
        :param dict request_dict: The dictionary of keyed by client
        request parameters and their request parameter values.
        """
        query = {}
        query['facet'] = 'true'
        query['facet.mincount'] = 1
        query['rows'] = self.rows
        query['start'] = self.start
        query['debugQuery'] = self.solr_debug_query
        query['fq'] = []
        # Starts with an initial facet field list
        query['facet.field'] = self.init_facet_fields 
        query['facet.range'] = []
        
        query['stats'] = self.solr_stats_query
        # Starts with an initial stats field list
        query['stats.field'] = self.init_stats_fields
        
        # -------------------------------------------------------------
        # SORTING
        # Set solr sorting, either to a default or by translating the
        # client request_dict.
        # -------------------------------------------------------------
        sort_opts = SortingOptions()
        # This method has unit tests.
        query['sort'] = sort_opts.make_solr_sort_param_from_request_dict(
            request_dict
        )
        
        # -------------------------------------------------------------
        # FULLTEXT (Keyword)
        # Set solr full text query and highlighting
        # -------------------------------------------------------------
        query['q'] = '*:*'  # default search for all
        raw_fulltext_search = utilities.get_request_param_value(
            request_dict, 
            param='q',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_fulltext_search:
            # Client requested a fulltext search. First prepare a list
            # of solr escaped and quoted terms.
            #
            # This method has unit tests.
            escaped_terms = utilities.prep_string_search_term_list(
                raw_fulltext_search
            )
            solr_fulltext = ' '.join(escaped_terms)
            query['q'] = 'text: {}'.format(solr_fulltext)
            query['q.op'] = 'AND'
            query['hl'] = 'true'  # search term highlighting
            query['hl.fl'] = 'text' # highlight the text field
            query['hl.fragsize'] = 200
            query['hl.simple.pre'] = configs.QUERY_SNIPPET_HIGHLIGHT_TAG_PRE
            query['hl.simple.post'] = configs.QUERY_SNIPPET_HIGHLIGHT_TAG_POST
            query['hl.q'] = 'text: {}'.format(solr_fulltext)
        
        # -------------------------------------------------------------
        # START and ROWS (Paging through results)
        # Set the pointer to a position in the solr result list, and
        # the number of rows to return from a solr search.
        # -------------------------------------------------------------
        start_pos = utilities.get_request_param_value(
            request_dict, 
            param='start',
            default=None,
            as_list=False,
            solr_escape=False,
            require_int=True,
        )
        if start_pos:
            # Client has requested a valid, non-default start position
            # for the solr results.
            if start_pos < 0:
                start_pos = 0
            query['start'] = start_pos
        
        rows = utilities.get_request_param_value(
            request_dict, 
            param='rows',
            default=None,
            as_list=False,
            solr_escape=False,
            require_int=True,
        )
        if rows:
            # Client has requested a non-default number of number
            # search result rows.
            if rows > self.max_rows:
                rows = self.max_rows
            elif rows < 0:
                rows = 0
            query['rows'] = rows
        

        # -------------------------------------------------------------
        # SIMPLE, GENERAL METADATA RELATED FUNCTIONS
        # -------------------------------------------------------------
        for url_param, filter_query in configs.REL_MEDIA_EXISTS:
            if not url_param in request_dict:
                # This url_param is not part of the client request
                # so don't add a solr filter query
                continue
            # Add this related media filter to the main query.
            query = utilities.combine_query_dict_lists(
                part_query_dict={'fq': [filter_query]},
                main_query_dict=query,
            )
        
        # Params: uuid, updated published processed here.
        for url_param, solr_field in configs.SIMPLE_METADATA:
            raw_value = utilities.get_request_param_value(
                request_dict, 
                param=url_param,
                default=None,
                as_list=False,
                solr_escape=False,
            )
            if not raw_value:
                # Skip, there's nothing to query for this
                # url_param.
                continue
            query_dict = querymaker.get_simple_metadata_query_dict(
                raw_value, 
                solr_field
            )
            # Now add this simple metadata to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )
        

        # -------------------------------------------------------------
        # ID RELATED Solr Search Params
        # -------------------------------------------------------------
        raw_identifier = utilities.get_request_param_value(
            request_dict, 
            param='id',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_identifier:
            query_dict = querymaker.get_identifier_query_dict(raw_identifier)
            # Now add results of this identifier to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )
        
        raw_object_uri = utilities.get_request_param_value(
            request_dict, 
            param='obj',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_object_uri:
            query_dict = querymaker.get_object_uri_query_dict(raw_object_uri)
            # Now add results of this object_uri to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )


        # -------------------------------------------------------------
        # Item Type
        # -------------------------------------------------------------
        raw_item_type = utilities.get_request_param_value(
            request_dict, 
            param='type',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_item_type:
            query_dict = querymaker.get_item_type_query_dict(raw_item_type)
            # Now add results of this raw_item_type to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )
        

        # -------------------------------------------------------------
        # GEO-SPACE AND TIME
        # -------------------------------------------------------------
        raw_disc_bbox = utilities.get_request_param_value(
            request_dict, 
            param='bbox',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_disc_bbox:
            query_dict = querymaker.get_discovery_bbox_query_dict(
                raw_disc_bbox
            )
            # Now add results of bounding box to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )
        
        raw_disc_geo = utilities.get_request_param_value(
            request_dict, 
            param='disc-geotile',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_disc_geo:
            query_dict = querymaker.get_discovery_geotile_query_dict(
                raw_disc_geo
            )
            # Now add results of disc-geotile to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )

        raw_chrono_tile = utilities.get_request_param_value(
            request_dict, 
            param='form-chronotile',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_chrono_tile:
            query_dict = querymaker.get_form_use_life_chronotile_query_dict(
                raw_chrono_tile
            )
            # Now add results of this form_use_life_chronotile 
            # to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )

        # One or both of the form use life date limits can be None. 
        query_dict = querymaker.get_form_use_life_span_query_dict(
            form_start=utilities.get_request_param_value(
                request_dict, 
                param='form-start',
                default=None,
                as_list=False,
                solr_escape=False,
                require_float=True,
            ), 
            form_stop=utilities.get_request_param_value(
                request_dict, 
                param='form-stop',
                default=None,
                as_list=False,
                solr_escape=False,
                require_float=True,
            ),
        )
        # Now add results of this raw_item_type to the over-all query.
        query = utilities.combine_query_dict_lists(
            part_query_dict=query_dict,
            main_query_dict=query,
        )
            

        # -------------------------------------------------------------
        # Spatial Context
        # -------------------------------------------------------------
        if request_dict.get('path') and self.do_context_paths:
            query_dict = querymaker.get_spatial_context_query_dict(
                request_dict['path']
            )
            if query_dict:

                # Associate the facet fields with the client request param
                # and param value.
                self._associate_facet_field_with_client_request(
                    param='path', 
                    raw_path=request_dict['path'], 
                    query_dict=query_dict
                )
                # Remove the default Root Solr facet field if it is there.
                query['facet.field'] = utilities.safe_remove_item_from_list(
                    SolrDocument.ROOT_CONTEXT_SOLR,
                    query['facet.field'].copy()
                )
                query = utilities.combine_query_dict_lists(
                    part_query_dict=query_dict,
                    main_query_dict=query,
                )
        
        # -------------------------------------------------------------
        # All Hierarchic Parameters (Projects, Properties, Dublin-Core,
        # etc.). The following iterates through a loop of tuples that
        # configure how different GET parameters get processed by the
        # function:
        #
        # querymaker.get_general_hierarchic_paths_query_dict
        #
        # Note how the last element in each tuple "param_args" is used
        # for key-word arguments in the function.
        # -------------------------------------------------------------
        for param, remove_field, param_args in configs.HIERARCHY_PARAM_TO_SOLR:
            raw_paths = utilities.get_request_param_value(
                request_dict, 
                param=param,
                default=None,
                as_list=True,
                solr_escape=False,
            )
            if not raw_paths:
                # We don't have a request using this param, so skip
                continue
            if not isinstance(raw_paths, list):
                raw_paths = [raw_paths]
            for raw_path in raw_paths:
                query_dict = querymaker.get_general_hierarchic_paths_query_dict(
                    raw_path=raw_path, **param_args
                )
                if not query_dict:
                    # We don't have a response for this query, so continue
                    # for now until we come up with error handling.
                    continue
                # Associate the facet fields with the client request param
                # and param value.
                self._associate_facet_field_with_client_request(
                    param=param, 
                    raw_path=raw_path, 
                    query_dict=query_dict
                )
                if remove_field:
                    # Remove a default facet field if it is there.
                    query['facet.field'] = utilities.safe_remove_item_from_list(
                        remove_field,
                        query['facet.field'].copy()
                    )
                
                # Now add results of this raw_path to the over-all query.
                query = utilities.combine_query_dict_lists(
                    part_query_dict=query_dict,
                    main_query_dict=query,
                )
                
        return query
    

    def update_query_with_stats_prequery(self, query):
        """Updates the main query dict if stats fields
           need facet ranges defined. If so, sends off an
           initial pre-query to solr.
        """
        # NOTE: This needs to happen at the end, after
        # we have already defined a bunch of solr 
        if not 'prequery-stats' in query:
            return query
        prestats_fields = query.get('prequery-stats', [])
        query.pop('prequery-stats')
        if not len(prestats_fields):
            return query
        self.solr_connect()
        stats_query = ranges.compose_stats_query(
            fq_list=query['fq'], 
            stats_fields_list=prestats_fields, 
            q=query['q']
        )
        stats_q_dict = ranges.stats_ranges_query_dict_via_solr(
            stats_query=stats_query, 
            solr=self.solr
        )
        query = utilities.combine_query_dict_lists(
            part_query_dict=stats_q_dict,
            main_query_dict=query,
        )
        return query
    

    def _set_solr_field_facet_limits(self, query):
        """ Sets facet limits on configured facet fields"""
        for facet_field, limit in configs.SOLR_FIELDS_FACET_LIMITS:
            if not facet_field in query.get('facet.field', []):
                # We could not find the facet field in the
                # query facet fields, so skip.
                continue
            limit_key = 'f.{}.facet.limit'.format(facet_field)
            query[limit_key] = limit
        return query


    def finish_query(self, query):
        """ Check solr query and put convenient format """
        assert 'q' in query
        query = self.update_query_with_stats_prequery(query)
        query = self._set_solr_field_facet_limits(query)
        compat_args(query)
        query['wt'] = 'json'
        return query
    

    def query_solr(self, query):
        """ Connects to solr and runs a query"""
        query = self.finish_query(query)
        self.solr_connect()
        url = urljoin(self.solr.base_url, 'select')
        try:
            http_response = self.solr.make_request.post(
                url,
                data=query,
                timeout=240
            )
            self.solr_response = parse_response(http_response.content)
        except Exception as error:
            logger.error(
                '[' + datetime.now().strftime('%x %X ')
                + settings.TIME_ZONE + '] Error: '
                + str(error)
                + ' => Query: ' + str(query)
            )
        return self.solr_response