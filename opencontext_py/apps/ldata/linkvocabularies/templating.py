import json
import copy
import datetime
from random import randint
from django.conf import settings
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, SKOS, OWL
from opencontext_py.libs.languages import Languages
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.libs.globalmaptiles import GlobalMercator
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.namespaces.models import ItemNamespaces
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkentities.models import LinkEntity


class TemplateVocab():
    """ This class makes an object useful displaying hierarchies
        of items in vocabularies
    """
    
    VERSION_CONTROL_LINKS = {
        'http://opencontext.org/vocabularies/dinaa': \
        'https://github.com/ekansa/oc-ontologies/blob/master/vocabularies/dinaa-alt.owl',
        'http://opencontext.org/vocabularies/oc-general': \
        'https://github.com/ekansa/oc-ontologies/blob/master/vocabularies/oc-general.owl',
        'http://opencontext.org/vocabularies/oc-general/': \
        'https://github.com/ekansa/oc-ontologies/blob/master/vocabularies/oc-general.owl'
    }

    def __init__(self):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.uri = None
        self.uuid = False
        self.vocab_uri = None
        self.json_obj = LastUpdatedOrderedDict()
        self.entity = None  # entity object for the concept or vocabulary item
        self.vocab_entity = None  # entity object for the parent vocabulary
        self.project_uuid = None
        self.version_control_uri = False  # uri to vocab version control
        self.default_comment = None
        self.comment = None
        self.root_classes = []
        self.root_properties = []
        self.json_tree = False
        self.parents = []
        self.children = []
    
    def create_template_for_entity(self, entity):
        """ creates a template for diplaying a
            concept or vocabulary entity, either in
            HTML or in JSON
        """
        self.entity = entity
        self.uri = entity.uri
        self.vocab_uri = entity.vocab_uri
        self.project_uuid = entity.project_uuid
        # add the version control uri
        for vocab_key, version_uri in self.VERSION_CONTROL_LINKS.items():
            if vocab_key == self.vocab_uri:
                self.version_control_uri = version_uri
                break
        self.get_comments()  # always get comments for the entity
        if self.uri == self.vocab_uri:
            # we have a vocabulary so do vocab methods
            self.vocab_entity = entity
            self.get_root_entities()
        else:
            # we have a concept in a vocabulary, so do
            # concept methods
            ent_voc = Entity()
            vocab_found = ent_voc.dereference(self.vocab_uri)
            if vocab_found:
                # found the parent vocab entity
                self.vocab_entity = ent_voc
            self.get_entity_parents()
            self.get_entity_children()
    
    def make_json_for_html(self):
        """ makes JSON strings for embedding in HTML """
        root_obj = []
        if len(self.root_classes) > 0:
            # we have root level categories
            root_dict = LastUpdatedOrderedDict()
            root_dict['root'] = 'Top-Level Classes / Categories'
            root_dict['children'] = self.root_classes
            root_dict['more'] = True
            root_obj.append(root_dict)
        if len(self.root_properties) > 0:
            # we have root level properties
            root_dict = LastUpdatedOrderedDict()
            root_dict['root'] = 'Top-Level Properties / Relations'
            root_dict['children'] = self.root_properties
            root_dict['more'] = True
            root_obj.append(root_dict)
        if len(self.children) > 0:
            # we have concpet children
            root_dict = LastUpdatedOrderedDict()
            if self.entity.entity_type == 'class':    
                root_dict['root'] = 'Sub-categories for ' + self.entity.label
            else:
                root_dict['root'] = 'Sub-properties for ' + self.entity.label
            root_dict['children'] = self.children
            root_dict['more'] = True
            root_obj.append(root_dict)
        if len(root_obj) > 0:
            # we items to display for the json_tree  
            self.json_tree = json.dumps(root_obj,
                                        ensure_ascii=False,
                                        indent=4)
    
    def make_json_obj(self, children_only=False):
        """ makes the json object for the current concept
            or vocabulary entity
        """
        if self.entity is not None:
            self.json_obj['id'] = self.entity.uri
            self.json_obj['label'] = self.entity.label
            self.json_obj['slug'] = self.entity.slug
            self.json_obj['href'] = self.make_local_url(self.entity.uri)
            self.json_obj['rdfs:comment'] = self.comment
            self.json_obj['vocab_uri'] = self.vocab_uri
            self.json_obj['version_control'] = self.version_control_uri
            if self.uri == self.vocab_uri:
                # we have a vocabulary so add vocab attributes
                self.json_obj['entity_type'] = 'vocabulary'
                self.json_obj['vocab_label'] = self.entity.label
                self.json_obj['root_classes'] = self.root_classes
                self.json_obj['root_properties'] = self.root_properties
            else:
                # we have a concept entity (from a vocabulary)
                self.json_obj['entity_type'] = self.entity.entity_type
                if self.vocab_entity is not None:
                    self.json_obj['vocab_label'] = self.vocab_entity.label
                self.json_obj['parents'] = self.parents
                self.json_obj['children'] = self.children
        return self.json_obj
    
    def get_entity_parents(self):
        """ gets the parents of a given entity """
        if isinstance(self.uri, str):
            lr = LinkRecursion()
            parents = lr.get_jsonldish_entity_parents(self.uri, False)
            if isinstance(parents, list):
                for parent in parents:
                    ent_dict = LastUpdatedOrderedDict()
                    ent_dict['id'] = parent['id']
                    ent_dict['label'] = parent['label']
                    ent_dict['slug'] = parent['slug']
                    ent_dict['href'] = self.make_local_url(parent['id'])
                    self.parents.append(ent_dict)
    
    def get_entity_children(self):
        """ gets the children of a given entity """
        if isinstance(self.uri, str):
            raw_children = self.get_uri_children(self.uri)
            for child in raw_children:
                child['children'] = self.get_uri_children(child['id'])
                if len(child['children']) > 0:
                    child['more'] = True;
                self.children.append(child)
    
    def get_uri_children(self, uri):
        """ gets the children for a given uri """
        output = []
        if isinstance(uri, str):
            lr = LinkRecursion()
            lr.get_entity_children(uri, False)
            children = lr.child_entities
            if isinstance(children, dict):
                child_uris = []
                for ch_uri, ch_list in children.items():
                    if uri == ch_uri:
                        child_uris = ch_list
                        break
                # now we have child entity uris, put them in the proper order
                lequiv = LinkEquivalence()
                child_uris = lequiv.get_identifier_list_variants(child_uris)
                child_ents = LinkEntity.objects\
                                       .filter(uri__in=child_uris)\
                                       .exclude(uri=self.uri)\
                                       .order_by('sort', 'label', 'uri')
                for act_ent in child_ents:
                    ent_dict = LastUpdatedOrderedDict()
                    ent_dict['id'] = act_ent.uri
                    ent_dict['label'] = act_ent.label
                    ent_dict['slug'] = act_ent.slug
                    ent_dict['href'] = self.make_local_url(act_ent.uri)
                    output.append(ent_dict)
        return output

    def get_comments(self):
        """ gets comments for the entity (or vocabulary) """
        if isinstance(self.uri, str):
            lequiv = LinkEquivalence()
            subjs = lequiv.get_identifier_list_variants(self.uri)
            lequiv = LinkEquivalence()
            # get all the varients of RDFS:comments
            comment_uris = lequiv.get_identifier_list_variants('rdfs:comment')
            commment_annos = LinkAnnotation.objects\
                                           .filter(subject__in=subjs,
                                                   predicate_uri__in=comment_uris)[:1]
            if len(commment_annos) > 0:
                self.comment = commment_annos[0].obj_extra
                lang = Languages()
                self.default_comment = lang.get_default_value_str(self.comment)
        
    def get_root_entities(self):
        """ gets top level entities that are not
            part of parent classes or properties
        """
        if isinstance(self.vocab_uri, str):
            class_ents = self.get_entities('class')
            prop_ents = self.get_entities('property')
            self.root_classes = self.make_root_entity_list(class_ents)
            self.root_properties = self.make_root_entity_list(prop_ents)
    
    def make_root_entity_list(self, entity_list):
        """ makes a list of entities that
            are not children of other items in the hierarchy
        """
        root_entities = []
        for act_ent in entity_list:
            lr = LinkRecursion()
            parents = lr.get_jsonldish_entity_parents(act_ent.uri, False)
            if parents is False:
                ent_dict = LastUpdatedOrderedDict()
                ent_dict['id'] = act_ent.uri
                ent_dict['label'] = act_ent.label
                ent_dict['slug'] = act_ent.slug
                ent_dict['href'] = self.make_local_url(act_ent.uri)
                ent_dict['children'] = self.get_uri_children(act_ent.uri)
                if len(ent_dict['children']) > 0:
                    ent_dict['more'] = True;
                root_entities.append(ent_dict)
        return root_entities
    
    def get_entities(self, entity_types):
        """ gets entities in the vocabulary """
        if not isinstance(entity_types, list):
            entity_types = [entity_types]
        ents = LinkEntity.objects\
                         .filter(vocab_uri=self.vocab_uri,
                                 ent_type__in=entity_types)\
                         .exclude(uri=self.vocab_uri)\
                         .order_by('sort', 'label', 'uri')
        return ents
    
    def make_local_url(self, uri):
        """ makes a local path from a URI by
            removing the cannonical part of the uri
        """
        output = uri.replace(settings.CANONICAL_HOST, self.base_url)
        return output
