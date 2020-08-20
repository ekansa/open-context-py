
import uuid as GenUUID
import itertools
import json

from django.db.models import Q

from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, SKOS, OWL

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllString,
    AllAssertion,
    AllHistory,
)
from opencontext_py.apps.all_items import utilities


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


# Mappings, keyed by an Open Contex item_type to different
# OWL entity types identified in an OWL ontology via the
# rdf:type predicate.
# NOTE: this is cleaned of the http:// prefix
ITEM_TYPE_OWL_TYPE_URIS = {
    'class': [
        'www.w3.org/2002/07/owl#Class'
    ],
    'property': [
        'www.w3.org/2002/07/owl#AnnotationProperty',
        'www.w3.org/2002/07/owl#DataProperty',
        'www.w3.org/2002/07/owl#ObjectProperty',
    ]
}

URI_PREFIXES = {
    'opencontext.org/vocabularies/oc-general/': 'oc-gen:',
    'opencontext.org/vocabularies/open-context-zooarch/': 'oc-zoo:',
    'opencontext.org/vocabularies/dinaa/': 'dinaa:',
}



# This class stores label and hierarchy data from RDF vocabularies used by Open Context
class OwlVocabulary():
    """
    Loads an OWL vocabulary (defaults to RDF-OWL)
    To store some hierarchy relationships, labels, and icons in the database
    """
    SORT_HIERARCHY_DEPTH = 10  # depth of the hiearchy for sorting purposes

    def __init__(self, vocabulary_uri, vocab_file_uri):
        self.vocabulary_uri = vocabulary_uri  # URI of the vocabulary namespace
        self.vocab_file_uri = vocab_file_uri  # location of the file with the vocabulary
        self.source_id = 'rdf-graph-import'
        self.graph = None  # Graph of triples


    def map_owl_entity_type_to_oc_item_type(self, owl_type_uri):
        """Maps an OWL entity type to an Open Context item_type"""
        owl_type_uri = AllManifest().clean_uri(owl_type_uri)
        for oc_item_type, owl_type_uris in ITEM_TYPE_OWL_TYPE_URIS.items():
            if owl_type_uri in owl_type_uris:
                # the owl_type_uri is in the list of owl_type_uris
                # mapped to this oc_item_type, so return the oc_item_type 
                return oc_item_type
        
        # This type does not map, so return none
        return None

    def update_graph_entity_types(self):
        """ updates the entity types (for class or property entities) """
        if not self.graph:
            return None

        for s, p, o in self.graph.triples((None, RDF.type, None)):
            subject_uri = s.__str__()  # get the URI of the subject as a string
            object_uri = o.__str__()  # get the URI of the rdf:type    
            print(f'{subject_uri} a (rdf:type) {object_uri}')

            oc_item_type = self.map_owl_entity_type_to_oc_item_type(object_uri)
            if not oc_item_type:
                # This type has no mapping to an OC item_type
                continue 
            
            sub_obj = utilities.get_man_obj_from_uri(subject_uri)
            if not sub_obj:
                # We have yet to import this
                continue

            if sub_obj.item_type == oc_item_type:
                # The subject entity already has the expected type, so
                # do nothing.
                continue

            if sub_obj.source_id == configs.DEFAULT_SOURCE_ID:
                # Don't update something that is an Open Context
                # default.
                continue

            # Change the subject item to the mapped oc_item_type
            sub_obj.item_type = oc_item_type
            sub_obj.save()
            print(
                f'Updated {sub_obj.label} {sub_obj.uri} [{sub_obj.uuid}] to {sub_obj.item_type}'
            )


    def save_entity_comments(self, replace_old_comments=False):
        """ saves comments about an entity """
        if not self.graph:
            return None
        
        for s, p, o in self.graph.triples((None, RDFS.comment, None)):
            subject_uri = s.__str__()  # get the URI of the subject as a string
            comment = o.__str__()  # get the comment from the object as a string
            
            sub_obj = utilities.get_man_obj_from_uri(subject_uri)
            if not sub_obj:
                # We have yet to import this subject entity, so
                # we can't talk about it yet.
                print(f'Unknown entity {subject_uri}')
                continue
            
            utilities.add_string_assertion_simple(
                subject_obj=sub_obj, 
                predicate_id=configs.PREDICATE_RDFS_COMMENT_UUID,
                source_id=self.source_id,
                str_content=comment,
                replace_old_content=replace_old_comments
            )


    def save_vocab_entities(self, replace_old=False):
        """ saves labels of entities in a vocabulary """
        if not self.graph or not self.vocabulary_uri:
            return None
        
        m_vocab = utilities.get_man_obj_from_uri(self.vocabulary_uri)
        if not m_vocab:
            print(f'Cannot find a manifest obj for vocab {self.vocabulary_uri} ')
            return None
        
        for s, p, o in self.graph.triples((None, RDFS.label, None)):
            subject_uri = s.__str__()  # get the URI of the subject as a string
            label = o.__str__()  # get the Label of from object as a string

            # Get the rdf:type for the subject uri
            oc_item_type = self.map_owl_entity_type_to_oc_item_type(subject_uri)
            if not oc_item_type:
                # This type has no mapping to an OC item_type
                continue

            # Make a new manifest dictionary object.
            uri = AllManifest().clean_uri(subject_uri)
            
            # Check to see if this item already exists as an Open Context
            # default.
            default_man = AllManifest.objects.filter(
                uri=uri,
                source_id=configs.DEFAULT_SOURCE_ID
            ).first()
            if default_man:
                # Skip database edits / interactions with this, it is
                # an Open Context default item.
                continue
            
            # Default data type.
            data_type = 'id'

            man_dict = {
                'publisher_id': m_vocab.publisher.uuid,
                'project_id': m_vocab.project.uuid,
                'source_id': self.source_id,
                'item_type': oc_item_type,
                'data_type': data_type,
                'label': label,
                'uri': uri,
                'context_id': m_vocab.uuid,
            }
            for uri_prefix, ns_prefix in URI_PREFIXES:
                if not uri.startswith(uri_prefix):
                    continue
                man_dict['item_key'] = ns_prefix + uri[len(uri_prefix):]

            new_man_obj, _ = AllManifest.objects.get_or_create(
                uri=uri,
                defaults=man_dict
            )
            print(
                f'Manifest item [{new_man_obj.uuid}]: {new_man_obj.label} at '
                f'{new_man_obj.uri} or {new_man_obj.item_key} {new_man_obj.slug}'
            )
         

    def save_vocabulary_hierarchy(self):
        """Saves hierarchic relations for class and property entities in a vocabulary"""
        if not self.graph or not self.vocabulary_uri:
            return None
        
        m_vocab = utilities.get_man_obj_from_uri(self.vocabulary_uri)
        if not m_vocab:
            print(f'Cannot find a manifest obj for vocab {self.vocabulary_uri} ')
            return None
        
        predicates = [
            (
                RDFS.subClassOf, 
                configs.PREDICATE_RDFS_SUB_CLASS_OF_UUID,
                'class',
            ),
            (
                RDFS.subPropertyOf, 
                configs.PREDICATE_RDFS_SUB_PROP_OF_UUID,
                'property',
            ),
        ]
        for query_p, predicate_uuid, ok_oc_item_type in predicates:
            for s, p, o in self.graph.triples((None, query_p, None)):
                subject_uri = s.__str__()  # get the URI of the subject as a string
                object_uri = o.__str__()  # get the URI of the object as a string
                
                if subject_uri == object_uri:
                    # No hierarchy relations with yourself!
                    continue

                sub_obj = utilities.get_man_obj_from_uri(subject_uri)
                if not sub_obj:
                    continue
                obj_obj = utilities.get_man_obj_from_uri(object_uri)
                if not obj_obj:
                    continue
                if (sub_obj.item_type != ok_oc_item_type 
                    or obj_obj.item_type != ok_oc_item_type):
                    print(
                        f'Both {sub_obj.label} {sub_obj.uri} {sub_obj.item_type} '
                        f'and {obj_obj.label} {obj_obj.uri} {obj_obj.item_type} '
                        f'must be item_type {ok_oc_item_type}'
                    )
                    continue
                ass_obj, _ = AllAssertion.objects.get_or_create(
                    uuid=AllAssertion().primary_key_create(
                        subject_id=subj_obj.uuid,
                        predicate_id=predicate_uuid,
                        object_id=obj_obj.uuid,
                    ),
                    defaults={
                        'publisher_id': m_vocab.publisher.uuid,
                        'project_id': m_vocab.project.uuid,
                        'source_id': self.source_id,
                        'subject': subj_obj,
                        'predicate_id': predicate_uuid,
                        'object': obj_obj,
                    }
                )
                print(
                    f'Assertion {ass_obj.uuid}: '
                    f'{ass_obj.subject.label} [{ass_obj.subject.uuid}]'
                    f'-> {ass_obj.predicate.label} [{ass_obj.predicate.uuid}]'
                    f'-> {ass_obj.object.label} [{ass_obj.object.uuid}]'
                )
        


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
            print(f'Failed to load the graph from {uri}')
            graph = None
        if graph is not None:
            self.vocab_file_uri = uri
            self.graph = graph
        return self.graph
    
    def update_load_vocabulary(self, vocab_file_uri, vocab_uri=False):
        """ Loads, parses, and stores a vocabulary or ontology
        Saves labels for entities referenced in the vocabulary, also saves
        hierarchical relationships for these entities in the database
        for use in formulating Solr index """
        output = {}
        if vocab_uri:
            self.vocabulary_uri = vocab_uri
        self.load_parse_vocabulary(vocab_file_uri)
        output['labels'] = self.save_entity_labels()
        output['subClasses'] = self.save_hierarchy('rdfs:subClassOf')
        output['subProperties'] = self.save_hierarchy('rdfs:subPropertyOf')
        output['hasIcons'] = self.save_icons()
        output['sorting'] = self.save_sort()
        return output