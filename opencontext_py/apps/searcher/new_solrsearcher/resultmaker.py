import copy
import logging
import time

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.isoyears import ISOyears

from opencontext_py.apps.contexts.models import SearchContext


# Imports directly related to Solr search and response prep.
from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.solr_agg_via_pandas import make_cache_df_of_solr_facets
from opencontext_py.apps.searcher.new_solrsearcher.result_facets_chronology import ResultFacetsChronology
from opencontext_py.apps.searcher.new_solrsearcher.result_facets_chronology_from_df import ResultFacetsChronologyFromDF
from opencontext_py.apps.searcher.new_solrsearcher.result_facets_geo import ResultFacetsGeo
from opencontext_py.apps.searcher.new_solrsearcher.result_facets_geo_from_df import ResultFacetsGeoFromDF
from opencontext_py.apps.searcher.new_solrsearcher.result_facets_nonpath import ResultFacetsNonPath
from opencontext_py.apps.searcher.new_solrsearcher.result_facets_standard import ResultFacetsStandard
from opencontext_py.apps.searcher.new_solrsearcher import project_overlays
from opencontext_py.apps.searcher.new_solrsearcher.result_records import (
    get_record_uuids_from_solr,
    get_record_uris_from_solr,
    ResultRecords,
)
from opencontext_py.apps.searcher.new_solrsearcher.searchfilters import SearchFilters
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks
from opencontext_py.apps.searcher.new_solrsearcher.sorting import SortingOptions
from opencontext_py.apps.searcher.new_solrsearcher import utilities


logger = logging.getLogger(__name__)


