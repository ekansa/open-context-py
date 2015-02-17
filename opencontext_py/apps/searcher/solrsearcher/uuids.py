import json
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict


class SolrUUIDs():
    """ methods to make get UUIDs from a solr
        search result JSON document,

        also makes URIs
    """

    def __init__(self):
        self.uuids = []
        self.uris = []
        self.total_found = False
        self.rec_start = False
        self.base_url = settings.CANONICAL_HOST

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
                if 'slug_type_uri_label' in solr_rec:
                    solr_val = solr_rec['slug_type_uri_label']
                    solr_ex = solr_val.split('___')
                    if len(solr_ex) == 4:
                        uri = self.base_url + solr_ex[2]
                        label = solr_ex[3]
                        if uris_only:
                            item = uri
                        else:
                            item = LastUpdatedOrderedDict()
                            item['id'] = uri
                            item['label'] = label
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
                solr_recs = solr_json['response']['docs']
            except KeyError:
                solr_recs = False
        return solr_recs
