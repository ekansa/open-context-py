import sys
import time
import re
from itertools import islice
import requests
from mysolr import Solr
from opencontext_py.apps.indexer.uuidlist import UUIDList
from opencontext_py.apps.indexer.solrdocument import SolrDocument


class Crawler():

    def __init__(self):
        self.uuidlist = UUIDList().uuids
        self.session = requests.Session()
        try:
            self.solr = Solr('http://localhost:8983/solr',
                             make_request=self.session)
        except requests.ConnectionError:
            print('\nError: Could not connect to Solr. Please '
                  'verify your Solr instance and configuration.\n')
            sys.exit()

    def crawl(self, chunksize=100):
        start_time = time.time()
        print('\n\nStarting crawl...\n')
        print("(#)\tUUID")
        print('--------------------------------------------')
        document_count = 0
        while self.uuidlist is not None:
            documents = []
            for uuid in islice(self.uuidlist, 0, chunksize):
                try:
                    solrdocument = SolrDocument(uuid).fields
                    if self._document_is_valid(solrdocument):
                        documents.append(solrdocument)
                        document_count += 1
                        print("(" + str(document_count) + ")\t" + uuid)
                    else:
                        print('Error: Skipping document due to datatype '
                              'mismatch -----> ' + uuid)
                except Exception as error:
                    print("Error: {0}".format(error) + " -----> " + uuid)
            # Commit documents but also save the solr response status
            # codes (e.g, 200, 400, etc.)
            solr_status = self.solr.update(documents, 'json',
                                           commit=True).status
            if solr_status == 200:
                print('--------------------------------------------')
                print('Crawl Rate: ' + self._documents_per_second(
                    document_count, start_time) + ' documents per second')
                print('--------------------------------------------')
            else:
                print('Error: ' + str(self.solr.update(
                    documents, 'json', commit=True
                    ).raw_content))

    def index_single_document(self, uuid):
        print('\nAttempting to index document ' + uuid + '...\n')
        documents = []
        try:
            solrdocument = SolrDocument(uuid).fields
            if self._document_is_valid(solrdocument):
                documents.append(solrdocument)
                # Commit the document and save the response status
                solr_status = self.solr.update(
                    documents, 'json', commit=True).status
                if solr_status != 200:
                    print('Error: ' + str(self.solr.update(
                        documents, 'json', commit=True
                        ).raw_content)
                    )
                else:
                    print('Successfully indexed ' + uuid + '.')
            else:
                print('Error: Unable to index ' + uuid + ' due to '
                      'datatype mismatch.')
        except TypeError:
            print("Error: Unable to process document " + uuid + '.')
        except Exception as error:
            print("Error: {0}".format(error) + " -----> " + uuid)

    def _document_is_valid(self, document):
        is_valid = True
        for key in document:
            if key.endswith('numeric'):
                if not(self._valid_float(document[key])):
                    is_valid = False
            if key.endswith('date'):
                if not(self._valid_date(document[key])):
                    is_valid = False
        return is_valid

    def _valid_float(self, value):
        if isinstance(value, float):
            return True
        elif isinstance(value, list):
            # If it's a list, make sure all items are floats
            return all(isinstance(item, float) for item in value)
        else:
            return False

    def _valid_date(self, value):
        pattern = re.compile(
            '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z'
            )
        return bool(pattern.search(value))

    def _documents_per_second(self, document_count, start_time):
        return str(int(document_count//(time.time() - start_time)))
