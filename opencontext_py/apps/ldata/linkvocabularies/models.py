import itertools
import json
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import SKOS, RDFS, OWL
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.libs.general import LastUpdatedOrderedDict


# This class stores label and hierarchy data from RDF vocabularies used by Open Context
class LinkVocabulary():
    """
    Loads an OWL vocabulary (defaults to RDF-OWL)
    To store some hierarchy relationships, labels, and icons in the database
    """
    def __init__(self):
        self.vocab_file_uri = False  # location of the file with the vocabulary
        self.vocabulary_uri = False  # URI of the vocabulary namespace
        self.graph = False  # Graph of triples
        self.replace_old = True  # replace old data - delete from active vocabulary before loading

    def update_load_vocabulary(self, vocab_file_uri, vocab_uri=False):
        """ Loads, parses, and stores a vocabulary or ontology
        Saves labels for entities referenced in the vocabulary, also saves
        hierarchical relationships for these entities in the database
        for use in formulating Solr index """
        output = {}
        if(vocab_uri is not False):
            self.vocabulary_uri = vocab_uri
        self.load_parse_vocabulary(vocab_file_uri)
        output['labels'] = self.save_entity_labels()
        output['subClasses'] = self.save_hierarchy('rdfs:subClassOf')
        output['subProperties'] = self.save_hierarchy('rdfs:subPropertyOf')
        output['hasIcons'] = self.save_icons()
        return output

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
            self.vocab_file_uri = uri
            self.graph = graph
        return self.graph

    def save_entity_labels(self):
        """ saves labels of entities in a vocabulary """
        output = False
        if(self.graph is not False and self.vocabulary_uri is not False):
            output = []
            if(self.replace_old):
                LinkEntity.objects.filter(vocab_uri=self.vocabulary_uri).delete()
            for s, p, o in self.graph.triples((None,
                                               RDFS.label,
                                               None)):
                subject_uri = s.__str__()  # get the URI of the subject as a string
                label = o.__str__()  # get the Label of the object as a string
                newr = LinkEntity()
                newr.uri = subject_uri
                newr.label = label
                newr.alt_label = label
                newr.ent_type = 'type'
                newr.vocab_uri = self.vocabulary_uri
                newr.save()
                act_t = {'s': subject_uri,
                         'o': label}
                output.append(act_t)
        return output

    def save_hierarchy(self, predicate_uri='rdfs:subClassOf'):
        """ Saves hierarchic relations from a vocabulary,
        defaulting to subClassOf predicates """
        data = False
        if(self.graph is not False and self.vocabulary_uri is not False):
            data = []
            if(self.replace_old):
                # delete old relations from this vocabulary using this predicate
                LinkAnnotation.objects.filter(source_id=self.vocabulary_uri,
                                              predicate_uri=predicate_uri).delete()
            if(predicate_uri == 'rdfs:subClassOf'):
                # for subClassOf predicates
                for s, p, o in self.graph.triples((None,
                                                   RDFS.subClassOf,
                                                   None)):
                    subject_uri = s.__str__()  # get the URI of the subject as a string
                    object_uri = o.__str__()  # get the URI of the object as a string
                    act_t = {'s': subject_uri,
                             'o': object_uri}
                    if(subject_uri != object_uri):
                        data.append(act_t)
            elif(predicate_uri == 'rdfs:subPropertyOf'):
                # for subPropertyOf predicates
                for s, p, o in self.graph.triples((None,
                                                   RDFS.subPropertyOf,
                                                   None)):
                    subject_uri = s.__str__()  # get the URI of the subject as a string
                    object_uri = o.__str__()  # get the URI of the object as a string
                    act_t = {'s': subject_uri,
                             'o': object_uri}
                    if(subject_uri != object_uri):
                        data.append(act_t)
            if(len(data) > 0):
                for act_t in data:
                    newr = LinkAnnotation()
                    # make the subject a prefixed URI if common
                    newr.subject = URImanagement.prefix_common_uri(act_t['s'])
                    newr.subject_type = 'uri'
                    newr.project_uuid = '0'
                    newr.source_id = self.vocabulary_uri
                    newr.predicate_uri = predicate_uri
                    newr.object_uri = act_t['o']
                    newr.save()
        return data

    def save_icons(self, predicate_uri='oc-gen:hasIcon'):
        """ Saves icons in the general Open Context namespace """
        data = False
        if(self.graph is not False and self.vocabulary_uri is not False):
            data = []
            if(self.replace_old):
                # delete old relations from this vocabulary using this predicate
                LinkAnnotation.objects.filter(source_id=self.vocabulary_uri,
                                              predicate_uri=predicate_uri).delete()
            if(predicate_uri == 'oc-gen:hasIcon'):
                # for subClassOf predicates
                full_pred_uri = URImanagement.convert_prefix_to_full_uri(predicate_uri)
                icon_pred = URIRef(full_pred_uri)
                for s, p, o in self.graph.triples((None,
                                                   icon_pred,
                                                   None)):
                    subject_uri = s.__str__()  # get the URI of the subject as a string
                    object_uri = o.__str__()  # get the URI of the object as a string
                    act_t = {'s': subject_uri,
                             'o': object_uri}
                    if(subject_uri != object_uri):
                        data.append(act_t)
            if(len(data) > 0):
                for act_t in data:
                    newr = LinkAnnotation()
                    # make the subject a prefixed URI if common
                    newr.subject = URImanagement.prefix_common_uri(act_t['s'])
                    newr.subject_type = 'uri'
                    newr.project_uuid = '0'
                    newr.source_id = self.vocabulary_uri
                    newr.predicate_uri = predicate_uri
                    newr.object_uri = act_t['o']
                    newr.save()
        return data
