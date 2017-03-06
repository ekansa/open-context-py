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
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks


class GeoJsonProjects():

    def __init__(self, solr_json):
        self.geojson_projects = []
        self.projects = {}
        self.total_found = False
        self.filter_request_dict_json = False
        self.geo_pivot = False
        self.chrono_pivot = False
        self.spatial_context = False
        try:
            self.total_found = solr_json['response']['numFound']
        except KeyError:
            self.total_found = False

    def make_project_geojson(self):
        """ makes the project geojson """
        self.process_chronology()
        self.process_geo()

    def process_geo(self):
        """ processes the solr_json 
            discovery geo tiles,
            aggregating to a certain
            depth
        """
        if isinstance(self.geo_pivot, list):
            i = 0
            for proj in self.geo_pivot:
                i += 1
                add_feature = True
                project_key = proj['value']
                proj_ex = project_key.split('___')
                slug = proj_ex[0]
                uri = self.make_url_from_val_string(proj_ex[2])
                href = self.make_url_from_val_string(proj_ex[2], False)
                label = proj_ex[3]
                fl = FilterLinks()
                fl.base_request_json = self.filter_request_dict_json
                fl.spatial_context = self.spatial_context
                new_rparams = fl.add_to_request('proj',
                                                slug)
                if 'response' in new_rparams:
                    new_rparams.pop('response', None)
                record = LastUpdatedOrderedDict()
                record['id'] = fl.make_request_url(new_rparams)
                record['json'] = fl.make_request_url(new_rparams, '.json')
                record['count'] = proj['count']
                record['type'] = 'Feature'
                record['category'] = 'oc-api:geo-project'
                min_date = False
                max_date = False
                if project_key in self.projects:
                    min_date = self.projects[project_key]['min_date']
                    max_date = self.projects[project_key]['max_date']
                if min_date is not False \
                   and max_date is not False:
                    when = LastUpdatedOrderedDict()
                    when['id'] = '#event-' + slug
                    when['type'] = 'oc-gen:formation-use-life'
                    # convert numeric to GeoJSON-LD ISO 8601
                    when['start'] = ISOyears().make_iso_from_float(self.projects[project_key]['min_date'])
                    when['stop'] = ISOyears().make_iso_from_float(self.projects[project_key]['max_date'])
                    record['when'] = when
                if 'pivot' not in proj:
                    add_feature = False
                else:
                    geometry = LastUpdatedOrderedDict()
                    geometry['id'] = '#geo-geom-' + slug
                    geometry['type'] = 'Point'
                    pivot_count_total = 0
                    total_lon = 0
                    total_lat = 0
                    for geo_data in proj['pivot']:
                        pivot_count_total += geo_data['count']
                        gm = GlobalMercator()
                        bounds = gm.quadtree_to_lat_lon(geo_data['value'])
                        mean_lon = (bounds[1] + bounds[3]) / 2
                        mean_lat = (bounds[0] + bounds[2]) / 2
                        total_lon += mean_lon * geo_data['count']
                        total_lat += mean_lat * geo_data['count']
                    weighted_mean_lon = total_lon / pivot_count_total
                    weighted_mean_lat = total_lat / pivot_count_total
                    geometry['coordinates'] = [weighted_mean_lon,
                                               weighted_mean_lat]
                    record['geometry'] = geometry
                # now make a link to search records for this project
                fl = FilterLinks()
                fl.spatial_context = self.spatial_context
                new_rparams = fl.add_to_request('proj',
                                                slug)
                search_link = fl.make_request_url(new_rparams)
                properties = LastUpdatedOrderedDict()
                properties['id'] = '#geo-proj-' + slug
                properties['uri'] = uri
                properties['href'] = href
                properties['search'] = search_link
                properties['label'] = label
                properties['feature-type'] = 'project '
                properties['count'] = proj['count']
                properties['early bce/ce'] = min_date
                properties['late bce/ce'] = max_date
                record['properties'] = properties
                if add_feature:
                    self.geojson_projects.append(record)

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
