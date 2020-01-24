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
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks
from opencontext_py.apps.searcher.new_solrsearcher import utilities


logger = logging.getLogger(__name__)


class SolrResult():

    def __init__(self, request_dict=None, base_search_url='/search/'):
        self.json_ld = LastUpdatedOrderedDict()
        self.request_dict = request_dict
        self.base_search_url = base_search_url
    
    def make_paging_links(self, start, rows, act_request_dict):
        """Makes links for paging for start rows from a request dict"""
        start = str(int(start))
        rows = str(rows)
        sl = SearchLinks(
            request_dict=act_request_dict,
            base_search_url=self.base_search_url
        )
        sl.add_param_value('start', start)
        sl.add_param_value('rows', rows)
        urls = sl.make_urls_from_request_dict()
        return urls

    def add_paging_json(self, solr_json):
        """ adds JSON for paging through results """
        total_found = utilities.get_dict_path_value(
            ['response', 'numFound'],
            solr_json
        )
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
            links = self.make_paging_links(
                start=0,
                rows=rows,
                act_request_dict=copy.deepcopy(act_request_dict)
            )
            self.json_ld['first'] = links['html']
            self.json_ld['first-json'] = links['json']
        if start >= rows:
            # add a previous page link
            links = self.make_paging_links(
                start=(start - rows),
                rows=rows,
                act_request_dict=copy.deepcopy(act_request_dict)
            )
            self.json_ld['previous'] = links['html']
            self.json_ld['previous-json'] = links['json']
        if start + rows < total_found:
            # add a next page link
            links = self.make_paging_links(
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
        links = self.make_paging_links(
            start=(num_pages * rows),
            rows=rows,
            act_request_dict=copy.deepcopy(act_request_dict)
        )
        self.json_ld['last'] = links['html']
        self.json_ld['last-json'] = links['json']

    def create_result(self):
        """Creates a solr result"""
        pass




    
    