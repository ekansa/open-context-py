import json
import requests
from django.conf import settings
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.apps.searcher.solrsearcher.uuids import SolrUUIDs


class SolrDirect():
    """ methods to request Solr json results
        directly, only by passing a URL

        This is useful for making requests generated
        through the Solr Administrative interface
    """

    def __init__(self):
        # Connect to Solr
        self.solr = SolrConnection().connection
        self.request_error = False

    def get_result_uuids(self, request_url):
        """ gets result uuids from
            a request directly to solr
        """
        uuids = []
        solr_json = self.get_solr_result_json(request_url)
        if isinstance(solr_json, dict):
            s_uuids = SolrUUIDs()
            uuids = s_uuids.make_uuids_from_solr(solr_json)
        else:
            print('Uh oh. No Solr JSON')
        return uuids

    def get_solr_result_json(self, request_url):
        """ gets request based on a url """
        try:
            r = requests.get(request_url,
                             timeout=60)
            self.request_url = r.url
            r.raise_for_status()
            json_r = r.json()
        except:
            self.request_error = True
            json_r = False
        return json_r

    def process_solr_recs(self, solr_recs):
        """ processes the solr_json to
             make GeoJSON records
        """
        i = self.rec_start
        for solr_rec in solr_recs:
            if 'uuid' in solr_rec:
                uuid = solr_rec['uuid']
                self.uuids.append(uuid)
