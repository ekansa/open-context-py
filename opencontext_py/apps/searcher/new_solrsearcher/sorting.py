import json
import django.utils.http as http
from django.conf import settings
from urllib.parse import urlparse, parse_qs
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks


class SortingOptions():

    """ Methods to show sorting options """

    IGNORE_PARAMS = [
        'geodeep',
        'chronodeep',
        'rows',
        'start'
    ]

    SORT_OPTIONS = [
        {'type': 'oc-api:sort-item',
         'value': 'item',
         'label': 'Item (type, provenance, label)',
         'opt': True},
        {'type': 'oc-api:sort-updated',
         'value': 'updated',
         'label': 'Updated',
         'opt': True},
        {'type': 'oc-api:sort-published',
         'value': 'published',
         'label': 'Published',
         'opt': False},  # don't make a sorting option available in the interface (hide this)
        {'type': 'oc-api:sort-interest',
         'value': None,
         'label': 'Interest score',
         'opt': True}
    ]

    SORT_SOLR_MAPPINGS = {
        'item': 'slug_type_uri_label',
        # 'item': 'sort_score',
        'updated': 'updated',
        'published': 'published',
        'interest': 'interest_score'
    }

    DEFAULT_SOLR_SORT = 'interest_score desc'

    def __init__(self):
        self.base_search_link = '/search/'
        self.spatial_context = None
        self.using_default_sorting = True
        self.current_sorting = []
        self.order_sep = '--'
        self.field_sep = '---'
        self.sort_links = []
        

    def set_default_current_sorting(self):
        """ Makes a default current sorting list
        """
        current_sort_obj = LastUpdatedOrderedDict()
        current_sort_obj['id'] = '#current-sort-1'
        current_sort_obj['type'] = 'oc-api:interest-score'
        current_sort_obj['label'] = 'Interest score'
        current_sort_obj['oc-api:sort-order'] = 'descending'
        self.current_sorting.append(current_sort_obj)


    def get_requested_sort_from_dict(self, request_dict):
        """ makes a list indicating the current
            sorting requested
            
        :param dict request_dict: The dictionary of keyed by client
        request parameters and their request parameter values.
        """
        requested_sort = request_dict.get('sort')
        # Check enforce that the requested_sort is not a list.
        if isinstance(requested_sort, list) and len(requested_sort):
            return requested_sort[0]
        if not requested_sort:
            return None
        return requested_sort
    

    def make_sort_args_list(self, raw_sorting_str, field_sep=None):
        """Makes a list of solr args by parsing a raw sorting string value
        
        :param str raw_sorting_str: The raw sorting order string.
        :param str field_sep: The delimiter/seperator for different
        sorting arguments.
        """
        if not field_sep:
            field_sep = self.field_sep
        if field_sep in raw_sorting_str:
            sort_args = raw_sorting_str.split(field_sep)
        else:
            sort_args = [raw_sorting_str]
        return sort_args
    
    
    def make_solr_sort_param(self, requested_sort):
        """ makes a solr sort paramater
            based on the current request's sort parameter
        """
        if not requested_sort:
            # No sort indicated in the request, so use the default
            return self.DEFAULT_SOLR_SORT
        
        sort_fields = []
        sole_sort_list = []
        
        # Iterate through a list of sorting arguments.
        for cur_field_raw in self.make_sort_args_list(requested_sort):
            order = 'asc'  # the default sort order
            if self.order_sep in cur_field_raw:
                cur_field_ex = cur_field_raw.split(self.order_sep)
                cur_field = cur_field_ex[0]
                if (len(cur_field_ex) == 2
                    and 'desc' == cur_field_ex[1]):
                    order = 'desc'
            else:
                cur_field = cur_field_raw
            if cur_field in self.SORT_SOLR_MAPPINGS:
                # The current field is in the solr mappings, so
                # it is a valid sort field
                act_solr_sort = self.SORT_SOLR_MAPPINGS[cur_field]
                act_solr_sort += ' ' + order
                sole_sort_list.append(act_solr_sort)
                sort_fields.append(cur_field)
        if len(sole_sort_list) == 0:
            # We didn't find valid sort fields, so use the default
            return self.DEFAULT_SOLR_SORT
            
        # We have valid sort fields, so make the solr sort
        if 'item' in sort_fields and 'interest' not in sort_fields:
            # Add interest sorting to sorting on items if
            # iterest sorting is not already present.
            sole_sort_list.append(self.DEFAULT_SOLR_SORT)
        if 'item' not in sort_fields:
            # Only append this if we're not already sorting by items
            sole_sort_list.append('sort_score asc')
            sole_sort_list.append('slug_type_uri_label asc')
        solr_sort = ', '.join(sole_sort_list)
        return solr_sort
    
    
    def make_solr_sort_param_from_request_dict(self, request_dict):
        """ Makes a solr sort parameter for a solr query.
        
        Returns either the default solr sorting or solr sorting
        translated from the client request dict.
        
        :param dict request_dict: The dictionary of keyed by client
        request parameters and their request parameter values.
        """
        requested_sort = self.get_requested_sort_from_dict(
            request_dict
        )
        return self.make_solr_sort_param(requested_sort)
    

    def make_current_sorting_list(self, request_dict):
        """ makes a list indicating the current
            sorting requested
        """
        current_sort = self.get_requested_sort_from_dict(
            request_dict
        )
        if not current_sort:
            # No sort indicated in the request, so use the default
            return self.set_default_current_sorting(self)
        
        # Iterate through a list of sorting arguments.
        for cur_field_raw in self.make_sort_args_list(current_sort):
            order = 'ascending'  # the default sort order
            cur_field = cur_field_raw
            if self.order_sep in cur_field_raw:
                cur_field_ex = cur_field_raw.split(self.order_sep)
                cur_field = cur_field_ex[0]
                if (len(cur_field_ex) == 2
                    and 'desc' in cur_field_ex[1]):
                    order = 'descending'
            for check_sort in self.SORT_OPTIONS:
                if not check_sort['value'] != cur_field:
                    continue
                self.using_default_sorting = False
                current_index = len(self.current_sorting) + 1
                current_sort_obj = LastUpdatedOrderedDict()
                current_sort_obj['id'] = '#current-sort-{}'.format(current_index)
                current_sort_obj['type'] = check_sort['type']
                current_sort_obj['label'] = check_sort['label']
                current_sort_obj['oc-api:sort-order'] = order
                self.current_sorting.append(current_sort_obj)
        return self.current_sorting


    def make_sort_links_list(self, request_dict):
        """ makes a list of the links for sort options
        """
        if 'sort' in request_dict:
            request_dict.pop('sort')
        
        order_opts = [
            {'key': 'asc',
             'order': 'ascending'},
            {'key': 'desc',
             'order': 'descending'}
        ]
        
        for act_sort in self.SORT_OPTIONS:
            if not act_sort.get('opt') or act_sort.get('value') is None:
                continue
            