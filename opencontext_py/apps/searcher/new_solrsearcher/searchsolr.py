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

from opencontext_py.apps.searcher.new_solrsearcher import utilities
from opencontext_py.apps.searcher.new_solrsearcher.sorting import SortingOptions


class SearchSolr():

    DEFAULT_FACET_FIELDS = [
        SolrDocumentNew.ROOT_LINK_DATA_SOLR,
        SolrDocumentNew.ROOT_PROJECT_SOLR,
        'image_media_count',
        'other_binary_media_count',
        'document_count'
    ]

    PROJECT_FACET_FIELDS = [
        # SolrDocument.ROOT_LINK_DATA_SOLR
        'dc_terms_subject___pred_id',
        'dc_terms_coverage___pred_id',
        'dc_terms_temporal___pred_id'
    ]

    # the number of rows to display by default for different item types
    ITEM_TYPE_ROWS = {'projects': 100}

    # the miniumum number of facets to display for different item types
    ITEM_TYPE_FACET_MIN = {'projects': 2}

    #facet fields for different item_types
    ITEM_TYPE_FACETFIELDS = {
        'projects': [
            'dc_terms_subject___pred_id',
            # 'dc_terms_temporal___pred_id',
            'dc_terms_spatial___pred_id',
            'dc_terms_coverage___pred_id'
        ],
        'subjects': [
            'oc_gen_subjects___pred_id'
        ]
    }

    ITEM_CAT_FIELDS = [
        'oc_gen_subjects___pred_id',
        'oc_gen_media___pred_id',
        'oc_gen_persons___pred_id',
    ]

    REL_CAT_FACET_FIELDS = ['rel__oc_gen_subjects___pred_id']
    GENERAL_STATS_FIELDS = [
        'updated',
        'published',
    ]
    CHRONO_STATS_FIELDS =  [
        'form_use_life_chrono_earliest',
        'form_use_life_chrono_latest'
    ]
    MEDIA_STATS_FIELDS = ['filesize___pred_numeric']

    def __init__(self):
        self.solr = False
        self.solr_connect()
        self.solr_response = False
        self.json_ld = False
        self.facet_fields = self.DEFAULT_FACET_FIELDS
        self.stats_fields = self.GENERAL_STATS_FIELDS
        self.rows = 20
        self.start = 0
        self.max_rows = 10000
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
        query['facet.field'] = []
        query['facet.range'] = []
        query['stats'] = self.solr_stats_query
        query['stats.field'] = self.stats_fields
        
        # -------------------------------------------------------------
        # SORTING
        # Set solr sorting, either to a default or by translating the
        # client request_dict.
        # -------------------------------------------------------------
        sort_opts = SortingOptions()
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
            solr_escape=True
        )
        if raw_fulltext_search:
            # Client requested a fulltext search. First prepare a list
            # of solr escaped and quoted terms.
            escaped_terms = utilities.prep_string_search_term_list(
                raw_fulltext_search
            )
            solr_fulltext = ' '.join(escaped_terms)
            query['q'] = 'text: {}'.format(solr_fulltext)
            query['q.op'] = 'AND'
            query['hl'] = 'true'  # search term highlighting
            query['hl.fl'] = 'text' # highlight the text field
            query['hl.q'] = 'text: {}'.format(solr_fulltext)
        