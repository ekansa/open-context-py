import copy
import itertools
import json
import logging
import re
import time
from datetime import datetime

from django.utils.html import strip_tags

from django.conf import settings

from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities



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
    

    def _is_uri_in_uri_list(self, uri, uri_list):
        """Checks if a URI is in a list of URIs"""
        # NOTE: This is slightly complicated by the possibility
        # of HTTP or HTTPS uri variants.
        check_uri_list = utilities.make_alternative_prefix_list(uri)
        # Get the alternate HTTP, HTTPs variant of each item in the
        # uri_list. That becomes the big_uri_list
        big_uri_list = []
        for act_uri in uri_list:
            big_uri_list += utilities.make_alternative_prefix_list(
                act_uri
            )
        # T/F is there an intersection between the uris in these lists?
        return (set(check_uri_list) & set(big_uri_list))


    def _is_uri_prefix_match(self, uris_for_prefix, uri):
        """Checks to see if two uris have matching prefixes"""
        # Get the alternate HTTP, HTTPs variant of each item in the
        # uri_list. That becomes the big_prefix_list. We then
        # checkout a cross-product of these two lists to see if
        # any uri starts with one of the prefixes.
        big_prefix_list = []
        for act_uri in uris_for_prefix:
            big_prefix_list += utilities.make_alternative_prefix_list(
                act_uri
            )

        uri_list = utilities.make_alternative_prefix_list(uri)
        for uri_prefix, uri_check in itertools.product(
            big_prefix_list, uri_list):
            if uri_check.startswith(uri_prefix):
                return True
        return False


    def _group_facet_options(self, dom_id_prefix, raw_options_list):
        """Groups facet options into groups of related uris"""
        # NOTE: Open Context indexes records described by a number of
        # URI identified (Linked Data) attributes. This method groups
        # together facet search options that share a common namespace.
        all_grouped_options = []
        all_grouped_uris = []
        for group_uris, group_head in configs.FACET_OPT_ORDERED_SUB_HEADINGS:
            group_opts = []
            for i, f_opt in enumerate(raw_options_list, 1):
                f_opt['dom_id'] = '{}-option-{}'.format(dom_id_prefix, i)
                opt_uri = f_opt.get('rdfs:isDefinedBy')
                if not opt_uri and not group_uris:
                    # This does not have URI identifier, 
                    # and goes into the catch-all other category.
                    group_opts.append(f_opt)
                    all_grouped_uris.append(opt_uri)
                    continue
                if not opt_uri or opt_uri in all_grouped_uris:
                    # There's no URI or we already grouped this,
                    # so skip.
                    continue
                if self._is_uri_in_uri_list(
                    opt_uri,
                    configs.FACET_OPT_HIDE_URI_MAPS):
                    # This uri is configured for hiding,
                    # so skip out and don't add to the
                    # list
                    all_grouped_uris.append(opt_uri)
                    continue
                if not group_uris:
                    # This is the catch-all other category.
                    group_opts.append(f_opt)
                    all_grouped_uris.append(opt_uri)
                    continue
                if not self._is_uri_prefix_match(group_uris, opt_uri):
                    # This opt_uri does not belong to this
                    # group, so continue and do nothing.
                    continue
                # We're at the point where the opt_uri has
                # been found to belong to this particular group.
                group_opts.append(f_opt)
                all_grouped_uris.append(opt_uri)
            
            if not len(group_opts):
                # We didn't find options belonging to this
                # group, so continue
                continue
            
            all_grouped_options.append(
                {
                    'opt_group_label': group_head,
                    'options': group_opts,
                }
            )

        if len(all_grouped_options) == 1:
            # There's only one group, so no need to have a label.
            all_grouped_options[0]['opt_group_label'] = None

        return all_grouped_options


    def _prep_facet_options_lists(self, result):
        """Prepares facet options lists for easier templating"""
        if not result.get('oc-api:has-facets'):
            # No facets, so nothing to change here.
            return result
        for f_field in result['oc-api:has-facets']:
            f_field['id'] = f_field['id'].lstrip('#')
            option_types = LastUpdatedOrderedDict()
            for opt_type, options_list_key in configs.FACETS_DATA_TYPE_OPTIONS_LISTS.items():
                if not f_field.get(options_list_key):
                    # This facet field does not have facet options for this datatype
                    continue
                option_types[opt_type] = {
                    'temp_id': '{}-{}'.format(
                        f_field['id'],
                        opt_type
                    ),
                    'grp_options': self._group_facet_options(
                        f_field['id'],
                        f_field.get(options_list_key)
                    ),
                }
            f_field['option_types'] = option_types
        return result

    
    def make_result_template_ready(self, result):
        """Makes a result dict ready for use in a template"""
        result = self._prep_filter_groups(result)
        result = self._prep_facet_options_lists(result)
        result = self._make_template_ready_dict_obj(result)
        return result