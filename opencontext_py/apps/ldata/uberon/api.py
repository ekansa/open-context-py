import json
import requests
from time import sleep
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import SKOS, RDFS, OWL
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI


class uberonAPI():
    """ Gets RDF data about an entity in the UBERON
        Ontology

from opencontext_py.apps.ldata.uberon.api import uberonAPI
u_api = uberonAPI()
u_api.get_uri_label_from_graph('http://purl.obolibrary.org/obo/UBERON_0011674')
u_api.get_uri_graph('http://purl.obolibrary.org/obo/UBERON_0011674')

    """
    VOCAB_URI = 'http://uberon.org/'
    DIRECT_BASE_URL = 'http://www.ontobee.org/ontology/UBERON?iri='
    SLEEP_TIME = .5

    def __init__(self):
        self.request_error = False
        self.base_url = self.DIRECT_BASE_URL
        self.delay_before_request = self.SLEEP_TIME
        self.graph = False
        self.request_url = False

    def get_uri_label_from_graph(self, uri):
        """ gets the label (and graph)
            for an Uberon enity identified by a URI
        """
        label = False
        graph = self.get_uri_graph(uri)
        if graph is not False:
            for s, p, o in self.graph.triples((None,
                                               RDFS.label,
                                               None)):
                subject_uri = s.__str__()  # get the URI of the subject as a string
                label = o.__str__()  # get the Label of the object as a string
                break
        return label

    def get_uri_graph(self, uri, fformat='application/rdf+xml'):
        """
        gets an RDF graph for the Uberon URI
        """
        url = self.base_url + quote_plus(uri)
        self.request_url = url
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        graph = Graph()
        try:
            if(fformat is not False):
                graph.parse(url, format=fformat)
            else:
                graph.parse(url)
        except:
            print('Failed to load the graph.')
            graph = False
        if graph is not False:
            self.graph = graph
        return self.graph
