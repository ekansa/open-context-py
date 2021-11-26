import copy
import pysolr

from django.conf import settings



class SolrClient():
    '''
    Provides a connection to our Solr instance. This is useful for both
    crawling and searching.
    '''
    def __init__(
        self,
        exit_on_error=True,
        solr_host=settings.SOLR_HOST,
        solr_port=settings.SOLR_PORT,
        solr_collection=settings.SOLR_COLLECTION,
        always_commit=False,
        timeout=30,
        auth=None,
        use_test_solr=False,
    ):
        if use_test_solr:
            # We're connecting to testing Solr instance
            solr_host = settings.SOLR_HOST_TEST
            solr_port = settings.SOLR_PORT_TEST
            solr_collection = settings.SOLR_COLLECTION_TEST

        if not solr_host.startswith('http://') and not solr_host.startswith('https://'):
            # forgiving of configurations
            solr_host = 'http://' + solr_host
        if len(solr_collection) > 1:
            solr_collection = '/' + solr_collection
        if solr_port == 80:
            solr_connection_string = solr_host \
                + '/solr' + solr_collection
        else:
            solr_connection_string = solr_host + ':' + str(solr_port) \
                + '/solr' + solr_collection
        try:
            # print(solr_connection_string)
            self.solr = pysolr.Solr(
                solr_connection_string, 
                always_commit=always_commit, 
                timeout=timeout, 
                auth=auth
            )
        except:
            print(f'Error: Could not connect to Solr at: {solr_connection_string}')
            self.solr = None
