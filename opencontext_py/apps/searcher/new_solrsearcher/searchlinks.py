import copy
import json
from urllib.parse import urlparse, parse_qs
from django.utils.http import urlquote, quote_plus, urlquote_plus
from django.utils.encoding import iri_to_uri

from django.conf import settings

from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities



def get_path_value(request_dict, default=None):
    """Gets the path value removed from a list"""
    path = request_dict.get('path')
    if not path:
        return default
    if isinstance(path, list):
        # Normalize a path to be a single string value.
        path = path[0]
    return path



class SearchLinks():

    def __init__(self, request_dict=None, base_search_url='/search/'):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.base_search_url = base_search_url
        self.request_dict = copy.deepcopy(request_dict)
        self.doc_formats = configs.REQUEST_URL_FORMAT_EXTENTIONS
    
    
    def remove_non_query_params(
        self, 
        remove_params=configs.QUERY_NEW_URL_IGNORE_PARAMS
    ):
        """Removes params that are not relevant to query filters"""
        for param in remove_params:
            if not param in self.request_dict:
                continue
            self.request_dict.pop(param, None)
        return self.request_dict


    def make_url_from_request_dict(
        self,
        base_request_url=None,
        request_dict=None,
        doc_extention=None,
    ):
        """Makes request url from a request_dict
        """
        if base_request_url is None:
            url = self.base_url + self.base_search_url
        else:
            url = base_request_url
    
        if request_dict is None:
            request_dict = self.request_dict

        path = get_path_value(request_dict)
        if path:
            url += path.replace(' ', '+')
        if doc_extention:
            url += doc_extention
        
        # Prepare the query parameters.
        param_list = []
        for param, param_vals in request_dict.items():
            if param == 'path':
                continue
            if not isinstance(param_vals, list):
                # params_vals maybe a single value, but we default
                # to treating it as a list.
                param_vals = [str(param_vals)]
            for val in param_vals:
                quote_val = quote_plus(val)
                quote_val = quote_val.replace('%7BSearchTerm%7D', '{SearchTerm}')
                param_item = param + '=' + quote_val
                param_list.append(param_item)
        if len(param_list):
            # keep a consistent sort order on query parameters + values.
            param_list.sort()
            url += '?' + '&'.join(param_list)
        return url


    def make_urls_from_request_dict(
        self,
        base_request_url=None,
        request_dict=None,
        doc_formats=None,
    ):
        """Makes URLs for different formats from a request_dict"""
        output = {}
        if not doc_formats:
            doc_formats = self.doc_formats
        for doc_format, doc_extention in doc_formats:
            output[doc_format] = self.make_url_from_request_dict(
                base_request_url=base_request_url,
                request_dict=request_dict,
                doc_extention=doc_extention,
            )
        return output


    def add_param_value(
        self,
        param,
        new_value,
        add_to_value=None
    ):
        """Adds to the new request object a parameter and value """
        if param is None or new_value is None:
            return None     
        if not self.request_dict:
            self.request_dict = {}
        if add_to_value is None or not param in self.request_dict:
            self.request_dict[param] = new_value
            return self.request_dict
        exist_param_values = utilities.get_request_param_value(
            request_dict=self.request_dict, 
            param=param,
            default=None,
            as_list=True,
            solr_escape=False,
        )
        new_param_values = []
        for exist_param_value in exist_param_values:
            if exist_param_value.endswith(add_to_value):
                new_param_values.append(new_value)
                continue
            new_param_values.append(exist_param_value) 
        self.request_dict[param] = new_param_values
        return self.request_dict
    

    def replace_param_value(
        self,
        param,
        match_old_value=None,
        new_value=None,
        add_to_param_list=False,
    ):
        """Replaces a request parameter value in a request object"""
        if param is None:
            return None
        if not self.request_dict:
            self.request_dict = {}
        if not param in self.request_dict:
            # This parameter is not in the current request dict.
            if new_value is None:
                # The new value so don't change the request_dict
                return self.request_dict
            return self.add_param_value(
                param,
                new_value
            )
        if match_old_value is None and new_value is None:
            self.request_dict.pop(param, None)
            return self.request_dict
        if (not add_to_param_list 
            and match_old_value is None 
            and new_value is not None):
            # Replace the entire param with the new value.
            self.request_dict[param] = new_value
            return self.request_dict
        if (add_to_param_list 
            and match_old_value is None 
            and new_value is not None):
            # Add to the list of existing values for this
            # parameter.
            all_param_vals = self.request_dict[param]
            if not isinstance(all_param_vals, list):
                all_param_vals = [all_param_vals]
            if new_value not in all_param_vals:
                all_param_vals.append(new_value)
            self.request_dict[param] = all_param_vals
            return self.request_dict
        exist_param_values = utilities.get_request_param_value(
            request_dict=self.request_dict, 
            param=param,
            default=None,
            as_list=True,
            solr_escape=False,
        )
        new_param_values = []
        for exist_param_value in exist_param_values:
            hierarchy_old_suffix = (
                configs.REQUEST_PROP_HIERARCHY_DELIM 
                + str(match_old_value)
            )
            if exist_param_value == match_old_value:
                if new_value is not None:
                    # Only add if the new_value is not None.
                    # A new_value of None means to remove
                    # the old value.
                    new_param_values.append(new_value)
                continue
            elif exist_param_value.endswith(hierarchy_old_suffix): 
                # Case of replacing a ---old_value
                # with ---new_value

                # Remove the old trailing hierarchy ending
                len_old_ending = len(hierarchy_old_suffix)
                replace_val = exist_param_value[0:-len_old_ending]
                if new_value is not None:
                    # Add the new_value to replace the old
                    # hierarchy ending
                    replace_val += (
                        configs.REQUEST_PROP_HIERARCHY_DELIM 
                        + str(new_value)
                    )
                new_param_values.append(replace_val)
            else:
                # No change, this value was not getting
                # modified.
                new_param_values.append(exist_param_value) 
        self.request_dict[param] = new_param_values
        return self.request_dict