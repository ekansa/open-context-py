import sys
from django.conf import settings
import requests
from mysolr import Solr


class SolrConnection():
    '''
    Provides a connection to our Solr instance. This is useful for both
    crawling and searching.
    '''
    def __init__(self,
                 exit_on_error=True,
                 solr_host=settings.SOLR_HOST,
                 solr_port=settings.SOLR_PORT,
                 solr_collection=settings.SOLR_COLLECTION):
        if 'http://' not in solr_host and 'https://' not in solr_host:
            # forgiving of configurations
            solr_host = 'http://' + solr_host
        self.session = requests.Session()
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
            self.connection = Solr(solr_connection_string,
                                   make_request=self.session,
                                   version=4)
        except requests.ConnectionError:
            print('\nError: Could not connect to Solr at: ' + solr_connection_string +\
                  '\nPlease verify your Solr instance and configuration.\n')
            if exit_on_error:
                sys.exit(1)
            else:
                self.connection = False
