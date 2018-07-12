import re
import json
import geojson
import copy
from django.conf import settings
from geojson import Feature, Point, Polygon, MultiPolygon, GeometryCollection, FeatureCollection
from geojson import MultiPoint, MultiLineString, LineString
from urllib.parse import urlparse, parse_qs
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.libs.validategeojson import ValidateGeoJson
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.subjects.models import Subject


class GeoJsonPolygons():

    def __init__(self, solr_json):
        self.geojson_features = []
        self.subjects_objs = {}
        self.geo_objs = {}
        self.total_found = False
        self.filter_request_dict_json = False
        self.spatial_context = False
        self.response_zoom_scope = 0  # the geographic zoom level that fits the current response
        self.polygon_min_zoom_scope = 15  # the self.response_zoom_scope must be larger than this
        self.min_date = False
        self.max_date = False
        try:
            self.total_found = solr_json['response']['numFound']
        except KeyError:
            self.total_found = False

    def process_solr_polygons(self, solr_polygons):
        """ processes the solr_json 
            discovery geo tiles,
            aggregating to a certain
            depth
        """
        if self.response_zoom_scope >= self.polygon_min_zoom_scope:
            # we're at a zoom level small enough to make it
            # worthwile to return complex contained-in polygon features
            self.get_polygon_db_objects(solr_polygons)
            i = 0
            cnt_i = -1
            for poly_key in solr_polygons[::2]:
                cnt_i += 2
                solr_facet_count = solr_polygons[cnt_i]
                parsed_key = self.parse_solr_value_parts(poly_key)
                # print('Key: ' + str(parsed_key))
                uuid = parsed_key['uuid']
                if isinstance(uuid, str):
                    if uuid in self.subjects_objs \
                       and uuid in self.geo_objs:
                        # we have Subjects and Geospatial models for this
                        # uuid
                        subj_obj = self.subjects_objs[uuid]
                        geo_obj = self.geo_objs[uuid]
                        i += 1
                        fl = FilterLinks()
                        fl.base_request_json = self.filter_request_dict_json
                        fl.spatial_context = self.spatial_context
                        new_rparams = fl.add_to_request('path',
                                                        subj_obj.context)
                        record = LastUpdatedOrderedDict()
                        record['id'] = fl.make_request_url(new_rparams)
                        record['json'] = fl.make_request_url(new_rparams, '.json')
                        record['count'] = solr_facet_count
                        record['type'] = 'Feature'
                        record['category'] = 'oc-api:geo-contained-in-feature'
                        if self.min_date is not False \
                           and self.max_date is not False:
                            when = LastUpdatedOrderedDict()
                            when['id'] = '#event-feature-' + uuid
                            when['type'] = 'oc-gen:formation-use-life'
                            # convert numeric to GeoJSON-LD ISO 8601
                            when['start'] = ISOyears().make_iso_from_float(self.min_date)
                            when['stop'] = ISOyears().make_iso_from_float(self.max_date)
                            record['when'] = when
                        geometry = LastUpdatedOrderedDict()
                        geometry['id'] = '#geo-disc-feature-geom-' + uuid
                        geometry['type'] =  geo_obj.ftype
                        coord_obj = json.loads(geo_obj.coordinates)
                        v_geojson = ValidateGeoJson()
                        coord_obj = v_geojson.fix_geometry_rings_dir(geo_obj.ftype,
                                                                     coord_obj)
                        geometry['coordinates'] = coord_obj
                        record['geometry'] = geometry
                        properties = LastUpdatedOrderedDict()
                        properties['id'] = '#geo-disc-feature-' + uuid
                        properties['href'] = record['id']
                        properties['item-href'] = parsed_key['href']
                        properties['label'] = subj_obj.context
                        properties['feature-type'] = 'containing-region'
                        properties['count'] = solr_facet_count
                        properties['early bce/ce'] = self.min_date
                        properties['late bce/ce'] = self.max_date
                        record['properties'] = properties
                        dump = json.dumps(record,
                                          ensure_ascii=False, indent=4)
                        geojson_obj = geojson.loads(dump)
                        self.geojson_features.append(record)

    def get_polygon_db_objects(self, solr_polygons):
        """ processes the solr_json 
            discovery geo tiles,
            aggregating to a certain
            depth
        """
        poly_uuids = []
        for poly_key in solr_polygons[::2]:
            parsed_key = self.parse_solr_value_parts(poly_key)
            uuid = parsed_key['uuid']
            if isinstance(uuid, str):
                if uuid not in poly_uuids:
                    poly_uuids.append(uuid)
        if len(poly_uuids) > 0:
            sub_objs = Subject.objects.filter(uuid__in=poly_uuids)
            for sub_obj in sub_objs:
                uuid = sub_obj.uuid
                self.subjects_objs[uuid] = sub_obj
            exclude_types = ['Point', 'point']
            geo_objs = Geospace.objects\
                               .filter(uuid__in=poly_uuids)\
                               .exclude(ftype__in=exclude_types)
            for geo_obj in geo_objs:
                uuid = geo_obj.uuid
                
                self.geo_objs[uuid] = geo_obj

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
                output['uuid'] = None
                if '/' in output['uri']:
                    uri_ex = output['uri'].split('/')
                    if len(uri_ex) > 0:
                        output['uuid'] = uri_ex[-1]
                output['href'] = self.make_url_from_val_string(output['uri'])
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
