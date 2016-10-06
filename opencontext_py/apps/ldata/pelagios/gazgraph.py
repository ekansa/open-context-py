import json
import requests
import hashlib
from time import sleep
from rdflib import Graph, URIRef, Literal, Namespace, BNode
from rdflib.namespace import RDF, RDFS, SKOS, OWL
from django.conf import settings
from django.db import connection
from django.db import models
from django.db.models import Q
from django.core.cache import caches
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ldata.pelagios.gazetteer import PelagiosGazetteer


class PelagiosGazetteerGraph():
    """ Uses the PelagiosData object to 
        to make Pelagios compliant open annotations
        
    """
    NAMESPACES = {
        'cito': 'http://purl.org/spar/cito',
        'cnt': 'http://www.w3.org/2011/content#',
        'dcterms': 'http://purl.org/dc/terms/',
        'foaf': 'http://xmlns.com/foaf/0.1/',
        'geo': 'http://www.w3.org/2003/01/geo/wgs84_pos#',
        'geosparql': 'http://www.opengis.net/ont/geosparql#',
        'gn': 'http://www.geonames.org/ontology#',
        'lawd': 'http://lawd.info/ontology/',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'skos': 'http://www.w3.org/2004/02/skos/core#',
        'oc-gen': 'http://opencontext.org/vocabularies/oc-general/'
    }
    
    def __init__(self):
        self.data_obj = PelagiosGazetteer()
        self.g = None
        self.prep_graph()
        self.base_uri = settings.CANONICAL_HOST + '/pelagios/data/'
        self.request = False
        self.refresh_cache = False
        self.print_caching = False
        self.cache_ok = True
        self.cache_timeout = None  # None means forever
    
    def prep_graph(self):
        """ prepares a graph for Pelagios """
        self.g = Graph()
        for prefix, ns_uri in self.NAMESPACES.items():
            ns = Namespace(ns_uri)
            self.g.bind(prefix, ns)
    
    def make_graph(self):
        associated_uris = []
        self.get_db_data()
        if len(self.data_obj.gaz_items) > 0:
            for uuid, gaz_item in self.data_obj.gaz_items.items():
                if gaz_item.is_valid:
                    # only make annotations if the item is valid
                    self.make_add_triple(gaz_item.uri,
                                         RDF.type,
                                         self.make_full_uri('lawd', 'Place'))
                    self.make_add_triple(gaz_item.uri,
                                         RDFS.label,
                                         None,
                                         gaz_item.label)
                    self.make_add_triple(gaz_item.uri,
                                         self.make_full_uri('dcterms', 'title'),
                                         None,
                                         gaz_item.title)
                    self.make_add_triple(gaz_item.uri,
                                         self.make_full_uri('dcterms', 'description'),
                                         None,
                                         gaz_item.description)
                    self.make_add_triple(gaz_item.uri,
                                         self.make_full_uri('dcterms', 'isPartOf'),
                                         gaz_item.project_uri)
                    if isinstance(gaz_item.temporal, str):
                        self.make_add_triple(gaz_item.uri,
                                             self.make_full_uri('dcterms', 'temporal'),
                                             None,
                                             gaz_item.temporal)
                    if gaz_item.geo_meta is not None and gaz_item.geo_meta is not False:
                        # print('ok! geo-meta: ' + str(gaz_item.geo_meta))
                        if len(gaz_item.geo_meta) > 0:
                            geo = gaz_item.geo_meta[0]
                            geo_node = BNode()
                            act_s = URIRef(gaz_item.uri)
                            pred_uri = self.make_full_uri('geo', 'location')
                            act_p = URIRef(pred_uri)
                            self.g.add((act_s, act_p, geo_node))
                            pred_uri = self.make_full_uri('geo', 'lat')
                            act_p = URIRef(pred_uri)
                            self.g.add((geo_node, act_p, Literal(geo.latitude)))
                            pred_uri = self.make_full_uri('geo', 'long')
                            act_p = URIRef(pred_uri)
                            self.g.add((geo_node, act_p, Literal(geo.longitude)))
    
    def check_valid_uri(self, uri):
        """ checks to see if a uri is valid """
        valid = False
        if isinstance(uri, str):
            uri_out = False
            try:
                uri_test = URIRef(uri)
                uri_out = uri_test.n3()
            except:
                # some sort of error thrown, so not valid
                valid = False
            if isinstance(uri_out, str):
                valid = True
        return valid
                                    
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
            
    def get_db_data(self):
        """ gets gazetteer related items, then
            populates these with manifest objects and context
            paths (for subjects)
        """
        key = self.make_cache_key('pelagios-gaz', 'data')
        if self.refresh_cache:
            # we forcing a refresh of the cache, not us of cached data
            cache_data_obj = None
        else:
            # check to see if we have a cached version
            cache_data_obj = self.get_cache_object(key)
        if cache_data_obj is None:
            self.data_obj.get_prep_linked_sites()
            # now cache the data
            self.save_cache_object(key, self.data_obj)
        else:
            # use the cached data for the data object
            self.data_obj = cache_data_obj
    
    def make_cache_key(self, prefix, identifier):
        """ makes a valid OK cache key """
        return str(prefix) + "-" + str(identifier)
    
    def make_cache_key_hash(self, prefix, identifier):
        """ makes a valid OK cache key """
        hash_obj = hashlib.sha1()
        concat_string = str(prefix) + "-" + str(identifier)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def get_cache_object(self, key):
        """ gets a cached reddis object """
        try:
            cache = caches['default']
            obj = cache.get(key)
            if self.print_caching:
                print('Cache checked: ' + key)
        except:
            obj = None
            if self.print_caching:
                print('Cache Fail checked: ' + key)
        return obj

    def save_cache_object(self, key, obj):
        """ saves a cached reddis object """
        try:
            cache = caches['default']
            cache.set(key, obj, self.cache_timeout)
            ok = True
            if self.print_caching:
                print('Cache Saved: ' + key)
        except:
            self.cache_ok = False
            ok = False
            if self.print_caching:
                print('Failed to cache: ' + key)
        return ok
    