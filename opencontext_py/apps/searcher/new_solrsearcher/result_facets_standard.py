import copy

from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import (
    get_path_value, 
    SearchLinks,
)
from opencontext_py.apps.searcher.new_solrsearcher import utilities


# ---------------------------------------------------------------------
# Methods to generate results for standard context, property, or
# project facets
# ---------------------------------------------------------------------
class ResultFacetsStandard():

    """ Methods to prepare context, property, project facets """

    def __init__(self, 
        request_dict=None, 
        current_filters_url=None, 
        facet_fields_to_client_request={},
        base_search_url='/search/'
    ):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.base_search_url = base_search_url
        self.request_dict = copy.deepcopy(request_dict)
        if current_filters_url is None:
            current_filters_url = self.base_search_url
        self.current_filters_url = current_filters_url
        # Dictionary of keyed by facet fields that are derived from the
        # raw request paths provided by clients. This dictionary makes
        # it easier to generate links for different facet options.
        self.facet_fields_to_client_request = facet_fields_to_client_request
    

    def make_facet_dict_from_solr_field(
        self, 
        solr_facet_field_key,
        facet_type,
        facet_labeling,
    ):
        """Makes the dict for a fact with id options."""

        if configs.FACET_STANDARD_ROOT_FIELDS.get(
                solr_facet_field_key
            ):
            # We have a standard "root" field. Return the facet
            # dict object for it.
            return configs.FACET_STANDARD_ROOT_FIELDS.get(
                solr_facet_field_key
            )

        solr_slug_parts = solr_facet_field_key.split(
            SolrDocument.SOLR_VALUE_DELIM
        )

        # Making this dict will require some database (usually from
        # the cache) because it is not a standard root solr field,
        # rather it is a solr field deeper in a hierarchy.
        m_cache = MemoryCache()

        # The solr field parts are in reverse hierarchy order
        solr_slug_parts.reverse()

        # Iterate through the parts, skipping the first item
        # which is the most general part (the field suffix).
        items = []
        for solr_slug in solr_slug_parts[1:]:
            is_related = False
            slug = solr_slug.replace('_', '-')
            if slug.startswith(configs.RELATED_ENTITY_ID_PREFIX):
                is_related = True
                slug = slug[len(configs.RELATED_ENTITY_ID_PREFIX):]
            item = m_cache.get_entity(slug)
            if not item:
                continue

            # Add an "is_related" attribute
            item.is_related = is_related
            items.append(item)
        
        if not len(items):
            return None
        
        slugs_id = configs.REQUEST_PROP_HIERARCHY_DELIM.join(
            [item.slug for item in items]
         )
        facet = LastUpdatedOrderedDict()
        if is_related:
            facet['id'] = '#facet-{}{}'.format(
                configs.RELATED_ENTITY_ID_PREFIX,
                slugs_id
            )
        else:
            facet['id'] = '#facet-{}'.format(
                slugs_id
            )
        
        labels = [item.label for item in items]
        if len(labels) == 1:
            labels.append(facet_labeling)
        # Put the last label in parentheses.
        labels[-1] = '({})'.format(labels[-1])
        facet['label'] = ' '.join(labels)
        facet['rdfs:isDefinedBy'] = items[0].uri
        facet['slug'] = items[0].slug
        facet['type'] = facet_type
        if items[0].is_related:
            facet['oc-api:related-property'] = True
        return facet


    def add_options_list_for_data_type(
        self, 
        param_key,
        match_old_value, 
        delim, 
        data_type, 
        options_tuples
    ):
        """Adds option dict object to a list based on data-type.
        
        :param str data_type: Solr data-type to match for inclusion
            in the output options list.
        :param list options_tuples: List of (facet_value, count) tuples
        """
        options = []
        for facet_value, count in options_tuples:
            if count < 1:
                # We don't make facet options for facet values with no
                # records.
                continue

            # Parse the solr encoded entity string. Note this does
            # NOT make a request to the database.
            parsed_val = utilities.parse_solr_encoded_entity_str(
                facet_value, base_url=self.base_url
            )
            if not parsed_val:
                # Can't interpret this as a solr value, so skip
                continue
            if parsed_val.get('data_type') != data_type:
                # The data type for this value does not match the
                # data type for the options list that we are 
                # building.
                continue

            # The new_value is generally the slug part of the parsed_val
            # (derived from the facet_value). However, context (path)
            # items are different, and we use the label for the new_value.
            if param_key == 'path':
                new_value = parsed_val['label']
            else:
                new_value = parsed_val['slug']
            
            if match_old_value is not None:
                # We have an old value to match. So the new_value
                # will be the match_old_value + delim + the new_value.
                if not match_old_value.endswith(delim):
                    new_value = match_old_value + delim + new_value
                else:
                    new_value = match_old_value + new_value

            sl = SearchLinks(
                request_dict=copy.deepcopy(self.request_dict),
                base_search_url=self.base_search_url
            )
            # Remove non search related params.
            sl.remove_non_query_params()

            # Update the request dict for this facet option.
            sl.replace_param_value(
                param_key,
                match_old_value=match_old_value,
                new_value=new_value,
            )  
            urls = sl.make_urls_from_request_dict()
            if urls['html'] == self.current_filters_url:
                # The new URL matches our current filter
                # url, so don't add this facet option.
                continue

            option = LastUpdatedOrderedDict()
            option['id'] = urls['html']
            option['json'] = urls['json']
            option['rdfs:isDefinedBy'] = parsed_val['uri']
            option['slug'] = parsed_val['slug']
            option['label'] = parsed_val['label']
            option['count'] = count
            options.append(option)
        return options



    def add_options_lists_to_facet(
        self, 
        facet, 
        solr_facet_field_key, 
        param_key, 
        delim, 
        options_tuples
    ):
        """Adds options lists for different data types to a facet"""
        
        # Look up the client's request parameter and reqest 
        param_key_val_dict = self.facet_fields_to_client_request.get(
            solr_facet_field_key,
            {param_key: None} # default parameter key with no matching value.
        )
        param_key = list(param_key_val_dict.keys())[0]
        match_old_value = param_key_val_dict[param_key]
        for data_type, options_list_key in configs.FACETS_DATA_TYPE_OPTIONS_LISTS.items():
            options = self.add_options_list_for_data_type(
                param_key,
                match_old_value, 
                delim, 
                data_type, 
                options_tuples
            )
            if not len(options):
                # No facet options of this datatype.
                continue
            facet[options_list_key] = options
        return facet


    def get_facets_and_options(self, solr_json):
        """Gets property facets and options from solr response json"""
        
        facets = []
        solr_facet_fields_dict = utilities.get_dict_path_value(
            configs.FACETS_SOLR_ROOT_PATH_KEYS,
            solr_json
        )
        if not solr_facet_fields_dict:
            # No facets active, so skip out
            return facets

        for (
                suffix, 
                param_key, 
                delim, 
                facet_type, 
                facet_labeling,
            ) in configs.FACETS_STANDARD:

            for (
                    solr_facet_field_key, 
                    solr_facet_value_count_list,
                ) in solr_facet_fields_dict.items():
                
                if not solr_facet_field_key.endswith(suffix):
                    # the type for field for the current suffix.
                    continue

                # Make  list of the tuples for this solr facet field.
                options_tuples = utilities.get_facet_value_count_tuples(
                    solr_facet_value_count_list
                )
                if not len(options_tuples):
                    # Skip, because we don't have any facet options
                    continue

                facet = self.make_facet_dict_from_solr_field(
                    solr_facet_field_key,
                    facet_type,
                    facet_labeling,
                )
                if not facet:
                    print('Strange. No facet object for {}'.format(
                        solr_facet_field_key)
                    )
                    continue

                # Add options lists for different data-types present in
                # the options tuples list.
                facet = self.add_options_lists_to_facet(
                    facet, 
                    solr_facet_field_key, 
                    param_key, 
                    delim, 
                    options_tuples
                )
                facets.append(facet)
        
        return facets

