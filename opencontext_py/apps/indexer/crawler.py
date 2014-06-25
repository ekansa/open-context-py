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

    def crawl(self, chunksize):
        while self.uuidlist is not None:
            documents = []
            print('creating container of ' + str(chunksize) + ' documents...')
            for uuid in islice(self.uuidlist, 0, chunksize):
                try:
                    solrdocument = SolrDocument(uuid)
                    documents.append(solrdocument.fields)
                    print('adding ' + uuid)
                except Exception as err:
                    print("KeyError: {0}".format(err) + " ---> " + uuid)
            self.solr.update(documents, 'json', commit=True)


if __name__ == '__main__':
    crawler = Crawler()
    crawler().crawl(100)
