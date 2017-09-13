import math
import re
import json
import geojson
from django.conf import settings
from geojson import Feature, Point, Polygon, GeometryCollection, FeatureCollection
from urllib.parse import urlparse, parse_qs
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks


class JsonLDchronology():

    def __init__(self, solr_json):
        self.chrono_tiles = []
        self.total_found = False
        self.filter_request_dict_json = False
        self.spatial_context = False
        self.min_tile_depth = 12
        self.aggregation_depth = 16
        self.min_tile_count = 14
        self.max_depth = ChronoTile.MAX_TILE_DEPTH
        self.limiting_tile = False
        self.ok_for_suggested_tile_depth = True
        self.min_date = False  # bce / ce
        self.max_date = False  # bce / ce
        self.exclude_before = False  # bce / ce
        self.exclude_after = False # bce / ce
        try:
            self.total_found = solr_json['response']['numFound']
        except KeyError:
            self.total_found = False

    def process_solr_tiles(self, solr_tiles):
        """ processes the solr_json 
            discovery geo tiles,
            aggregating to a certain
            depth
        """
        # first aggregate counts for tile that belong togther
        aggregate_tiles = LastUpdatedOrderedDict()
        i = -1
        t = 0
        if len(solr_tiles) <= self.min_tile_count:
            # it's half of the solr_tile list, because the first item is the key
            # 2nd item is the count.
            # don't aggregate if there's not much to aggregate
            self.aggregation_depth = self.max_depth
        else:
            # suggest tile-depth
            self.aggregation_depth = self.get_suggested_tile_depth(solr_tiles)
        for tile_key in solr_tiles[::2]:
            t += 1
            i += 2
            solr_facet_count = solr_tiles[i]
            if tile_key != 'false':
                if self.limiting_tile is False:
                    ok_to_add = True
                else:
                    # constrain to show facets ONLY within
                    # the current queried tile
                    if self.limiting_tile in tile_key:
                        ok_to_add = True
                    else:
                        ok_to_add = False
                if ok_to_add:
                    # first get full date range for
                    # facets that are OK to add
                    chrono_t = ChronoTile()
                    dates = chrono_t.decode_path_dates(tile_key)
                    if isinstance(dates, dict):
                        # chronotupe is valid, now check to make sure we
                        # actually want it in the results
                        if self.exclude_before is not False:
                            if dates['earliest_bce'] < self.exclude_before:
                                # too early before the exclude before date
                                ok_to_add = False
                        if self.exclude_after is not False:
                            if dates['latest_bce'] > self.exclude_after:
                                # to late, after the exclude after date
                                ok_to_add = False
                    else:
                        # not valid tile, so don't add
                        ok_to_add = False
                if ok_to_add:
                    if isinstance(dates, dict):
                        if self.min_date is False:
                            self.min_date = dates['earliest_bce']
                            self.max_date = dates['latest_bce']
                        else:
                            if self.min_date > dates['earliest_bce']:
                                self.min_date = dates['earliest_bce']
                            if self.max_date < dates['latest_bce']:
                                self.max_date = dates['latest_bce']
                    # now aggregrate the OK to use facets
                    trim_tile_key = tile_key[:self.aggregation_depth]
                    if trim_tile_key not in aggregate_tiles:
                        aggregate_tiles[trim_tile_key] = 0
                    aggregate_tiles[trim_tile_key] += solr_facet_count
        # now generate GeoJSON for each tile region
        # print('Chronology tiles: ' + str(t) + ' reduced to ' + str(len(aggregate_tiles)))
        # --------------------------------------------
        # code to sort the list of tiles by start date and time span
        # --------------------------------------------
        sorting_ranges = []
        for tile_key, aggregate_count in aggregate_tiles.items():
            chrono_t = ChronoTile()
            dates = chrono_t.decode_path_dates(tile_key)
            dates['tile_key'] = tile_key
            sorting_ranges.append(dates)
        # now sort by earliest bce, then reversed latest bce
        # this makes puts early dates with longest timespans first
        sorted_ranges = sorted(sorting_ranges,
                               key=lambda k: (k['earliest_bce'],
                                              -k['latest_bce']))
        sorted_tiles = LastUpdatedOrderedDict()
        for sort_range in sorted_ranges:
            tile_key = sort_range['tile_key']
            sorted_tiles[tile_key] = aggregate_tiles[tile_key]
        i = 0
        for tile_key, aggregate_count in sorted_tiles.items():
            i += 1
            fl = FilterLinks()
            fl.base_request_json = self.filter_request_dict_json
            fl.spatial_context = self.spatial_context
            new_rparams = fl.add_to_request('form-chronotile',
                                            tile_key)
            record = LastUpdatedOrderedDict()
            record['id'] = fl.make_request_url(new_rparams)
            record['json'] = fl.make_request_url(new_rparams, '.json')
            record['count'] = aggregate_count
            record['category'] = 'oc-api:chrono-facet'
            chrono_t = ChronoTile()
            dates = chrono_t.decode_path_dates(tile_key)
            if self.exclude_before is not False:
                if dates['earliest_bce'] < self.exclude_before:
                    dates['earliest_bce'] = self.exclude_before
            if self.exclude_after is not False:
                if dates['latest_bce'] > self.exclude_after:
                    dates['latest_bce'] = self.exclude_after
            # convert numeric to GeoJSON-LD ISO 8601
            record['start'] = ISOyears().make_iso_from_float(dates['earliest_bce'])
            record['stop'] = ISOyears().make_iso_from_float(dates['latest_bce'])
            properties = LastUpdatedOrderedDict()
            properties['early bce/ce'] = dates['earliest_bce']
            properties['late bce/ce'] = dates['latest_bce']
            record['properties'] = properties
            self.chrono_tiles.append(record)

    def set_aggregation_depth(self, request_dict_json):
        """ sets the aggregatin depth for
            aggregating chronological tiles

            aggregation depth varies between 3 and 20
            with 32 being the most fine-grain, specific
            level of time specificity
        """
        # now set up for filter requests, by removing the
        request_dict = json.loads(request_dict_json)
        filter_request_dict = request_dict
        if 'form-chronotile' in request_dict:
            self.limiting_tile = request_dict['form-chronotile'][0]
            self.aggregation_depth = len(self.limiting_tile) + 2
            filter_request_dict.pop('form-chronotile', None)  # so as to set up for filter links
        if 'chronodeep' in request_dict:
            deep = request_dict['chronodeep'][0]
            # filter out non numeric characters
            deep = re.sub(r'[^0-9]', r'', deep)
            if len(deep) > 0:
                self.ok_for_suggested_tile_depth = False
                self.aggregation_depth = int(float(deep))
        if self.aggregation_depth < 6:
            self.aggregation_depth = 6
        if self.aggregation_depth > self.max_depth:
            self.aggregation_depth = self.max_depth
        # now make sure we've got a 'clean' request dict
        # to make filter links
        self.filter_request_dict_json = json.dumps(filter_request_dict,
                                                   ensure_ascii=False,
                                                   indent=4)
        return self.aggregation_depth

    def set_date_exclusions_from_request_params(self, request_dict_json):
        """ sets date exclusions from the request parameters """
        request_dict = json.loads(request_dict_json)
        if 'form-start' in request_dict:
            self.exclude_before = self.validate_request_date(request_dict['form-start'][0])
        if 'form-stop' in request_dict:
            self.exclude_after = self.validate_request_date(request_dict['form-stop'][0])

    def validate_request_date(self, date_str):
        """ validates a date str, converts to integer """
        val_date = False
        try:
            val_date = int(float(date_str))
        except:
            val_date = False
        return val_date

    def get_suggested_tile_depth(self, solr_tiles):
        """ gets the suggested tile depth
        """
        if len(solr_tiles) <= self.min_tile_count:
            # don't aggregate if there's not much to aggregate
            self.aggregation_depth = self.max_depth
        elif self.ok_for_suggested_tile_depth:
            # only do this if we've got more than
            # the minimum number of chronotiles to aggregate
            # also only do this if we haven't gotten a tile depth by
            # other means
            tile_depths = LastUpdatedOrderedDict()
            t_depth = self.min_tile_depth - 1
            keep_looping = True
            while keep_looping:
                t_depth += 1
                tile_depths[t_depth] = []
                # print('now' + str(self.min_tile_count + exclude_add))
                # print('check: ' + str(t_depth) + ' ' + str(len(tile_depths[t_depth])))
                if t_depth > self.max_depth:
                    keep_looping = False
                else:
                    for tile_key in solr_tiles[::2]:
                        if tile_key != 'false':
                            tile_key_at_depth = tile_key[:t_depth]
                            if tile_key_at_depth not in tile_depths[t_depth]:
                                # we haven't seen this tile yet, so add it
                                tile_depths[t_depth].append(tile_key_at_depth)
                            if len(tile_depths[t_depth]) >= self.min_tile_count:
                                self.aggregation_depth = t_depth
                                keep_looping = False
                                break
            # add some more to the aggregation depth based on date filters
            self.set_aggregation_depth_from_exclusion_range()
        else:
            pass
        return self.aggregation_depth

    def set_aggregation_depth_from_exclusion_range(self):
        """ changes an aggregation depth based on the scale of the
            time range
        """
        if self.exclude_before is not False:
            latest = 2000
            if self.exclude_after is not False:
                latest = self.exclude_after
            span = abs(latest - self.exclude_before)
            try:
                span_mag = round(math.log(span, 10), 0)  
                span_add = int(span_mag)
                span_add = 6 - span_add
                if span_add < 0:
                    span_add = 0
            except:
                span_add = 0
            print('span-add: ' + str(span_add))
            self.aggregation_depth += span_add
            

    def make_url_from_val_string(self,
                                 partial_url,
                                 use_cannonical=True):
        """ parses a solr value if it has
            '___' delimiters, to get the URI part
            string.
            if it's already a URI part, it makes
            a URL
        """
        if use_cannonical:
            base_url = settings.CANONICAL_HOST
        else:
            base_url = settings.DEPLOYED_HOST
            if settings.DEBUG:
                base_url = 'http://127.0.0.1:8000'
        solr_parts = self.parse_solr_value_parts(partial_url)
        if isinstance(solr_parts, dict):
            partial_url = solr_parts['uri']
        if 'http://' not in partial_url \
           and 'https://' not in partial_url:
            url = base_url + partial_url
        else:
            url = partial_url
        return url

    def parse_solr_value_parts(self, solr_value):
        """ parses a solr_value string into
            slug, solr-data-type, uri, and label
            parts
        """
        output = False
        if '___' in solr_value:
            solr_ex = solr_value.split('___')
            if len(solr_ex) == 4:
                output = {}
                output['slug'] = solr_ex[0]
                output['data_type'] = solr_ex[1]
                output['uri'] = solr_ex[2]
                output['label'] = solr_ex[3]
        return output

    def get_key_val(self, key, dict_obj):
        """ returns the value associated
            with a key, if the key exists
            else, none
        """
        output = None
        if isinstance(dict_obj, dict):
            if key in dict_obj:
                output = dict_obj[key]
        return output
