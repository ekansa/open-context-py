import copy

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import db_entities
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
        if not item_type_val_count_list:
            return None
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
            option['count'] = count
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


    def check_if_pivot_item_class_slug_ok(
        self,
        item_type,
        item_class_slug,
        proj_class_sum_list,
    ):
        """Checks to see if a pivot item_class_slug is on the list for
        project
        
        :param dict item_type: The item type associated with the
            item_class_slug
        :param dict item_class_slug: The item_class_slug for the pivot
            item that we're checking to see if it exists in the
            proj_class_sum_list
        :param list proj_class_sum_list: The proj_class_sum_list is the
            list of item type, item_classes that exist for the projects
            queried in this solr query
        """
        for proj_dict in proj_class_sum_list:
            if proj_dict.get('item_type') != item_type:
                continue
            if proj_dict.get('item_class__slug') == item_class_slug:
                return True
        return False


    def make_project_item_class_summary_facets(self, solr_json):
        """Makes item_class_summary facets from a solr_json response""" 
        item_type_classes_pivot = utilities.get_dict_path_value(
            ['facet_counts', 'facet_pivot', 'item_type,obj_all___oc_gen_category___pred_id'],
            solr_json
        )
        if not item_type_classes_pivot:
            # There are no item_type_classes pivot data here.
            print('No project summary pivot on item_type,obj_all___oc_gen_category___pred_id')
            return None
        raw_all_projects_list = utilities.get_dict_path_value(
            (configs.FACETS_SOLR_ROOT_PATH_KEYS + ['obj_all___project_id']),
            solr_json
        )
        if not raw_all_projects_list:
            # We don't have a list of all projects
            return None
        proj_tuples = utilities.get_facet_value_count_tuples(
            raw_all_projects_list
        )
        if not len(proj_tuples):
            return None
        project_slugs = []
        for solr_proj, _ in proj_tuples:
            parsed_val = utilities.parse_solr_encoded_entity_str(
                solr_proj, base_url=self.base_url
            )
            if not parsed_val:
                # Can't interpret this as a solr value, so skip
                continue
            project_slugs.append(parsed_val['slug'])
        print(f'Checking database item classes for project slugs {project_slugs}')
        proj_class_sum_list = db_entities.get_unique_project_item_class_list(
            project_slugs=project_slugs
        )
        if not proj_class_sum_list:
            return  None
        print(f'project_slugs has {len(proj_class_sum_list)} item-classes')
        options = []
        for item_type_piv in item_type_classes_pivot:
            item_type = item_type_piv.get('value')
            item_type_dict = copy.deepcopy(
                configs.ITEM_TYPE_MAPPINGS.get(item_type, {})
            )
            if not item_type_dict:
                continue
            item_type_dict['count'] = item_type_piv.get('count')
            sl = SearchLinks(
                request_dict=copy.deepcopy(self.request_dict),
                base_search_url=self.base_search_url
            )
            # Remove non search related params.
            sl.remove_non_query_params()
            if sl.request_dict.get('proj-summary'):
                sl.request_dict.pop('proj-summary', None)
            # Update the request dict for this facet option.
            sl.replace_param_value(
                'type',
                match_old_value=None,
                new_value=item_type,
            )  
            urls = sl.make_urls_from_request_dict()
            if urls['html'] == self.current_filters_url:
                # The new URL matches our current filter
                # url, so don't add this facet option.
                continue
            item_type_dict['id'] = urls['html']
            item_type_dict['json'] = urls['json']
            pivot_options = []
            for piv_dict in item_type_piv.get('pivot', []):
                parsed_val = utilities.parse_solr_encoded_entity_str(
                    piv_dict.get('value'), base_url=self.base_url
                )
                if not parsed_val:
                    # Can't interpret this as a solr value, so skip
                    continue
                ok = self.check_if_pivot_item_class_slug_ok(
                    item_type,
                    parsed_val.get('slug'),
                    proj_class_sum_list,
                )
                if not ok:
                    # This item class is a parent, not the most
                    # specific level present
                    continue
                sl.replace_param_value(
                    'cat',
                    match_old_value=None,
                    new_value=parsed_val.get('slug'),
                )
                piv_urls = sl.make_urls_from_request_dict()
                if piv_urls['html'] == self.current_filters_url:
                    # The new URL matches our current filter
                    # url, so don't add this facet option.
                    continue
                piv_opt = {
                    'id': piv_urls['html'],
                    'json': piv_urls['json'],
                    'label': parsed_val.get('label'),
                    'rdfs:isDefinedBy': parsed_val.get('uri'),
                    'slug': parsed_val.get('slug'),
                    'count': piv_dict.get('count'),
                }
                pivot_options.append(piv_opt)

            if pivot_options and len(pivot_options) > 0:
                item_type_dict["oc-api:has-id-options"] = pivot_options
            options.append(item_type_dict)
        return options