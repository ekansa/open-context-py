import json
import geojson
import django.utils.http as http
from django.conf import settings
from django.db import connection
from django.db import models
from django.db.models import Q
from geojson import Feature, Point, Polygon, GeometryCollection, FeatureCollection
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.searcher.solrsearcher.uuids import SolrUUIDs
from opencontext_py.apps.searcher.solrsearcher.recordprops import RecordProperties
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile


class GeoJsonRecords():
    """ methods to make JSON-LD for records returned
        in a solr search; i.e. items in (response.docs)

        This makes GeoJSON-LD features for items with
        geo data.

        TO DO: add JSON-LD for non spatial items
    """

    def __init__(self, response_dict_json):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.mem_cache_obj = MemoryCache()  # memory caching object
        self.response_dict_json = response_dict_json
        self.response_dict = json.loads(response_dict_json)
        self.highlighting = False
        # make values to these fields "flat" not a list
        self.flatten_rec_fields = True
        self.geojson_recs = []
        self.non_geo_recs = []
        self.total_found = False
        self.rec_start = False
        self.min_date = False
        self.max_date = False
        # flatten list of an attribute values to single value
        self.flatten_rec_attributes = False
        # A list of (non-standard) attributes to include in a record
        self.rec_attributes = []
        self.do_complex_geo = False  # get complex (Polygons, etc.) geospatial data from database

    def make_records_from_solr(self, solr_json):
        """ makes geojson-ld point records from a solr response """
        #first do lots of checks to make sure the solr-json is OK
        if isinstance(solr_json, dict):
            try:
                self.total_found = solr_json['response']['numFound']
            except KeyError:
                self.total_found = False
            try:
                self.rec_start = solr_json['response']['start']
            except KeyError:
                self.rec_start = False
            try:
                solr_recs = solr_json['response']['docs']
            except KeyError:
                solr_recs = False
            try:
                self.highlighting = solr_json['highlighting']
            except KeyError:
                self.highlighting = False
            if isinstance(solr_recs, list):
                self.process_solr_recs(solr_recs)

    def process_solr_recs(self, solr_recs):
        """ processes the solr_json to
             make GeoJSON records
        """
        # check database for complex geo objects for all of these records
        db_geo = self.get_recs_complex_geo_features(solr_recs)
        thumbnail_data = self.get_media_thumbs(solr_recs)
        i = self.rec_start
        for solr_rec in solr_recs:
            i += 1
            record = LastUpdatedOrderedDict()
            rec_props_obj = RecordProperties(self.response_dict_json)
            rec_props_obj.mem_cache_obj = self.mem_cache_obj
            rec_props_obj.min_date = self.min_date
            rec_props_obj.max_date = self.max_date
            rec_props_obj.highlighting = self.highlighting
            rec_props_obj.flatten_rec_attributes = self.flatten_rec_attributes
            rec_props_obj.rec_attributes = self.rec_attributes
            rec_props_obj.thumbnail_data = thumbnail_data
            rec_props_obj.parse_solr_record(solr_rec)
            record['id'] = '#record-' + str(i) + '-of-' + str(self.total_found)
            if rec_props_obj.label is False:
                record['label'] = 'Record ' + str(i) + ' of ' + str(self.total_found)
            else:
                record['label'] = rec_props_obj.label
            if rec_props_obj.uri is not False:
                record['rdfs:isDefinedBy'] = rec_props_obj.uri
            if rec_props_obj.latitude is not False \
               and rec_props_obj.longitude is not False:
                # check to see if there are complex geo objects for this item
                geometry = self.get_item_complex_geo_feature(i,
                                                             solr_rec['uuid'],
                                                             db_geo)
                if geometry is False:
                    geometry = LastUpdatedOrderedDict()
                    geometry['id'] = '#geo-rec-geom-' + str(i) + '-of-' + str(self.total_found)
                    geometry['type'] = 'Point'
                    geometry['coordinates'] = [rec_props_obj.longitude,
                                               rec_props_obj.latitude]
                record['type'] = 'Feature'
                record['category'] = 'oc-api:geo-record'
                record['geometry'] = geometry
            else:
                geometry = False
            if rec_props_obj.early_date is not False \
               and rec_props_obj.late_date is not False:
                when = LastUpdatedOrderedDict()
                when['id'] = '#event-rec-when-' + str(i) + '-of-' + str(self.total_found)
                when['type'] = 'oc-gen:formation-use-life'
                # convert numeric to GeoJSON-LD ISO 8601
                when['start'] = ISOyears().make_iso_from_float(rec_props_obj.early_date)
                when['stop'] = ISOyears().make_iso_from_float(rec_props_obj.late_date)
                record['when'] = when
            # start adding GeoJSON properties
            properties = LastUpdatedOrderedDict()
            properties['id'] = '#rec-' + str(i) + '-of-' + str(self.total_found)
            properties['feature-type'] = 'item record'
            properties['uri'] = rec_props_obj.uri
            properties['href'] = rec_props_obj.href
            properties['citation uri'] = rec_props_obj.cite_uri
            properties['label'] = rec_props_obj.label
            properties['project label'] = rec_props_obj.project_label
            properties['project href'] = rec_props_obj.project_href
            properties['context label'] = rec_props_obj.context_label
            properties['context href'] = rec_props_obj.context_href
            properties['early bce/ce'] = rec_props_obj.early_date
            properties['late bce/ce'] = rec_props_obj.late_date
            properties['item category'] = rec_props_obj.category
            if rec_props_obj.snippet is not False:
                properties['snippet'] = rec_props_obj.snippet
            properties['thumbnail'] = rec_props_obj.thumbnail_scr
            properties['published'] = rec_props_obj.published
            properties['updated'] = rec_props_obj.updated
            if isinstance(rec_props_obj.other_attributes, list):
                for attribute in rec_props_obj.other_attributes:
                    prop_key = attribute['property']
                    prop_key = rec_props_obj.prevent_attribute_key_collision(properties,
                                                                             prop_key)
                    if self.flatten_rec_attributes:
                        properties[prop_key] = attribute['value']
                    else:
                        properties[prop_key] = attribute['values_list']
            record['properties'] = properties
            if geometry is not False:
                # add to list of geospatial records
                self.geojson_recs.append(record)
            else:
                # case when the record is not GeoSpatial in nature
                item = SolrUUIDs().make_item_dict_from_rec_props_obj(rec_props_obj, False)
                self.non_geo_recs.append(item)

    def get_item_complex_geo_feature(self, i, uuid, db_geo):
        """ gets complex geo-features """
        geometry = False
        if self.do_complex_geo and isinstance(db_geo, dict):
            # print('Looking for geo on: ' + uuid)
            if uuid in db_geo:
                # print('yeah!')
                try:
                    geometry = LastUpdatedOrderedDict()
                    geometry['id'] = '#geo-rec-geom-' + str(i) + '-of-' + str(self.total_found)
                    geometry['type'] = db_geo[uuid].ftype
                    geometry['coordinates'] = json.loads(db_geo[uuid].coordinates)
                except:
                    geometry = False
        return geometry

    def get_recs_complex_geo_features(self, solr_recs):
        """ gets complex solr features for
            all the UUIDs in the solr records
            cuts down on the number of queries to get
            them all at once
        """
        db_geo = {}
        if self.do_complex_geo:
            uuids = []
            for solr_rec in solr_recs:
                uuids.append(solr_rec['uuid'])
            geo_data = Geospace.objects\
                               .filter(uuid__in=uuids)\
                               .exclude(ftype__in=['Point',
                                                   'point'])
            for geo in geo_data:
                if len(geo.coordinates) > 0:
                    if geo.uuid not in db_geo:
                        db_geo[geo.uuid] = geo
        # print('Number complex: ' + str(len(db_geo)))
        return db_geo

    def get_media_thumbs(self, solr_recs):
        """ gets media thumbnail items """
        thumb_results = {}
        not_media_uuids = []
        media_uuids = []
        rec_props_obj = RecordProperties(self.response_dict_json)
        for solr_rec in solr_recs:
            item = rec_props_obj.get_solr_record_uuid_type(solr_rec)
            if item is not False:
                uuid = item['uuid']
                if item['item_type'] != 'media':
                    not_media_uuids.append(uuid)
                else:
                    media_uuids.append(uuid)
                thumb_results[uuid] = False
        if len(not_media_uuids) > 0:
            rows = self.get_thumbs_for_non_media(not_media_uuids)
            for row in rows:
                uuid = row['uuid']
                thumb_obj = {}
                thumb_obj['href'] = self.base_url + '/media/' + row['media_uuid']
                thumb_obj['uri'] = settings.CANONICAL_HOST + '/media/' + row['media_uuid']
                thumb_obj['scr'] = row['file_uri']
                if thumb_results[uuid] is False:
                    thumb_results[uuid] = thumb_obj
        if len(media_uuids) > 0:
            thumbs = Mediafile.objects\
                              .filter(uuid__in=media_uuids,
                                      file_type='oc-gen:thumbnail')
            for thumb in thumbs:
                uuid = thumb.uuid
                thumb_obj = {}
                thumb_obj['href'] = self.base_url + '/media/' + thumb.uuid
                thumb_obj['uri'] = settings.CANONICAL_HOST + '/media/' + thumb.uuid
                thumb_obj['scr'] = thumb.file_uri
                thumb_results[uuid] = thumb_obj
        return thumb_results

    def get_thumbs_for_non_media(self, uuid_list):
        q_uuids = self.make_quey_uuids(uuid_list)
        query = ('SELECT ass.uuid AS uuid, m.file_uri AS file_uri, '
                 'm.uuid AS media_uuid '
                 'FROM oc_assertions AS ass '
                 'JOIN oc_mediafiles AS m ON ass.object_uuid = m.uuid '
                 'AND m.file_type=\'oc-gen:thumbnail\'  '
                 'WHERE ass.uuid IN (' + q_uuids + ') '
                 'GROUP BY ass.uuid,  m.file_uri, m.uuid; ')
        cursor = connection.cursor()
        cursor.execute(query)
        rows = self.dictfetchall(cursor)
        return rows

    def make_quey_uuids(self, uuid_list):
        """ makes a string for uuid list query """
        uuid_q = []
        for uuid in uuid_list:
            uuid = '\'' + uuid + '\''
            uuid_q.append(uuid)
        return ', '.join(uuid_q)

    def dictfetchall(self, cursor):
        """ Return all rows from a cursor as a dict """
        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]
