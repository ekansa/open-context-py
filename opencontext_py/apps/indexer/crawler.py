from itertools import islice
import requests
from mysolr import Solr
from opencontext_py.apps.indexer.uuidlist import UUIDList
from opencontext_py.apps.indexer.solrdocument import SolrDocument


class Crawler():

    def __init__(self):
        self.uuidlist = UUIDList().uuids
        self.session = requests.Session()
        self.solr = Solr('http://localhost:8983/solr',
                         make_request=self.session)

    def crawl(self, chunksize=500):
        document_count = 0
        while self.uuidlist is not None:
            documents = []
            print('Creating container of ' + str(chunksize) + ' documents...')
            for uuid in islice(self.uuidlist, 0, chunksize):
                try:
                    solrdocument = SolrDocument(uuid).fields
                    if self._document_is_valid(solrdocument):
                        documents.append(solrdocument)
                        document_count += 1
                        print('(' + str(document_count) + ') adding ' + uuid)
                    else:
                        print('Error: Datatype mismatch -----> ' + uuid)
                except Exception as err:
                    print("Error: {0}".format(err) + " -----> " + uuid)
            self.solr.update(documents, 'json', commit=True)
            if self.solr.update(documents, 'json', commit=True).status != 200:
                print('Error: ' + str(self.solr.update(
                    documents, 'json', commit=True
                    ).raw_content))

    def index_single_document(self, uuid):
        documents = []
        try:
            solrdocument = SolrDocument(uuid).fields
            if self._document_is_valid(solrdocument):
                documents.append(solrdocument)
                self.solr.update(documents, 'json', commit=True)
                if self.solr.update(
                        documents, 'json', commit=True).status != 200:
                        print('Error: ' + str(self.solr.update(
                            documents, 'json', commit=True
                            ).raw_content)
                            )
                else:
                    print('Successfully indexed ' + uuid)
            else:
                print('Error: Datatype mismatch -----> ' + uuid)
        except Exception as err:
            print("Error: {0}".format(err) + " -----> " + uuid)

    def _document_is_valid(self, document):
        is_valid = True
        for key in document:
            if key.endswith('numeric'):
                if not(self._valid_float(document[key])):
                    is_valid = False
        return is_valid

    def _valid_float(self, value):
        # The values we are checking could be either (mulit-valued) lists
        # or individual values. We need to check both cases.
        # Check if all items in a list are floats
        if isinstance(value, list):
            return all(isinstance(item, float) for item in value)
        else:
            return isinstance(value, float)
