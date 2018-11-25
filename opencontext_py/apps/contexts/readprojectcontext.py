from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.ocitem.itemkeys import ItemKeys
from opencontext_py.apps.ocitems.ocitem.caching import ItemGenerationCache


class ReadProjectContextVocabGraph():
    """ Methods to read the project context vocabulary graph """
    
    GLOBAL_VOCAB_GRAPH = [
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
    
    # predicates used for equivalence, used to make
    # inferred assertions
    REL_PREDICATES_FOR_INFERRENCE = [
        'skos:closeMatch',
        'skos:exactMatch'
    ]
    REL_MEASUREMENTS = ['cidoc-crm:P67_refers_to',
                        'oc-gen:has-technique',
                        'rdfs:range']
    ITEM_REL_PREDICATES = ['skos:closeMatch',
                           'skos:exactMatch',
                           'owl:sameAs',
                           'skos:related',
                           'skos:broader',
                           'dc-terms:references',
                           'dc-terms:hasVersion',
                           'http://nomisma.org/ontology#hasTypeSeriesItem']
    
    def __init__(self, proj_context_json_ld=None):
        self.context = None
        self.graph = self.GLOBAL_VOCAB_GRAPH
        if isinstance(proj_context_json_ld, dict):
            if '@context' in proj_context_json_ld:
                self.context = proj_context_json_ld['@context']
            if '@graph' in proj_context_json_ld:
                self.graph += proj_context_json_ld['@graph']
    
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
    
    def lookup_type_by_type_obj(self, type_obj):
        """looks up an Open Context type to get
           more information, including linked data equivalents
           by looking up the a type from how it is used as
           the object of a descriptive predicate in an observation
        """
        output = type_obj
        type_ids = self.get_id_list_for_g_obj(type_obj)
        found = False
        for type_id in type_ids:
            if found is False:
                found_type_obj = self.lookup_type(type_id)
                if isinstance(found_type_obj, dict):
                    found = True
                    output = found_type_obj
                    break
        return output
    
    def lookup_oc_descriptor(self, id, item_type):
        """looks up a predicate, or a type by an identifier
           (slud id, uri, slug, or uuid)
        """
        output = None
        if (isinstance(self.graph, list) and
            isinstance(id, str)):
            for g_obj in self.graph:
                id_list = self.get_id_list_for_g_obj(g_obj)
                if id in id_list:
                    output = g_obj
                    if item_type == 'predicates' and '@type' not in g_obj:
                        output['@type'] = self.get_predicate_datatype_for_graph_obj(g_obj)
                    break
        return output
    
    def get_predicate_datatype_for_graph_obj(self, g_obj):
        """ looks up a predicate data type for a given graph object """
        slug_uri = self.get_id_from_g_obj(g_obj)
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
    
    def get_id_from_g_obj(self, g_obj):
        """ gets the id form a g_obj, either the @id or id varient """
        id  = None
        if isinstance(g_obj, dict):
            if '@id' in g_obj:
                id = g_obj['@id']
            elif 'id' in g_obj:
                id = g_obj['id']
            else:
                id = None
        return id
        
    def get_predicate_datatype_by_slug_uri(self, slug_uri):
        """looks up a predicates datatype via the slug URI """
        datatype = 'xsd:string'  # default to treating all as a string
        if (isinstance(self.context, dict) and
            isinstance(slug_uri, str)):
            if '@context' in self.context:
                if slug_uri in self.context['@context']:
                    if '@type' in self.context['@context'][slug_uri]:
                        datatype = self.context['@context'][slug_uri]['@type']
                    elif 'type' in self.context['@context'][slug_uri]:
                        datatype = self.context['@context'][slug_uri]['type']
        return datatype

    def get_equivalent_objects(self, info_dict):
        """ Gets equivalent linked data dicts associated with an
            info_dict.
        """
        equiv_uris = []
        equiv_objects = []
        for rel_pred in self.REL_PREDICATES_FOR_INFERRENCE:
            if rel_pred in info_dict:
                for equiv_obj in info_dict[rel_pred]:
                    equiv_uri = self.get_id_from_g_obj(equiv_obj)
                    if equiv_uri and equiv_uri not in equiv_uris:
                        # make sure that the equivalent URIs are unique
                        equiv_uris.append(equiv_uri)
                        equiv_objects.append(equiv_obj)
        return equiv_objects

    def infer_assertions_for_item_json_ld(self, json_ld):
        """ makes a list of inferred assertions from item json ld """
        inferred_assertions = []
        if isinstance(json_ld, dict):
            if ItemKeys.PREDICATES_OCGEN_HASOBS in json_ld:
                unique_pred_assertions = LastUpdatedOrderedDict()
                for obs_dict in json_ld[ItemKeys.PREDICATES_OCGEN_HASOBS]:
                    for obs_pred_key, obj_values in obs_dict.items():
                        assertion = None
                        obs_pred_info = self.lookup_predicate(obs_pred_key)
                        equiv_pred_objs = self.get_equivalent_objects(obs_pred_info)
                        if len(equiv_pred_objs):
                            # we're ony going to use the first equivalent of a predicate
                            # otherwise this gets too complicated
                            equiv_pred_obj = equiv_pred_objs[0]
                            equiv_pred_uri = self.get_id_from_g_obj(equiv_pred_obj)
                            # inferred assertions will have unique LOD predicates, with
                            # one or more values. The unique_pred_assertions dict makes
                            # sure the LOD predicates are used only once.
                            if equiv_pred_uri not in unique_pred_assertions:
                                assertion = equiv_pred_obj
                                assertion['ld_objects'] = LastUpdatedOrderedDict()
                                assertion['oc_objects'] = LastUpdatedOrderedDict()
                                assertion['literals'] = []
                                unique_pred_assertions[equiv_pred_uri] = assertion
                            assertion = unique_pred_assertions[equiv_pred_uri]
                        if assertion and equiv_pred_uri:
                            # we have a LOD equvalient property
                            if not isinstance(obj_values, list):
                                obj_values = [obj_values]
                            for obj_val in obj_values:
                                literal_val = None
                                if not isinstance(obj_val, dict):
                                    # the object of the assertion is not a dict, so it must be
                                    # a literal
                                    literal_val = obj_val
                                    if obj_val not in assertion['literals']:
                                        has_literal = True
                                        assertion['literals'].append(obj_val)
                                else:
                                    if 'xsd:string' in obj_val:
                                        literal_val = obj_val['xsd:string']
                                if literal_val and literal_val not in assertion['literals']:
                                    assertion['literals'].append(literal_val)
                                if literal_val is None:
                                    # add any linked data equivalences by looking for this
                                    # type in the graph list
                                    obj_val = self.lookup_type_by_type_obj(obj_val)
                                    obj_uri = self.get_id_from_g_obj(obj_val)
                                    equiv_obj_objs = self.get_equivalent_objects(obj_val)           
                                    if len(equiv_obj_objs):
                                        # we have LD equivalents for the object value
                                        for equiv_obj_obj in equiv_obj_objs:
                                            equiv_obj_uri = self.get_id_from_g_obj(equiv_obj_obj)
                                            assertion['ld_objects'][equiv_obj_uri] = equiv_obj_obj
                                    elif obj_uri:
                                        # we don't have LD equivalents for the object value
                                        # add to the oc_objects
                                        assertion['oc_objects'][obj_uri] = obj_val
                                    unique_pred_assertions[equiv_pred_uri] = assertion
                for pred_key, assertion in unique_pred_assertions.items():                            
                    inferred_assertions.append(assertion)
        return inferred_assertions