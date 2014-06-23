from itertools import islice
import requests
from mysolr import Solr
from opencontext_py.apps.index.uuidlist import UUIDList
from opencontext_py.apps.index.solrdocument import SolrDocument


class Crawler():

    def __init__(self):
        self.uuidlist = UUIDList().uuids
        self.session = requests.Session()
        self.solr = Solr('http://localhost:8983/solr',
                         make_request=self.session)

    def crawl(self):
        while self.uuidlist is not None:
            documents = []
            print('creating documents container list')
            for uuid in islice(self.uuidlist, 0, 100):
                solrdocument = SolrDocument(uuid)
                documents.append(solrdocument.__dict__)
                print('adding...')
                print(solrdocument.uuid)
            self.solr.update(documents, 'json', commit=True)


if __name__ == '__main__':
    crawler = Crawler()
    crawler().crawl()
