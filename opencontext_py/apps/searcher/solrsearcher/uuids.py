import json
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.apps.searcher.solrsearcher.recordprops import RecordProperties


class SolrUUIDs():
    """ methods to make get UUIDs from a solr
        search result JSON document,

        also makes URIs
    """

    def __init__(self, response_dict_json=False):
        self.uuids = []
        self.uris = []
        self.mem_cache_obj = MemoryCache()  # memory caching object
        self.response_dict_json = response_dict_json
        self.highlighting = False
        # make values to these fields "flat" not a list
        self.flatten_rec_fields = True
        self.total_found = False
        self.rec_start = False
        self.min_date = False
        self.max_date = False
        # flatten list of an attribute values to single value
        self.flatten_rec_attributes = False
        # A list of (non-standard) attributes to include in a record
        self.rec_attributes = []

    def make_uuids_from_solr(self, solr_json):
        """ makes geojson-ld point records from a solr response """
        #first do lots of checks to make sure the solr-json is OK
        solr_recs = self.extract_solr_recs(solr_json)
        if isinstance(solr_recs, list):
            for solr_rec in solr_recs:
                if 'uuid' in solr_rec:
                    uuid = solr_rec['uuid']
                    self.uuids.append(uuid)
        return self.uuids

    def make_uris_from_solr(self, solr_json, uris_only=True):
        """ processes the solr_json to
             make GeoJSON records
        """
        solr_recs = self.extract_solr_recs(solr_json)
        if isinstance(solr_recs, list):
            for solr_rec in solr_recs:
                rec_props_obj = RecordProperties(self.response_dict_json)
                rec_props_obj.mem_cache_obj = self.mem_cache_obj
                rec_props_obj.min_date = self.min_date
                rec_props_obj.max_date = self.max_date
                rec_props_obj.highlighting = self.highlighting
                rec_props_obj.flatten_rec_attributes = self.flatten_rec_attributes
                rec_props_obj.rec_attributes = self.rec_attributes
                item_ok = rec_props_obj.get_item_basics(solr_rec)
                if item_ok:
                    if uris_only:
                        item = rec_props_obj.uri
                    else:
                        rec_props_obj.parse_solr_record(solr_rec)
                        self.entities = rec_props_obj.entities  # add to existing list of entities, reduce lookups
                        item = self.make_item_dict_from_rec_props_obj(rec_props_obj)
                    self.uris.append(item)
        return self.uris

    def make_item_dict_from_rec_props_obj(self, rec_props_obj, cannonical=True):
        """ makes item dictionary object from a record prop obj """
        item = LastUpdatedOrderedDict()
        item['uri'] = rec_props_obj.uri
        if cannonical is False:
            item['href'] = rec_props_obj.href
        item['citation uri'] = rec_props_obj.cite_uri
        item['label'] = rec_props_obj.label
        item['project label'] = rec_props_obj.project_label
        if cannonical:
            item['project uri'] = rec_props_obj.project_uri
        else:
            item['project href'] = rec_props_obj.project_href
        item['context label'] = rec_props_obj.context_label
        if cannonical:
            item['context uri'] = rec_props_obj.context_uri
        else:
            item['context href'] = rec_props_obj.context_href
        item['latitude'] = rec_props_obj.latitude
        item['longitude'] = rec_props_obj.longitude
        item['early bce/ce'] = rec_props_obj.early_date
        item['late bce/ce'] = rec_props_obj.late_date
        item['item category'] = rec_props_obj.category
        if rec_props_obj.snippet is not False:
            item['snippet'] = rec_props_obj.snippet
        item['published'] = rec_props_obj.published
        item['updated'] = rec_props_obj.updated
        if isinstance(rec_props_obj.other_attributes, list):
            for attribute in rec_props_obj.other_attributes:
                prop_key = attribute['property']
                prop_key = rec_props_obj.prevent_attribute_key_collision(item,
                                                                         prop_key)
                if self.flatten_rec_attributes:
                    item[prop_key] = attribute['value']
                else:
                    item[prop_key] = attribute['values_list']
        return item

    def extract_solr_recs(self, solr_json):
        """ extracts solr_recs along with
           some basic metadata from solr_json
        """
        solr_recs = False
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
                self.highlighting = solr_json['highlighting']
            except KeyError:
                self.highlighting = False
            try:
                solr_recs = solr_json['response']['docs']
            except KeyError:
                solr_recs = False
        return solr_recs
