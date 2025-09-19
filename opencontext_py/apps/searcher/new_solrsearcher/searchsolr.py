import logging
from datetime import datetime
from django.conf import settings

from opencontext_py.libs.solrclient import SolrClient
from opencontext_py.apps.indexer import solrdocument_new_schema as SolrDoc

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities
from opencontext_py.apps.searcher.new_solrsearcher import querymaker
from opencontext_py.apps.searcher.new_solrsearcher import ranges
from opencontext_py.apps.searcher.new_solrsearcher.sorting import SortingOptions


logger = logging.getLogger(__name__)


class SearchSolr():

    def __init__(self):
        self.solr = None
        self.solr_connect()
        self.solr_response = None
        self.json_ld = None
        # Use the copy() method to make sure we don't mutate the configs!
        self.init_facet_fields = configs.DEFAULT_FACET_FIELDS.copy()
        self.init_stats_fields = configs.ALL_TYPES_STATS_FIELDS.copy()
        self.rows = configs.SOLR_DEFAULT_ROW_COUNT
        self.start = 0
        self.max_rows = configs.SOLR_MAX_RESULT_ROW_COUNT
        self.prequery_stats = []
        self.item_type_limit = None  # limit searches to a specific item type
        self.do_context_paths = True  # make sure context paths are in the query
        self.is_bot = False
        self.do_bot_limit = False
        self.solr_debug_query = 'false'
        self.solr_stats_query = 'true'
        # This is for storing slugs that have pre-defined facet configs.
        self.slugs_for_config_facets = []
        # Dictionary of keyed by facet fields that are derived from the
        # raw request paths provided by clients. This dictionary makes
        # it easier to generate links for different facet options.
        self.facet_fields_to_client_request = {}
        # Limit number of project facets (because we don't want
        # too many collections returned as facet counts)
        self.limit_project_facets = False

    def solr_connect(self):
        """ Connects to solr """
        if self.solr is not None:
            # We are already connected, so skip connecting.
            return None

        if configs.USE_TEST_SOLR_CONNECTION:
            # Connect to the testing solr server
            self.solr = SolrClient(use_test_solr=True).solr
        else:
            # Connect to the default solr server
            self.solr = SolrClient().solr


    def _check_add_projects_facet(self, request_dict):
        """Checks to see if we should add the projects facet query"""
        add_projects_facet = False
        if request_dict.get('path', ''):
            add_projects_facet = True
        if request_dict.get('type'):
            add_projects_facet = True
        if request_dict.get('prop'):
            add_projects_facet = True
        if request_dict.get('q'):
            add_projects_facet = True
        if request_dict.get('project-map'):
            add_projects_facet = True
        if len(request_dict) > 2:
            add_projects_facet = True
        if SolrDoc.ROOT_PROJECT_SOLR in self.init_facet_fields:
            # No need to add it again!
            add_projects_facet = False
        return add_projects_facet


    def add_initial_facet_fields(self, request_dict):
        """Adds to initial facet field list based on request_dict"""
        add_projects_facet = self._check_add_projects_facet(
            request_dict
        )
        if add_projects_facet:
            self.limit_project_facets = True
            self.init_facet_fields.append(
                SolrDoc.ROOT_PROJECT_SOLR
            )
        if 'proj' in request_dict:
            self.limit_project_facets = True
            self.init_facet_fields.append(
                SolrDoc.ROOT_PREDICATE_SOLR
            )
        requested_facets = utilities.get_request_param_value(
            request_dict,
            param='facets',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if requested_facets:
            facets = requested_facets.split(configs.MULTIVALUE_ATTRIB_CLIENT_DELIM)
            self.init_facet_fields += facets
            

    def _remove_unwanted_facet_query(self, request_dict, query):
        """Removes unwanted (expensive, time consuming)
        facet queries
        """
        add_projects_facet = self._check_add_projects_facet(
            request_dict
        )
        if add_projects_facet:
            # Don't change anything, the request specifically
            # needs a projects facet
            return query
        raw_client_responses = utilities.get_request_param_value(
            request_dict,
            param='response',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if not raw_client_responses:
            # Don't change anything, the client hasn't specified
            # response types
            return query

        # The client specified some response types, which can be
        # comma separated for multiple responses. We don't validate
        # these because if we don't recognize a client specified
        # response type, nothing will happen.
        if ',' in raw_client_responses:
            act_responses = raw_client_responses.split(',')
        else:
            act_responses = [raw_client_responses]
        # Now check to see if the set of client requested response
        # types includes response types that require facet queries
        if set(act_responses).intersection(
            set(configs.RESPONSE_TYPES_WITH_FACET_QUERIES)):
            # The client asked for a response type that requires
            # facet queries, so do NOT remove them from the query dict
            return query
        # OK now remove the facet related keys
        print('Ask Solr to skip facet counts')
        facet_keys = [
            'facet.field',
            'facet.pivot',
        ]
        for key in facet_keys:
            if key not in query:
                continue
            # Remove this key
            query.pop(key)
        # Explicitly ask solr to NOT do faceting
        query['facet'] = 'false'
        return query


    def _associate_facet_field_with_client_request(
        self,
        param,
        raw_path,
        query_dict
    ):
        """Associates a facet field with a client request."""

        # NOTE: Because there's some complex logic in how we determine
        # facet fields from a client request, it is useful to store
        # the associations for later use. The main later use will
        # be the creation of links for different facet search options
        # when we process a raw solr response into a result that we
        # give to a client. This function stores the associations
        # between solr facet fields and the URL parameters and values
        # made by the requesting client.

        if not query_dict:
            return None
        for key in ['prequery-stats', 'facet.field']:
            for path_facet_field in query_dict.get(key, []):
                # Associate the facet field for this raw-path with the
                # client request parameter and the raw path from the
                # client. This is also done with solr fields in the
                # prequery-stats key, so as to associate range facets
                # with raw paths. The association is between a
                # solr_field and a param, raw_path tuple.
                self.facet_fields_to_client_request[path_facet_field] = (
                    param, raw_path
                )

    
    def _exclude_collections_from_projects(self, query):
        """Excludes collection items from project searches"""
        # query['fq'] = f'obj_all___oc_gen_category___pred_id:{configs.PROJECT_COLLECTIONS_DATA_PUB_SOLR_SLUG}_*'
        query['fq'] = f'-obj_all___oc_gen_category___pred_id:{configs.PROJECT_COLLECTIONS_SOLR_SLUG}_*'
        return query

    
    def _add_project_index_query_terms(self, query):
        """Adds project index query terms"""
        # Get facets for all the object category (item_class) entities
        query['facet.field'] = [configs.SITEMAP_FACET_FIELD]
        query[f'f.{configs.SITEMAP_FACET_FIELD}.facet.limit'] = -1
        query[f'f.{configs.SITEMAP_FACET_FIELD}.facet.mincount'] = 2
        # query[f'f.{configs.SITEMAP_FACET_FIELD}.facet.sort'] = 'index'
        return query

    def _add_project_summary_query_terms(self, query):
        """Adds project summary query terms"""
        # Get facets for all the object category (item_class) entities
        query['facet.field'].append('obj_all___project_id')
        query['facet.pivot'] = [
            'item_type,obj_all___oc_gen_category___pred_id'
        ]
        return query

    def _add_project_map_query_terms(self, query):
        """Adds project map query terms"""
        # Get facets for all the object category (item_class) entities
        if 'obj_all___project_id' not in query['facet.field']:
            query['facet.field'].append('obj_all___project_id')
        query['facet.limit'] = -1
        return query

    def _add_keyword_query_terms(self, query):
        """Adds facet query terms to get keywords"""
        # Get facets for all the object category (item_class) entities
        if not query.get('facet.field'):
            query['facet.field'] = []
        query['facet.field'].append('keywords')
        query[f'f.keywords.facet.limit'] = configs.KEYWORDS_FACET_LIMIT
        query[f'f.keywords.facet.mincount'] = configs.KEYWORDS_FACET_MINCOUNT
        # query[f'f.{configs.SITEMAP_FACET_FIELD}.facet.sort'] = 'index'
        return query

    def compose_query(self, request_dict):
        """Composes a solr query by translating a client request_dict

        :param dict request_dict: The dictionary of keyed by client
        request parameters and their request parameter values.
        """
        query = {}
        query['facet'] = 'true'
        query['facet.mincount'] = 1
        query['rows'] = self.rows
        query['start'] = self.start
        query['debugQuery'] = self.solr_debug_query
        query['fq'] = []
        # Starts with an initial facet field list
        query['facet.field'] = self.init_facet_fields

        # Default facet value sorting
        query['facet.sort'] = configs.FACET_SORT_DEFAULT

        query['facet.range'] = []
        query['stats'] = self.solr_stats_query
        # Starts with an initial stats field list
        query['stats.field'] = self.init_stats_fields

        # -------------------------------------------------------------
        # SORTING
        # Set solr sorting, either to a default or by translating the
        # client request_dict.
        # -------------------------------------------------------------
        sort_opts = SortingOptions()
        # This method has unit tests.
        query['sort'] = sort_opts.make_solr_sort_param_from_request_dict(
            request_dict
        )


        # -------------------------------------------------------------
        # FACET OPTION SORTING
        # Set solr sorting, either to a default or by translating the
        # client request_dict.
        # -------------------------------------------------------------
        facet_sort = utilities.get_request_param_value(
            request_dict,
            param='fsort',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if facet_sort == 'index':
            # we want to sort by the index (the terms in the facet options)
            query['facet.sort'] = 'index'


        # -------------------------------------------------------------
        # FULLTEXT (Keyword)
        # Set solr full text query and highlighting
        # -------------------------------------------------------------
        query['q'] = '*:*'  # default search for all
        raw_fulltext_search = utilities.get_request_param_value(
            request_dict,
            param='q',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_fulltext_search:
            # Client requested a fulltext search. First prepare a list
            # of solr escaped and quoted terms.
            #
            # This method has unit tests.
            escaped_terms, string_op = utilities.prep_string_search_term_list(
                raw_fulltext_search
            )
            grouped_terms = [f'(text:{term})' for term in escaped_terms]
            solr_fulltext = f' {string_op} '.join(grouped_terms)
            query['q.op'] = 'AND'
            print(f'solr escaped fulltext: {solr_fulltext}')
            query['q'] = solr_fulltext
            query['hl'] = 'true'  # search term highlighting
            query['hl.fl'] = 'text' # highlight the text field
            query['hl.fragsize'] = 200
            query['hl.simple.pre'] = configs.QUERY_SNIPPET_HIGHLIGHT_TAG_PRE
            query['hl.simple.post'] = configs.QUERY_SNIPPET_HIGHLIGHT_TAG_POST
            # query['hl.q'] = f'text: {solr_fulltext}'

        # -------------------------------------------------------------
        # START and ROWS (Paging through results)
        # Set the pointer to a position in the solr result list, and
        # the number of rows to return from a solr search.
        # -------------------------------------------------------------
        start_pos = utilities.get_request_param_value(
            request_dict,
            param='start',
            default=None,
            as_list=False,
            solr_escape=False,
            require_int=True,
        )
        if start_pos:
            # Client has requested a valid, non-default start position
            # for the solr results.
            if start_pos < 0:
                start_pos = 0
            query['start'] = start_pos

        # ------------------------------------------------------------
        # The cursorMark param cannot be used with the start param
        # start must be absent or start=0 to allow a cursorMark.
        # ------------------------------------------------------------
        if query.get('start', 0) == 0:
            # We can set a curser param.
            cursor_val = utilities.get_request_param_value(
                request_dict,
                param='cursorMark',
                default='*',
                as_list=False,
                solr_escape=False,
            )
            query['cursorMark'] = cursor_val

        if query.get('cursorMark', '*') != '*':
            # We have a non-default cursor mark specified, so do
            # NOT pass on a start parameter. We can use only one or the
            # other.
            query.pop('start', None)

        rows = utilities.get_request_param_value(
            request_dict,
            param='rows',
            default=None,
            as_list=False,
            solr_escape=False,
            require_int=True,
        )
        if rows:
            # Client has requested a non-default number of number
            # search result rows.
            if rows > self.max_rows:
                rows = self.max_rows
            elif rows < 0:
                rows = 0
            query['rows'] = rows


        # -------------------------------------------------------------
        # SIMPLE, GENERAL METADATA RELATED FUNCTIONS
        # -------------------------------------------------------------
        for url_param, filter_query in configs.REL_MEDIA_EXISTS:
            if not url_param in request_dict:
                # This url_param is not part of the client request
                # so don't add a solr filter query
                continue
            # Add this related media filter to the main query.
            query = utilities.combine_query_dict_lists(
                part_query_dict={'fq': [filter_query]},
                main_query_dict=query,
            )

        # Params: uuid, updated published processed here.
        for url_param, solr_field in configs.SIMPLE_METADATA:
            raw_value = utilities.get_request_param_value(
                request_dict,
                param=url_param,
                default=None,
                as_list=False,
                solr_escape=False,
            )
            if not raw_value:
                # Skip, there's nothing to query for this
                # url_param.
                continue
            query_dict = querymaker.get_simple_metadata_query_dict(
                raw_value,
                solr_field
            )
            # Now add this simple metadata to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )


        # -------------------------------------------------------------
        # ID RELATED Solr Search Params
        # -------------------------------------------------------------
        raw_identifier = utilities.get_request_param_value(
            request_dict,
            param='id',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_identifier:
            query_dict = querymaker.get_identifier_query_dict(raw_identifier)
            # Now add results of this identifier to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )

        raw_object_uri = utilities.get_request_param_value(
            request_dict,
            param='obj',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_object_uri:
            query_dict = querymaker.get_object_uri_query_dict(raw_object_uri)
            # Now add results of this object_uri to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )

        raw_person_id = utilities.get_request_param_value(
            request_dict,
            param='pers',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_person_id:
            print(f'do a person query {raw_person_id}')
            query_dict = querymaker.get_person_query_dict(raw_person_id)
            # Now add results of this person to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )

        # -------------------------------------------------------------
        # Item Type
        # -------------------------------------------------------------
        raw_item_type = utilities.get_request_param_value(
            request_dict,
            param='type',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_item_type:
            query_dict = querymaker.get_item_type_query_dict(raw_item_type)
            # Now add results of this raw_item_type to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )


        do_lr_geotile_facet = True
        do_lr_chronotile_facet = True
        # -------------------------------------------------------------
        # GEO-SPACE AND TIME
        # -------------------------------------------------------------
        raw_disc_bbox = utilities.get_request_param_value(
            request_dict,
            param='bbox',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_disc_bbox:
            do_lr_geotile_facet = False  # Spatial constraint, so do high res geotile
            query_dict = querymaker.get_discovery_bbox_query_dict(
                raw_disc_bbox
            )
            # Now add results of bounding box to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )

        raw_disc_geo = utilities.get_request_param_value(
            request_dict,
            param='allevent-geotile',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_disc_geo:
            do_lr_geotile_facet = False  # Spatial constraint, so do high res geotile
            # Do the actual query using the high resolution parameter.
            query_dict = querymaker.get_discovery_geotile_query_dict(
                raw_disc_geo, low_res=False
            )
            # Now add results of disc-geotile to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )

        raw_chrono_tile = utilities.get_request_param_value(
            request_dict,
            param='allevent-chronotile',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_chrono_tile:
            # we have chronological limits, so look at high resolution chronotiles
            do_lr_chronotile_facet = False
            query_dict = querymaker.get_form_use_life_chronotile_query_dict(
                raw_chrono_tile
            )
            # Now add results of this form_use_life_chronotile
            # to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )

        # One or both of the form use life date limits can be None.
        all_start = utilities.get_request_param_value(
            request_dict,
            param='allevent-start',
            default=None,
            as_list=False,
            solr_escape=False,
            require_float=True,
        )
        all_stop=utilities.get_request_param_value(
            request_dict,
            param='allevent-stop',
            default=None,
            as_list=False,
            solr_escape=False,
            require_float=True,
        )
        query_dict = querymaker.get_all_event_chrono_span_query_dict(
            all_start=all_start,
            all_stop=all_stop,
        )
        if all_start or all_stop:
            # we have chronological limits, so look at high resolution chronotiles
            do_lr_chronotile_facet = False
        # Now add results of this raw_item_type to the over-all query.
        query = utilities.combine_query_dict_lists(
            part_query_dict=query_dict,
            main_query_dict=query,
        )


        # -------------------------------------------------------------
        # Spatial Context
        # -------------------------------------------------------------
        if request_dict.get('path') and self.do_context_paths:
            query_dict = querymaker.get_spatial_context_query_dict(
                spatial_context=request_dict.get('path')
            )
            if query_dict:
                context_deep = utilities.get_path_depth(
                    path=request_dict.get('path', ''),
                    delimiter=configs.REQUEST_CONTEXT_HIERARCHY_DELIM
                )
                if context_deep >= configs.MIN_CONTEXT_DEPTH_FOR_HIGH_RES_GEOTILES:
                    do_lr_geotile_facet = False
                    do_lr_chronotile_facet = False

                # Associate the facet fields with the client request param
                # and param value.
                self._associate_facet_field_with_client_request(
                    param='path',
                    raw_path=request_dict['path'],
                    query_dict=query_dict
                )
                # Remove the default Root Solr facet field if it is there.
                query['facet.field'] = utilities.safe_remove_item_from_list(
                    SolrDoc.ROOT_CONTEXT_SOLR,
                    query['facet.field'].copy()
                )
                query = utilities.combine_query_dict_lists(
                    part_query_dict=query_dict,
                    main_query_dict=query,
                )


        # -------------------------------------------------------------
        # All Hierarchic Parameters (Projects, Properties, Dublin-Core,
        # etc.). The following iterates through a loop of tuples that
        # configure how different GET parameters get processed by the
        # function:
        #
        # querymaker.get_general_hierarchic_paths_query_dict
        #
        # Note how the last element in each tuple "param_args" is used
        # for key-word arguments in the function.
        # -------------------------------------------------------------
        for param, remove_field, param_args in configs.HIERARCHY_PARAM_TO_SOLR:
            raw_paths = utilities.get_request_param_value(
                request_dict,
                param=param,
                default=None,
                as_list=True,
                solr_escape=False,
            )
            if not raw_paths:
                # We don't have a request using this param, so skip
                continue
            if not isinstance(raw_paths, list):
                raw_paths = [raw_paths]
            if param == 'proj':
                # One ore more projects are selected, so do high
                # resolution map tiles.
                do_lr_geotile_facet = False
                do_lr_chronotile_facet = False
            if param == 'cat' and raw_paths == [configs.REQUEST_ISAMPLES_ATTRIBUTES]:
                # Replace the raw-paths with the category slugs relevant to 
                # iSamples
                raw_paths = [configs.ISAMPLES_DEFAULT_CLASS_SLUG_RAW_PATH]
            for raw_path in raw_paths:
                query_dict = querymaker.get_general_hierarchic_paths_query_dict(
                    raw_path=raw_path, **param_args
                )
                if not query_dict:
                    # We don't have a response for this query, so continue
                    # for now until we come up with error handling.
                    continue
                
                # Make sure we limit the number of project facets that we return
                if param == 'proj' and self.limit_project_facets:
                    for ff in query_dict.get('facet.field', []):
                        # Limit the number of project facets we display
                        query[f'f.{ff}.facet.limit'] = 50

                # Associate the facet fields with the client request param
                # and param value.
                self._associate_facet_field_with_client_request(
                    param=param,
                    raw_path=raw_path,
                    query_dict=query_dict
                )
                if remove_field:
                    # Remove a default facet field if it is there.
                    query['facet.field'] = utilities.safe_remove_item_from_list(
                        remove_field,
                        query['facet.field'].copy()
                    )

                if param == 'cat':
                    for cat_slug_key, cat_facet_fields_tups in configs.ITEM_CAT_FACET_FIELDS_SOLR.items():
                        if cat_slug_key not in raw_path:
                            continue
                        # Keep track of the cats that have special facets configs.
                        self.slugs_for_config_facets.append(cat_slug_key)
                        # Add additional facet fields configured for use with a
                        # given category. This is especially useful for zooarchaeology where
                        # some useful standard fields may be "buried" too deep in a hierarchy
                        # to be easily accessible to users.
                        for cat_raw_path, cat_facet_field in cat_facet_fields_tups:
                            print(f'check add {cat_facet_field}')
                            if cat_facet_field in query['facet.field']:
                                continue
                            query['facet.field'].append(cat_facet_field)


                # Now add results of this raw_path to the over-all query.
                query = utilities.combine_query_dict_lists(
                    part_query_dict=query_dict,
                    main_query_dict=query,
                )


        # -------------------------------------------------------------
        # GEOSPACE and Chronology tiles.
        # -------------------------------------------------------------
        # Add the geo-tile facet field.
        geodeep = utilities.get_request_param_value(
            request_dict,
            param='geodeep',
            default=0,
            as_list=False,
            solr_escape=False,
            require_int=True,
        )
        if not do_lr_geotile_facet or geodeep > SolrDoc.LOW_RESOLUTION_GEOTILE_LENGTH:
            geo_tile_facet_field = f'{configs.ROOT_EVENT_CLASS}___geo_tile'
        else:
            geo_tile_facet_field = f'{configs.ROOT_EVENT_CLASS}___lr_geo_tile'
        query['facet.field'].append(geo_tile_facet_field)

        # Add the chrono-tile facet field.
        chronodeep = utilities.get_request_param_value(
            request_dict,
            param='chronodeep',
            default=0,
            as_list=False,
            solr_escape=False,
            require_int=True,
        )
        if not do_lr_chronotile_facet or (chronodeep > SolrDoc.LOW_RESOLUTION_CHRONOTILE_DROP_LAST):
            chrono_tile_facet_field = f'{configs.ROOT_EVENT_CLASS}___chrono_tile'
        else:
            chrono_tile_facet_field = f'{configs.ROOT_EVENT_CLASS}___lr_chrono_tile'
        query['facet.field'].append(chrono_tile_facet_field)


        # -------------------------------------------------------------
        # Special purpose queries
        # -------------------------------------------------------------
        if request_dict.get('proj-index'):
            # we're making a project index query
            query = self._exclude_collections_from_projects(query)
            query = self._add_project_index_query_terms(query)
        if request_dict.get('proj-summary'):
            # we're making a project summary query.
            query = self._add_project_summary_query_terms(query)
        if request_dict.get('project-map'):
            # we're making a project summary query.
            query = self._exclude_collections_from_projects(query)
            query = self._add_project_map_query_terms(query)
        if request_dict.get('keywords'):
            # we want to get common keyword facets for this query
            query = self._add_keyword_query_terms(query)

        dinaa_linked = utilities.get_request_param_value(
            request_dict,
            param='linked',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if dinaa_linked and 'dinaa' in dinaa_linked:
            # We're querying for DINAA record with cross references with other
            # resources outside Open Context
            # First, remove this filter if present. It will conflict with
            # query terms we have set up for DINAA.
            if 'ld___pred_id:dc_terms_is_referenced_by___*' in query['fq']:
                query['fq'].remove('ld___pred_id:dc_terms_is_referenced_by___*')
            query_dict = querymaker.get_linked_dinaa_query_dict()
            # Now combine the DINAA query to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )

        raw_trinomial = utilities.get_request_param_value(
            request_dict,
            param='trinomial',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if raw_trinomial:
            # We're querying for Trinomial stings in DINAA records
            query_dict = querymaker.get_trinomial_query_dict(raw_trinomial)
            # Now combine the DINAA query to the over-all query.
            query = utilities.combine_query_dict_lists(
                part_query_dict=query_dict,
                main_query_dict=query,
            )


        # Explicitly remove the facet query for client requested
        # response types that don't need it.
        query = self._remove_unwanted_facet_query(request_dict, query)

        return query


    def update_query_with_stats_prequery(self, query):
        """Updates the main query dict if stats fields
           need facet ranges defined. If so, sends off an
           initial pre-query to solr.
        """
        # NOTE: This needs to happen at the end, after
        # we have already defined a bunch of solr
        if not 'prequery-stats' in query:
            return query
        prestats_fields = query.get('prequery-stats', [])
        query.pop('prequery-stats')
        if not len(prestats_fields):
            return query
        self.solr_connect()
        stats_query = ranges.compose_stats_query(
            fq_list=query['fq'],
            stats_fields_list=prestats_fields,
            q=query['q']
        )
        stats_q_dict = ranges.stats_ranges_query_dict_via_solr(
            stats_query=stats_query,
            solr=self.solr
        )
        query = utilities.combine_query_dict_lists(
            part_query_dict=stats_q_dict,
            main_query_dict=query,
        )
        return query

    def compose_sitemap_query(self):
        """Makes a query specialized knowing what projects can be
        included in a site map
        """
        query = {}
        query['facet'] = 'true'
        query['facet.mincount'] = 1
        query['rows'] = self.rows
        query['start'] = self.start
        query['fq'] = []
        query['q'] = '*:*'  # default search for all
        # Starts with an initial facet field list
        query['facet.field'] = [
            configs.SITEMAP_FACET_FIELD
        ]
        return query


    def _set_solr_field_facet_limits(self, query):
        """ Sets facet limits on configured facet fields"""
        for facet_field, limit in configs.SOLR_FIELDS_FACET_LIMITS:
            if not facet_field in query.get('facet.field', []):
                # We could not find the facet field in the
                # query facet fields, so skip.
                continue
            limit_key = f'f.{facet_field}.facet.limit'
            query[limit_key] = limit
        return query


    def finish_query(self, query):
        """ Check solr query and put convenient format """
        assert 'q' in query
        query = self.update_query_with_stats_prequery(query)
        query = self._set_solr_field_facet_limits(query)
        query['wt'] = 'json'
        query['cache'] = 'true'
        return query


    def query_solr(self, query):
        """ Connects to solr and runs a query"""
        query = self.finish_query(query)
        self.solr_connect()
        try:
            results = self.solr.search(**query)
            self.solr_response = results.raw_response
        except Exception as error:
            logger.error(
                f'[{datetime.now().strftime("%x %X ")}'
                f'{settings.TIME_ZONE}] Error: '
                f'{str(error)} => Query: {query}'
            )
            if settings.DEBUG:
                # Print the query problem if in debug mode
                print(query)
                print(str(error))
        return self.solr_response
