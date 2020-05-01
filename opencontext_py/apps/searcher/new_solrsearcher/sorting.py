import copy

from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks


class SortingOptions():

    """ Methods to show sorting options """

    def __init__(self, base_search_url='/search/'):
        self.using_default_sorting = True
        self.current_sorting = []
        self.solr_sort_default = configs.SOLR_SORT_DEFAULT
        self.request_sort_dir_delim = configs.REQUEST_SORT_DIR_DELIM
        self.field_sep = configs.REQUEST_PROP_HIERARCHY_DELIM
        self.request_solr_sort_mappings = configs.REQUEST_SOLR_SORT_MAPPINGS
        self.sort_links = []
        self.base_search_url = base_search_url

    def set_default_current_sorting(self):
        """ Makes a default current sorting list
        """
        current_sort_obj = LastUpdatedOrderedDict()
        current_sort_obj['id'] = '#current-sort-1'
        current_sort_obj['type'] = configs.SORT_DEFAULT_TYPE
        current_sort_obj['label'] = configs.SORT_DEFAULT_LABEL
        current_sort_obj['oc-api:sort-order'] = configs.SORT_DEFAULT_ORDER
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
        """ Translates a client request sort parameter to a solr
            sorting parameter.
        
        :param str requested_sort: A string provided by a client with
            a sorting value that needs translating for Solr.
        """
        if not requested_sort:
            # No sort indicated in the request, so use the default
            return self.solr_sort_default
        
        sort_fields = []
        sole_sort_list = []
        
        # Iterate through a list of sorting arguments.
        for cur_field_raw in self.make_sort_args_list(requested_sort):
            order = 'asc'  # the default sort order
            if self.request_sort_dir_delim in cur_field_raw:
                cur_field_ex = cur_field_raw.split(self.request_sort_dir_delim)
                cur_field = cur_field_ex[0]
                if (len(cur_field_ex) == 2
                    and 'desc' == cur_field_ex[1]):
                    order = 'desc'
            else:
                cur_field = cur_field_raw
            if not cur_field in self.request_solr_sort_mappings:
                # Skip. We don't recognize the cur_field in our
                # mappings for solr sorting.
                continue
            # The current field is in the solr mappings, so
            # it is a valid sort field
            act_solr_sort = self.request_solr_sort_mappings[cur_field]
            act_solr_sort += ' ' + order
            sole_sort_list.append(act_solr_sort)
            sort_fields.append(cur_field)
        if len(sole_sort_list) == 0:
            # We didn't find valid sort fields, so use the default
            return self.solr_sort_default
            
        # We have valid sort fields, so make the solr sort
        if 'item' in sort_fields and 'interest' not in sort_fields:
            # Add interest sorting to sorting on items if
            # iterest sorting is not already present.
            sole_sort_list.append(self.solr_sort_default)
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
            return self.set_default_current_sorting()
        # Iterate through a list of sorting arguments.
        for cur_field_raw in self.make_sort_args_list(current_sort):
            order = 'ascending'  # the default sort order
            cur_field = cur_field_raw
            if self.request_sort_dir_delim in cur_field_raw:
                cur_field_ex = cur_field_raw.split(self.request_sort_dir_delim)
                cur_field = cur_field_ex[0]
                if (len(cur_field_ex) == 2
                    and 'desc' in cur_field_ex[1]):
                    order = 'descending'
            for check_sort in configs.SORT_OPTIONS:
                if check_sort['value'] != cur_field:
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

        sort_links = []
        
        # Make a deep copy, because we're mutating the
        # request_dict.
        act_request_dict = copy.deepcopy(request_dict)
        # Remove a sort or start parameter.
        for param in ['sort', 'start']:
            if param in act_request_dict:
                act_request_dict.pop(param, None)
        
        order_opts = [
            {'key': 'asc',
             'order': 'ascending'},
            {'key': 'desc',
             'order': 'descending'}
        ]
        
        for act_sort in configs.SORT_OPTIONS:
            if not act_sort.get('opt'):
                continue
            for order_opt in order_opts:
                sl = SearchLinks(
                    request_dict=act_request_dict,
                    base_search_url=self.base_search_url
                )
                if act_sort.get('value') is None: 
                    if order_opt['key'] == 'asc':
                        # Skip the option of adding an ascending order sort
                        # option if the act_sort value is None (the default sorting
                        # option by interest score).
                        continue
                else:
                    # Make sort links for this sort_option and
                    # order_opt.
                    act_sort_val = (
                        act_sort['value'] 
                        + self.request_sort_dir_delim
                        + order_opt['key']
                    )
                    sl.add_param_value('sort', act_sort_val)
                
                urls = sl.make_urls_from_request_dict()
                new_sort_obj = LastUpdatedOrderedDict()
                new_sort_obj['id'] = urls['html']
                new_sort_obj['json'] = urls['json']
                new_sort_obj['type'] = act_sort['type']
                new_sort_obj['label'] = act_sort['label']
                new_sort_obj['oc-api:sort-order'] = order_opt['order']
                in_active_list = False
                for cur_act_sort in self.current_sorting:
                    if (new_sort_obj['type'] == cur_act_sort['type']
                        and new_sort_obj['oc-api:sort-order'] == cur_act_sort['oc-api:sort-order']):
                        # the new_sort_obj option is ALREADY in use
                        in_active_list = True
                        break
                if in_active_list is False:
                    sort_links.append(new_sort_obj)
        
        # Return the sort option links
        return sort_links