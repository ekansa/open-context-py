from rdflib import Graph, URIRef, Literal
from rdflib.namespace import SKOS, RDFS, OWL
import itertools
import json
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.libs.general import LastUpdatedOrderedDict


# This class stores linked data annotations made on the data contributed to open context
class LinkVocabulary():
    """
    Loads an OWL vocabulary (defaults to RDF-OWL)
    To store some hierarchy relationships, labels, and icons in the database
    """
    def __init__(self):
        self.vocabulary_uri = False
        self.graph = False

    def load_parse_vocabulary(self, uri, fformat='application/rdf+xml'):
        """
        Loads and parses a vocabulary, defaulting to the RDF-XML file format
        """
        graph = Graph()
        try:
            if(fformat is not False):
                graph.parse(uri, format=fformat)
            else:
                graph.parse(uri)
        except:
            graph = False
        if(graph is not False):
            self.vocabulary_uri = uri
            self.graph = graph
        return self.graph

    def save_entity_labels(self):
        output = False
        if(self.graph is not False):
            output = []
            # ent_labels = self.graph.subject_objects('http://www.w3.org/2000/01/rdf-schema#label')
            for s, p, o in self.graph.triples((None,
                                               RDFS.label,
                                               None)):
                act_t = {'s': s,
                         'o': o}
                output.append(act_t)
        return output


