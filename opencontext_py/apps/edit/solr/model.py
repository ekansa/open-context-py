from django.db import models
from opencontext_py.apps.searcher.solrsearcher.solrdirect import SolrDirect
from opencontext_py.apps.indexer.crawler import Crawler


# Help organize the code, with a class to make editing items easier
class SolrIndexEdit():
    """ This class contains methods to make updates to the solr index
        after edits
    """

    def __init__(self):
        self.uuids = []
        self.iteration = 0
        # maximum number of times to iterate and make requests
        self.max_iterations = 1000
        # if not false, get uuids by directly requsting JSON from solr
        self.solr_direct_url = False
        # if not false, use a request to Open Context to generate a
        # solr request to get UUIDs
        self.oc_url = False
        # if not false, use a dictionary of paramaters with Open Context
        # to generate a solr request to get UUIDs
        self.oc_params = False
        # if not false, use a Postgres SQL auery to get a list of
        # UUIDs
        self.sql = False

    def reindex(self):
        """ Reindexes items in Solr,
            with item UUIDs coming from a given source
        """
        if self.solr_direct_url is not False:
            pass
        return output

    def get_uuids_solr_direct(self, solr_request_url):
        """ gets uuids from solr by direct request
        """
        pass
