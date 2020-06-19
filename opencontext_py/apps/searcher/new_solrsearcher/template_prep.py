import copy
import json
import logging
import re
import time
from datetime import datetime

from django.utils.html import strip_tags

from django.conf import settings

from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict



class SearchTemplate():
    """ methods use Open Context JSON-LD
        search results and turn them into a
        user interface
    """
    KEY_FIND_REPLACES = [
        ('-', '_',),
        (':', '__',),
        ('#', '',),
        (' ', '_',),
        ('/', '_',),
    ]

    DEFAULT_FILTER_GROUP_DELIM = ' :: '
    FILTER_GROUP_DELIMS = {
        'Context': ' / ',
    }

    def __init__(self, result):
        self.result = None
        if isinstance(result, dict):
            self.result = self.make_result_template_ready(
                result
            )
    
    def _make_key_template_ok(self, key):
        """Makes a key OK for a template"""
        if not isinstance(key, str):
            return key
        new_key = key.lower()
        for f, r in self.KEY_FIND_REPLACES:
            new_key = new_key.replace(f, r)
        return new_key
    
    def _make_template_ready_dict_obj(self, dict_obj):
        """Makes a result object ready for use in a template"""
        if not isinstance(dict_obj, dict):
            return dict_obj
        temp_dict = LastUpdatedOrderedDict()
        for key, value in dict_obj.items():
            new_key = self._make_key_template_ok(key)
            if isinstance(value, dict):
                value = self._make_template_ready_dict_obj(value)
            elif isinstance(value, list):
                temp_dict[new_key] = [
                    self._make_template_ready_dict_obj(v)
                    for v in value
                ]
                continue
            temp_dict[new_key] = value
        return temp_dict

    def _prep_filter_groups(self, result):
        """Prepare filter groups for easier templating"""
        # NOTE: The list of "oc-api:active-filters" can have groups
        # of related filters. These should be organized and displayed
        # together to make user experience less painful. This method
        # puts filter items together into lists of shared groups.
        if not result.get('oc-api:active-filters'):
            # No active filters, just return the result dict.
            return result
        
        grouped_filters = LastUpdatedOrderedDict()
        for act_filter in result['oc-api:active-filters']:
            # Filter group key is either set in the act_filter, or
            # as a fall-back, will be the filter's id.
            fgroup_key = act_filter.get(
                'oc-api:filter-group',
                act_filter['id']
            )
            if not fgroup_key in grouped_filters:
                grouped_filters[fgroup_key] = {
                    'group_label': act_filter.get('oc-api:filter'),
                    'group_remove_href': act_filter.get('oc-api:remove'),
                    'group_delim': self.FILTER_GROUP_DELIMS.get(
                        act_filter.get('oc-api:filter'),
                        self.DEFAULT_FILTER_GROUP_DELIM,
                    ),
                    'filters': [],
                }

            grouped_filters[fgroup_key]['filters'].append(act_filter)
        
        result['active_filters_grouped'] =  grouped_filters
        return result
    
    def make_result_template_ready(self, result):
        """Makes a result dict ready for use in a template"""
        result = self._prep_filter_groups(result)
        result = self._make_template_ready_dict_obj(result)
        return result