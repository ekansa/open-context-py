import json
import requests
from time import sleep
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, SKOS, OWL
from django.conf import settings
from django.db import connection
from django.db import models
from django.db.models import Q
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ldata.pelagios.models import PelagiosData


class PelagiosGraph():
    """ Uses the PelagiosData object to 
        to make Pelagios compliant open annotations
        
from opencontext_py.apps.ldata.pelagios.graph import PelagiosGraph
pelagios = PelagiosGraph()
pelagios.project_uuids = ['3']
pelagios.test_limit = 10
pelagios.make_graph()
pelagios.g.serialize(format='turtle')
    """
    NAMESPACES = {
        'cnt': 'http://www.w3.org/2011/content#',
        'dcterms': 'http://purl.org/dc/terms/',
        'foaf': 'http://xmlns.com/foaf/0.1/',
        'oa': 'http://www.w3.org/ns/oa#',
        'pelagios': 'http://pelagios.github.io/vocab/terms#',
        'relations': 'http://pelagios.github.io/vocab/relations#',
        'xsd': 'http://www.w3.org/2001/XMLSchema',
        'oc-gen': 'http://opencontext.org/vocabularies/oc-general/'
    }
    
    def __init__(self):
        self.data_obj = PelagiosData()
        self.project_uuids = []
        self.test_limit = False
        self.g = None
        self.prep_graph()
        self.base_uri = settings.CANONICAL_HOST + '/pelagios/.ttl#'
    
    def prep_graph(self):
        """ prepares a graph for Pelagios """
        self.g = Graph()
        for prefix, ns_uri in self.NAMESPACES.items():
            ns = Namespace(ns_uri)
            self.g.bind(prefix, ns)
    
    def make_graph(self):
        self.get_db_data()
        if len(self.data_obj.oa_items) > 0:
            item_cnt = 0
            for uuid, oa_item in self.data_obj.oa_items.items():
                if oa_item.is_valid:
                    # make annotation assertion
                    uri = URImanagement.make_oc_uri(oa_item.manifest.uuid,
                                                    oa_item.manifest.item_type)
                    self.make_add_triple(uri, RDF.type, 'pelagios:AnnotatedThing')
                    title = self.make_dcterms_title(oa_item.manifest.label,
                                                    oa_item.context)
                    self.make_add_triple(uri,
                                         self.make_full_uri('dcterms', 'title'),
                                         None,
                                         title)
                    self.make_add_triple(uri,
                                         self.make_full_uri('foaf', 'homepage'),
                                         settings.CANONICAL_HOST)
                                    
    def make_add_triple(self, sub_uri, pred_uri, obj_uri=None, obj_literal=None):
        """ makes a triple and adds it to the graph """
        act_s = URIRef(sub_uri)
        act_p = URIRef(pred_uri)
        if obj_literal is not None:
            act_o = Literal(obj_literal)
        else:
            act_o = URIRef(obj_uri)
        self.g.add((act_s, act_p, act_o))
    
    def make_full_uri(self, prefix, value):
        """ makes a full uri for a prefix and value """
        if prefix in self.NAMESPACES:
            output = self.NAMESPACES[prefix] + value
        else:
            output = prefix + ':' + value
        return output
    
    def make_dcterms_title(self, label, context):
        """ makes a dcterms title, includes context if present """
        if isinstance(context, str):
            if '/' in context:
                context_ex = context.split('/')
                if context_ex[-1] == label:
                    context_ex.pop(-1)
                context = '/'.join(context_ex)
            title = label + ' from ' + context       
        else:
            title = label
        return title
    
    def get_db_data(self):
        """ gets gazetteer related items, then
            populates these with manifest objects and context
            paths (for subjects)
        """
        self.data_obj.project_uuids = self.project_uuids
        self.data_obj.test_limit = self.test_limit
        self.data_obj.get_prep_ocitems_rel_gazetteer()
    
    