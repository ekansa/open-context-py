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
        range_data_type=None,
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

        if range_data_type is None:
            id_prefix = 'facet'
        else:
            id_prefix = 'range-facet'

        if is_related:
            facet['id'] = '#{}-{}{}'.format(
                id_prefix,
                configs.RELATED_ENTITY_ID_PREFIX,
                slugs_id
            )
        else:
            facet['id'] = '#{}-{}'.format(
                id_prefix,
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
        if range_data_type:
            facet['data-type'] = range_data_type
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

            if param_key == 'prop':
                # Prop can be a list. If the match_old_value is None
                # then we add to new_value to the existing list of 
                # all prop parameter values.
                add_to_param_list = True
            else:
                # All the other param_key's can only take a single
                # value.
                add_to_param_list = False

            # Update the request dict for this facet option.
            sl.replace_param_value(
                param_key,
                match_old_value=match_old_value,
                new_value=new_value,
                add_to_param_list=add_to_param_list,
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
        param_key, match_old_value = self.facet_fields_to_client_request.get(
            solr_facet_field_key,
            (param_key, None,) # default parameter key with no matching value.
        )
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
    

    def add_range_options_list(
        self, 
        param_key,
        match_old_value,
        data_type,
        field_max_value,
        options_tuples,
        round_digits=None
    ):
        """Adds option dict object to a list based on data-type.
        
        :param str data_type: Solr data-type to match for inclusion
            in the output options list.
        :param list options_tuples: List of (facet_value, count) tuples
        """
        delim = configs.REQUEST_PROP_HIERARCHY_DELIM
        options = []
        options_length = len(options_tuples)
        for i, option_tup in enumerate(options_tuples):
            facet_value, count = option_tup
            if count < 1:
                # We don't make facet options for facet values with no
                # records.
                continue

            if (i + 1) == options_length:
                max_value = field_max_value
                # This indicates a less than or equal range
                # for the max_value.
                range_query_end = ']'
            else:
                # Get the first element of the next options
                # tuple. That's the facet value for the
                # next maximum value.
                max_value = options_tuples[(i + 1)][0]
                # This indicates a less than range for the
                # max_value. We don't want to include
                # values for the next facet.
                range_query_end = '}'
            
            label = facet_value
            if round_digits is not None:
                label = str(round(float(facet_value), round_digits))

            if data_type == 'xsd:integer':
                min_value = int(round(float(facet_value),0))
                max_value = int(round(float(max_value),0))
            elif data_type == 'xsd:double':
                if round_digits is not None:
                    label = str(round(float(facet_value), round_digits))
                min_value = float(facet_value)
                max_value = float(max_value)
            elif data_type == 'xsd:date':
                min_value = facet_value
            else:
                # How van we even be here with the wrong data-type?
                continue
            

            # Except for the last range query option, a
            # range query is greater than or equal to the min_value
            # and less than the max_value.
            # 
            # For the last range query option, the range query
            # is greater than or equal to the min_value and less than
            # or equal to the maximum value (thus, we include the
            # max_value for the last, greatest facet option). 
            range_query = '[{min_val} TO {max_val}{q_end}'.format(
                min_val=min_value, 
                max_val=max_value,
                q_end=range_query_end,
            )

            new_value = None
            old_range_seps = [(delim + '['), (delim + '{')]
            for old_range_sep in old_range_seps:
                if not old_range_sep in match_old_value:
                    continue
                if new_value is not None:
                    continue
                # Remove the part of the match_old_value that
                # has the range query value.
                old_parts = match_old_value.split(old_range_sep)
                # The first part of the old_parts has the
                # old range removed.
                new_value = old_parts[0] + delim + range_query
            
            if new_value is None:
                # No old range query to replace.
                if match_old_value.endswith(delim):
                    new_value = match_old_value + range_query
                else:
                    new_value = match_old_value + delim + range_query

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
            option['label'] = label
            option['count'] = count
            option['oc-api:min'] = min_value
            option['oc-api:max'] = max_value
            options.append(option)
        return options


    def get_facet_ranges_and_options(self, solr_json):
        """Gets property range facets and options from solr response json"""
        
        facet_ranges = []
        solr_facet_ranges_dict = utilities.get_dict_path_value(
            configs.FACETS_RANGE_SOLR_ROOT_PATH_KEYS,
            solr_json
        )
        if not solr_facet_ranges_dict:
            # No facets ranges active, so skip out
            return facet_ranges
        
        # Now get the related stats fields.
        solr_stats_dict = utilities.get_dict_path_value(
            configs.STATS_FIELDS_PATH_KEYS,
            solr_json
        )
        if not solr_stats_dict:
            # No solr stats. So skip out.
            return None
        
        for (
                solr_field_key, 
                range_dict,
            ) in solr_facet_ranges_dict.items():

            # Look up the client's request parameter and reqest 
            (
                param_key, 
                match_old_value,
            ) = self.facet_fields_to_client_request.get(
                solr_field_key,
                ('prop', None,) # default parameter, matching value.
            )
            if not match_old_value:
                # This should never happen, but we can't associate a
                # this solr field with a client request param and value
                continue

            # Parse the solr field to get the data type
            data_type = utilities.get_data_type_for_solr_field(
                solr_field_key
            )
            if data_type not in [
                    'xsd:integer', 
                    'xsd:double', 
                    'xsd:date',
                ]:
                # The data type for solr field is missing or
                # is of a type that does not have ranges.
                continue

            stats_dict = solr_stats_dict.get(solr_field_key)
            if not stats_dict:
                # We can't find stats for this solr field
                # that gave us ranges. Which should not happen, but
                # it did, so skip.
                continue

            # Get the raw list of value counts
            range_value_count_list = range_dict.get('counts', [])
            # Make  list of the tuples for this solr facet field.
            options_tuples = utilities.get_facet_value_count_tuples(
                range_value_count_list
            )
            if not len(options_tuples):
                # Skip, because we don't have any facet range options
                continue
            
            facet_range = self.make_facet_dict_from_solr_field(
                solr_field_key,
                'oc-api:range-facet',
                'Ranges',
                range_data_type=data_type,
            )
            for key in ['min', 'max', 'mean', 'stddev']:
                facet_range['oc-api:{}'.format(key)] = stats_dict[key]
            for key in ['gap']:
                facet_range['oc-api:{}'.format(key)] = range_dict[key]

            round_digits = None
            if data_type == 'xsd:double':
                digits = [
                    utilities.get_rounding_level_from_float(
                        stats_dict[key]
                    )
                    for key in ['min', 'max']
                ]
                round_digits = max(digits)


            # Now add the links do different options.
            facet_range['oc-api:has-range-options'] = self.add_range_options_list(
                param_key,
                match_old_value,
                data_type,
                stats_dict['max'],  
                options_tuples,
                round_digits=round_digits,
            )

            facet_ranges.append(facet_range)

        return facet_ranges
            

        
            

