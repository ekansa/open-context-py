import itertools
import json
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, SKOS, OWL
from opencontext_py.libs.languages import Languages
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.libs.general import LastUpdatedOrderedDict


# This class stores label and hierarchy data from RDF vocabularies used by Open Context
class LinkVocabulary():
    """
    Loads an OWL vocabulary (defaults to RDF-OWL)
    To store some hierarchy relationships, labels, and icons in the database

from opencontext_py.apps.ldata.linkvocabularies.models import LinkVocabulary
lv = LinkVocabulary()
lv.vocabulary_uri = 'http://opencontext.org/vocabularies/dinaa'
lv.vocab_file_uri = 'https://raw.githubusercontent.com/ekansa/oc-ontologies/master/vocabularies/dinaa-alt.owl'
lv.load_parse_vocabulary(lv.vocab_file_uri)
lv.update_entity_types()
lv.save_entity_comments()

from opencontext_py.apps.ldata.linkvocabularies.models import LinkVocabulary
lv = LinkVocabulary()
lv.vocabulary_uri = 'http://opencontext.org/vocabularies/oc-general'
lv.vocab_file_uri = 'https://raw.githubusercontent.com/ekansa/oc-ontologies/master/vocabularies/oc-general.owl'
lv.load_parse_vocabulary(lv.vocab_file_uri)
lv.replace_old = False
lv.save_entity_labels()
lv.save_entity_comments()

    """
    SORT_HIERARCHY_DEPTH = 10  # depth of the hiearchy for sorting purposes

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
        if vocab_uri is not False:
            self.vocabulary_uri = vocab_uri
        self.load_parse_vocabulary(vocab_file_uri)
        output['labels'] = self.save_entity_labels()
        output['subClasses'] = self.save_hierarchy('rdfs:subClassOf')
        output['subProperties'] = self.save_hierarchy('rdfs:subPropertyOf')
        output['hasIcons'] = self.save_icons()
        output['sorting'] = self.save_sort()
        return output

    def load_parse_vocabulary(self, uri, fformat='application/rdf+xml'):
        """
        Loads and parses a vocabulary, defaulting to the RDF-XML file format
        """
        graph = Graph()
        try:
            if fformat is not False:
                graph.parse(uri, format=fformat)
            else:
                graph.parse(uri)
        except:
            print('Failed to load the graph.')
            graph = False
        if graph is not False:
            self.vocab_file_uri = uri
            self.graph = graph
        return self.graph

    def update_entity_types(self):
        """ updates the entity types (for class or property entities) """
        if self.graph is not False and self.vocabulary_uri is not False:
            for s, p, o in self.graph.triples((None,
                                               RDF.type,
                                               None)):
                subject_uri = s.__str__()  # get the URI of the subject as a string
                object_uri = o.__str__()  # get the Label of the object as a string    
                print(subject_uri + ' a ' + object_uri)
                if 'Property' in object_uri or \
                   'property' in object_uri or \
                   'Class' in object_uri or \
                   'class' in object_uri:
                    # update the entity's ent_type
                    link_ent = False
                    try:
                        link_ent = LinkEntity.objects.get(uri=subject_uri)
                    except LinkEntity.DoesNotExist:
                        link_ent = False
                    if link_ent is not False:
                        if 'Property' in object_uri or \
                           'property' in object_uri:
                            # is a property entity
                            link_ent.ent_type = 'property'
                        else:
                            # has to be a class
                            link_ent.ent_type = 'class'
                        link_ent.save()

    def save_entity_comments(self):
        """ saves comments about an entity """
        if self.graph is not False and self.vocabulary_uri is not False:
            lequiv = LinkEquivalence()
            # get all the varients of RDFS:comments
            comment_uris = lequiv.get_identifier_list_variants('rdfs:comment')
            # now get all the entities from this vocabulary (that may be the subject of a comment)
            raw_subject_uris = LinkEntity.objects.filter(vocab_uri=self.vocabulary_uri)
            lequiv = LinkEquivalence()
            subject_uris = lequiv.get_identifier_list_variants(raw_subject_uris)
            if self.replace_old:
                # delete the old comments
                LinkAnnotation.objects\
                              .filter(subject__in=subject_uris,
                                      predicate_uri__in=comment_uris)\
                              .delete()
            for s, p, o in self.graph.triples((None,
                                               RDFS.comment,
                                               None)):
                subject_uri = s.__str__()  # get the URI of the subject as a string
                comment = o.__str__()  # get the comment from the object as a string
                # update the entity's comment
                link_ent = False
                try:
                    link_ent = LinkEntity.objects.get(uri=subject_uri)
                except LinkEntity.DoesNotExist:
                    link_ent = False
                if link_ent is not False:
                    lang = Languages()
                    newr = LinkAnnotation()
                    # make the subject a prefixed URI if common
                    newr.subject = URImanagement.prefix_common_uri(subject_uri)
                    newr.subject_type = 'uri'
                    newr.project_uuid = '0'
                    newr.source_id = self.vocabulary_uri
                    newr.predicate_uri = 'rdfs:comment'
                    newr.obj_extra = {}
                    newr.obj_extra[lang.DEFAULT_LANGUAGE] = comment
                    newr.save()

    def save_entity_labels(self):
        """ saves labels of entities in a vocabulary """
        output = False
        if self.graph is not False and self.vocabulary_uri is not False:
            output = []
            if self.replace_old:
                LinkEntity.objects.filter(vocab_uri=self.vocabulary_uri).delete()
            for s, p, o in self.graph.triples((None,
                                               RDFS.label,
                                               None)):
                subject_uri = s.__str__()  # get the URI of the subject as a string
                label = o.__str__()  # get the Label of from object as a string
                le_ents = LinkEntity.objects.filter(uri=subject_uri)[:1]
                if len(le_ents) < 1 or self.replace_old:
                    newr = LinkEntity()
                    newr.uri = subject_uri
                    newr.label = label
                    newr.alt_label = label
                    newr.ent_type = 'class'
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

    def save_sort(self, predicate_uri='http://purl.org/ontology/olo/core#index'):
        """ Saves sort order """
        data_indexes = False
        if(self.graph is not False and self.vocabulary_uri is not False):
            data_indexes = {}
            index_pred = URIRef(predicate_uri)
            for s, p, o in self.graph.triples((None,
                                               index_pred,
                                               None)):
                subject_uri = s.__str__()  # get the URI of the subject as a string
                index = o.__str__()  # get the URI of the object as a string
                data_indexes[subject_uri] = int(float(index)) + 1  # add 1
                # so first child does not have the exact same index as the first parent.
            if(len(data_indexes) > 0):
                for subject_uri, index in data_indexes.items():
                    print('Sorting: ' + subject_uri)
                    sort_strings = []
                    parents = LinkRecursion().get_jsonldish_entity_parents(subject_uri)
                    for parent in parents:
                        if parent['id'] in data_indexes:
                            parent_index = data_indexes[parent['id']]
                        else:
                            parent_index = 0
                        parent_sort = self.sort_digits(parent_index)
                        sort_strings.append(parent_sort)
                    while len(sort_strings) < self.SORT_HIERARCHY_DEPTH:
                        deep_sort = self.sort_digits(0)
                        sort_strings.append(deep_sort)
                    sort = '-'.join(sort_strings)
                    try:
                        le = LinkEntity.objects.get(uri=subject_uri)
                    except LinkEntity.DoesNotExist:
                        le = False
                    if le is not False:
                        le.sort = sort
                        le.save()
        return data_indexes

    def get_uri_entity_index(self, subject_uri, predicate_uri):
        index = 0
        subject_ent = URIRef(subject_uri)
        index_pred = URIRef(predicate_uri)
        for s, p, o in self.graph.triples((subject_ent,
                                           index_pred,
                                           None)):
            index = o.__str__()  # get the literal object as a string
        if index != 0:
            index = int(float(index))
        return index

    def sort_digits(self, index):
        """ Makes a 3 digit sort friendly string from an index """
        if index >= 1000:
            index = 999
        sort = str(index)
        if len(sort) < 3:
            while len(sort) < 3:
                sort = '0' + sort
        return sort