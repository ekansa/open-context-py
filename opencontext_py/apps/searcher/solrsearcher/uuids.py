import json
from django.conf import settings


class SolrUUIDs():
    """ methods to make get UUIDs from a solr
        search result JSON document
    """

    def __init__(self):
        self.uuids = []
        self.total_found = False
        self.rec_start = False

    def make_uuids_from_solr(self, solr_json):
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
            if isinstance(solr_recs, list):
                self.process_solr_recs(solr_recs)
        return self.uuids

    def process_solr_recs(self, solr_recs):
        """ processes the solr_json to
             make GeoJSON records
        """
        i = self.rec_start
        for solr_rec in solr_recs:
            if 'uuid' in solr_rec:
                uuid = solr_rec['uuid']
                self.uuids.append(uuid)
