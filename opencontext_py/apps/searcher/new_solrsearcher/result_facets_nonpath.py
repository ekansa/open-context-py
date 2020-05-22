import copy

from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks
from opencontext_py.apps.searcher.new_solrsearcher import utilities

# ---------------------------------------------------------------------
# Methods to generate results for facets that are NOT entities in a
# hierarchy
# ---------------------------------------------------------------------
class ResultFacetsNonPath():

    """ Methods to prepare result facets not involving entities in a hierarchy """

    def __init__(self, 
        request_dict=None, 
        current_filters_url=None, 
        base_search_url='/search/'
    ):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.base_search_url = base_search_url
        self.request_dict = copy.deepcopy(request_dict)
        if current_filters_url is None:
            current_filters_url = self.base_search_url
        self.current_filters_url = current_filters_url
    

    def make_item_type_facets(self, solr_json):
        """Makes item_type facets from a solr_json response""" 
        item_type_path_keys = (
            configs.FACETS_SOLR_ROOT_PATH_KEYS 
            + ['item_type']
        )
        item_type_val_count_list = utilities.get_dict_path_value(
            item_type_path_keys,
            solr_json,
            default=[]
        )
        if not len(item_type_val_count_list):
            return None
        options_tuples = utilities.get_facet_value_count_tuples(
            item_type_val_count_list
        )
        if not len(options_tuples):
            return None

        # Iterate through tuples of item_type counts
        options = []
        for facet_value, count in options_tuples:
            # The get_item_type_dict should return the
            # type_dict for slugs, full uris, prefixed URIs
            # or lower-case item types.
            type_dict = utilities.get_item_type_dict(
                facet_value
            )
            if not type_dict:
                # Unrecognized item type. Skip.
                continue
            sl = SearchLinks(
                request_dict=copy.deepcopy(self.request_dict),
                base_search_url=self.base_search_url
            )
            # Remove non search related params.
            sl.remove_non_query_params()

            # Update the request dict for this facet option.
            sl.replace_param_value(
                'type',
                match_old_value=None,
                new_value=facet_value,
            )  
            urls = sl.make_urls_from_request_dict()
            if urls['html'] == self.current_filters_url:
                # The new URL matches our current filter
                # url, so don't add this facet option.
                continue

            option = LastUpdatedOrderedDict()
            option['id'] = urls['html']
            option['json'] = urls['json']
            for key, val in type_dict.items():
                option[key] = val
            options.append(option)
        
        if not len(options):
            return None
        
        facet = configs.FACETS_ITEM_TYPE.copy()
        facet['oc-api:has-id-options'] = options
        return facet


    def make_related_media_facets(self, solr_json):
        """Makes related media facets from a solr_json response""" 
        options = []
        for media_config in configs.FACETS_RELATED_MEDIA['oc-api:has-rel-media-options']:
            facet_val_count_tups = utilities.get_path_facet_value_count_tuples(
                media_config['facet_path'], 
                solr_json
            )
            
            media_type_total_count = 0
            for facet_val, facet_count in facet_val_count_tups:
                if facet_val == "0":
                    # Skip, this facet_value is for
                    # items with NO related media of this type
                    continue
                media_type_total_count += facet_count
 
            if media_type_total_count == 0:
                # No items have related media of this type,
                # so continue and don't make a facet option
                # for this.
                continue

            sl = SearchLinks(
                request_dict=copy.deepcopy(self.request_dict),
                base_search_url=self.base_search_url
            )

            # Remove non search related params.
            sl.remove_non_query_params()

            sl.replace_param_value(
                media_config['param_key'],
                new_value=1,
            ) 
            urls = sl.make_urls_from_request_dict()
            if urls['html'] == self.current_filters_url:
                # The new URL matches our current filter
                # url, so don't add this facet option.
                continue

            option = LastUpdatedOrderedDict()
            option['label'] = media_config['label']
            option['count'] = media_type_total_count
            option['id'] = urls['html']
            option['json'] = urls['json']
            options.append(option)
        
        if not len(options):
            # We found no related media configs, so return None
            return None

        # Return the related media facets object.
        rel_media_facets = LastUpdatedOrderedDict()
        rel_media_facets['id'] = configs.FACETS_RELATED_MEDIA['id']
        rel_media_facets['label'] = configs.FACETS_RELATED_MEDIA['label']
        rel_media_facets['oc-api:has-rel-media-options'] = options
        return rel_media_facets

