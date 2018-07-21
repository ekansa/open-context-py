import time
import json
import django.utils.http as http
from datetime import datetime
from django.conf import settings
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.apps.contexts.models import SearchContext
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.indexer.solrdocument import SolrDocument
from opencontext_py.apps.ocitems.namespaces.models import ItemNamespaces
from opencontext_py.apps.searcher.solrsearcher.responsetypes import SolrResponseTypes
from opencontext_py.apps.searcher.solrsearcher.sorting import SortingOptions
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks
from opencontext_py.apps.searcher.solrsearcher.querymaker import QueryMaker
from opencontext_py.apps.searcher.solrsearcher.filters import ActiveFilters
from opencontext_py.apps.searcher.solrsearcher.chronology import JsonLDchronology
from opencontext_py.apps.searcher.solrsearcher.geojsonregions import GeoJsonRegions
from opencontext_py.apps.searcher.solrsearcher.geojsonpolygons import GeoJsonPolygons
from opencontext_py.apps.searcher.solrsearcher.geojsonprojects import GeoJsonProjects
from opencontext_py.apps.searcher.solrsearcher.geojsonrecords import GeoJsonRecords
from opencontext_py.apps.searcher.solrsearcher.uuids import SolrUUIDs


class MakeJsonLd():

    TEXT_SEARCH_TITLE = 'Filter by Text Search'
    
    def __init__(self, request_dict_json):
        self.m_cache = MemoryCache()  # memory caching object
        self.base_search_link = '/search/'
        self.hierarchy_delim = '---'
        self.request_dict = json.loads(request_dict_json)
        self.request_dict_json = request_dict_json
        self.request_full_path = False
        self.spatial_context = False
        self.min_date = False
        self.max_date = False
        # ---------------
        # get the type of responses requested
        # ---------------
        self.act_responses = SolrResponseTypes(self.request_dict).responses
        self.id = False
        self.label = settings.CANONICAL_SITENAME + ' API'
        self.json_ld = LastUpdatedOrderedDict()
        self.rel_media_facet = False
        self.get_all_media = False  # get links to all media files for an item
        # flatten list of an attribute values to single value
        self.flatten_rec_attributes = False
        # A list of (non-standard) attributes to include in a record
        self.rec_attributes = []
        # check for additional requested record attributes
        self.get_requested_attributes()

    def convert_solr_json(self, solr_json):
        """ Converst the solr jsont """
        ok_show_debug = True
        if 'solr' in self.act_responses:
            return solr_json
        if 'context' in self.act_responses \
           or 'geo-facet' in self.act_responses \
           or 'geo-project' in self.act_responses \
           or 'geo-record' in self.act_responses:
            search_context_obj = SearchContext()
            self.json_ld['@context'] = [search_context_obj.id,
                                        search_context_obj.geo_json_context]
        if 'metadata' in self.act_responses:
            self.json_ld['id'] = self.make_id()
            self.json_ld['label'] = self.label
            self.json_ld['dcmi:modified'] = self.get_modified_datetime(solr_json)
            self.json_ld['dcmi:created'] = self.get_created_datetime(solr_json)
            self.json_ld['oai-pmh:earliestDatestamp'] = self.get_earliest_created_datetime(solr_json)
            self.json_ld['start'] = self.get_earliest_form_use_time(solr_json)
            self.json_ld['stop'] = self.get_latest_form_use_time(solr_json)
            if  self.json_ld['start'] is not None and self.json_ld['stop'] is not None:
                if self.json_ld['start'] != self.json_ld['stop']:
                    self.json_ld['dc-terms:temporal'] = self.json_ld['start'] + '/' + self.json_ld['stop']
                else:
                    self.json_ld['dc-terms:temporal'] = self.json_ld['start']
            else:
                self.json_ld['dc-terms:temporal'] = None
            self.add_paging_json(solr_json)
            self.add_sorting_json()
            self.add_filters_json()
            self.add_text_fields()
        # now process numeric + date fields, facets will
        # only be added if 'facet' in self.act_response
        self.add_numeric_fields(solr_json)
        self.add_date_fields(solr_json)
        # now check for form-use-life chronology
        # note! Do this first to set time bounds for geo-features
        # needs to be done, even if facet results are not displayed
        self.make_form_use_life_chronotiles(solr_json)
        if 'geo-facet' in self.act_responses:
            # now check for discovery geotiles
            self.make_discovery_geotiles(solr_json)
        if 'geo-feature' in self.act_responses:
            # make polygons of features that contain search results
            self.make_containing_geopolygons(solr_json)
        if 'geo-project' in self.act_responses:
            # now check for project geojson
            self.make_project_geojson(solr_json)
        # now process regular facets.
        # they will only be added to the response if
        # 'facet' in self.act_response
        self.make_facets(solr_json)
        if 'geo-record' in self.act_responses \
           or 'nongeo-record' in self.act_responses:
            # now add the result information
            geojson_recs_obj = GeoJsonRecords(self.request_dict_json)
            if len(self.act_responses) <= 2:
                # get more complex geospatial data, if we're not asking
                # for too many types of resonses
                geojson_recs_obj.do_complex_geo = True
            geojson_recs_obj.min_date = self.min_date
            geojson_recs_obj.max_date = self.max_date
            geojson_recs_obj.flatten_rec_attributes = self.flatten_rec_attributes
            geojson_recs_obj.rec_attributes = self.rec_attributes
            geojson_recs_obj.get_all_media = self.get_all_media
            geojson_recs_obj.make_records_from_solr(solr_json)
            if len(geojson_recs_obj.geojson_recs) > 0 \
               and 'geo-record' in self.act_responses:
                self.json_ld['type'] = 'FeatureCollection'
                if 'features' not in self.json_ld:
                    self.json_ld['features'] = []
                self.json_ld['features'] += geojson_recs_obj.geojson_recs
            if len(geojson_recs_obj.non_geo_recs) > 0 \
               and 'nongeo-record' in self.act_responses:
                self.json_ld['oc-api:has-results'] = geojson_recs_obj.non_geo_recs
        if 'uuid' in self.act_responses:
            solr_uuids = SolrUUIDs(self.request_dict_json)
            solr_uuids.do_media_thumbs = False
            uuids = solr_uuids.make_uuids_from_solr(solr_json)
            if len(self.act_responses) > 1:
                # return a list inside a key
                self.json_ld['oc-api:uuids'] = uuids
            else:
                # just return a simple list
                self.json_ld = uuids
                ok_show_debug = False
        if 'uri' in self.act_responses:
            solr_uuids = SolrUUIDs(self.request_dict_json)
            uris = solr_uuids.make_uris_from_solr(solr_json)
            if len(self.act_responses) > 1:
                # return a list inside a key
                self.json_ld['oc-api:has-results'] = uris
            else:
                # just return a simple list
                self.json_ld = uris
                ok_show_debug = False
        elif 'uri-meta' in self.act_responses:
            solr_uuids = SolrUUIDs(self.request_dict_json)
            solr_uuids.min_date = self.min_date
            solr_uuids.max_date = self.max_date
            solr_uuids.flatten_rec_attributes = self.flatten_rec_attributes
            solr_uuids.rec_attributes = self.rec_attributes
            solr_uuids.do_media_thumbs = self.check_do_media_thumbs(solr_json)
            solr_uuids.get_all_media = self.get_all_media
            uris = solr_uuids.make_uris_from_solr(solr_json,
                                                  False)
            if len(self.act_responses) > 1:
                # return a list inside a key
                self.json_ld['oc-api:has-results'] = uris
            else:
                # just return a simple list
                self.json_ld = uris
                ok_show_debug = False
        if settings.DEBUG and ok_show_debug:
            self.json_ld['request'] = self.request_dict
            # self.json_ld['request'] = self.request_dict
            self.json_ld['solr'] = solr_json
        return self.json_ld

    def add_paging_json(self, solr_json):
        """ adds JSON for paging through results """
        total_found = self.get_path_in_dict(['response',
                                            'numFound'],
                                            solr_json)
        start = self.get_path_in_dict(['responseHeader',
                                       'params',
                                       'start'],
                                      solr_json)
        rows = self.get_path_in_dict(['responseHeader',
                                      'params',
                                      'rows'],
                                     solr_json)
        if start is not False \
           and rows is not False \
           and total_found is not False:
            # add numeric information about this search
            total_found = int(float(total_found))
            start = int(float(start))
            rows = int(float(rows))
            self.json_ld['totalResults'] = total_found
            self.json_ld['startIndex'] = start
            self.json_ld['itemsPerPage'] = rows
            # start off with a the request dict, then
            # remove 'start' and 'rows' parameters
            ini_request_dict = self.request_dict
            if 'start' in ini_request_dict:
                ini_request_dict.pop('start', None)
            if 'rows' in ini_request_dict:
                ini_request_dict.pop('rows', None)
            # do this stupid crap so as not to get a memory
            # error with FilterLinks()
            ini_request_dict_json = json.dumps(ini_request_dict,
                                               ensure_ascii=False,
                                               indent=4)
            # add a first page link
            if start > 0:
                links = self.make_paging_links(0,
                                               rows,
                                               ini_request_dict_json)
                self.json_ld['first'] = links['html']
                self.json_ld['first-json'] = links['json']
            if start >= rows:
                # add a previous page link
                links = self.make_paging_links(start - rows,
                                               rows,
                                               ini_request_dict_json)
                self.json_ld['previous'] = links['html']
                self.json_ld['previous-json'] = links['json']
            if start + rows < total_found:
                # add a next page link
                links = self.make_paging_links(start + rows,
                                               rows,
                                               ini_request_dict_json)
                self.json_ld['next'] = links['html']
                self.json_ld['next-json'] = links['json']
            num_pages = round(total_found / rows, 0)
            if num_pages * rows >= total_found:
                num_pages -= 1
            # add a last page link
            links = self.make_paging_links(num_pages * rows,
                                           rows,
                                           ini_request_dict_json)
            self.json_ld['last'] = links['html']
            self.json_ld['last-json'] = links['json']

    def make_paging_links(self, start, rows, ini_request_dict_json):
        """ makes links for paging for start, rows, with
            an initial request dict json string

            a big of a hassle to avoid memory errors with FilterLinks()
        """
        start = int(start)
        start = str(start)
        rows = str(rows)
        fl = FilterLinks()
        fl.base_search_link = self.base_search_link
        fl.base_request_json = ini_request_dict_json
        fl.spatial_context = self.spatial_context
        fl.remove_start_param = False
        start_rparams = fl.add_to_request('start',
                                          start)
        start_rparams_json = json.dumps(start_rparams,
                                        ensure_ascii=False,
                                        indent=4)
        fl.base_request_json = start_rparams_json
        new_rparams = fl.add_to_request('rows',
                                        rows)
        urls = fl.make_request_urls(new_rparams)
        return urls

    def add_sorting_json(self):
        """ adds JSON to describe result sorting """
        sort_opts = SortingOptions()
        sort_opts.base_search_link = self.base_search_link
        sort_opts.spatial_context = self.spatial_context
        sort_opts.make_current_sorting_list(self.request_dict)
        self.json_ld['oc-api:active-sorting'] = sort_opts.current_sorting
        sort_opts.make_sort_links_list(self.request_dict)
        self.json_ld['oc-api:has-sorting'] = sort_opts.sort_links

    def add_filters_json(self):
        """ adds JSON describing search filters """
        a_filters = ActiveFilters()
        a_filters.base_search_link = self.base_search_link
        a_filters.hierarchy_delim = self.hierarchy_delim
        filters = a_filters.add_filters_json(self.request_dict)
        if len(filters) > 0:
            self.json_ld['oc-api:active-filters'] = filters

    def make_filter_label_dict(self, act_val):
        """ returns a dictionary object
            with a label and set of entities (in cases of OR
            searchs)
        """
        return ActiveFilters().make_filter_label_dict(act_val)

    def make_id(self):
        """ makes the ID for the document """
        if self.id is not False:
            output = self.id
        elif self.request_full_path is not False:
            output = settings.CANONICAL_HOST + self.request_full_path
        else:
            output = False
        return output

    def get_modified_datetime(self, solr_json):
        """ Makes the last modified time in ISO 8601 format
            Solr already defaults to that format
        """
        modified = self.get_path_in_dict(['stats',
                                          'stats_fields',
                                          'updated',
                                          'max'],
                                         solr_json)
        if modified is False:
            modified = time.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
        return modified

    def get_created_datetime(self, solr_json):
        """ Makes the last modified time in ISO 8601 format
            Solr already defaults to that format
        """
        created = self.get_path_in_dict(['stats',
                                        'stats_fields',
                                        'published',
                                        'max'],
                                        solr_json)
        if created is False:
            created = time.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
        return created

    def get_earliest_created_datetime(self, solr_json):
        """ Makes the last modified time in ISO 8601 format
            Solr already defaults to that format
        """
        earliest_created = self.get_path_in_dict(['stats',
                                                  'stats_fields',
                                                  'published',
                                                  'min'],
                                                 solr_json)
        if earliest_created is False:
            earliest_created = time.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
        return earliest_created

    def get_earliest_form_use_time(self, solr_json, iso=True):
        """ Makes the last modified time in ISO 8601 format
            Solr already defaults to that format
        """
        earliest_f_u_l = self.get_path_in_dict(['stats',
                                                'stats_fields',
                                                'form_use_life_chrono_earliest',
                                                'min'],
                                               solr_json)
        if earliest_f_u_l is False:
            earliest_f_u_l = None
        else:
            if iso and earliest_f_u_l is not None:
                earliest_f_u_l = ISOyears().make_iso_from_float(earliest_f_u_l)
        return earliest_f_u_l

    def get_latest_form_use_time(self, solr_json, iso=True):
        """ Makes the last modified time in ISO 8601 format
            Solr already defaults to that format
        """
        latest_f_u_l = self.get_path_in_dict(['stats',
                                              'stats_fields',
                                              'form_use_life_chrono_latest',
                                              'max'],
                                             solr_json)
        if latest_f_u_l is False:
            latest_f_u_l = None
        else:
            if iso and latest_f_u_l is not None: 
                latest_f_u_l = ISOyears().make_iso_from_float(latest_f_u_l)
        return latest_f_u_l

    def add_text_fields(self):
        """ adds text fields with query options """
        text_fields = []
        # first add a general key-word search option
        fl = FilterLinks()
        fl.base_search_link = self.base_search_link
        fl.base_request_json = self.request_dict_json
        fl.base_r_full_path = self.request_full_path
        fl.spatial_context = self.spatial_context
        q_request_dict = self.request_dict
        if 'q' not in q_request_dict:
            q_request_dict['q'] = []
        param_vals = q_request_dict['q']
        if len(param_vals) < 1:
            search_term = None
        else:
            search_term = param_vals[0]
        field = LastUpdatedOrderedDict()
        field['id'] = '#textfield-keyword-search'
        field['label'] = self.TEXT_SEARCH_TITLE
        field['oc-api:search-term'] = search_term
        if search_term is False or search_term is None:
            new_rparams = fl.add_to_request_by_solr_field('q',
                                                          '{SearchTerm}')
            field['oc-api:template'] = fl.make_request_url(new_rparams)
            field['oc-api:template-json'] = fl.make_request_url(new_rparams, '.json')
        else:
            param_search = param_vals[0].replace(search_term, '{SearchTerm}')
            rem_request = fl.make_request_sub(q_request_dict,
                                              'q',
                                              search_term,
                                              '{SearchTerm}')
            field['oc-api:template'] = fl.make_request_url(rem_request)
            field['oc-api:template-json'] = fl.make_request_url(rem_request, '.json')
        text_fields.append(field)
        # now add an option looking in properties
        if 'prop' in self.request_dict:
            param_vals = self.request_dict['prop']
            for param_val in param_vals:
                if self.hierarchy_delim in param_val:
                    all_vals = param_val.split(self.hierarchy_delim)
                else:
                    all_vals = [param_val]
                if len(all_vals) < 2:
                    check_field = all_vals[0]
                    search_term = None  # no search term
                else:
                    check_field = all_vals[-2]  # penultimate value is the field
                    search_term = all_vals[-1]  # last value is search term
                check_dict = self.make_filter_label_dict(check_field)
                if check_dict['data-type'] == 'string':
                    fl = FilterLinks()
                    fl.base_search_link = self.base_search_link
                    fl.base_request_json = self.request_dict_json
                    fl.base_r_full_path = self.request_full_path
                    fl.spatial_context = self.spatial_context
                    field = LastUpdatedOrderedDict()
                    field['id'] = '#textfield-' + check_dict['slug']
                    field['label'] = check_dict['label']
                    field['oc-api:search-term'] = search_term
                    if len(check_dict['entities']) == 1:
                        field['rdfs:isDefinedBy'] = check_dict['entities'][0].uri
                    if search_term is False or search_term is None:
                        param_search = param_val + self.hierarchy_delim + '{SearchTerm}'
                        new_rparams = fl.add_to_request_by_solr_field('prop',
                                                                      param_search)
                        field['oc-api:template'] = fl.make_request_url(new_rparams)
                        field['oc-api:template-json'] = fl.make_request_url(new_rparams, '.json')
                    else:
                        param_search = param_val.replace(search_term, '{SearchTerm}')
                        rem_request = fl.make_request_sub(self.request_dict,
                                                          'prop',
                                                          param_val,
                                                          param_search)
                        field['oc-api:template'] = fl.make_request_url(rem_request)
                        field['oc-api:template-json'] = fl.make_request_url(rem_request, '.json')
                    text_fields.append(field)
        if len(text_fields) > 0:
            self.json_ld['oc-api:has-text-search'] = text_fields

    def get_solr_ranges(self, solr_json, data_type):
        """ gets solr ranges of a specific data-type """
        output = LastUpdatedOrderedDict()
        facet_ranges = self.get_path_in_dict(['facet_counts',
                                              'facet_ranges'],
                                             solr_json)
        if isinstance(facet_ranges, dict):
            for solr_field_key, ranges in facet_ranges.items():
                facet_key_list = solr_field_key.split('___')
                slug = facet_key_list[0].replace('_', '-')
                fdata_type = facet_key_list[-1].replace('pred_', '')
                # print('Check: ' + fdata_type + ' on ' + data_type)
                if fdata_type == data_type:
                    output[solr_field_key] = ranges
        if len(output) < 1:
            output = False
        return output

    def add_numeric_fields(self, solr_json):
        """ adds numeric fields with query options """
        num_fields = []
        num_facet_ranges = self.get_solr_ranges(solr_json, 'numeric')
        if num_facet_ranges is not False:
            for solr_field_key, ranges in num_facet_ranges.items():
                facet_key_list = solr_field_key.split('___')
                slug = facet_key_list[0].replace('_', '-')
                # check to see if the field is a linkded data field
                # if so, it needs some help with making Filter Links
                linked_field = False
                field_entity = self.m_cache.get_entity(slug)
                if field_entity:
                    self.add_active_facet_field(slug)
                    if field_entity.item_type == 'uri':
                        linked_field = True
                field = self.get_facet_meta(solr_field_key)
                field['oc-api:min'] = float(ranges['start'])
                field['oc-api:max'] = float(ranges['end'])
                gap = float(ranges['gap'])
                field['oc-api:gap'] = gap
                field['oc-api:has-range-options'] = []
                i = -1
                for range_min_key in ranges['counts'][::2]:
                    i += 2
                    solr_count = ranges['counts'][i]
                    fl = FilterLinks()
                    fl.base_search_link = self.base_search_link
                    fl.base_request_json = self.request_dict_json
                    fl.base_r_full_path = self.request_full_path
                    fl.spatial_context = self.spatial_context
                    fl.partial_param_val_match = True
                    range_start = float(range_min_key)
                    range_end = range_start + gap
                    solr_range = '[' + str(range_start) + ' TO ' + str(range_end) + ' ]'
                    new_rparams = fl.add_to_request('prop',
                                                    solr_range,
                                                    slug)
                    range_dict = LastUpdatedOrderedDict()
                    range_dict['id'] = fl.make_request_url(new_rparams)
                    range_dict['json'] = fl.make_request_url(new_rparams, '.json')
                    range_dict['label'] = str(round(range_start,3))
                    range_dict['count'] = solr_count
                    range_dict['oc-api:min'] = range_start
                    range_dict['oc-api:max'] = range_end
                    field['oc-api:has-range-options'].append(range_dict)
                num_fields.append(field)
        if len(num_fields) > 0 and 'facet' in self.act_responses:
            self.json_ld['oc-api:has-numeric-facets'] = num_fields

    def add_date_fields(self, solr_json):
        """ adds numeric fields with query options """
        date_fields = []
        date_facet_ranges = self.get_solr_ranges(solr_json, 'date')
        if date_facet_ranges is not False:
            for solr_field_key, ranges in date_facet_ranges.items():
                facet_key_list = solr_field_key.split('___')
                slug = facet_key_list[0].replace('_', '-')
                # check to see if the field is a linkded data field
                # if so, it needs some help with making Filter Links
                linked_field = False
                field_entity = self.m_cache.get_entity(slug)
                if field_entity:
                    self.add_active_facet_field(slug)
                    if field_entity.item_type == 'uri':
                        linked_field = True
                field = self.get_facet_meta(solr_field_key)
                field['oc-api:min-date'] = ranges['start']
                field['oc-api:max-date'] = ranges['end']
                field['oc-api:gap-date'] = ranges['gap']
                field['oc-api:has-range-options'] = []
                i = -1
                qm = QueryMaker()
                for range_min_key in ranges['counts'][::2]:
                    i += 2
                    solr_count = ranges['counts'][i]
                    fl = FilterLinks()
                    fl.base_search_link = self.base_search_link
                    fl.base_request_json = self.request_dict_json
                    fl.base_r_full_path = self.request_full_path
                    fl.spatial_context = self.spatial_context
                    fl.partial_param_val_match = True
                    dt_end = qm.add_solr_gap_to_date(range_min_key, ranges['gap'])
                    range_end = qm.convert_date_to_solr_date(dt_end)
                    solr_range = '[' + range_min_key + ' TO ' + range_end + ' ]'
                    new_rparams = fl.add_to_request('prop',
                                                    solr_range,
                                                    slug)
                    range_dict = LastUpdatedOrderedDict()
                    range_dict['id'] = fl.make_request_url(new_rparams)
                    range_dict['json'] = fl.make_request_url(new_rparams, '.json')
                    range_dict['label'] = qm.make_human_readable_date(range_min_key) + ' to ' + qm.make_human_readable_date(range_end)
                    range_dict['count'] = solr_count
                    range_dict['oc-api:min-date'] = range_min_key
                    range_dict['oc-api:max-date'] = range_end
                    field['oc-api:has-range-options'].append(range_dict)
                date_fields.append(field)
        if len(date_fields) > 0 and 'facet' in self.act_responses:
            self.json_ld['oc-api:has-date-facets'] = date_fields

    def make_discovery_geotiles(self, solr_json, add_features=True):
        """ makes discovery geotile facets.
            discovery geotiles need
            special handling.
            This finds any geodiscovery tiles
            and removes them from the other list
            of facets
        """
        solr_disc_geotile_facets = self.get_path_in_dict(['facet_counts',
                                                         'facet_fields',
                                                         'discovery_geotile'],
                                                         solr_json)
        if solr_disc_geotile_facets is not False:
            geo_regions = GeoJsonRegions(solr_json)
            geo_regions.min_date = self.min_date
            geo_regions.max_date = self.max_date
            geo_regions.spatial_context = self.spatial_context
            geo_regions.set_aggregation_depth(self.request_dict_json,
                                              solr_disc_geotile_facets)  # also needed for making filter links
            geo_regions.process_solr_tiles(solr_disc_geotile_facets)
            if len(geo_regions.geojson_regions) > 0:
                self.json_ld['type'] = 'FeatureCollection'
                self.json_ld['oc-api:max-disc-tile-zoom'] = geo_regions.max_tile_precision
                self.json_ld['oc-api:response-tile-zoom'] = geo_regions.result_depth
                self.json_ld['oc-api:geotile-scope'] = geo_regions.geotile_scope
                if add_features:
                    self.json_ld['features'] = geo_regions.geojson_regions
                
    def make_containing_geopolygons(self, solr_json):
        """ makes discovery geotile facets.
            discovery geotiles need
            special handling.
            This finds any geodiscovery tiles
            and removes them from the other list
            of facets
        """
        if 'oc-api:response-tile-zoom' not in self.json_ld:
            # we haven't yet determined the tile scope for this response, so do it now
            self.make_discovery_geotiles(solr_json, False)
        solr_disc_geopoly_facets = self.get_path_in_dict(['facet_counts',
                                                         'facet_fields',
                                                         'disc_geosource'],
                                                         solr_json)
        if solr_disc_geopoly_facets is not False:
            # print('Found contained polygons')
            geo_polys = GeoJsonPolygons(solr_json)
            geo_polys.min_date = self.min_date
            geo_polys.max_date = self.max_date
            geo_polys.spatial_context = self.spatial_context
            if 'oc-api:response-tile-zoom' in self.json_ld:
                geo_polys.response_zoom_scope = self.json_ld['oc-api:response-tile-zoom']
            geo_polys.process_solr_polygons(solr_disc_geopoly_facets)
            if len(geo_polys.geojson_features) > 0:
                if 'type' not in self.json_ld:
                    self.json_ld['type'] = 'FeatureCollection'
                if 'features' in self.json_ld:
                    # we already have some features so add the new ones
                    self.json_ld['features'] += geo_polys.geojson_features
                else:
                    self.json_ld['features'] = geo_polys.geojson_features

    def make_project_geojson(self, solr_json):
        """ makes project geojson based on a special
            pivot-facet request.
        """
        solr_proj_geo_facets = self.get_path_in_dict(['facet_counts',
                                                      'facet_pivot',
                                                      'root___project_id,discovery_geotile'],
                                                     solr_json)
        solr_proj_chrono_facets = self.get_path_in_dict(['facet_counts',
                                                         'facet_pivot',
                                                         'root___project_id,form_use_life_chrono_tile'],
                                                        solr_json)
        if solr_proj_geo_facets is not False\
           and solr_proj_chrono_facets is not False:
            geo_projects = GeoJsonProjects(solr_json)
            geo_projects.geo_pivot = solr_proj_geo_facets
            geo_projects.chrono_pivot = solr_proj_chrono_facets
            geo_projects.spatial_context = self.spatial_context
            geo_projects.filter_request_dict_json = self.request_dict_json  # needed for making filter links
            geo_projects.make_project_geojson()
            if len(geo_projects.geojson_projects) > 0:
                self.json_ld['type'] = 'FeatureCollection'
                if 'features' not in self.json_ld:
                    self.json_ld['features'] = []
                self.json_ld['features'] += geo_projects.geojson_projects

    def make_form_use_life_chronotiles(self, solr_json):
        """ makes tile facets for chronology
            form-use-life tiles need
            special handling.
            This finds any form-use-lide tiles
            and removes them from the other list
            of facets
        """
        solr_form_use_life_chono_facets = self.get_path_in_dict(['facet_counts',
                                                                'facet_fields',
                                                                'form_use_life_chrono_tile'],
                                                                solr_json)
        if solr_form_use_life_chono_facets is not False:
            chrono_tiles = JsonLDchronology(solr_json)
            chrono_tiles.spatial_context = self.spatial_context
            chrono_tiles.set_aggregation_depth(self.request_dict_json)  # also needed for making filter links
            chrono_tiles.set_date_exclusions_from_request_params(self.request_dict_json)
            chrono_tiles.process_solr_tiles(solr_form_use_life_chono_facets)
            self.min_date = chrono_tiles.min_date
            self.max_date = chrono_tiles.max_date
            if len(chrono_tiles.chrono_tiles) > 0 \
               and 'chrono-facet' in self.act_responses:
                self.json_ld['oc-api:has-form-use-life-ranges'] = chrono_tiles.chrono_tiles

    def add_rel_media_fields(self, solr_json):
        """ adds facet options for solr media """
        rel_media_options = []
        solr_facet_fields = self.get_path_in_dict(['facet_counts',
                                                  'facet_fields'],
                                                  solr_json)
        if solr_facet_fields is not False:
            rel_image_count = self.get_rel_media_counts(solr_facet_fields,
                                                        'image_media_count')
            rel_other_count = self.get_rel_media_counts(solr_facet_fields,
                                                        'other_binary_media_count')
            rel_doc_count = self.get_rel_media_counts(solr_facet_fields,
                                                      'document_count')
            rel_media_options = self.make_rel_media_option(rel_image_count,
                                                           'images',
                                                           rel_media_options)
            rel_media_options = self.make_rel_media_option(rel_other_count,
                                                           'other-media',
                                                           rel_media_options)
            rel_media_options = self.make_rel_media_option(rel_doc_count,
                                                           'documents',
                                                           rel_media_options)
            if len(rel_media_options) > 0:
                self.rel_media_facet = LastUpdatedOrderedDict()
                self.rel_media_facet['id'] = '#related-media'
                self.rel_media_facet['label'] = 'Has Related Media'
                self.rel_media_facet['oc-api:has-rel-media-options'] = rel_media_options

    def check_do_media_thumbs(self, solr_json):
        """ checks to see if media thumbnails should be in records """
        output = False
        total_found = self.get_path_in_dict(['response',
                                            'numFound'],
                                            solr_json)
        solr_facet_fields = self.get_path_in_dict(['facet_counts',
                                                  'facet_fields'],
                                                  solr_json)
        if solr_facet_fields is not False \
           and total_found is not False:
            total_found = int(float(total_found))
            rel_image_count = self.get_rel_media_counts(solr_facet_fields,
                                                        'image_media_count')
            if rel_image_count >= (total_found * .33):
                output = True
        return output

    def make_rel_media_option(self,
                              rel_media_count,
                              rel_media_type,
                              rel_media_options):
        """ makes a facet option for related media """
        if rel_media_count > 0:
            fl = FilterLinks()
            fl.base_search_link = self.base_search_link
            fl.base_request_json = self.request_dict_json
            fl.base_r_full_path = self.request_full_path
            fl.spatial_context = self.spatial_context
            option = LastUpdatedOrderedDict()
            new_rparams = fl.add_to_request_by_solr_field(rel_media_type,
                                                          '1')
            option['id'] = fl.make_request_url(new_rparams)
            option['json'] = fl.make_request_url(new_rparams, '.json')
            if rel_media_type == 'images':
                option['label'] = 'Linked with images'
            elif rel_media_type == 'other-media':
                option['label'] = 'Linked with media (non-image)'
            elif rel_media_type == 'documents':
                option['label'] = 'Linked with documents'
            option['count'] = rel_media_count
            rel_media_options.append(option)
        return rel_media_options

    def get_rel_media_counts(self, solr_facet_fields, solr_media_field):
        """ returns the number of items with the requested type of
            media, as indicated in the 'solr_media_field'
        """
        output = 0
        if solr_media_field in solr_facet_fields:
            solr_facet_values = solr_facet_fields[solr_media_field]
            i = -1
            for solr_facet_value_key in solr_facet_values[::2]:
                i += 2
                if solr_facet_value_key != '0':
                    output += solr_facet_values[i]
                    # print(solr_media_field + ' now: ' + str(output))
        return output

    def make_facets(self, solr_json):
        """ Makes a list of facets """
        self.add_rel_media_fields(solr_json)
        solr_facet_fields = self.get_path_in_dict(['facet_counts',
                                                  'facet_fields'],
                                                  solr_json)
        if solr_facet_fields is not False:
            pre_sort_facets = {}
            json_ld_facets = []
            if 'discovery_geotile' in solr_facet_fields:
                # remove the geotile field
                solr_facet_fields.pop('discovery_geotile', None)
            if 'form_use_life_chrono_tile' in solr_facet_fields:
                # remove the form-use-life chronology tile field
                solr_facet_fields.pop('form_use_life_chrono_tile', None)
            if 'image_media_count' in solr_facet_fields:
                # remove image media facet
                solr_facet_fields.pop('image_media_count', None)
            if 'other_binary_media_count' in solr_facet_fields:
                # remove other media facet
                solr_facet_fields.pop('other_binary_media_count', None)
            if 'document_count' in solr_facet_fields:
                # remove document count facet
                solr_facet_fields.pop('document_count', None)
            if 'disc_geosource' in solr_facet_fields:
                # remove document count facet
                solr_facet_fields.pop('disc_geosource', None)
            # do this to consolidate facet fields for dcterms is referenced by
            consolidated_solr_facet_fields = LastUpdatedOrderedDict()
            dc_ref_field = 'dc_terms_isreferencedby___pred_id'
            root_dc_ref_field_exists = False
            if dc_ref_field in solr_facet_fields:
                root_dc_ref_field_exists = True    
            for solr_facet_key, solr_facet_values in solr_facet_fields.items():
                if dc_ref_field == solr_facet_key:
                    if solr_facet_key not in consolidated_solr_facet_fields:
                        # only add facet values for the root if they aren't added yet
                        consolidated_solr_facet_fields[solr_facet_key] = solr_facet_values
                elif (dc_ref_field in solr_facet_key) and (dc_ref_field != solr_facet_key):
                    # OK, we have a dc_ref_field deeper in the hierarchy, replace any
                    # root facets with the child facets
                    solr_facet_key = dc_ref_field
                    consolidated_solr_facet_fields[solr_facet_key] = solr_facet_values
                else:
                    consolidated_solr_facet_fields[solr_facet_key] = solr_facet_values        
            solr_facet_fields = consolidated_solr_facet_fields
            for solr_facet_key, solr_facet_values in solr_facet_fields.items():
                facet = self.get_facet_meta(solr_facet_key)
                count_raw_values = len(solr_facet_values)
                id_options = []
                num_options = []
                date_options = []
                string_options = []
                i = -1
                if facet['data-type'] == 'id':
                    for solr_facet_value_key in solr_facet_values[::2]:
                        i += 2
                        solr_facet_count = solr_facet_values[i]
                        facet_val_obj = self.make_facet_value_obj(solr_facet_key,
                                                                  solr_facet_value_key,
                                                                  solr_facet_count)
                        val_obj_data_type = facet_val_obj['data-type']
                        facet_val_obj.pop('data-type', None)
                        in_filters = self.check_facet_value_in_filters(facet_val_obj)
                        if not in_filters:
                            # only add facet values if they are not already in
                            # the active search filters.
                            if val_obj_data_type == 'id':
                                id_options.append(facet_val_obj)
                            elif val_obj_data_type == 'numeric':
                                num_options.append(facet_val_obj)
                            elif val_obj_data_type == 'date':
                                date_options.append(facet_val_obj)
                            elif val_obj_data_type == 'string':
                                string_options.append(facet_val_obj)
                    if len(id_options) > 0:
                        facet['oc-api:has-id-options'] = id_options
                    if len(num_options) > 0:
                        facet['oc-api:has-numeric-options'] = num_options
                    if len(date_options) > 0:
                        facet['oc-api:has-date-options'] = date_options
                    if len(string_options) > 0:
                        facet['oc-api:has-text-options'] = string_options
                    if count_raw_values > 0:
                        # check so facets without options are not presented
                        pre_sort_facets[facet['id']] = facet
                else:
                    pre_sort_facets[facet['id']] = facet
            # now make a sorted list of facets
            json_ld_facets = self.make_sorted_facet_list(pre_sort_facets)
            if len(json_ld_facets) > 0 and 'facet' in self.act_responses:
                self.json_ld['oc-api:has-facets'] = json_ld_facets

    def check_facet_value_in_filters(self, facet_val_obj):
        """ checks to see if a facet_val_object is in the active filters. """
        in_filter = False
        if 'oc-api:active-filters' in self.json_ld:
            for filter in self.json_ld['oc-api:active-filters']:
                if 'oc-api:filter-slug' in filter and 'slug' in facet_val_obj:
                    if filter['oc-api:filter-slug'] == facet_val_obj['slug']:
                        in_filter = True
                        break
        return in_filter

    def make_sorted_facet_list(self, pre_sort_facets):
        """ makes a list of sorted facets based on 
            a dictionary oject of pre_sort_facets
        """
        json_ld_facets = []
        used_keys = []
        if 'prop' in self.request_dict:
            # first check for 'prop' related facets
            # these get promoted to the first positions in the list
            raw_plist = self.request_dict['prop']
            plist = raw_plist[::-1]  # reverse the list, so last props first
            qm = QueryMaker()
            for param_val in plist:
                param_paths = qm.expand_hierarchy_options(param_val)
                for id_key, facet in pre_sort_facets.items():
                    for param_slugs in param_paths:
                        last_slug = param_slugs[-1]
                        if last_slug in id_key \
                           and id_key not in used_keys:
                            # the facet id has the last slug id!
                            # so add to the ordered list of facets
                            json_ld_facets.append(facet)
                            used_keys.append(id_key)
        # now add facet for context
        for id_key, facet in pre_sort_facets.items():
            if '#facet-context' in id_key \
               and id_key not in used_keys:
                json_ld_facets.append(facet)
                used_keys.append(id_key)
        # now add facet for item-types
        if '#facet-item-type' in pre_sort_facets \
           and '#facet-item-type' not in used_keys:
                json_ld_facets.append(pre_sort_facets['#facet-item-type'])
                used_keys.append('#facet-item-type')
        # now add item categories
        for id_key, facet in pre_sort_facets.items():
            if '#facet-prop-oc-gen-' in id_key \
               and id_key not in used_keys:
                json_ld_facets.append(facet)
                used_keys.append(id_key)
        # now add facet for projects
        for id_key, facet in pre_sort_facets.items():
            if '#facet-project' in id_key \
               and id_key not in used_keys:
                json_ld_facets.append(facet)
                used_keys.append(id_key)
        # now add facet for root linked data
        if '#facet-prop-ld' in pre_sort_facets \
           and '#facet-prop-ld' not in used_keys:
                json_ld_facets.append(pre_sort_facets['#facet-prop-ld'])
                used_keys.append('#facet-prop-ld')
        # now add facet for root properties
        if '#facet-prop-var' in pre_sort_facets \
           and '#facet-prop-var' not in used_keys:
                json_ld_facets.append(pre_sort_facets['#facet-prop-var'])
                used_keys.append('#facet-prop-var')
        for id_key in used_keys:
            # delete all the used facets by key
            pre_sort_facets.pop(id_key, None)
        for id_key, facet in pre_sort_facets.items():
            # add remaining (unsorted) facets
            json_ld_facets.append(facet)
        if self.rel_media_facet is not False:
            # add the related media facet
            json_ld_facets.append(self.rel_media_facet)
        return json_ld_facets

    def get_facet_meta(self, solr_facet_key):
        facet = LastUpdatedOrderedDict()
        # facet['solr'] = solr_facet_key
        id_prefix = '#' + solr_facet_key
        if '___project_id' in solr_facet_key:
            id_prefix = '#facet-project'
            ftype = 'oc-api:facet-project'
        elif '___context_id' in solr_facet_key:
            id_prefix = '#facet-context'
            ftype = 'oc-api:facet-context'
        elif '___pred_' in solr_facet_key:
            id_prefix = '#facet-prop'
            ftype = 'oc-api:facet-prop'
        elif 'item_type' in solr_facet_key:
            id_prefix = '#facet-item-type'
            ftype = 'oc-api:facet-item-type'
        if 'dc_terms_isreferencedby___pred_id' == solr_facet_key:
            id_prefix = '#facet-dc-terms-isreferencedby'
            ftype = 'oc-api:facet-prop'
        if solr_facet_key == SolrDocument.ROOT_CONTEXT_SOLR:
            facet['id'] = id_prefix
            facet['rdfs:isDefinedBy'] = 'oc-api:facet-context'
            facet['label'] = 'Context'
            facet['data-type'] = 'id'
        elif solr_facet_key == SolrDocument.ROOT_PROJECT_SOLR:
            facet['id'] = id_prefix
            facet['rdfs:isDefinedBy'] = 'oc-api:facet-project'
            facet['label'] = 'Project'
            facet['data-type'] = 'id'
        elif solr_facet_key == SolrDocument.ROOT_LINK_DATA_SOLR:
            facet['id'] = id_prefix + '-ld'
            facet['rdfs:isDefinedBy'] = 'oc-api:facet-prop-ld'
            facet['label'] = 'Descriptions (Common Standards)'
            facet['data-type'] = 'id'
        elif solr_facet_key == SolrDocument.ROOT_PREDICATE_SOLR:
            facet['id'] = id_prefix + '-var'
            facet['rdfs:isDefinedBy'] = 'oc-api:facet-prop-var'
            facet['label'] = 'Descriptions (Project Defined)'
            facet['data-type'] = 'id'
        elif solr_facet_key == 'item_type':
            facet['id'] = id_prefix
            facet['rdfs:isDefinedBy'] = 'oc-api:facet-item-type'
            facet['label'] = 'Open Context Type'
            facet['data-type'] = 'id'
        elif solr_facet_key == 'obj_all___biol_term_hastaxonomy___pred_id':
            facet['id'] = id_prefix
            facet['rdfs:isDefinedBy'] = 'http://purl.org/NET/biol/ns#term_hasTaxonomy'
            facet['label'] = 'Has Biological Taxonomy'
            facet['data-type'] = 'id'
        elif solr_facet_key == 'dc_terms_isreferencedby___pred_id':
            facet['id'] = id_prefix
            facet['rdfs:isDefinedBy'] = 'dc-terms:isReferencedBy'
            facet['label'] = 'Is referenced by'
            facet['data-type'] = 'id'
        else:
            # ------------------------
            # Facet is not at the root
            # ------------------------
            facet['id'] = id_prefix
            facet['label'] = ''
            facet_key_list = solr_facet_key.split('___')
            fsuffix_list = facet_key_list[-1].split('_')
            slug = facet_key_list[0].replace('_', '-')
            db_slug = self.clean_related_slug(slug)
            entity = self.m_cache.get_entity(db_slug)
            if entity:
                if facet_key_list[-1] != facet_key_list[1]:
                    # there's a predicate slug as the second
                    # item in te facet_key_list
                    pred_slug = facet_key_list[1].replace('_', '-')
                    self.add_active_facet_field(pred_slug, fsuffix_list[0])
                else:
                    # the predicate field is the first item in the
                    # facet key list
                    self.add_active_facet_field(slug, fsuffix_list[0])
                facet['id'] = id_prefix + '-' + entity.slug
                facet['rdfs:isDefinedBy'] = entity.uri
                if self.check_related_slug_field_prefix(slug):
                    facet['label'] =  '(Related) ' + entity.label
                else:
                    facet['label'] = entity.label
                    if id_prefix == '#facet-context':
                        facet['label'] += ' (Context)'
                facet['slug'] = slug
            facet['data-type'] = fsuffix_list[-1]
        facet['type'] = ftype
        return facet

    def check_related_slug_field_prefix(self, slug):
        """ gets the field prefix for a related property
            if it is present in the slug, 
            then return the solr_field prefix otherwise
            return a '' string
        """
        field_prefix = SolrDocument.RELATED_SOLR_FIELD_PREFIX
        prefix_len = len(field_prefix)
        slug_start = slug[:prefix_len]
        if slug_start == field_prefix:
            return True
        else:
            return False

    def clean_related_slug(self, slug):
        """ removes the field_prefix for related slugs """
        field_prefix = SolrDocument.RELATED_SOLR_FIELD_PREFIX
        prefix_len = len(field_prefix)
        slug_start = slug[:prefix_len]
        if slug_start == field_prefix:
            slug = slug[prefix_len:]
        return slug

    def make_facet_value_obj(self,
                             solr_facet_key,
                             solr_facet_value_key,
                             solr_facet_count):
        """ Makes an last-ordered-dict for a facet """
        facet_key_list = solr_facet_value_key.split('___')
        if len(facet_key_list) == 4:
            # ----------------------------
            # Case where facet values are encoded as:
            # slug___data-type___/uri-item-type/uuid___label
            # ----------------------------
            data_type = facet_key_list[1]
            if 'http://' in facet_key_list[2] or 'https://' in facet_key_list[2]:
                is_linked_data = True
            else:
                is_linked_data = False
            fl = FilterLinks()
            fl.base_search_link = self.base_search_link
            fl.base_request_json = self.request_dict_json
            fl.base_r_full_path = self.request_full_path
            fl.spatial_context = self.spatial_context
            fl.partial_param_val_match = is_linked_data  # allow partial matches of parameters.
            output = LastUpdatedOrderedDict()
            slug = facet_key_list[0]
            new_rparams = fl.add_to_request_by_solr_field(solr_facet_key,
                                                          slug)
            output['id'] = fl.make_request_url(new_rparams)
            output['json'] = fl.make_request_url(new_rparams, '.json')
            if is_linked_data:
                output['rdfs:isDefinedBy'] = facet_key_list[2]
            else:
                output['rdfs:isDefinedBy'] = settings.CANONICAL_HOST + facet_key_list[2]
            output['label'] = facet_key_list[3]
            output['count'] = solr_facet_count
            output['slug'] = slug
            output['data-type'] = data_type
        else:
            # ----------------------------
            # Sepcilized cases of non-encoded facet values
            # ----------------------------
            output = self.make_specialized_facet_value_obj(solr_facet_key,
                                                           solr_facet_value_key,
                                                           solr_facet_count)
        return output

    def make_specialized_facet_value_obj(self,
                                         solr_facet_key,
                                         solr_facet_value_key,
                                         solr_facet_count):
        """ makes a facet_value obj for specialzied solr faccets """
        fl = FilterLinks()
        fl.base_search_link = self.base_search_link
        fl.base_request_json = self.request_dict_json
        fl.base_r_full_path = self.request_full_path
        fl.spatial_context = self.spatial_context
        new_rparams = fl.add_to_request_by_solr_field(solr_facet_key,
                                                      solr_facet_value_key)
        output = LastUpdatedOrderedDict()
        output['id'] = fl.make_request_url(new_rparams)
        output['json'] = fl.make_request_url(new_rparams, '.json')
        output['label'] = False
        if solr_facet_key == 'item_type':
            if solr_facet_value_key in QueryMaker.TYPE_URIS:
                output['rdfs:isDefinedBy'] = QueryMaker.TYPE_URIS[solr_facet_value_key]
                entity = self.m_cache.get_entity(output['rdfs:isDefinedBy'])
                if entity:
                    output['label'] = entity.label
        output['count'] = solr_facet_count
        output['slug'] = solr_facet_value_key
        output['data-type'] = 'id'
        return output

    def add_active_facet_field(self, facet_slug, facet_type=False):
        """ adds an active facet field to pass to
            the item record generator object so that
            non-standandard attributes can be added
            to item records based on the user request
        """
        if 'oc-gen' not in facet_slug \
           and facet_type != 'context' \
           and facet_type != 'project':
            if facet_slug not in self.rec_attributes:
                # print('adding:' + facet_slug)
                self.rec_attributes.append(facet_slug)

    def get_requested_attributes(self):
        """ adds to the list of attributes to include
            in individual record results based on
            the GET parameter 'attributes' requested
            by the client
        """
        if isinstance(self.request_dict, dict):
            if 'attributes' in self.request_dict:
                req_att_val = self.request_dict['attributes'][0]
                if ',' in req_att_val:
                    # comma seperated list of values for requested attributes
                    requested_attributes = req_att_val.split(',')
                else:
                    requested_attributes = [req_att_val]
                for req_attribute in requested_attributes:
                    if req_attribute not in self.rec_attributes:
                        # add these to the list of requested attributes
                        self.rec_attributes.append(req_attribute)
            if 'flatten-attributes' in self.request_dict:
                self.flatten_rec_attributes = True

    def get_path_in_dict(self, key_path_list, dict_obj, default=False):
        """ get part of a dictionary object by a list of keys """
        act_dict_obj = dict_obj
        for key in key_path_list:
            if isinstance(act_dict_obj, dict): 
                if key in act_dict_obj:
                    act_dict_obj = act_dict_obj[key]
                    output = act_dict_obj
                else:
                    output = default
                    break
            else:
                output = default
                break
        return output
