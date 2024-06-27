import copy


from operator import itemgetter

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.all_items.representations import rep_utils

from opencontext_py.apps.indexer import solrdocument_new_schema as SolrDoc

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import db_entities
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import (
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
        slugs_for_config_facets=[],
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
        self.facet_fields_to_client_request = copy.deepcopy(facet_fields_to_client_request)
        # Keep track of the slugs that have pre-defined facets configs.
        self.slugs_for_config_facets = copy.deepcopy(slugs_for_config_facets)


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
            SolrDoc.SOLR_VALUE_DELIM
        )

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
            item_obj = db_entities.get_cache_man_obj_by_any_id(slug)
            if not item_obj:
                continue

            # Add an "is_related" attribute
            item_obj.is_related = is_related
            items.append(item_obj)

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
            facet['id'] = f'#{id_prefix}-{configs.RELATED_ENTITY_ID_PREFIX}{slugs_id}'
        else:
            facet['id'] = f'#{id_prefix}-{slugs_id}'
        labels = [item.label for item in items]
        if len(labels) == 1:
            labels.append(facet_labeling)
        # Put the last label in parentheses.
        labels[-1] = '({})'.format(labels[-1])
        facet['label'] = ' '.join(labels)
        if range_data_type is None:
            facet['rdfs:isDefinedBy'] = rep_utils.make_web_url(items[0])
            facet['slug'] = items[0].slug
        else:
            # The final item is the one we want for a definition range facets, because
            # this item defines the most specific attribute that we're getting
            # ranges for.
            facet['rdfs:isDefinedBy'] = rep_utils.make_web_url(items[-1])
            facet['slug'] = items[-1].slug
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

        :param str param_key: The request parameter key value.
        :param str match_old_value: If not None, this is for iterating
            through lists of values for a given request parameter so we
            can replace that value
        :param str delim: Delimiter for hierarchy path values
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
            if parsed_val.get('slug') in configs.NOT_INCLUDE_FACET_OPTION_SLUGS:
                # This slug is configured to be not included as a
                # facet option.
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
            if parsed_val.get('alt_label'):
                option['skos:altLabel'] = parsed_val.get('alt_label')
            option['count'] = count
            options.append(option)
        return options



    def add_options_lists_to_facet(
        self,
        facet,
        solr_facet_field_key,
        param_key,
        delim,
        options_tuples,
        add_to_existing_opts=False,
        obj_all_facet=False,
    ):
        """Adds options lists for different data types to a facet"""
        # Look up the client's request parameter and reqest
        param_key, match_old_value = self.facet_fields_to_client_request.get(
            solr_facet_field_key,
            (param_key, None,) # default parameter key with no matching value.
        )

        if not match_old_value and obj_all_facet:
            # We have an obj_all facet, and there's no existing match_old_value.
            # To keep the hierarchy OK, use the slug for this facet as the match_old_value.
            match_old_value = facet.get('slug')

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
            if add_to_existing_opts and facet.get(options_list_key):
                # First sort by label, this will mean options with
                # the same count will be secondarily sorted by label.
                all_options = sorted(
                    (facet[options_list_key] + options),
                    key=itemgetter('label')
                )
                # Second sort the options by count.
                facet[options_list_key] = sorted(
                    all_options,
                    key=itemgetter('count'),
                    reverse=True
                )

            else:
                facet[options_list_key] = options
        return facet


    def prep_preconfig_facet(
        self,
        param_key,
    ):
        """Prepare a preconfigured facet if applicable

        :param str param_key: The request parameter key value.

        return preconfig_facet
        """
        if param_key != 'prop' or not len(self.slugs_for_config_facets):
            return None

        # Iterate through the list of configs.ITEM_CAT_FACET_FIELDS_BACKEND.
        # This will go from more general to more specific. The most specific
        # matched configuration will be the one we use.
        preconfig_facet = None
        for config_slug, act_config in configs.PRECONFIG_FACET_FIELDS_BACKEND:
            if config_slug not in self.slugs_for_config_facets:
                continue
            preconfig_facet = copy.deepcopy(act_config)
        return preconfig_facet


    def prep_preconfig_facet_options(
        self,
        preconfig_facet,
        solr_facet_field_key,
        param_key,
        delim,
        options_tuples
    ):
        """Prepare a preconfigured facet if applicable

        :param dict preconfig_facet: A dictionary for a pre-configured
            facet field.
        :param str solr_facet_field_key: A solr facet field key that's
            checked to see if it matches expectations in the pre_config
            facet.
        :param str param_key: The request parameter key value.
        :param str delim: A hierarchy path delimiter
        :param list options_tuples: List of (facet_value, count) tuples

        return preconfig_facet, remaining_options_tuples
        """
        if not preconfig_facet or not options_tuples or not len(options_tuples):
            return preconfig_facet, options_tuples

        solr_fact_field_config = preconfig_facet.get(
            'solr_facet_field_keys_opts_slugs',
            {}
        ).get(solr_facet_field_key)

        if not solr_fact_field_config:
            # The current solr_facet_field_key is not in the dict of
            # solr_facet_field_keys relevant to this pre-configured facet
            return preconfig_facet, options_tuples

        if solr_fact_field_config == 'ALL':
            # Add ALL of the options_tuples for current solr_facet_field_key to the preconfig_facet
            preconfig_facet = self.add_options_lists_to_facet(
                preconfig_facet,
                solr_facet_field_key,
                param_key,
                delim,
                options_tuples,
                add_to_existing_opts=True,
            )
            # Return the preconfig_facet and an empty list of options tuples
            # because we used all of these options_tuples and none remain.
            return  preconfig_facet, []

        if not isinstance(solr_fact_field_config, list):
            # We have a bad config. Raise an error.
            raise ValueError(f'Bad config in {preconfig_facet}, check {solr_facet_field_key}')

        preconfig_options_tuples = []
        remaining_options_tuples = []
        for facet_value, count in options_tuples:
            # Parse the solr encoded entity string. Note this does
            # NOT make a request to the database.
            parsed_val = utilities.parse_solr_encoded_entity_str(
                facet_value, base_url=self.base_url
            )
            if not parsed_val:
                # Can't interpret this as a solr value, so skip
                continue
            slug_matches = False
            for opt_slug in solr_fact_field_config:
                if parsed_val.get('slug') == opt_slug:
                    slug_matches = True
                    break
            if slug_matches:
                # This matches the preconfiged slug,
                preconfig_options_tuples.append((facet_value, count,))
            else:
                remaining_options_tuples.append((facet_value, count,))

        if not len(preconfig_options_tuples):
            # We didn't actually find any matching option_tuples in
            # current solr_facet_field_key
            return preconfig_facet, options_tuples

        preconfig_facet = self.add_options_lists_to_facet(
            preconfig_facet,
            solr_facet_field_key,
            param_key,
            delim,
            preconfig_options_tuples,
            add_to_existing_opts=True,
        )
        # Return the preconfig_facet and a smaller list of options tuples
        # remaining_options_tuples
        return  preconfig_facet, remaining_options_tuples



    def get_facets_and_options(self, solr_json):
        """Gets property facets and options from solr response json"""
        preconfig_facets = []
        normal_facets = []
        solr_facet_fields_dict = utilities.get_dict_path_value(
            configs.FACETS_SOLR_ROOT_PATH_KEYS,
            solr_json
        )
        if not solr_facet_fields_dict:
            # No facets active, so skip out
            return []

        for (
                suffix,
                param_key,
                delim,
                facet_type,
                facet_labeling,
            ) in configs.FACETS_STANDARD:

            preconfig_facet = self.prep_preconfig_facet(param_key)
            for (
                    solr_facet_field_key,
                    solr_facet_value_count_list,
                ) in solr_facet_fields_dict.items():

                if not solr_facet_field_key.endswith(suffix):
                    # the type for field for the current suffix.
                    continue
                if (
                    suffix == configs.FACETS_PROP_SUFFIX
                    and solr_facet_field_key.endswith(configs.FACETS_CAT_SUFFIX)
                ):
                    # We don't want to double count categories, because
                    # the prop-suffix is also a suffix of the category
                    # suffix.
                    continue

                # Make  list of the tuples for this solr facet field.
                options_tuples = utilities.get_facet_value_count_tuples(
                    solr_facet_value_count_list
                )

                # Add to the preconfigured facet, of it exists, and if criteria
                # match.
                preconfig_facet, options_tuples = self.prep_preconfig_facet_options(
                    copy.deepcopy(preconfig_facet),
                    solr_facet_field_key,
                    param_key,
                    delim,
                    options_tuples
                )

                if not len(options_tuples):
                    # Skip, because we don't have any facet options
                    continue

                obj_all_facet = False
                if solr_facet_field_key.startswith(f'obj_all{SolrDoc.SOLR_VALUE_DELIM}'):
                    # Remove the 'obj_all___' prefix. We're doing a special request
                    # facet for counts of everything within a facet attribute, regardless of hierarchy.
                    solr_facet_field_key = solr_facet_field_key[len(f'obj_all{SolrDoc.SOLR_VALUE_DELIM}'):]
                    obj_all_facet = True

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
                    copy.deepcopy(facet),
                    solr_facet_field_key,
                    param_key,
                    delim,
                    options_tuples,
                    obj_all_facet=obj_all_facet
                )
                normal_facets.append(facet)

            if preconfig_facet:
                preconfig_facet.pop('solr_facet_field_keys_opts_slugs')
                preconfig_facets.append(preconfig_facet)

        # Make the preconfig facet the first facet.
        return preconfig_facets + normal_facets



    def get_sitemap_facets_and_options(self, solr_json):
        """Gets property facets and options from solr response json"""
        normal_facets = []
        solr_facet_fields_dict = utilities.get_dict_path_value(
            configs.FACETS_SOLR_ROOT_PATH_KEYS,
            solr_json
        )
        facet = configs.SITE_MAP_FACETS_DICT.get(
            configs.SITEMAP_FACET_FIELD,
        )
        if not facet :
            return normal_facets

        for (
            solr_facet_field_key,
            solr_facet_value_count_list,
            ) in solr_facet_fields_dict.items():

            if solr_facet_field_key != configs.SITEMAP_FACET_FIELD:
                # We're only interested in the sitemap facet field
                continue

            # Make  list of the tuples for this solr facet field.
            options_tuples = utilities.get_facet_value_count_tuples(
                solr_facet_value_count_list
            )

            if not len(options_tuples):
                # Skip, because we don't have any facet options
                continue

            # Add options lists for different data-types present in
            # the options tuples list.
            facet = self.add_options_lists_to_facet(
                copy.deepcopy(facet),
                solr_facet_field_key,
                param_key='proj',
                delim='---',
                options_tuples=options_tuples
            )
            normal_facets.append(facet)

        # Make the preconfig facet the first facet.
        return normal_facets



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
            if False and count < 1:
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
                if max_value <= min_value:
                    continue
            elif data_type == 'xsd:double':
                if round_digits is not None:
                    label = str(round(float(facet_value), round_digits))
                min_value = float(facet_value)
                max_value = float(max_value)
                if max_value <= min_value:
                    continue
            elif data_type == 'xsd:date':
                min_value = facet_value
            elif data_type == 'xsd:boolean':
                min_value = False
                max_value = True
                label = facet_value
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
            if data_type == 'xsd:boolean':
                range_query = facet_value

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


    def get_facet_boolean_options(self, solr_json):
        """Gets boolean property range facets and options from solr response json"""
        facet_ranges = []
        solr_facet_fields_dict = utilities.get_dict_path_value(
            configs.FACETS_SOLR_ROOT_PATH_KEYS,
            solr_json
        )
        if not solr_facet_fields_dict:
            # No facets ranges active, so skip out
            return facet_ranges
        for (
            solr_field_key,
            solr_facet_value_count_list,
        ) in solr_facet_fields_dict.items():

            if not solr_field_key.endswith('___pred_bool'):
                # boolean datatype for field.
                continue
            # Make  list of the tuples for this solr facet field.
            options_tuples = utilities.get_facet_value_count_tuples(
                solr_facet_value_count_list
            )
            if not len(options_tuples):
                # Skip, because we don't have any facet options
                continue
            # Look up the client's request parameter and request
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
            data_type = utilities.get_data_type_for_solr_field(
                solr_field_key
            )
            facet_range = self.make_facet_dict_from_solr_field(
                solr_field_key,
                'oc-api:range-facet',
                'Ranges',
                range_data_type=data_type,
            )
            facet_range['oc-api:has-range-options'] = self.add_range_options_list(
                param_key,
                match_old_value,
                data_type,
                True,
                options_tuples,
                round_digits=None,
            )

            facet_ranges.append(facet_range)

        return facet_ranges



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

            # Look up the client's request parameter and request
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
                range_value_count_list,
                no_zeros=(data_type in ['xsd:date',]),
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
