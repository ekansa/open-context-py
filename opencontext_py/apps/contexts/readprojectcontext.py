from django.conf import settings
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.assertions.models import Assertion


class ReadProjectContextVocabGraph():
    """ Methods to read the project context vocabulary graph """
    
    GLOBAL_VOCABS = [
        {'@id': 'oc-pred:link',
         'owl:sameAs': 'http://opencontext.org/predicates/oc-3',
         'label': 'link',
         'slug': 'link',
         'oc-gen:predType': 'link',
         '@type': '@id'},
        {'@id': Assertion.PREDICATES_NOTE,
         'label': 'Note',
         'owl:sameAs': False,
         'slug': False,
         '@type': 'xsd:string'},
    ]
    
    def __init__(self, proj_context_json_ld=None):
        self.context = proj_context_json_ld
    
    def lookup_predicate(self, id):
        """looks up an Open Context predicate by an identifier
           (slud id, uri, slug, or uuid)
        """
        output = self.lookup_oc_descriptor(id, 'predicates')
        return output
    
    def lookup_type(self, id):
        """looks up an Open Context type by an identifier
           (slud id, uri, slug, or uuid)
        """
        output = self.lookup_oc_descriptor(id, 'types')
        return output
    
    def lookup_oc_descriptor(self, id, item_type):
        """looks up a predicate, or a type by an identifier
           (slud id, uri, slug, or uuid)
        """
        output = None
        if (isinstance(self.context, dict) and
            isinstance(id, str)):
            if '@graph' in self.context:
                self.context['@graph'] += self.GLOBAL_VOCABS
                for g_obj in self.context['@graph']:
                    id_list = self.get_id_list_for_g_obj(g_obj)
                    if id in id_list:
                        output = g_obj
                        if item_type == 'predicates' and '@type' not in g_obj:
                            output['@type'] = self.get_predicate_datatype_for_graph_obj(g_obj)
                        break
        return output
    
    def get_predicate_datatype_for_graph_obj(self, g_obj):
        """ looks up a predicate data type for a given graph object """
        datatype = None
        if isinstance(g_obj, dict):
            if '@id' in g_obj:
                slug_uri = g_obj['@id']
            elif 'id' in g_obj:
                slug_uri = g_obj['id']
            else:
                slug_uri = None
            datatype = self.get_predicate_datatype_by_slug_uri(slug_uri)
        return datatype
    
    def get_id_list_for_g_obj(self, g_obj):
        """gets a list of ids for an object"""
        id_list = []
        id_keys = [
            '@id',
            'id',
            'owl:sameAs',
            'slug',
            'uuid'
        ]
        if isinstance(g_obj, dict):
            for id_key in id_keys:
                if id_key in g_obj:
                    if g_obj[id_key] not in id_list:
                        id_list.append(g_obj[id_key])
        return id_list
    
    def get_predicate_datatype_by_slug_uri(self, slug_uri):
        """looks up a predicates datatype via the slug URI """
        datatype = 'xsd:string'  # default to treating all as a string
        if (isinstance(self.context, dict) and
            isinstance(slug_uri, str)):
            if '@context' in self.context:
                if slug_uri in self.context['@context']:
                    if '@type' in self.context['@context'][slug_uri]:
                        datatype = self.context['@context'][slug_uri]['@type']
        return datatype

