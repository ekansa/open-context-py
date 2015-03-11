import json
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.searcher.solrsearcher.recordprops import RecordProperties


class SolrUUIDs():
    """ methods to make get UUIDs from a solr
        search result JSON document,

        also makes URIs
    """

    def __init__(self, response_dict_json):
        self.uuids = []
        self.uris = []
        self.entities = {}
        self.response_dict_json = response_dict_json
        self.highlighting = False
        # make values to these fields "flat" not a list
        self.flatten_rec_fields = True
        self.total_found = False
        self.rec_start = False
        self.min_date = False
        self.max_date = False

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
                rec_props_obj.entities = self.entities
                rec_props_obj.min_date = self.min_date
                rec_props_obj.max_date = self.max_date
                rec_props_obj.highlighting = self.highlighting
                item_ok = rec_props_obj.get_item_basics(solr_rec)
                if item_ok:
                    if uris_only:
                        item = rec_props_obj.uri
                    else:
                        item = LastUpdatedOrderedDict()
                        rec_props_obj.parse_solr_record(solr_rec)
                        self.entities = rec_props_obj.entities  # add to existing list of entities, reduce lookups
                        item['uri'] = rec_props_obj.uri
                        item['citation uri'] = rec_props_obj.cite_uri
                        item['label'] = rec_props_obj.label
                        item['project label'] = rec_props_obj.project_label
                        item['project uri'] = rec_props_obj.project_uri
                        item['context label'] = rec_props_obj.context_label
                        item['context uri'] = rec_props_obj.context_uri
                        item['latitude'] = rec_props_obj.latitude
                        item['longitude'] = rec_props_obj.longitude
                        item['early bce/ce'] = rec_props_obj.early_date
                        item['late bce/ce'] = rec_props_obj.late_date
                        item['item category'] = rec_props_obj.category
                        if rec_props_obj.snippet is not False:
                            item['snippet'] = rec_props_obj.snippet
                    self.uris.append(item)
        return self.uris

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
