
import itertools


from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, SKOS, OWL

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllResource,
)
from opencontext_py.apps.all_items import utilities


"""
    Loads an OWL vocabulary (defaults to RDF-OWL)
    To store some hierarchy relationships, labels, and icons in the database

from opencontext_py.apps.all_items.owl_vocabulary import (
    OwlVocabulary,
    load_vocabularies_and_related_namespaces,
    save_entities_from_related_namespaces
)
# Loads the default Open Context vocabularies.
load_vocabularies_and_related_namespaces()



# Another example of use for loading a single vocabulary.
from opencontext_py.apps.all_items.owl_vocabulary import (
    OwlVocabulary,
    save_entities_from_related_namespaces
)
owl_v1 = OwlVocabulary(
    vocabulary_uri='http://opencontext.org/vocabularies/oc-general',
    vocab_file_uri='https://raw.githubusercontent.com/ekansa/oc-ontologies/master/vocabularies/oc-general.owl',
)
save_entities_from_related_namespaces(owl_v1.graph)
owl_v1.save_vocab_entities()
owl_v1.save_vocabulary_hierarchy()
owl_v1.save_vocabulary_units_of_measure()
owl_v1.save_vocabulary_icon_assertions()
owl_v1.save_vocabulary_entity_comments()
"""

# These are the main vocabularies used by Open Context. Expand this
# configuration list as needed.
OC_MAIN_VOCABULARIES = [
    configs.OC_GEN_VOCAB_UUID,
    configs.OCZOO_VOCAB_UUID,
    configs.DINAA_VOCAB_UUID,
]


OC_RELATED_NAMESPACES = [
    ('cidoc-crm', 'http://erlangen-crm.org/current/', configs.CIDOC_VOCAB_UUID, ),
    ('crm-eh', 'http://purl.org/crmeh#', configs.CRMEH_VOCAB_UUID, ),
    ('bibo', 'http://purl.org/ontology/bibo/', configs.BIBO_VOCAB_UUID, ),
    ('foaf', 'http://xmlns.com/foaf/0.1/', configs.FOAF_VOCAB_UUID, ),
]


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
    'opencontext.org/vocabularies/oc-general/': 'oc-gen',
    'opencontext.org/vocabularies/open-context-zooarch/': 'oc-zoo',
    'opencontext.org/vocabularies/dinaa/': 'dinaa',
    'purl.org/ontology/bibo': 'bibo',
}

CIDOC_P1_HAS_UNIT_URI = 'http://erlangen-crm.org/current/P91_has_unit'
OC_GEN_HAS_ICON_URI = 'http://opencontext.org/vocabularies/oc-general/hasIcon'



def save_entities_from_related_namespaces(graph, ns_configs=OC_RELATED_NAMESPACES):
    """Saves graph entities from related namespaces that we care about
    
    :param Graph graph: A graph object that contains entities defined in
        related namespaces. We will attempt to get and store the labels
        and comments made about certain entities from these other
        namespaces.
    :param list ns_configs: A list of config tuples that specify the other
        namespaces allowed to for retrieval and referencinging of certain
        entities referenced in the graph object.
    """
    predicates = [
        RDFS.subClassOf, 
        RDFS.subPropertyOf, 
        SKOS.exactMatch, 
        SKOS.closeMatch,
        OWL.sameAs,
    ]
    for ns_prefix, uri_prefix, vocab_uuid in ns_configs:
        vocab_obj = AllManifest.objects.get(uuid=vocab_uuid)
        ent_uris = []
        for p in predicates:
            for s, p, o in graph.triples((None, p, None)):
                uris = [s.__str__(), o.__str__()]
                for uri in uris:
                    if not uri.startswith(uri_prefix):
                        continue
                    ent_uris.append(uri)
        # De-duplicate
        ent_uris = list(set(ent_uris))
        if not len(ent_uris):
            print(f'No URIs for {vocab_obj.label}, {uri_prefix}')
            continue
        # The actual file location for the vocabulary will
        # be in the meta_json, but if not, fallback to the uri_prefix.
        vocab_file_uri = vocab_obj.meta_json.get(
            'vocab_file_uri', 
            uri_prefix
        )
        owl_v = OwlVocabulary(
            vocabulary_uri=vocab_obj.uri,
            vocab_file_uri=vocab_file_uri,
        )
        for uri in ent_uris:
            owl_v.save_vocab_entity(uri, fallback_oc_item_type='class')
        # Now save any comments bout the entities that we cared enough
        # to name and store.
        owl_v.save_vocabulary_entity_comments()


