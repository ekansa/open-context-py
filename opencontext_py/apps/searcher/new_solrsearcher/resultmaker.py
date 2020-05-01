import copy
import json
import logging
import time
from datetime import datetime
from django.conf import settings
from mysolr.compat import urljoin, compat_args, parse_response
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.searchfilters import SearchFilters
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks
from opencontext_py.apps.searcher.new_solrsearcher.sorting import SortingOptions
from opencontext_py.apps.searcher.new_solrsearcher import utilities


logger = logging.getLogger(__name__)


class SolrResult():

    def __init__(self, request_dict=None, base_search_url='/search/'):
        self.json_ld = LastUpdatedOrderedDict()
        self.request_dict = copy.deepcopy(request_dict)
        self.base_search_url = base_search_url
        self.act_responses = []

    def _make_paging_links(self, start, rows, act_request_dict):
        """Makes links for paging for start rows from a request dict"""
        start = str(int(start))
        rows = str(rows)

        # Remove previously set parameters relating to paging.
        for param in ['start', 'rows']:
            if param in act_request_dict:
                act_request_dict.pop(param, None)

        sl = SearchLinks(
            request_dict=act_request_dict,
            base_search_url=self.base_search_url
        )
        sl.add_param_value('start', start)
        sl.add_param_value('rows', rows)
        urls = sl.make_urls_from_request_dict()
        return urls


    def add_paging_json(self, solr_json):
        """ Adds JSON for paging through results """
        
        # The total found (numFound) is in the solr response.
        total_found = utilities.get_dict_path_value(
            ['response', 'numFound'],
            solr_json
        )

        # Start and rows comes from the responseHeader
        start = utilities.get_dict_path_value(
            ['responseHeader', 'params', 'start'],
            solr_json
        )
        rows = utilities.get_dict_path_value(
            ['responseHeader', 'params', 'rows'],
            solr_json
        )
        if (total_found is None
            or start is None
            or rows is None):
            return None
        
        # Add number found, start index, paging
        # information about this search result.
        total_found = int(float(total_found))
        start = int(float(start))
        rows = int(float(rows))
        self.json_ld['totalResults'] = total_found
        self.json_ld['startIndex'] = start
        self.json_ld['itemsPerPage'] = rows
        
        # start off with a the request dict, then
        # remove 'start' and 'rows' parameters
        act_request_dict = copy.deepcopy(self.request_dict)
        if 'start' in act_request_dict:
            act_request_dict.pop('start', None)
        if 'rows' in act_request_dict:
            act_request_dict.pop('rows', None)

        # add a first page link
        if start > 0:
            links = self._make_paging_links(
                start=0,
                rows=rows,
                act_request_dict=copy.deepcopy(act_request_dict)
            )
            self.json_ld['first'] = links['html']
            self.json_ld['first-json'] = links['json']
        if start >= rows:
            # add a previous page link
            links = self._make_paging_links(
                start=(start - rows),
                rows=rows,
                act_request_dict=copy.deepcopy(act_request_dict)
            )
            self.json_ld['previous'] = links['html']
            self.json_ld['previous-json'] = links['json']
        if start + rows < total_found:
            # add a next page link
            print('Here: {}'.format(str(act_request_dict)))
            links = self._make_paging_links(
                start=(start + rows),
                rows=rows,
                act_request_dict=copy.deepcopy(act_request_dict)
            )
            self.json_ld['next'] = links['html']
            self.json_ld['next-json'] = links['json']
        num_pages = round(total_found / rows, 0)
        if num_pages * rows >= total_found:
            num_pages -= 1
        # add a last page link
        links = self._make_paging_links(
            start=(num_pages * rows),
            rows=rows,
            act_request_dict=copy.deepcopy(act_request_dict)
        )
        self.json_ld['last'] = links['html']
        self.json_ld['last-json'] = links['json']
    

    def add_sorting_json(self):
        """Adds JSON to describe result sorting """
        # Deep copy the request dict to not mutate it.
        act_request_dict = copy.deepcopy(self.request_dict)
        sort_opts = SortingOptions(base_search_url=self.base_search_url)
        sort_opts.make_current_sorting_list(act_request_dict)
        # Add objects describing the currently active sorting.
        self.json_ld['oc-api:active-sorting'] = sort_opts.current_sorting
        act_request_dict = copy.deepcopy(self.request_dict)
        sort_links = sort_opts.make_sort_links_list(act_request_dict)
        # Add objects describing other sort options available.
        self.json_ld['oc-api:has-sorting'] = sort_links

    
    def add_filters_json(self):
        """Adds JSON describing currently used query filters"""
        search_filters = SearchFilters(
            base_search_url=self.base_search_url
        )
        filters = search_filters.add_filters_json(self.request_dict)
        if len(filters) > 0:
            self.json_ld['oc-api:active-filters'] = filters


    def add_text_fields(self):
        """ adds text fields with query options """
        text_fields = []
        # first add a general key-word search option
        act_request_dict = copy.deepcopy(self.request_dict)
        sl = SearchLinks(
            request_dict=act_request_dict,
            base_search_url=self.base_search_url
        )
        raw_fulltext_search = utilities.get_request_param_value(
            act_request_dict, 
            param='q',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        field = LastUpdatedOrderedDict()
        field['id'] = '#textfield-keyword-search'
        field['label'] = configs.FILTER_TEXT_SEARCH_TITLE
        field['oc-api:search-term'] = raw_fulltext_search
        if not raw_fulltext_search:
            # No keyword search found in request, so
            # make a template for keyword searches.
            sl.add_param_value(
                'q', 
                '{SearchTerm}'
            )
            urls = sl.make_urls_from_request_dict()
            field['oc-api:template'] = urls['html']
            field['oc-api:template-json'] = urls['json']
        else:
            # A keyword search was found, so make a
            # template for replacing it with another
            # keyword search.
            sl.replace_param_value(
                'q',
                match_old_value=raw_fulltext_search,
                new_value='{SearchTerm}'
            )
            urls = sl.make_urls_from_request_dict()
            field['oc-api:template'] = urls['html']
            field['oc-api:template-json'] = urls['json']
        text_fields.append(field)

        # NOTE TODO: Add text-string search options!

        # Add the text fields if they exist.
        if len(text_fields):
            self.json_ld['oc-api:has-text-search'] = text_fields
        return text_fields


    def create_result(self, solr_json):
        """Creates a solr result"""
        if 'metadata' in self.act_responses:
            self.add_paging_json(solr_json)
            self.add_sorting_json()
            self.add_filters_json()
            self.add_text_fields()




    
    