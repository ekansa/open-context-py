import copy
import json
import logging
import re
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
        self.init_stats_fields = configs.GENERAL_STATS_FIELDS.copy()
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
    
    
    def solr_connect(self):
        """ Connects to solr """
        if self.solr is None:
            self.solr = SolrConnection(False).connection
    
    def finish_request(self, query):
        """ Check solr query and put convenient format """
        assert 'q' in query
        compat_args(query)
        query['wt'] = 'json'
        return query
    
    def query_solr(self, query):
        """ Connects to solr and runs a query"""
        query = self.finish_request(query)
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
        # Spatial Context
        # -------------------------------------------------------------
        if request_dict.get('path') and self.do_context_paths:
            query_dict = querymaker.get_spatial_context_query_dict(
                request_dict['path']
            )
            if query_dict:
                # Remove the default Root Solr facet field if it is there.
                query['facet.field'] = utilities.safe_remove_item_from_list(
                    SolrDocument.ROOT_CONTEXT_SOLR,
                    query['facet.field'].copy()
                )
                query['fq'] += query_dict['fq']
                query['facet.field'] += query_dict['facet.field']
        
        # -------------------------------------------------------------
        # All Hierarchic Parameters (Projects, Properties, Dublin-Core,
        # etc.). The following iterates through a loop of tuples that
        # configure how different GET parameters get processed by the
        # function:
        #
        # querymaker.get_general_hierarchic_paths_query_dict
        #
        # Note how the last element in each tuple "param_args" is used
        # as for key-word arguments in the function.
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