import copy
import json
import logging
import time
from datetime import datetime
from django.conf import settings
from mysolr.compat import urljoin, compat_args, parse_response
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.isoyears import ISOyears

from opencontext_py.apps.contexts.models import SearchContext

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

# Imports directly related to Solr search and response prep.
from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.result_facets_chronology import ResultFacetsChronology
from opencontext_py.apps.searcher.new_solrsearcher.result_facets_geo import ResultFacetsGeo
from opencontext_py.apps.searcher.new_solrsearcher.result_facets_nonpath import ResultFacetsNonPath
from opencontext_py.apps.searcher.new_solrsearcher.result_facets_standard import ResultFacetsStandard
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
        self.facet_fields_to_client_request = facet_fields_to_client_request
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
        self.min_date = None
        self.max_date = None
    

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


    def add_form_use_life_date_range(self, solr_json, iso_year_format=True):
        """Adds earliest and latest form-use-life dates"""
        meta_configs = [
            (
                # Earliest date items formed, used, or alive.
                'start',
                (
                    configs.STATS_FIELDS_PATH_KEYS + [
                        'form_use_life_chrono_earliest',
                        'min',
                    ]
                ),
            ),
            (
                # Latest date items formed, used, or alive
                'stop',
                (
                    configs.STATS_FIELDS_PATH_KEYS + [
                        'form_use_life_chrono_latest',
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

        # Start and rows comes from the responseHeader
        start = utilities.get_dict_path_value(
            ['responseHeader', 'params', 'start'],
            solr_json
        )
        rows = utilities.get_dict_path_value(
            ['responseHeader', 'params', 'rows'],
            solr_json
        )
        if (total_found is None
            or start is None
            or rows is None):
            return None
        
        # Add number found, start index, paging
        # information about this search result.
        self.total_found = int(float(total_found))
        self.start = int(float(start))
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


    def add_paging_json(self, solr_json):
        """ Adds JSON for paging through results """
        
        self.set_total_start_rows_attributes(solr_json)

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
        if self.start + self.rows < self.total_found:
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
        if not len(facet_ranges):
            # Skip out, we found no facets.
            return None
        if not "oc-api:has-range-facets" in self.result:
            # We don't have a facet list yet, so make it.
            self.result["oc-api:has-range-facets"] = []
        self.result["oc-api:has-range-facets"] += facet_ranges


    def add_chronology_facets(self, solr_json):
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
        self.result["oc-api:has-form-use-life-ranges"] = chrono_options
    

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


    def add_geotile_facets(self, solr_json):
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
            facet_fields_to_client_request=self.facet_fields_to_client_request,
            base_search_url=self.base_search_url,
        ) 
        facets = facets_standard.get_facets_and_options(
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

        if (self.total_found is None
            or self.start is None
            or self.rows is None):
            return None

        r_recs = ResultRecords(
            request_dict=self.request_dict,
            total_found=self.total_found,
            start=self.start,
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

        if (self.total_found is None
            or self.start is None
            or self.rows is None):
            return None

        r_recs = ResultRecords(
            request_dict=self.request_dict,
            total_found=self.total_found,
            start=self.start,
        )
        
        # Make geojson features for each individual search result
        # record in the solr_json response.
        geo_result_records = r_recs.make_geojson_records_from_solr(
            solr_json
        )
        self._add_geojson_features_to_result(
            geo_result_records
        )


    # -----------------------------------------------------------------
    # The main method to make the client response result from a 
    # solr response json dict.
    # -----------------------------------------------------------------
    def create_result(self, solr_json):
        """Creates a search result for a client based on a solr_json 
        response.
        """

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

        if 'metadata' in self.act_responses:
            # Add search metadata to the response to the client.
            self.result['id'] = self.make_response_id()
            self.add_publishing_datetime_metadata(solr_json)
            self.add_form_use_life_date_range(solr_json)
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
        
        if 'geo-record' in self.act_responses:
            # Adds geo-json expressed features for individual 
            # result records
            self.add_geo_records(solr_json)
    
        if 'solr' in self.act_responses:
            # Adds the raw solr response to the result.
            if len(self.act_responses) == 1:
                self.result = solr_json
            else:
                self.result['solr'] = solr_json