import re
import json
import geojson
from django.conf import settings
from geojson import Feature, Point, Polygon, GeometryCollection, FeatureCollection
from urllib.parse import urlparse, parse_qs
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks


class GeoJsonProjects():

    def __init__(self, solr_json):
        self.geojson_projects = []
        self.projects = {}
        self.total_found = False
        self.filter_request_dict_json = False
        self.geo_pivot = False
        self.chrono_pivot = False
        try:
            self.total_found = solr_json['response']['numFound']
        except KeyError:
            self.total_found = False

    def make_project_geojson(self):
        """ makes the project geojson """
        self.process_chronology()

    def process_solr_tiles(self, solr_tiles):
        """ processes the solr_json 
            discovery geo tiles,
            aggregating to a certain
            depth
        """
        # first aggregate counts for tile that belong togther
        aggregate_tiles = {}
        i = -1
        t = 0
        all_tile_lens = []
        for tile_key in solr_tiles[::2]:
            t += 1
            i += 2
            solr_facet_count = solr_tiles[i]
            # to compute the main tile precision level
            # for this filtered set of data
            tile_key_len = len(tile_key)
            if tile_key_len > 6:
                all_tile_lens.append(tile_key_len)
            trim_tile_key = tile_key[:self.aggregation_depth]
            if trim_tile_key not in aggregate_tiles:
                aggregate_tiles[trim_tile_key] = 0
            aggregate_tiles[trim_tile_key] += solr_facet_count
        if len(all_tile_lens) > 0:
            # gets the average tile depth, so clients don't over-zoom
            mean_tile_len = sum(all_tile_lens) / len(all_tile_lens)
            # print(str(mean_tile_len))
            self.max_tile_precision = round(mean_tile_len)
        # now generate GeoJSON for each tile region
        # print('Total tiles: ' + str(t) + ' reduced to ' + str(len(aggregate_tiles)))
        i = 0
        for tile_key, aggregate_count in aggregate_tiles.items():
            i += 1
            add_region = True
            fl = FilterLinks()
            fl.base_request_json = self.filter_request_dict_json
            fl.spatial_context = self.spatial_context
            new_rparams = fl.add_to_request('disc-geotile',
                                            tile_key)
            record = LastUpdatedOrderedDict()
            record['id'] = fl.make_request_url(new_rparams)
            record['json'] = fl.make_request_url(new_rparams, '.json')
            record['count'] = aggregate_count
            record['type'] = 'Feature'
            record['category'] = 'oc-api:geo-facet'
            if self.min_date is not False \
               and self.max_date is not False:
                when = LastUpdatedOrderedDict()
                when['id'] = '#event-' + tile_key
                when['type'] = 'oc-gen:formation-use-life'
                # convert numeric to GeoJSON-LD ISO 8601
                when['start'] = ISOyears().make_iso_from_float(self.min_date)
                when['stop'] = ISOyears().make_iso_from_float(self.max_date)
                record['when'] = when
            gm = GlobalMercator()
            geo_coords = gm.quadtree_to_geojson_poly_coords(tile_key)
            geometry = LastUpdatedOrderedDict()
            geometry['id'] = '#geo-disc-tile-geom-' + tile_key
            geometry['type'] = 'Polygon'
            geometry['coordinates'] = geo_coords
            record['geometry'] = geometry
            properties = LastUpdatedOrderedDict()
            properties['id'] = '#geo-disc-tile-' + tile_key
            properties['href'] = record['id']
            properties['label'] = 'Discovery region (' + str(i) + ')'
            properties['feature-type'] = 'discovery region (facet)'
            properties['count'] = aggregate_count
            properties['early bce/ce'] = self.min_date
            properties['late bce/ce'] = self.max_date
            record['properties'] = properties
            if len(tile_key) >= 6:
                if tile_key[:6] == '211111':
                    # no bad coordinates (off 0, 0 coast of Africa)
                    add_region = False  # don't display items without coordinates
            if add_region:
                self.geojson_regions.append(record)

    def process_chronology(self):
        """ sets the aggregatin depth for
            aggregating geospatial tiles

            aggregation depth varies between 3 and 20
            with 20 being the most fine-grain, specific
            level of spatial depth
        """
        if isinstance(self.chrono_pivot, list):
            for proj in self.chrono_pivot:
                project_key = proj['value']
                if project_key not in self.projects:
                    self.projects[project_key] = {}
                min_date = False
                max_date = False
                if 'pivot' in proj:
                    for chrono_data in proj['pivot']:
                        chrono_t = ChronoTile()
                        dates = chrono_t.decode_path_dates(chrono_data['value'])
                        if isinstance(dates, dict):
                            if min_date is False:
                                min_date = dates['earliest_bce']
                                max_date = dates['latest_bce']
                            else:
                                if min_date > dates['earliest_bce']:
                                    min_date = dates['earliest_bce']
                                if max_date < dates['latest_bce']:
                                    max_date = dates['latest_bce']
                self.projects[project_key]['min_date'] = min_date
                self.projects[project_key]['max_date'] = max_date

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
