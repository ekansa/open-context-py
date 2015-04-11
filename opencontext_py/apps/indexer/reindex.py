import json
import requests
from django.db import models
from opencontext_py.apps.searcher.solrsearcher.solrdirect import SolrDirect
from opencontext_py.apps.indexer.crawler import Crawler
from opencontext_py.apps.ocitems.manifest.models import Manifest


class SolrReIndex():
    """ This class contains methods to make updates to
        the solr index especially after edits
    """

    def __init__(self):
        self.uuids = []
        self.iteration = 0
        self.recursive = True
        # maximum number of times to iterate and make requests
        self.max_iterations = 100
        # if not false, get uuids by directly requsting JSON from solr
        self.solr_direct_url = False
        # if not false, use a request to Open Context to generate a
        # solr request to get UUIDs
        self.oc_url = False
        # if not false, use a dictionary of paramaters with Open Context
        # to generate a solr request to get UUIDs
        self.oc_params = False
        # if not false, use a Postgres SQL query to get a list of
        # UUIDs from a list of projects
        self.project_uuids = False
        # if not false, use a Postgres SQL query to get a list of
        # UUIDs
        self.sql = False

    def reindex(self):
        """ Reindexes items in Solr,
            with item UUIDs coming from a given source
        """
        self.iteration += 1
        print('Iteration: ' + str(self.iteration))
        if self.iteration <= self.max_iterations:
            uuids = []
            if self.solr_direct_url is not False:
                print('Get uuids from solr: ' + str(self.solr_direct_url))
                uuids = self.get_uuids_solr_direct(self.solr_direct_url)
            elif self.oc_url is not False:
                # now validate to make sure we're asking for uuids
                if 'response=uuid' in self.oc_url \
                   and '.json' in self.oc_url:
                    print('Get uuids from OC-API: ' + str(self.oc_url))
                    uuids = self.get_uuids_oc_url(self.oc_url)
            elif isinstance(self.project_uuids, list):
                # now validate to make sure we're asking for uuids
                uuids = Manifest.objects\
                                .filter(project_uuid__in=self.project_uuids)\
                                .values_list('uuid', flat=True)
            if isinstance(uuids, list):
                print('Ready to index ' + str(len(uuids)) + ' items')
                crawler = Crawler()
                crawler.index_document_list(uuids)
                self.reindex()
            else:
                print('Problem with: ' + str(uuids))

    def get_uuids_solr_direct(self, solr_request_url):
        """ gets uuids from solr by direct request
        """
        solr_d = SolrDirect()
        uuids = solr_d.get_result_uuids(solr_request_url)
        return uuids

    def get_uuids_oc_url(self, oc_url):
        """ gets uuids from the Open Context API
        """
        try:
            r = requests.get(oc_url,
                             timeout=60)
            r.raise_for_status()
            uuids = r.json()
        except:
            uuids = []
        return uuids