def load_vocabularies_and_related_namespaces(
    vocab_uuids=OC_MAIN_VOCABULARIES, 
    ns_configs=OC_RELATED_NAMESPACES
):
    """Loads a list of vocabularies and entities from related namespaces referenced in a vocab
    
    :param list vocab_uuids: List of vocabulary uuids to load
    :param list ns_configs: List of tuples to configure retrieval of referenced entities from
        other namespaces
    """
    for vocab_uuid in vocab_uuids:
        vocab_obj = AllManifest.objects.get(uuid=vocab_uuid)
        owl_v = OwlVocabulary(
            vocabulary_uri=vocab_obj.uri,
            vocab_file_uri=vocab_obj.meta_json.get('vocab_file_uri'),
        )
        # First save entities referenced from other namespaces,
        save_entities_from_related_namespaces(owl_v.graph, ns_configs)
        # Now save the entities in this vocabulary graph
        owl_v.save_vocab_entities()
        # Save hierarchy relationships
        owl_v.save_vocabulary_hierarchy()
        # Save assertions about units of measure
        owl_v.save_vocabulary_units_of_measure()
        # Save assertions about icons
        owl_v.save_vocabulary_icon_assertions()
        # Save comments about the entities in this vocabulary.
        owl_v.save_vocabulary_entity_comments()


def get_make_icon_man_obj_and_resource_obj(icon_uri, icon_label, source_id, vocab_obj):
    """Gets or creates an icon from an icon_uri (also its file uri)"""
    # Get or make a manifest item for the icon itself.
    icon_uri = AllManifest().clean_uri(icon_uri)
    icon_man_dict = {
        'publisher': vocab_obj.publisher,
        'project': vocab_obj.project,
        'source_id': source_id,
        'item_type': 'uri',
        'data_type': 'id',
        'label': icon_label,
        'uri': icon_uri,
        'context': vocab_obj,
    }

    icon_man_obj, _ = AllManifest.objects.get_or_create(
        uri=icon_uri,
        defaults=icon_man_dict
    )
    print(
        f'Manifest item [{icon_man_obj.uuid}]: {icon_man_obj.label} at '
        f'{icon_man_obj.uri} or {icon_man_obj.slug}'
    )
    icon_res_obj, _ = AllResource.objects.get_or_create(
        uuid=AllResource().primary_key_create(
            item_id=icon_man_obj.uuid,
            resourcetype_id=configs.OC_RESOURCE_ICON_UUID,
        ),
        defaults={
            'item': icon_man_obj,
            'project': vocab_obj.project,
            'resourcetype_id': configs.OC_RESOURCE_ICON_UUID,
            'source_id': source_id,
            'uri': icon_uri,
        }
    )
    return icon_man_obj, icon_res_obj




