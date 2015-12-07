import json
import django.utils.http as http
from django.conf import settings
from urllib.parse import urlparse, parse_qs
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks


class SortingOptions():

    """ Methods to show sorting options """

    IGNORE_PARAMS = ['geodeep',
                     'chronodeep',
                     'rows',
                     'start']

    SORT_OPTIONS = [
        {'type': 'oc-api:sort-item',
         'value': 'item',
         'label': 'Item (type, provenance, label)'},
        {'type': 'oc-api:sort-updated',
         'value': 'updated',
         'label': 'Updated'},
        {'type': 'oc-api:sort-interest',
         'value': None,
         'label': 'Interest score'}
    ]

    def __init__(self):
        self.base_search_link = '/search/'
        self.spatial_context = None
        self.using_default_sorting = True
        self.current_sorting = []
        self.order_sep = '--'
        self.field_sep = '---'
        self.sort_links = []

    def make_current_sorting_list(self, request_dict):
        """ makes a list indicating the current
            sorting requested
        """
        if 'sort' not in request_dict:
            # no sort indicated in the request, so use the default
            self.set_default_current_sorting(request_dict)
        else:
            current_sort = request_dict['sort']
            if isinstance(current_sort, list):
                current_sort = current_sort[0]
            if self.field_sep in current_sort:
                current_sorts = current_sort.split(self.field_sep)
            else:
                current_sorts = [current_sort]
            for cur_field_raw in current_sorts:
                order = 'ascending'  # the default sort order
                if self.order_sep in cur_field_raw:
                    cur_field_ex = cur_field_raw.split(self.order_sep)
                    cur_field = cur_field_ex[0]
                    if len(cur_field_ex) == 2:
                        if 'desc' in cur_field_ex[1]:
                            order = 'descending'
                else:
                    cur_field = cur_field_raw
                for check_sort in self.SORT_OPTIONS:
                    if check_sort['value'] is not None:
                        if check_sort['value'] == cur_field:
                            self.using_default_sorting = False
                            current_index = len(self.current_sorting) + 1
                            current_sort_obj = LastUpdatedOrderedDict()
                            current_sort_obj['id'] = '#current-sort-' + str(current_index)
                            current_sort_obj['type'] = check_sort['type']
                            current_sort_obj['label'] = check_sort['label']
                            current_sort_obj['oc-api:sort-order'] = order
                            self.current_sorting.append(current_sort_obj)
        return self.current_sorting

    def set_default_current_sorting(self, request_dict):
        """ makes a default current sorting list
        """
        current_sort_obj = LastUpdatedOrderedDict()
        current_sort_obj['id'] = '#current-sort-1'
        current_sort_obj['type'] = 'oc-api:interest-score'
        current_sort_obj['label'] = 'Interest score'
        current_sort_obj['oc-api:sort-order'] = 'descending'
        self.current_sorting.append(current_sort_obj)

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
            if act_sort['value'] is not None:
                for order_opt in order_opts:
                    act_sort_val = act_sort['value'] + self.order_sep + order_opt['key']
                    fl = FilterLinks()
                    fl.base_search_link = self.base_search_link
                    fl.base_request_json = json.dumps(request_dict,
                                                      ensure_ascii=False,
                                                      indent=4)
                    fl.spatial_context = self.spatial_context
                    sort_rparams = fl.add_to_request('sort',
                                                     act_sort_val)
                    links = fl.make_request_urls(sort_rparams)
                    current_sort_obj = LastUpdatedOrderedDict()
                    current_sort_obj['id'] = links['html']
                    current_sort_obj['json'] = links['json']
                    current_sort_obj['type'] = act_sort['type']
                    current_sort_obj['label'] = act_sort['label']
                    current_sort_obj['oc-api:sort-order'] = order_opt['order']
                    in_active_list = False
                    for cur_act_sort in self.current_sorting:
                        if act_sort['type'] == cur_act_sort['type'] \
                           and order_opt['order'] == cur_act_sort['oc-api:sort-order']:
                            # the current sort option is ALREADY in use
                            in_active_list = True
                    if in_active_list is False:
                        # only add the sort option if it's not already in use
                        self.sort_links.append(current_sort_obj)
            else:
                if self.using_default_sorting is False:
                    # only add a link to the default sorting if
                    # we are not currently using it
                    fl = FilterLinks()
                    fl.base_search_link = self.base_search_link
                    fl.base_request_json = json.dumps(request_dict,
                                                      ensure_ascii=False,
                                                      indent=4)
                    fl.spatial_context = self.spatial_context
                    links = fl.make_request_urls(request_dict)
                    current_sort_obj = LastUpdatedOrderedDict()
                    current_sort_obj['id'] = links['html']
                    current_sort_obj['json'] = links['json']
                    current_sort_obj['type'] = act_sort['type']
                    current_sort_obj['label'] = act_sort['label']
                    current_sort_obj['oc-api:sort-order'] = 'descending'
                    self.sort_links.append(current_sort_obj)
