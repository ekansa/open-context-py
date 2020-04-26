import copy
import json
from urllib.parse import urlparse, parse_qs
from django.utils.http import (
    urlquote, 
    quote_plus, 
    urlquote_plus, 
    urlunquote_plus,
)
from django.utils.encoding import iri_to_uri

from django.conf import settings

from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks



class SearchFilters():

    def __init__(self, request_dict=None, base_search_url='/search/'):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.base_search_url = base_search_url
        self.request_dict = copy.deepcopy(request_dict)
        self.doc_formats = configs.REQUEST_URL_FORMAT_EXTENTIONS
    

    def add_entity_item_to_act_filter(
            self, 
            lookup_val, 
            act_filter, 
            is_spatial_context=False
        ):
        """Looks up a entity item to add to an act_filter"""
        lookup_val = str(lookup_val)
        m_cache = MemoryCache()
        if is_spatial_context:
            item = m_cache.get_entity_by_context(lookup_val)
        else:
            item = m_cache.get_entity(lookup_val)
        if item:
            act_filter['label'] = item.label
            act_filter['rdfs:isDefinedBy'] = item.uri
            act_filter['oc-api:filter-slug'] = item.slug
        else:
            act_filter['label'] = lookup_val.replace(
                configs.REQUEST_OR_OPERATOR, 
                ' OR '
            )
        return act_filter, item

    def add_links_to_act_filter(
        self,
        param_key, 
        match_old_value,
        new_value,
        act_filter, 
        request_dict
    ):
        """Adds links to an active filter"""
        act_request_dict = copy.deepcopy(request_dict)
        sl = SearchLinks(
            request_dict=act_request_dict,
            base_search_url=self.base_search_url
        )
        sl.replace_param_value(
            param_key,
            match_old_value=match_old_value,
            new_value=new_value,
        ) 
        urls = sl.make_urls_from_request_dict()
        if new_value is None:
            # If the new_value is None, then we're completely
            # removing the search filter.
            act_filter['oc-api:remove'] = urls['html']
            act_filter['oc-api:remove-json'] = urls['json']
        else:
            # Make links to broaden a filter to a higher
            # point in a given filter's hierarchy
            act_filter['oc-api:broaden'] = urls['html']
            act_filter['oc-api:broaden-json'] = urls['json']
        return act_filter


    def add_non_hiearchy_filter_json(
        self,
        param_key,
        param_vals,
        param_config,
        filters, 
        request_dict,
    ):
        """Adds JSON for non-hierarchy filters."""
        return filters


    def add_filters_json(self, request_dict):
        """Adds JSON describing active search filters.
        
        :param dict request_dict: Dictionary object of the GET
            request from the client.
        """
        # NOTE: 

        filters = []
        string_fields = []  # so we have an interface for string searches

        for param_key, param_vals in request_dict.items():
            if param_vals is None:
                continue
            if param_key in configs.FILTER_IGNORE_PARAMS:
                continue
            
            # Normalize the values of this parameter into a
            # list to make processing easier
            if not isinstance(param_vals, list):
                param_vals = [param_vals]

            # Get the configuration for this specific request
            # parameter.
            param_config = configs.FILTER_PARAM_CONFIGS.get(
                param_key
            )
            if not param_config:
                # No configuration for this request parameter
                continue

            # Get the hierarchy delimiter configured 
            # for values used by this param_key.
            hierarchy_delim = param_config.get('hierarchy_delim')
            
            for param_val in param_vals:
                
                if (hierarchy_delim is not None 
                    and hierarchy_delim in param_val):
                    hierarchy_vals = param_val.split(hierarchy_delim)
                else:
                    hierarchy_vals = [param_val]
                
                parent_path_vals = []
                for act_val in hierarchy_vals:
                    act_val = urlunquote_plus(act_val)
                    parent_path_vals.append(act_val)
                    if hierarchy_delim is not None:
                        act_full_path = hierarchy_delim.join(
                            parent_path_vals
                        )
                    else:
                        act_full_path = act_val
                    
                    # Count the existing filters to make the 
                    # index of the next one.
                    i = len(filters) + 1

                    act_filter = LastUpdatedOrderedDict()
                    act_filter['id'] = '#filter-{}'.format(i)
                    act_filter['oc-api:filter'] = param_config['oc-api:filter']
                    
                    # The filter-group helps to group together all of the
                    # levels of the hierarchy_vals.
                    act_filter['oc-api:filter-group'] = param_val

                    if param_key == "path":
                        # Look up item entity for spatial context
                        # path items by the current path, which will
                        # include the hierarchy of parent items.
                        item_lookup_val = act_full_path
                    else:
                        # Look up the item entity simply by using
                        # the current act_val.
                        item_lookup_val = act_val
                    
                    act_filter, item = self.add_entity_item_to_act_filter(
                        item_lookup_val,
                        act_filter,
                        is_spatial_context=param_config.get(
                            'is_spatial_context', 
                            False
                        )
                    )
                    
                    # Add the totally remove filter links
                    act_filter = self.add_links_to_act_filter(
                        param_key, 
                        match_old_value=param_val,
                        new_value=None,
                        act_filter=act_filter, 
                        request_dict=request_dict,
                    )

                    if len(parent_path_vals) < len(hierarchy_vals):
                        # We can add links to broaden this current
                        # filter to a higher level in the hierarchy.
                        act_filter = self.add_links_to_act_filter(
                            param_key, 
                            match_old_value=param_val,
                            new_value=act_full_path,
                            act_filter=act_filter, 
                            request_dict=request_dict,
                        )

                    filters.append(act_filter)
                    
        return filters