class ResultMaker():

    def __init__(
        self,
        request_dict=None,
        facet_fields_to_client_request={},
        slugs_for_config_facets=[],
        base_search_url='/search/'
    ):
        self.result = LastUpdatedOrderedDict()
        self.request_dict = copy.deepcopy(request_dict)
        self.base_search_url = base_search_url
        self.id = None
        # The current filters URL is used to validate if a filter
        # option is actual for a new search.
        self.current_filters_url = self._set_current_filters_url()
        # Dictionary of keyed by facet fields that are derived from the
        # raw request paths provided by clients. This dictionary makes
        # it easier to generate links for different facet options.
        self.facet_fields_to_client_request = copy.deepcopy(facet_fields_to_client_request)
        # Keep track of the slugs that have pre-defined facets configs.
        self.slugs_for_config_facets = copy.deepcopy(slugs_for_config_facets)
        # Set the act_response types to the default. The act_response
        # lists the types of response objects to provide back to the client.
        self.act_responses = configs.RESPONSE_DEFAULT_TYPES.copy()
        # Override the default act_response list if the client asked.
        self._set_client_response_types()
        # These other attributes are record some state that needs to
        # be widely shared in a number of methods.
        self.total_found = None
        self.start = None
        self.rows = None
        self.cursor = None # for iterating through large results
        self.min_date = None
        self.max_date = None
        self.sitemap_facets = False
        self.facets_df = None

    def _set_client_response_types(self):
        """Sets the response type if specified by the client"""
        raw_client_responses = utilities.get_request_param_value(
            self.request_dict,
            param='response',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        if not raw_client_responses:
            # The client did not specify the response types. So
            # don't change the default setting.
            return None

        # The client specified some response types, which can be
        # comma seperated for multiple responses. We don't validate
        # these because if we don't recognize a client specified
        # response type, nothing will happen.
        if ',' in raw_client_responses:
            self.act_responses = raw_client_responses.split(',')
        else:
            self.act_responses = [raw_client_responses]



    def _set_current_filters_url(self):
        """Make a URL for the current filters, removed of all paging
        and other irrelevant parameters.
        """
        # NOTE: we use the self.current_filters_url to determine if
        # a given new filter url (say for a facet) is new (meaning if
        # it actually changes search/query filters). If it is not new,
        # then the result should not present the new filter url as
        # a search option.
        #
        # NOTE: Since we generate search urls programatically via the
        # SearchLinks class, we have a predictable order of parameters
        # and values. This makes it possible to match url strings.
        sl = SearchLinks(
            request_dict=copy.deepcopy(self.request_dict),
            base_search_url=self.base_search_url
        )
        # Remove non search related params.
        sl.remove_non_query_params()
        urls = sl.make_urls_from_request_dict()
        self.current_filters_url = urls['html']
        return self.current_filters_url


    # -----------------------------------------------------------------
    # Methods to make geneal response metadata
    # -----------------------------------------------------------------
    def make_response_id(self):
        """Makes the ID for the response JSON-LD"""
        # NOTE: The order of the URL parameters will be predicable
        # to help normalize search IDs.
        if self.id:
            return self.id
        sl = SearchLinks(
            request_dict=self.request_dict,
            base_search_url=self.base_search_url
        )
        urls = sl.make_urls_from_request_dict()
        self.id = urls['html']
        return self.id


    def add_publishing_datetime_metadata(self, solr_json, default_to_current=True):
        """Adds publishing modified and created metadata to the response JSON-LD"""
        # NOTE: Solr already defaults to representing time in
        # ISO 8601, so we're just pulling the appropriate time
        # info from the solr_json to metadata fields in our response
        # JSON-LD.
        meta_configs = [
            (
                # Last modified.
                'dcmi:modified',
                (configs.STATS_FIELDS_PATH_KEYS + ['updated', 'max',]),
            ),
            (
                # Last published
                'dcmi:created',
                (configs.STATS_FIELDS_PATH_KEYS + ['published', 'max',]),
            ),
            (
                # Earliest published
                'oai-pmh:earliestDatestamp',
                (configs.STATS_FIELDS_PATH_KEYS + ['published', 'min',]),
            ),
            (
                # Least interesting
                'oc-api:descriptiveness-min',
                (configs.STATS_FIELDS_PATH_KEYS + ['interest_score', 'min',]),
            ),
            (
                # Most interesting
                'oc-api:descriptiveness-max',
                (configs.STATS_FIELDS_PATH_KEYS + ['interest_score', 'max',]),
            ),
        ]
        for json_ld_key, path_keys_list in meta_configs:
            act_time = utilities.get_dict_path_value(
                path_keys_list,
                solr_json
            )
            if not act_time:
                # We could not find the time object.
                if not default_to_current:
                    # Skip, since we're not to default to
                    # the current time.
                    continue
                # Add ISO 8601 current time for the missing value.
                act_time = time.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
            self.result[json_ld_key] = act_time


    def add_human_remains_flag(self, solr_json,):
        """Adds flagging to indicate human remains in results JSON-LD"""
        # NOTE: Solr already defaults to representing time in
        # ISO 8601, so we're just pulling the appropriate time
        # info from the solr_json to metadata fields in our response
        # JSON-LD.
        meta_configs = [
            (
                # Last modified.
                'oc-api:human-remains-flagged',
                (configs.FACETS_SOLR_ROOT_PATH_KEYS + ['human_remains',]),
            ),
        ]
        for json_ld_key, path_keys_list in meta_configs:
            flags_counts_list = utilities.get_dict_path_value(
                path_keys_list,
                solr_json
            )
            if not flags_counts_list:
                continue
            flag_tups = utilities.get_facet_value_count_tuples(flags_counts_list)
            for bool_str, count in flag_tups:
                if bool_str != 'true' or count < 1:
                    continue
                self.result[json_ld_key] = True


    def add_all_events_date_range(self, solr_json, iso_year_format=True):
        """Adds earliest and latest form-use-life dates"""
        meta_configs = [
            (
                # Earliest date items formed, used, or alive.
                'allevent-start',
                (
                    configs.STATS_FIELDS_PATH_KEYS + [
                        f'{configs.ROOT_EVENT_CLASS}___chrono_point_0___pdouble',
                        'min',
                    ]
                ),
            ),
            (
                # Latest date items formed, used, or alive
                'allevent-stop',
                (
                    configs.STATS_FIELDS_PATH_KEYS + [
                        f'{configs.ROOT_EVENT_CLASS}___chrono_point_1___pdouble',
                        'max',
                    ]
                )
            ),
        ]
        all_dates = []
        for json_ld_key, path_keys_list in meta_configs:
            act_date = utilities.get_dict_path_value(
                path_keys_list,
                solr_json
            )
            if act_date is None:
                # We don't have a date for this.
                continue
            all_dates.append(act_date)
            if iso_year_format and act_date is not None:
                act_date = ISOyears().make_iso_from_float(act_date)
            self.result[json_ld_key] = act_date

        if not len(all_dates):
            # We don't have dates, so skip out.
            return None
        # Set the query result minimum and maximum date range.
        self.min_date = min(all_dates)
        self.max_date = max(all_dates)


    def _add_geo_chrono_counts_json(self, solr_json):
        meta_configs = [
            (
                # Facets with counts of geo-spatial features per record (document)
                "oc-api:all-geospatial-feature-counts",
                (
                    configs.FACETS_SOLR_ROOT_PATH_KEYS + [
                        f'{configs.ROOT_EVENT_CLASS}___geo_count',
                    ]
                ),
            ),
            (
                # Facets with counts of chronological ranges per record (document)
                "oc-api:all-chronology-range-counts",
                (
                    configs.FACETS_SOLR_ROOT_PATH_KEYS + [
                        f'{configs.ROOT_EVENT_CLASS}___chrono_count',
                    ]
                )
            ),
        ]
        for result_key, facets_path in meta_configs:
            val_count_list = utilities.get_dict_path_value(
                facets_path,
                solr_json,
                default=[]
            )
            print(f'{result_key} from {facets_path} to {val_count_list}')
            if not val_count_list:
                continue
            val_tuples = utilities.get_facet_value_count_tuples(
                val_count_list
            )
            if not val_tuples:
                continue
            self.result[result_key] = []
            for num_feat, count in val_tuples:
                self.result[result_key].append(
                    {
                        'total_events_count': int(float(num_feat)),
                        'count': count,
                    }
                )
        return None


    def _add_geo_chrono_counts_from_json(self, solr_json):
        meta_configs = [
            (
                # Facets with counts of geo-spatial features per record (document)
                "oc-api:all-geospatial-feature-counts",
                (
                    configs.FACETS_SOLR_ROOT_PATH_KEYS + [
                        f'{configs.ROOT_EVENT_CLASS}___geo_count',
                    ]
                ),
            ),
            (
                # Facets with counts of chronological ranges per record (document)
                "oc-api:all-chronology-range-counts",
                (
                    configs.FACETS_SOLR_ROOT_PATH_KEYS + [
                        f'{configs.ROOT_EVENT_CLASS}___chrono_count',
                    ]
                )
            ),
        ]
        for result_key, facets_path in meta_configs:
            val_count_list = utilities.get_dict_path_value(
                facets_path,
                solr_json,
                default=[]
            )
            print(f'{result_key} from {facets_path} to {val_count_list}')
            if not val_count_list:
                continue
            val_tuples = utilities.get_facet_value_count_tuples(
                val_count_list
            )
            if not val_tuples:
                continue
            self.result[result_key] = []
            for num_feat, count in val_tuples:
                self.result[result_key].append(
                    {
                        'total_events_count': int(float(num_feat)),
                        'count': count,
                    }
                )
        return None


# from_facets_df
    def _add_geo_chrono_counts_from_facets_df(self):
        meta_configs = [
            (
                # Facets with counts of geo-spatial features per record (document)
                "oc-api:all-geospatial-feature-counts",
                f'{configs.ROOT_EVENT_CLASS}___geo_count',
            ),
            (
                # Facets with counts of chronological ranges per record (document)
                "oc-api:all-chronology-range-counts",
                f'{configs.ROOT_EVENT_CLASS}___chrono_count',
                
            ),
        ]
        for result_key, facet_key in meta_configs:
            index = self.facets_df['facet_field_key'] == facet_key
            df = self.facets_df[index].copy()
            if not len(df.index):
                continue
            self.result[result_key] = []
            for _, row in df.iterrows():
                num_feat = row['facet_value']
                count = row['facet_count']
                self.result[result_key].append(
                    {
                        'total_events_count': int(float(num_feat)),
                        'count': count,
                    }
                )
        return None


    def _facets_df_ok(self):
        """Checks if self.facets_df is OK"""
        if self.facets_df is None:
            return False
        if not len(self.facets_df.index):
            return False
        if not set(['facet_field_key', 'facet_value', 'facet_count']).issubset(set(self.facets_df.columns.tolist())):
            return False
        return True
    

    def add_geo_chrono_counts(self, solr_json):
        if self._facets_df_ok():
            # Use the new way via pandas
            return self._add_geo_chrono_counts_from_facets_df()
        else:
            # Use the old, slow way of processing the
            # solr_json.
            return self._add_geo_chrono_counts_from_json(solr_json)

    # -----------------------------------------------------------------
    # Methods to make links for paging + sorting navigation
    # -----------------------------------------------------------------
    def set_total_start_rows_attributes(self, solr_json):
        """Sets the total_found, start, rows_attributes"""

        if (self.total_found is not None
            and self.start is not None
            and self.rows is not None):
            # Skip, we already did this.
            return None

        # The total found (numFound) is in the solr response.
        total_found = utilities.get_dict_path_value(
            ['response', 'numFound'],
            solr_json
        )
        if total_found is not None:
            self.total_found = int(float(total_found))

        # Start and rows comes from the responseHeader
        start = utilities.get_dict_path_value(
            ['responseHeader', 'params', 'start'],
            solr_json
        )
        if start is not None:
            self.start = int(float(start))

        rows = utilities.get_dict_path_value(
            ['responseHeader', 'params', 'rows'],
            solr_json
        )
        if rows is not None:
            self.rows = int(float(rows))



    def _make_paging_links(self, start, rows, act_request_dict):
        """Makes links for paging for start rows from a request dict"""
        start = str(int(start))
        rows = str(rows)

        # Remove previously set parameters relating to paging.
        for param in ['start', 'rows']:
            if param in act_request_dict:
                act_request_dict.pop(param, None)

        sl = SearchLinks(
            request_dict=act_request_dict,
            base_search_url=self.base_search_url
        )
        sl.add_param_value('start', start)
        sl.add_param_value('rows', rows)
        urls = sl.make_urls_from_request_dict()
        return urls


    def add_cursor_json(self, solr_json):
        """ Adds JSON for paging through results using a cursor """
        self.result['totalResults'] = self.total_found
        self.result['itemsPerPage'] = self.rows
        # start off with a the request dict, then
        # remove 'start' and 'rows' parameters
        act_request_dict = copy.deepcopy(self.request_dict)
        if 'start' in act_request_dict:
            act_request_dict.pop('start', None)
        if 'rows' in act_request_dict:
            act_request_dict.pop('rows', None)
        if 'cursorMark' in act_request_dict:
            act_request_dict.pop('cursorMark', None)

        sl = SearchLinks(
            request_dict=act_request_dict,
            base_search_url=self.base_search_url
        )
        sl.add_param_value('rows', str(self.rows))
        sl.add_param_value('cursorMark', solr_json.get('nextCursorMark', '*'))
        urls = sl.make_urls_from_request_dict()
        self.result['next'] = urls['html']
        self.result['next-json'] = urls['json']
        if solr_json.get('nextCursorMark'):
            self.result['nextCursorMark'] = solr_json.get('nextCursorMark', '*')


    def add_paging_json(self, solr_json):
        """ Adds JSON for paging through results """

        self.set_total_start_rows_attributes(solr_json)

        if self.total_found and self.request_dict.get('cursorMark'):
            # We haven't specified a start index, but we do have enough
            # results where a cursor is a REALLY GOOD IDEA.
            print(f"Current cursor mark: {self.request_dict.get('cursorMark')}")
            return self.add_cursor_json(solr_json)

        if (self.total_found is None
            or self.start is None
            or self.rows is None):
            return None

        self.result['totalResults'] = self.total_found
        self.result['startIndex'] = self.start
        self.result['itemsPerPage'] = self.rows

        # start off with a the request dict, then
        # remove 'start' and 'rows' parameters
        act_request_dict = copy.deepcopy(self.request_dict)
        if 'start' in act_request_dict:
            act_request_dict.pop('start', None)
        if 'rows' in act_request_dict:
            act_request_dict.pop('rows', None)

        # add a first page link
        if self.start > 0:
            links = self._make_paging_links(
                start=0,
                rows=self.rows,
                act_request_dict=copy.deepcopy(act_request_dict)
            )
            self.result['first'] = links['html']
            self.result['first-json'] = links['json']
        if self.start >= self.rows:
            # add a previous page link
            links = self._make_paging_links(
                start=(self.start - self.rows),
                rows=self.rows,
                act_request_dict=copy.deepcopy(act_request_dict)
            )
            self.result['previous'] = links['html']
            self.result['previous-json'] = links['json']
        if self.start + self.rows >= self.total_found:
            # Don't add the next or last page.
            return None
        # add a next page link
        links = self._make_paging_links(
            start=(self.start + self.rows),
            rows=self.rows,
            act_request_dict=copy.deepcopy(act_request_dict)
        )
        self.result['next'] = links['html']
        self.result['next-json'] = links['json']
        num_pages = round(self.total_found / self.rows, 0)
        if num_pages * self.rows >= self.total_found:
            num_pages -= 1
        # add a last page link
        links = self._make_paging_links(
            start=(num_pages * self.rows),
            rows=self.rows,
            act_request_dict=copy.deepcopy(act_request_dict)
        )
        self.result['last'] = links['html']
        self.result['last-json'] = links['json']


    def add_sorting_json(self):
        """Adds JSON to describe result sorting """
        # Deep copy the request dict to not mutate it.
        act_request_dict = copy.deepcopy(self.request_dict)
        sort_opts = SortingOptions(base_search_url=self.base_search_url)
        sort_opts.make_current_sorting_list(act_request_dict)
        # Add objects describing the currently active sorting.
        self.result['oc-api:active-sorting'] = sort_opts.current_sorting
        act_request_dict = copy.deepcopy(self.request_dict)
        sort_links = sort_opts.make_sort_links_list(act_request_dict)
        # Add objects describing other sort options available.
        self.result['oc-api:has-sorting'] = sort_links


    # -----------------------------------------------------------------
    # Methods to make active filters with links to remove or broaden
    # -----------------------------------------------------------------
    def add_filters_json(self):
        """Adds JSON describing currently used query filters"""
        search_filters = SearchFilters(
            base_search_url=self.base_search_url,
            current_filters_url=self.current_filters_url,
        )
        filters = search_filters.add_filters_json(self.request_dict)
        if len(filters) > 0:
            self.result['oc-api:active-filters'] = filters


    def add_text_fields(self):
        """Adds general and project-specific property text query options """
        text_fields = []
        # first add a general key-word search option
        act_request_dict = copy.deepcopy(self.request_dict)
        sl = SearchLinks(
            request_dict=act_request_dict,
            base_search_url=self.base_search_url
        )
        # Remove non search related params.
        sl.remove_non_query_params()
        raw_fulltext_search = utilities.get_request_param_value(
            act_request_dict,
            param='q',
            default=None,
            as_list=False,
            solr_escape=False,
        )
        field = LastUpdatedOrderedDict()
        field['id'] = '#textfield-keyword-search'
        field['label'] = configs.FILTER_TEXT_SEARCH_TITLE
        field['oc-api:search-term'] = raw_fulltext_search
        if not raw_fulltext_search:
            # No keyword search found in request, so
            # make a template for keyword searches.
            sl.add_param_value(
                'q',
                configs.URL_TEXT_QUERY_TEMPLATE
            )
            urls = sl.make_urls_from_request_dict()
            field['oc-api:template'] = urls['html']
            field['oc-api:template-json'] = urls['json']
        else:
            # A keyword search was found, so make a
            # template for replacing it with another
            # keyword search.
            sl.replace_param_value(
                'q',
                match_old_value=raw_fulltext_search,
                new_value=configs.URL_TEXT_QUERY_TEMPLATE
            )
            urls = sl.make_urls_from_request_dict()
            field['oc-api:template'] = urls['html']
            field['oc-api:template-json'] = urls['json']
        text_fields.append(field)

        # NOTE This adds project specific property text
        # query options are listed in the search-filters

        # Add the text fields if they exist.
        if len(text_fields):
            self.result['oc-api:has-text-search'] = text_fields
        return text_fields


    # -----------------------------------------------------------------
    # Methods for adding search facets with links for filtering options
    # -----------------------------------------------------------------
    def _add_facet_dict_to_facets_list(
        self,
        facet_dict,
        facet_type_key="oc-api:has-facets",
    ):
        """Adds a facet_dict to the response facet list"""
        if not facet_dict:
            # Not a facet result to add.
            return None
        if not facet_type_key in self.result:
            # We don't have a facet list yet, so make it.
            self.result[facet_type_key] = []

        self.result[facet_type_key].append(facet_dict)


    def add_facet_ranges(self, solr_json):
        """Adds facets ranges for integer, double and date data types."""
        facets_standard = ResultFacetsStandard(
            request_dict=self.request_dict,
            current_filters_url=self.current_filters_url,
            facet_fields_to_client_request=self.facet_fields_to_client_request,
            base_search_url=self.base_search_url,
        )
        facet_ranges = facets_standard.get_facet_ranges_and_options(
            solr_json
        )
        facet_ranges += facets_standard.get_facet_boolean_options(solr_json)
        if not len(facet_ranges):
            # Skip out, we found no facets.
            return None
        if not "oc-api:has-range-facets" in self.result:
            # We don't have a facet list yet, so make it.
            self.result["oc-api:has-range-facets"] = []
        self.result["oc-api:has-range-facets"] += facet_ranges


    def _add_chronology_facets_from_json(self, solr_json):
        """Adds facets for chronological tiles"""
        facets_chrono = ResultFacetsChronology(
            request_dict=self.request_dict,
            current_filters_url=self.current_filters_url,
            base_search_url=self.base_search_url,
        )
        chrono_options = facets_chrono.make_chronology_facet_options(
            solr_json
        )
        if chrono_options is None or not len(chrono_options):
            # Skip out, we found no chronological options
            return None
        self.result["oc-api:has-event-time-ranges"] = chrono_options
    

    def _add_chronology_facets_df(self):
        """Adds facets for chronological tiles"""
        facets_chrono = ResultFacetsChronologyFromDF(
            request_dict=self.request_dict,
            current_filters_url=self.current_filters_url,
            base_search_url=self.base_search_url,
        )
        tiles_df = facets_chrono.get_valid_tiles_df(
            self.facets_df
        )
        chrono_options = facets_chrono.make_chronology_facet_options(
            tiles_df
        )
        if chrono_options is None or not len(chrono_options):
            # Skip out, we found no chronological options
            return None
        self.result["oc-api:has-event-time-ranges"] = chrono_options


    def add_chronology_facets(self, solr_json):
        """Adds facets for chronological tiles"""
        if self._facets_df_ok():
            # Use the new way via pandas
            self._add_chronology_facets_df()
        else:
            # Use the old, slow way of processing the
            # solr_json.
            self._add_chronology_facets_from_json(solr_json)


    def _add_geojson_features_to_result(self, geo_features_list):
        """Adds geojson features to the result """
        if not isinstance(geo_features_list, list):
            return None
        if not len(geo_features_list):
            return None
        self.result["type"] = "FeatureCollection"
        if not "features" in self.result:
            # We don't have a facet list yet, so make it.
            self.result["features"] = []
        self.result["features"] += geo_features_list


    def _add_geotile_facets_from_json(self, solr_json):
        """Adds facets for geographic tiles"""
        facets_geo = ResultFacetsGeo(
            request_dict=self.request_dict,
            current_filters_url=self.current_filters_url,
            base_search_url=self.base_search_url,
        )
        facets_geo.min_date = self.min_date
        facets_geo.max_date = self.max_date

        # Make the tile facet options
        geo_options = facets_geo.make_geotile_facet_options(
            solr_json
        )
        self._add_geojson_features_to_result(
            geo_options
        )


    def _add_geotile_facets_from_facets_df(self):
        """Adds facets for geographic tiles"""
        facets_geo = ResultFacetsGeoFromDF(
            request_dict=self.request_dict,
            current_filters_url=self.current_filters_url,
            base_search_url=self.base_search_url,
        )
        facets_geo.min_date = self.min_date
        facets_geo.max_date = self.max_date
        tiles_df = facets_geo.get_valid_tiles_df(self.facets_df)
        # Make the tile facet options
        geo_options = facets_geo.make_geotile_facet_options(
            tiles_df
        )
        self._add_geojson_features_to_result(
            geo_options
        )


    def add_geotile_facets(self, solr_json):
        """Adds facets for geographic tiles"""
        if self._facets_df_ok():
            # Use the new way via pandas
            self._add_geotile_facets_from_facets_df()
        else:
            # Use the old, slow way of processing the
            # solr_json.
            self._add_geotile_facets_from_json(solr_json)


    def add_geo_contained_in_facets(self, solr_json):
        """Adds facets for geo features that contain query results"""
        facets_geo = ResultFacetsGeo(
            request_dict=self.request_dict,
            current_filters_url=self.current_filters_url,
            base_search_url=self.base_search_url,
        )
        facets_geo.min_date = self.min_date
        facets_geo.max_date = self.max_date

        # Make the tile facet options
        geo_options = facets_geo.make_geo_contained_in_facet_options(
            solr_json
        )
        self._add_geojson_features_to_result(
            geo_options
        )


    def add_standard_facets(self, solr_json):
        """Adds facets for entities that maybe in hierarchies"""
        facets_standard = ResultFacetsStandard(
            request_dict=self.request_dict,
            current_filters_url=self.current_filters_url,
            facet_fields_to_client_request=copy.deepcopy(self.facet_fields_to_client_request),
            slugs_for_config_facets=copy.deepcopy(self.slugs_for_config_facets),
            base_search_url=self.base_search_url,
        )
        facets = facets_standard.get_facets_and_options(
            solr_json
        )
        if self.sitemap_facets or self.request_dict.get('proj-index'):
            # a project index also gets the same facets as the site map, as
            # these have a similar purpose.
            facets += facets_standard.get_sitemap_facets_and_options(
                solr_json
            )
        if not len(facets):
            # Skip out, we found no facets.
            return None
        if not "oc-api:has-facets" in self.result:
            # We don't have a facet list yet, so make it.
            self.result["oc-api:has-facets"] = []
        self.result["oc-api:has-facets"] += facets


    def add_item_type_facets(self, solr_json):
        """Adds facets that indicated records with links to media"""
        facets_nonpath = ResultFacetsNonPath(
            request_dict=self.request_dict,
            current_filters_url=self.current_filters_url,
            base_search_url=self.base_search_url,
        )
        item_type_facet_dict = facets_nonpath.make_item_type_facets(
            solr_json
        )
        self._add_facet_dict_to_facets_list(
            item_type_facet_dict,
            facet_type_key="oc-api:has-facets"
        )
        proj_summary = facets_nonpath.make_project_item_class_summary_facets(
            solr_json
        )
        if proj_summary:
            self.result['oc-api:project-item-classes'] = proj_summary


    def add_rel_media_facets(self, solr_json):
        """Adds facets that indicated records with links to media"""
        facets_nonpath = ResultFacetsNonPath(
            request_dict=self.request_dict,
            current_filters_url=self.current_filters_url,
            base_search_url=self.base_search_url,
        )
        rel_media_facet_dict = facets_nonpath.make_related_media_facets(
            solr_json
        )
        self._add_facet_dict_to_facets_list(
            rel_media_facet_dict,
            facet_type_key="oc-api:has-facets"
        )


    def add_keyword_facets(self, solr_json):
        """Adds facets that indicated records with links to media"""
        facets_nonpath = ResultFacetsNonPath(
            request_dict=self.request_dict,
            current_filters_url=self.current_filters_url,
            base_search_url=self.base_search_url,
        )
        keyword_facet_dict = facets_nonpath.make_keywords_facets(
            solr_json
        )
        self._add_facet_dict_to_facets_list(
            keyword_facet_dict,
            facet_type_key="oc-api:has-facets"
        )


    def add_uuid_records(self, solr_json):
        """Adds a simple list of uuids to the result"""
        uuids = get_record_uuids_from_solr(solr_json)
        if len(self.act_responses) == 1:
            self.result = uuids
        else:
            self.result['uuids'] = uuids


    def add_uri_records(self, solr_json):
        """Adds a simple list of uuids to the result"""
        uri_list = get_record_uris_from_solr(solr_json)
        if len(self.act_responses) == 1:
            self.result = uri_list
            return None
        if not len(uri_list):
            return None
        if not 'oc-api:has-results' in self.result:
            self.result['oc-api:has-results'] = []
        self.result['oc-api:has-results'] += uri_list


    def add_uri_meta_records(self, solr_json):
        """Adds result record attribute metadata dicts to the result"""
        self.set_total_start_rows_attributes(solr_json)

        if self.total_found is None:
            return None

        r_recs = ResultRecords(
            request_dict=self.request_dict,
            total_found=self.total_found,
            start=self.start,
            proj_index=self.request_dict.get('proj-index', False),
        )

        # Make metadata dict objects for each individual search result
        # record in the solr_json response.
        meta_result_records = r_recs.make_uri_meta_records_from_solr(
            solr_json
        )
        if len(self.act_responses) == 1:
            self.result = meta_result_records
            return None
        if not len(meta_result_records):
            return None
        if not 'oc-api:has-results' in self.result:
            self.result['oc-api:has-results'] = []
        self.result['oc-api:has-results'] += meta_result_records


    def add_geo_records(self, solr_json):
        """Adds result record geojson features to the result"""
        self.set_total_start_rows_attributes(solr_json)

        if self.total_found is None:
            return None

        r_recs = ResultRecords(
            request_dict=self.request_dict,
            total_found=self.total_found,
            start=self.start,
            proj_index=self.request_dict.get('proj-index', False),
        )

        # Make geojson features for each individual search result
        # record in the solr_json response.
        geo_result_records, non_geo_records = r_recs.make_geojson_records_from_solr(
            solr_json
        )
        if geo_result_records and 'geo-record' in self.act_responses:
            self._add_geojson_features_to_result(
                geo_result_records
            )
        if non_geo_records and 'no-geo-record' in self.act_responses:
            if not 'oc-api:has-no-geo-results' in self.result:
                self.result['oc-api:has-no-geo-results'] = []
            self.result['oc-api:has-no-geo-results'] += non_geo_records


    def add_project_image_overlays(self):
        """Adds project image overlay dict objects"""
        overlay_dicts = project_overlays.add_project_image_overlays(
            result_json=self.result
        )
        if not overlay_dicts:
            return None
        self.result["oc-api:oc-gen-has-geo-overlays"] = overlay_dicts


    def prepare_facets_df(self, solr_json):
        facet_resp_keys = [
            'chrono-facet',
            'prop-facet',
            'prop-range',
            'geo-facet',
            'geo-feature',
        ]
        make_facet_df = False
        for key in facet_resp_keys:
            if not key in self.act_responses:
                continue
            make_facet_df = True
            break
        if not make_facet_df:
            return None
        self.facets_df  = make_cache_df_of_solr_facets(
            request_dict=self.request_dict,
            solr_json=solr_json, 
            reset_cache=False
        )

    # -----------------------------------------------------------------
    # The main method to make the client response result from a
    # solr response json dict.
    # -----------------------------------------------------------------
    def create_result(self, solr_json):
        """Creates a search result for a client based on a solr_json
        response.
        """
        if not solr_json:
            return None

        if set(self.act_responses).intersection(
            set(configs.RESPONSE_TYPES_JSON_LD_CONTEXT)):
            # The list of act_responses includes an
            # element that requires a JSON-LD
            # context object in the response to the client.
            search_context_obj = SearchContext()
            self.result['@context'] = [
                search_context_obj.id,
                search_context_obj.geo_json_context
            ]
        
        # Make the facets dataframe to speed processing
        # of facet results.
        self.prepare_facets_df(solr_json)

        if 'metadata' in self.act_responses:
            # Add search metadata to the response to the client.
            self.result['id'] = self.make_response_id()
            self.add_publishing_datetime_metadata(solr_json)
            self.add_human_remains_flag(solr_json)
            self.add_all_events_date_range(solr_json)
            self.add_geo_chrono_counts(solr_json)
            # The paging function below provides the count of
            # search results
            self.add_paging_json(solr_json)
            self.add_sorting_json()
            self.add_filters_json()
            self.add_text_fields()

        if 'chrono-facet' in self.act_responses:
            # Add facet options for chronology tiles (time spans)
            self.add_chronology_facets(solr_json)

        if 'prop-range' in self.act_responses:
            # Add facet ranges to the result.
            self.add_facet_ranges(solr_json)

        if 'prop-facet' in self.act_responses:
            # Add the "standard" facets (for entities, often in hierarchies)
            self.add_standard_facets(solr_json)
            # Add the item-type facets
            self.add_item_type_facets(solr_json)
            # Add related media facet options
            self.add_rel_media_facets(solr_json)
            # Add keyword facet options (if keywords are present)
            self.add_keyword_facets(solr_json)
            # Adds overlay images, associated with project facet options.
            self.add_project_image_overlays()

        if 'geo-facet' in self.act_responses:
            # Add the geographic tile facets.
            self.add_geotile_facets(solr_json)

        if 'geo-feature' in self.act_responses:
            # Add the geographic tile facets.
            self.add_geo_contained_in_facets(solr_json)

        if 'uuid' in self.act_responses:
            # Adds a simple list of uuids to the result.
            self.add_uuid_records(solr_json)

        if 'uri' in self.act_responses:
            # Adds a simple list of uuids to the result.
            self.add_uri_records(solr_json)

        if 'uri-meta' in self.act_responses:
            # Adds uri-meta dictionary objects that provide
            # record uri together with attribute metadata.
            self.add_uri_meta_records(solr_json)

        if 'geo-record' in self.act_responses or 'no-geo-record'in self.act_responses:
            # Adds geo-json expressed features for individual
            # result records
            self.add_geo_records(solr_json)

        if 'solr' in self.act_responses:
            # Adds the raw solr response to the result.
            if len(self.act_responses) == 1:
                self.result = solr_json
            else:
                self.result['solr'] = solr_json