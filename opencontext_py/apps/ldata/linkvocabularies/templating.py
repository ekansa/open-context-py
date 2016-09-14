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


# Help organize the code, with a class to make templating easier
class TemplateVocab():
    """ This class makes an object useful displaying hierarchies
        of items in vocabularies
    """

    def __init__(self):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.uri = None
        self.vocab_uri = None
        self.default_comment = None
        self.comment = None
        self.top_classes = []
        self.top_properties = []
        self.parents = []
        self.children = []
    
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
        
    def get_top_entities(self):
        """ gets top level entities that are not
            part of parent classes or properties
        """
        if isinstance(self.vocab_uri, str):
            class_ents = self.get_entities('class')
            prop_ents = self.get_entities('property')
            self.top_classes = self.make_top_entity_list(class_ents)
            self.top_properties = self.make_top_entity_list(prop_ents)
    
    def make_top_entity_list(self, entity_list):
        """ makes a list of entities that
            are not children of other items in the hierarchy
        """
        top_entities = []
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
                top_entities.append(ent_dict)
        return top_entities
    
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
