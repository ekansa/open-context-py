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
        self.solr = SolrConnection(False).connection
    
    

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
        if 'path' in request_dict and self.do_context_paths:
            # Remove the default Root Solr facet field if it is there.
            query['facet.field'] = utilities.safe_remove_item_from_list(
                SolrDocument.ROOT_CONTEXT_SOLR,
                query['facet.field']
            )
            query_dict = querymaker.get_spatial_context_query_dict(
                request_dict['path']
            )
            query['fq'] += query_dict['fq']
            query['facet.field'] += query_dict['facet.field']
    
        return query