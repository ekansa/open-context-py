import logging
from django.conf import settings
from django.core.cache import caches
from opencontext_py.libs.languages import Languages
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.ocitem.biotaxa import biological_taxonomy_validation
from opencontext_py.apps.ocitems.ocitem.itemkeys import ItemKeys
from opencontext_py.apps.ocitems.ocitem.caching import ItemGenerationCache

"""
Testing:

from opencontext_py.apps.ocitems.ocitem.generation import OCitem
from opencontext_py.apps.contexts.readprojectcontext import ReadProjectContextVocabGraph

uuid = '9095FCBB-35A8-452E-64A3-B8D52A0B2DB3'
oc_item = OCitem()
oc_item.check_exists(uuid)
oc_item.generate_json_ld()
rpg = ReadProjectContextVocabGraph(oc_item.proj_context_json_ld)
ia = rpg.infer_assertions_for_item_json_ld(oc_item.json_ld)

"""

logger = logging.getLogger("tests-regression-logger")


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
         'slug': 'oc-gen-has-note',
         '@type': 'xsd:string'},
    ]
    
    # predicates used for equivalence, used to make
    # inferred assertions
    REL_PREDICATES_FOR_INFERRENCE = [
        'skos:closeMatch',
        'skos:exactMatch'
    ]
    REL_MEASUREMENTS = [
        'cidoc-crm:P67_refers_to',
        'oc-gen:has-technique',
        'rdfs:range'
    ]
    ITEM_REL_PREDICATES = [
        'skos:closeMatch',
        'skos:exactMatch',
        'owl:sameAs',
        'skos:related',
        'skos:broader',
        'dc-terms:references',
        'dc-terms:hasVersion',
        'http://nomisma.org/ontology#hasTypeSeriesItem'
    ]
    
    # Skip the following predicate keys when looking
    # for inferred linked data assertions in an observation.
    LINKDATA_OBS_PREDS_SKIP = [
        'id',
        'type',
        ItemKeys.PREDICATES_OCGEN_SOURCEID,
        ItemKeys.PREDICATES_OCGEN_OBSTATUS,
        ItemKeys.PREDICATES_OCGEN_OBSLABEL,
        ItemKeys.PREDICATES_OCGEN_OBSNOTE,
    ]
    
    def __init__(self, proj_context_json_ld=None):
        self.m_cache = MemoryCache()
        self.context = None
        self.graph = None
        self.fail_on_missing_entities = False
        if not isinstance(proj_context_json_ld, dict):
            return None
        if '@context' in proj_context_json_ld:
            self.context = proj_context_json_ld['@context']
        if '@graph' in proj_context_json_ld:
            self.graph = self.GLOBAL_VOCAB_GRAPH + proj_context_json_ld['@graph']
        else:
            self.graph = self.GLOBAL_VOCAB_GRAPH
        logger.info('Read project graph size: {}'.format(len(self.graph)))
    
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
        type_ids = self.get_id_list_for_g_obj(type_obj)
        for type_id in type_ids:
            found_type_obj = self.lookup_type(type_id)
            if isinstance(found_type_obj, dict):
                return found_type_obj
        return type_obj
    
    def lookup_oc_descriptor(self, id, item_type):
        """looks up a predicate, or a type by an identifier
           (slud id, uri, slug, or uuid)
        """
        cache_key = self.m_cache.make_cache_key(
            'lookup_oc_descriptor_{}'.format(item_type),
            id
        )
        output = self.m_cache.get_cache_object(cache_key)
        if (output is None
            and isinstance(self.graph, list)
            and isinstance(id, str)
        ):
            for g_obj in self.graph:
                id_list = self.get_id_list_for_g_obj(g_obj)
                if not id in id_list:
                    continue
                output = g_obj
                if item_type == 'predicates' and '@type' not in g_obj:
                    output['@type'] = self.get_predicate_datatype_for_graph_obj(g_obj)
                    break
            if output:
                self.m_cache.save_cache_object(cache_key, output)
        if self.fail_on_missing_entities and not output:
            raise RuntimeError('Cannot find {}, item_type: {}'.format(id, item_type))
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
                if not id_key in g_obj:
                    continue
                if g_obj[id_key] not in id_list:
                    id_list.append(g_obj[id_key])
        return id_list
    
    def get_id_from_g_obj(self, g_obj):
        """ gets the id form a g_obj, either the @id or id varient """
        id_variants = ['@id', 'id']
        id  = None
        if not isinstance(g_obj, dict):
            return None
        for id_variant in id_variants:
            if id_variant not in g_obj:
                continue
            id = g_obj[id_variant]
        return id
        
    def get_predicate_datatype_by_slug_uri(self, slug_uri):
        """Looks up a predicate's datatype via the predicate slug URI."""
        datatype = 'xsd:string'  # Default to treating all as a string
        if (isinstance(self.context, dict) and
            isinstance(slug_uri, str)):
            if not slug_uri in self.context:
                return datatype
            for type_variant in ['@type', 'type']:
                if type_variant not in self.context[slug_uri]:
                    continue
                datatype = self.context[slug_uri][type_variant]
        return datatype

    def get_equivalent_objects(self, info_dict):
        """ Gets equivalent linked data dicts associated with an
            info_dict.
        """
        equiv_uris = []
        equiv_objects = []
        for rel_pred in self.REL_PREDICATES_FOR_INFERRENCE:
            if not rel_pred in info_dict:
                continue
            for equiv_obj in info_dict[rel_pred]:
                equiv_uri = self.get_id_from_g_obj(equiv_obj)
                if equiv_uri and equiv_uri not in equiv_uris:
                    # Make sure that the equivalent URIs are unique.
                    equiv_uris.append(equiv_uri)
                    equiv_objects.append(equiv_obj)
        return equiv_objects

    def infer_assertions_for_item_json_ld(self, json_ld):
        """Makes a list of inferred assertions from item json ld """
        lang_obj = Languages()
        inferred_assertions = []
        if not isinstance(json_ld, dict):
            return inferred_assertions
        if not ItemKeys.PREDICATES_OCGEN_HASOBS in json_ld:
            return inferred_assertions
        unique_pred_assertions = LastUpdatedOrderedDict()
        for obs_dict in json_ld[ItemKeys.PREDICATES_OCGEN_HASOBS]:
            # Get the status of the observation, defaulting to 'active'. If
            # active, then it's OK to infer assertions, otherwise skip the
            # observation.
            obs_status = obs_dict.get(ItemKeys.PREDICATES_OCGEN_OBSTATUS, 'active')
            if obs_status != 'active':
                # Skip this observation. It's there but has a deprecated
                # status.
                continue
            for obs_pred_key, obj_values in obs_dict.items():
                if obs_pred_key in self.LINKDATA_OBS_PREDS_SKIP:
                    # Skip this obs_pred_key, it is a general
                    # description of the observation, and will
                    # not have any linked assertions to infer.
                    continue
                obs_pred_info = self.lookup_predicate(obs_pred_key)
                pred_data_type = self.get_predicate_datatype_for_graph_obj(obs_pred_info)
                if not obs_pred_info:
                    continue
                equiv_pred_objs = self.get_equivalent_objects(obs_pred_info)
                if not equiv_pred_objs:
                    # No linked data equivalence for the obs_pred_key
                    # so continue, skipping the rest.
                    continue
                # Start with a None assertion.
                assertion = None
                # Iterate through all the equivalent predicate objects.
                for equiv_pred_obj in equiv_pred_objs:
                    equiv_pred_uri = self.get_id_from_g_obj(equiv_pred_obj)
                    # Inferred assertions will have unique LOD predicates, with
                    # one or more values. The unique_pred_assertions dict makes
                    # sure the LOD predicates are used only once.
                    if not equiv_pred_uri in unique_pred_assertions:
                        assertion = equiv_pred_obj
                        assertion['type'] = pred_data_type
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
                                    assertion['literals'].append(obj_val)
                            elif 'xsd:string' in obj_val:
                                literal_val = lang_obj.get_all_value_str(obj_val['xsd:string'])
                            if literal_val and literal_val not in assertion['literals']:
                                assertion['literals'].append(literal_val)
                            if literal_val is None:
                                # Add any linked data equivalences by looking for this
                                # type in the graph list
                                obj_val = self.lookup_type_by_type_obj(obj_val)
                                obj_uri = self.get_id_from_g_obj(obj_val)
                                equiv_obj_objs = self.get_equivalent_objects(obj_val)           
                                if len(equiv_obj_objs):
                                    # We have LD equivalents for the object value
                                    for equiv_obj_obj in equiv_obj_objs:
                                        equiv_obj_uri = self.get_id_from_g_obj(equiv_obj_obj)
                                        if not biological_taxonomy_validation(
                                            equiv_pred_uri, equiv_obj_uri):
                                            # This object_uri does not belong to this
                                            # predicated uri.
                                            continue
                                        assertion['ld_objects'][equiv_obj_uri] = equiv_obj_obj
                                elif obj_uri:
                                    # We don't have LD equivalents for the object value
                                    # add to the oc_objects
                                    assertion['oc_objects'][obj_uri] = obj_val
                                unique_pred_assertions[equiv_pred_uri] = assertion
        for pred_key, assertion in unique_pred_assertions.items():                            
            inferred_assertions.append(assertion)
        return inferred_assertions