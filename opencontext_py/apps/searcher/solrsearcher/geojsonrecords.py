import json
import geojson
import django.utils.http as http
from django.conf import settings
from geojson import Feature, Point, Polygon, GeometryCollection, FeatureCollection
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.searcher.solrsearcher.uuids import SolrUUIDs
from opencontext_py.apps.searcher.solrsearcher.recordprops import RecordProperties


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
        self.entities = {}
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
        i = self.rec_start
        for solr_rec in solr_recs:
            i += 1
            record = LastUpdatedOrderedDict()
            rec_props_obj = RecordProperties(self.response_dict_json)
            rec_props_obj.entities = self.entities
            rec_props_obj.min_date = self.min_date
            rec_props_obj.max_date = self.max_date
            rec_props_obj.highlighting = self.highlighting
            rec_props_obj.flatten_rec_attributes = self.flatten_rec_attributes
            rec_props_obj.rec_attributes = self.rec_attributes
            rec_props_obj.parse_solr_record(solr_rec)
            self.entities = rec_props_obj.entities  # add to existing list of entities, reduce lookups
            record['id'] = '#record-' + str(i) + '-of-' + str(self.total_found)
            if rec_props_obj.label is False:
                record['label'] = 'Record ' + str(i) + ' of ' + str(self.total_found)
            else:
                record['label'] = rec_props_obj.label
            if rec_props_obj.uri is not False:
                record['rdfs:isDefinedBy'] = rec_props_obj.uri
            if rec_props_obj.latitude is not False \
               and rec_props_obj.longitude is not False:
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
                when['start'] = rec_props_obj.early_date
                when['stop'] = rec_props_obj.late_date
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