# This class stores label and hierarchy data from RDF vocabularies used by Open Context
class OwlVocabulary():
    """
    Loads an OWL vocabulary (defaults to RDF-OWL)
    To store some hierarchy relationships, labels, and icons in the database
    """
    SORT_HIERARCHY_DEPTH = 10  # depth of the hierarchy for sorting purposes

    def __init__(self, vocabulary_uri, vocab_file_uri):
        self.vocabulary_uri = vocabulary_uri  # URI of the vocabulary namespace
        self.vocab_file_uri = vocab_file_uri  # location of the file with the vocabulary
        self.source_id = 'rdf-graph-import'
        self.graph = None  # Graph of triples
        self.vocab_object = utilities.get_man_obj_from_uri(
            self.vocabulary_uri,
            filters={'item_type': 'vocabularies'}
        )
        self.load_parse_vocabulary(self.vocab_file_uri)


    def load_parse_vocabulary(self, vocab_file_uri, mime_type='application/rdf+xml'):
        """
        Loads and parses a vocabulary, defaulting to the RDF-XML file format
        """
        graph = Graph()
        try:
            if mime_type:
                graph.parse(vocab_file_uri, format=mime_type)
            else:
                graph.parse(vocab_file_uri)
        except:
            print(f'Failed to load the graph from {vocab_file_uri}')
            graph = None
        if graph is not None:
            self.vocab_file_uri = vocab_file_uri
            self.graph = graph
        return self.graph


    def delete_saved_vocab_classes_properties_assertions(self):
        """Deletes previously saved classes, properties, and assertions"""
        if not self.graph or not self.vocab_object:
            return None

        # Delete all the assertions where the publisher is the vocabulary
        # publisher and the subject is an entity from this vocabulary.
        # NOTE: We exclude assertions from the default source id.
        AllAssertion.objects.filter(
            publisher=self.vocab_object.publisher,
            subject__context=self.vocab_object,
        ).exclude(
            source_id=configs.DEFAULT_SOURCE_ID,
        ).delete()

        # Now delete class and property items from the vocabulary,
        # excluding those defined from the default source id.
        AllManifest.objects.filter(
            publisher=self.vocab_object.publisher,
            context=self.vocab_object,
            item_type__in=['class', 'property'],
        ).exclude(
            source_id=configs.DEFAULT_SOURCE_ID,
            uuid=self.vocab_object.uuid
        ).delete()


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


    def get_man_obj_from_uri_or_key(self, uri, filters=None, excludes=None):
        """Gets an manifest object from a URI or URI derived item_key"""
        item_key = utilities.uri_to_common_prefix(
            uri,
            uri_prefixes=URI_PREFIXES,
        )
        return utilities.get_man_obj_from_uri(
            uri,
            item_key=item_key,
            filters=filters,
            excludes=excludes
        )


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


    def get_entity_owl_type_uri(self, s):
        """Gets the owl type URI for a subject entity from the graph"""
        if not self.graph:
            return None

        for s, _, o in self.graph.triples((s, RDF.type, None)):
            subject_uri = s.__str__()  # get the URI of the subject as a string
            object_uri = o.__str__()  # get the URI of the rdf:type    
            print(f'{subject_uri} a (rdf:type) {object_uri}')
            return object_uri
        
        # Not found, so return nothing.
        return None


    def get_units_of_measure_object(self, s):
        """Gets a units of measurement object for a s (subject) from the graph"""
        if not self.graph:
            return None
        
        # Get the predicate object for cidoc-crm:P91_has_unit
        p = URIRef(CIDOC_P1_HAS_UNIT_URI)
        for _, _, o in self.graph.triples((s, p, None)):
            object_uri = o.__str__()
            unit_object = self.get_man_obj_from_uri_or_key(
                object_uri,
                filters={'item_type': 'units'}
            )
            if unit_object:
                return unit_object
        return None


    def save_vocabulary_entity_comments(self, replace_old_comments=False):
        """Saves comments about entities in a vocabulary """
        if not self.graph or not self.vocab_object:
            return None
        
        for s, p, o in self.graph.triples((None, RDFS.comment, None)):
            subject_uri = s.__str__()  # get the URI of the subject as a string
            comment = o.__str__()  # get the comment from the object as a string
            
            sub_obj = self.get_man_obj_from_uri_or_key(subject_uri)
            if not sub_obj:
                # We have yet to import this subject entity, so
                # we can't talk about it yet.
                print(f'Skip comments on unknown entity {subject_uri}')
                continue
            
            utilities.add_string_assertion_simple(
                project_id=self.vocab_object.project.uuid,
                publisher_id=self.vocab_object.publisher.uuid,
                subject_obj=sub_obj, 
                predicate_id=configs.PREDICATE_RDFS_COMMENT_UUID,
                source_id=self.source_id,
                str_content=comment,
                replace_old_content=replace_old_comments
            )


    def save_vocabulary_units_of_measure(self, units_of_measure_uri=CIDOC_P1_HAS_UNIT_URI):
        """Saves assertions about units of measure for entities in a vocabulary"""
        if not self.graph or not self.vocab_object:
            return None
        
        p = URIRef(units_of_measure_uri)
        for s, p, o in self.graph.triples((None, p, None)):
            subject_uri = s.__str__()  # get the URI of the subject as a string
            object_uri = o.__str__()  # get the URI of the object as a string
            
            subj_obj = self.get_man_obj_from_uri_or_key(subject_uri)
            if not subj_obj:
                continue
            unit_object = self.get_man_obj_from_uri_or_key(
                object_uri,
                filters={'item_type': 'units'}
            )
            if not unit_object:
                continue
            
            # OK to make the assertion about the units of measurement.
            ass_obj, _ = AllAssertion.objects.get_or_create(
                uuid=AllAssertion().primary_key_create(
                    subject_id=subj_obj.uuid,
                    predicate_id=configs.PREDICATE_CIDOC_HAS_UNIT_UUID,
                    object_id=unit_object.uuid,
                ),
                defaults={
                    'publisher': self.vocab_object.publisher,
                    'project': self.vocab_object.project,
                    'source_id': self.source_id,
                    'subject': subj_obj,
                    'predicate_id': configs.PREDICATE_CIDOC_HAS_UNIT_UUID,
                    'object': unit_object,
                }
            )
            print(
                f'Assertion {ass_obj.uuid}: '
                f'{ass_obj.subject.label} [{ass_obj.subject.uuid}]'
                f'-> {ass_obj.predicate.label} [{ass_obj.predicate.uuid}]'
                f'-> {ass_obj.object.label} [{ass_obj.object.uuid}]'
            )


    def save_vocabulary_icon_assertions(self, has_icon_uri=OC_GEN_HAS_ICON_URI):
        """Saves assertions about icons describing entities in a vocabulary"""
        if not self.graph or not self.vocab_object:
            return None
        
        p = URIRef(has_icon_uri)
        for s, p, o in self.graph.triples((None, p, None)):
            subject_uri = s.__str__()  # get the URI of the subject as a string
            object_uri = o.__str__()  # get the URI of the object as a string
            
            subj_obj = self.get_man_obj_from_uri_or_key(subject_uri)
            if not subj_obj:
                continue

            # Get or make a manifest item for the icon itself.
            icon_obj, _ = get_make_icon_man_obj_and_resource_obj(
                icon_uri=object_uri, 
                icon_label=f'Icon for {subj_obj.label}', 
                source_id=self.source_id, 
                vocab_obj=self.vocab_object,
            )
            print(
                f'Manifest item [{icon_obj.uuid}]: {icon_obj.label} at '
                f'{icon_obj.uri} or {icon_obj.slug}'
            )
            
            # OK to make the assertion about the units of measurement.
            ass_obj, _ = AllAssertion.objects.get_or_create(
                uuid=AllAssertion().primary_key_create(
                    subject_id=subj_obj.uuid,
                    predicate_id=configs.PREDICATE_OC_HAS_ICON_UUID,
                    object_id=icon_obj.uuid,
                ),
                defaults={
                    'publisher': self.vocab_object.publisher,
                    'project': self.vocab_object.project,
                    'source_id': self.source_id,
                    'subject': subj_obj,
                    'predicate_id': configs.PREDICATE_OC_HAS_ICON_UUID,
                    'object': icon_obj,
                }
            )
            print(
                f'Assertion {ass_obj.uuid}: '
                f'{ass_obj.subject.label} [{ass_obj.subject.uuid}]'
                f'-> {ass_obj.predicate.label} [{ass_obj.predicate.uuid}]'
                f'-> {ass_obj.object.label} [{ass_obj.object.uuid}]'
            )


    def save_vocabulary_hierarchy(self):
        """Saves hierarchic relations for class and property entities in a vocabulary"""
        if not self.graph or not self.vocab_object:
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

                subj_obj = self.get_man_obj_from_uri_or_key(subject_uri)
                if not subj_obj:
                    continue
                obj_obj = self.get_man_obj_from_uri_or_key(object_uri)
                if not obj_obj:
                    continue
                if (subj_obj.item_type != ok_oc_item_type 
                    or obj_obj.item_type != ok_oc_item_type):
                    print(
                        f'Both {subj_obj.label} {subj_obj.uri} {subj_obj.item_type} '
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
                        'publisher': self.vocab_object.publisher,
                        'project': self.vocab_object.project,
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


    def save_vocab_entity(self, subject_uri, label=None, fallback_oc_item_type=None):
        """Saves a subject entity"""
        s = URIRef(subject_uri)
        if not label:
            for _, _, o in self.graph.triples((s, RDFS.label, None)):
                label = o.__str__()  # get the Label of from object as a string
        if not label:
            print(f'Cannot find label for entity: {subject_uri}')
            return None
        
        # Get the rdf:type for the subject uri
        subj_owl_type_uri = self.get_entity_owl_type_uri(s)
        oc_item_type = self.map_owl_entity_type_to_oc_item_type(subj_owl_type_uri)
        if fallback_oc_item_type and not oc_item_type:
            # Fallback to this default value for the OC item type.
            oc_item_type = fallback_oc_item_type
        if not oc_item_type:
            # This type has no mapping to an OC item_type
            print(f'Cannot determine OC item type for: {label}, {subject_uri}')
            return None

        # Make a new manifest dictionary object.
        uri = AllManifest().clean_uri(subject_uri)
        
        # Check to see if this item already exists as an Open Context
        # default.
        default_man = self.get_man_obj_from_uri_or_key(
            uri,
            filters={'source_id': configs.DEFAULT_SOURCE_ID}
        )
        if default_man:
            # Skip database edits / interactions with this, it is
            # an Open Context default item.
            print(f'Already a default entity: {label}, {subject_uri}')
            return None
        
        # Default data type.
        data_type = 'id'
        unit_object = self.get_units_of_measure_object(s)
        if unit_object:
            # We have a unit of measurement object for this subject.
            # Update the data_type accordingly.
            data_type = unit_object.meta_json.get('data_type', 'xsd:double')

        man_dict = {
            'publisher': self.vocab_object.publisher,
            'project': self.vocab_object.project,
            'source_id': self.source_id,
            'item_type': oc_item_type,
            'data_type': data_type,
            'label': label,
            'uri': uri,
            'context': self.vocab_object,
        }
        item_key = utilities.uri_to_common_prefix(
            uri,
            uri_prefixes=URI_PREFIXES,
        )
        if item_key:
            man_dict['item_key'] = item_key

        new_man_obj, _ = AllManifest.objects.get_or_create(
            uri=uri,
            defaults=man_dict
        )
        print(
            f'Manifest item [{new_man_obj.uuid}]: {new_man_obj.label} at '
            f'{new_man_obj.uri} or {new_man_obj.slug}'
        )


    def save_vocab_entities(self, replace_old=False):
        """ saves labels of entities in a vocabulary """
        if not self.graph or not self.vocab_object:
            print('Missing data, not saving entities')
            return None
        
        for s, p, o in self.graph.triples((None, RDFS.label, None)):
            subject_uri = s.__str__()  # get the URI of the subject as a string
            label = o.__str__()  # get the Label of from object as a string
            self.save_vocab_entity(subject_uri, label=label)

    
