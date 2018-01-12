import time
import json
from collections import OrderedDict
from django.conf import settings
from django.db import models
from django.db.models import Q
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.languages import Languages
from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.ocitem.caching import ItemGenerationCache
from opencontext_py.apps.ocitems.ocitem.partsjsonld import PartsJsonLD
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.authorship import Authorship
from opencontext_py.apps.ldata.linkannotations.licensing import Licensing


# OCitem is a very general class for all Open Context items.
# This class is used to make a JSON-LD output from data returned from the database via other apps
class ItemAttributes():
    
    PREDICATES_DCTERMS_PUBLISHED = 'dc-terms:issued'
    PREDICATES_DCTERMS_MODIFIED = 'dc-terms:modified'
    PREDICATES_DCTERMS_CREATOR = 'dc-terms:creator'
    PREDICATES_DCTERMS_CONTRIBUTOR = 'dc-terms:contributor'
    PREDICATES_DCTERMS_ISPARTOF = 'dc-terms:isPartOf'
    PREDICATES_DCTERMS_TITLE = 'dc-terms:title'
    PREDICATES_OCGEN_PREDICATETYPE = 'oc-gen:predType'
    PREDICATES_OCGEN_HASOBS = 'oc-gen:has-obs'
    PREDICATES_OCGEN_SOURCEID = 'oc-gen:sourceID'
    PREDICATES_OCGEN_OBSTATUS = 'oc-gen:obsStatus'
    PREDICATES_OCGEN_OBSLABEL = 'label'
    PREDICATES_OCGEN_OBSNOTE = 'oc-gen:obsNote'
    PREDICATES_FOAF_PRIMARYTOPICOF = 'foaf:isPrimaryTopicOf'
    
    # predicates not for use in observations
    NO_OBS_ASSERTION_PREDS = [
        'skos:note'
    ]
    
    NUMERIC_OBJECT_TYPES = [
        'xsd:integer',
        'xsd:double',
        'xsd:boolean'
    ]

    def __init__(self):
        self.proj_context_json_ld = None
        self.project_uuid = None
        self.manifest = None
        self.assertion_hashes = False
        self.assertions = None
        self.link_annotations = None
        self.stable_ids = None
        self.obs_list = []
        self.string_obj_dict = {}  # OCstring objects, in a dict, with uuid as key
        self.manifest_obj_dict = {}  # manifest objects, in a dict with uuid as key
        dc_terms_obj = DCterms()
        self.DC_META_PREDS = dc_terms_obj.get_dc_terms_list()
        self.item_gen_cache = ItemGenerationCache()
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.class_uri_list = []  # uris of item classes used in this item

    def get_db_item_attributes(self):
        """ gets item attributes (other than context, space, temporal) that describe
            an item
        """
        self.get_db_assertions()
        self.get_db_link_anotations()
        self.get_db_stable_ids()

    def add_json_ld_attributes(self, json_ld):
        """ adds attribute information to the JSON-LD """
        json_ld = self.add_json_ld_descriptive_assertions(json_ld)
        json_ld = self.add_json_ld_stable_ids(json_ld)
        json_ld = self.add_json_ld_link_annotations(json_ld)
        return json_ld

    def add_json_ld_descriptive_assertions(self, json_ld):
        """
        adds descriptive assertions (descriptive properties, non spatial containment links)
        to items, as parts of Observations
        """
        observations = []
        working_obs = LastUpdatedOrderedDict()
        act_obs = LastUpdatedOrderedDict()
        for assertion in self.assertions:
            act_obs_num = assertion.obs_num
            if assertion.predicate_uuid in self.NO_OBS_ASSERTION_PREDS:
                # we've got a predicate that does not belong in an observation
                json_ld = self.add_json_ld_direct_assertion(json_ld,
                                                            assertion)
            else:    
                if act_obs_num not in working_obs:
                    # we've got a new observation, so make a new observation object for it
                    act_obs = self.make_json_ld_obs_dict_w_metadata(assertion)
                    working_obs[act_obs_num] = act_obs
                else:
                    act_obs = working_obs[act_obs_num]
                act_obs = self.add_json_ld_assertion_predicate_objects(act_obs,
                                                                       assertion)
                working_obs[act_obs_num] = act_obs
        # now that we've gotten observations made,
        # add them to the final list of observations
        for obs_num in self.obs_list:
            if obs_num in working_obs:
                act_obs = working_obs[obs_num]
                observations.append(act_obs)
        if len(observations) > 0:
            json_ld[self.PREDICATES_OCGEN_HASOBS] = observations
        return json_ld
    
    def add_json_ld_assertion_predicate_objects(self,
                                                act_obs,
                                                assertion):
        """ adds value objects to for an assertion predicate """
        # we've already looked up objects from the manifest
        parts_json_ld = PartsJsonLD()
        parts_json_ld.proj_context_json_ld = self.proj_context_json_ld
        parts_json_ld.manifest_obj_dict = self.manifest_obj_dict
        pred_slug_uri = parts_json_ld.get_json_ld_predicate_slug_uri(assertion.predicate_uuid)
        if isinstance(pred_slug_uri, str):
            if pred_slug_uri in act_obs:
                act_obj_list = act_obs[pred_slug_uri]
            else:
                act_obj_list = []
            act_obj = None
            add_literal_object = True
            if assertion.object_type == 'xsd:string':
                # look for the string uuid in the dict of string objects we already
                # got from the database
                if assertion.object_uuid in self.string_obj_dict:
                    act_obj = LastUpdatedOrderedDict()
                    act_obj['id'] = '#string-' + str(assertion.object_uuid)
                    string_obj = self.string_obj_dict[assertion.object_uuid]
                    lang_obj = Languages()
                    act_obj['xsd:string'] = lang_obj.make_json_ld_value_obj(string_obj.content,
                                                                            string_obj.localized_json)
                else:
                    act_obj = 'string content missing'
            elif assertion.object_type == 'xsd:date':
                act_obj = assertion.data_date.date().isoformat()
            elif assertion.object_type == 'xsd:integer':
                try:
                    act_obj = int(float(assertion.data_num))
                except:
                    act_obj = None
            elif assertion.object_type in self.NUMERIC_OBJECT_TYPES:
                act_obj = assertion.data_num
            else:
                # the object of is something identified by a URI, not a literal
                # so we're using function in the parts_json_ld to add the uri identified
                # object as a dict that has some useful information
                # {id, label, slug, sometimes class}
                add_literal_object = False
                if self.assertion_hashes:
                    # we need to add the assertion hash identifier so as to be able
                    # to identify assertions for editing purposes
                    act_obs = parts_json_ld.addto_predicate_list(act_obs,
                                                                 pred_slug_uri,
                                                                 assertion.object_uuid,
                                                                 assertion.object_type,
                                                                 False,
                                                                 assertion.hash_id)
                else:
                    # normal default assertion creation, without identification of
                    # the assertion's hash ID
                    act_obs = parts_json_ld.addto_predicate_list(act_obs,
                                                                 pred_slug_uri,
                                                                 assertion.object_uuid,
                                                                 assertion.object_type)
            if act_obj is not None and add_literal_object:
                if self.assertion_hashes:
                    # we need to add the assertion hash identifier so as to be able
                    # to identify assertions for editing purposes
                    if not isinstance(act_obj, dict):
                        literal = act_obj
                        act_obj = LastUpdatedOrderedDict()
                        act_obj['literal'] = literal
                    act_obj['hash_id'] = assertion.hash_id
                act_obj_list.append(act_obj)
            if len(act_obj_list) > 0 and add_literal_object:
                # only add a list of literal objects if they are literal objects :)
                act_obs[pred_slug_uri] = act_obj_list
        return act_obs

    def add_json_ld_direct_assertion(self, json_ld, assertion):
        """ adds an JSON-LD for an assertion that is made directly
            to the item, and is not part of an observation
        """
        if assertion.predicate_uuid in self.NO_OBS_ASSERTION_PREDS:
            # these predicates describe the item, but not in an observation
            act_obj = None
            if assertion.object_type == 'xsd:string':
                # look for the string uuid in the dict of string objects we already
                # got from the database
                if assertion.object_uuid in self.string_obj_dict:
                    string_obj = self.string_obj_dict[assertion.object_uuid]
                    lang_obj = Languages()
                    act_obj = lang_obj.make_json_ld_value_obj(string_obj.content,
                                                              string_obj.localized_json)
                else:
                    act_obj = 'string content missing'
            elif assertion.object_type == 'xsd:date':
                act_obj = assertion.data_date.date().isoformat()
            elif assertion.object_type == 'xsd:integer':
                try:
                    act_obj = int(float(assertion.data_num))
                except:
                    act_obj = None
            elif assertion.object_type in self.NUMERIC_OBJECT_TYPES:
                act_obj = assertion.data_num
            else:
                # the object of is something identified by a URI, not a literal
                ent = parts_json_ld.get_new_object_item_entity(
                        assertion.object_uuid,
                        assertion.object_type
                        )
                if ent is not False:
                    act_obj = entity.uri
            if act_obj is not None:
                json_ld[assertion.predicate_uuid] = act_obj
        return json_ld
    
    def make_json_ld_obs_dict_w_metadata(self, assertion):
        """ makes metadata for an observation """
        act_obs = LastUpdatedOrderedDict()
        act_obs['id'] = "#obs-" + str(assertion.obs_num)
        if isinstance(assertion.obs_node, str):
            if len(assertion.obs_node) > 1:
                if assertion.obs_node[:1] == '#':
                    act_obs['id'] = str(assertion.obs_node)
        act_obs[self.PREDICATES_OCGEN_SOURCEID] = assertion.source_id
        if assertion.obs_num >= 0 and assertion.obs_num != 100:
            act_obs[self.PREDICATES_OCGEN_OBSTATUS] = 'active'
        else:
            act_obs[self.PREDICATES_OCGEN_OBSTATUS] = 'deprecated'
        # now go get observation meta
        obs_meta = self.item_gen_cache.get_observation_metadata(assertion.source_id,
                                                                assertion.obs_num)
        if obs_meta is not False:
            act_obs[self.PREDICATES_OCGEN_OBSLABEL] = obs_meta.label
            if isinstance(obs_meta.note, str):
                if len(obs_meta.note) > 0:
                    act_obs[self.PREDICATES_OCGEN_OBSNOTE] = obs_meta.note
        act_obs['type'] = 'oc-gen:observations'
        return act_obs
    
    def add_json_ld_stable_ids(self, json_ld):
        """
        adds stable identifier information to an item's JSON-LD dictionary object
        """
        if self.stable_ids is not False:
            if len(self.stable_ids) > 0:
                stable_id_list = []
                for stable_id in self.stable_ids:
                    if stable_id.stable_type in settings.STABLE_ID_URI_PREFIXES:
                        uri = settings.STABLE_ID_URI_PREFIXES[stable_id.stable_type]
                        uri += str(stable_id.stable_id)
                        id_dict = {'id': uri}
                        stable_id_list.append(id_dict)
                if self.manifest.item_type == 'persons' and len(stable_id_list) > 0:
                    # persons with ORCID ids use the foaf:primarytopic predicate to link to ORCID
                    primary_topic_list = []
                    same_as_list = []
                    for id_dict in stable_id_list:
                        if 'http://orcid.org' in id_dict['id']:
                            primary_topic_list.append(id_dict)
                        else:
                            same_as_list.append(id_dict)
                    stable_id_list = same_as_list  # other types of identifiers use as owl:sameAs
                    if len(primary_topic_list) > 0:
                        json_ld[self.PREDICATES_FOAF_PRIMARYTOPICOF] = primary_topic_list
                if len(stable_id_list) > 0:
                    json_ld['owl:sameAs'] = stable_id_list
        return json_ld

    def add_json_ld_link_annotations(self, json_ld):
        """
        adds linked data annotations (typically referencing URIs from
        outside Open Context)
        """
        if self.link_annotations is not False:
            if len(self.link_annotations) > 0:
                parts_json_ld = PartsJsonLD()
                parts_json_ld.proj_context_json_ld = self.proj_context_json_ld
                parts_json_ld.manifest_obj_dict = self.manifest_obj_dict
                for la in self.link_annotations:
                    tcheck = URImanagement.get_uuid_from_oc_uri(la.object_uri, True)
                    if tcheck is False:
                        # this item is NOT from open context
                        item_type = False
                    else:
                        # an Open Context item
                        item_type = tcheck['item_type']
                    act_pred = URImanagement.prefix_common_uri(la.predicate_uri)
                    json_ld = parts_json_ld.addto_predicate_list(json_ld,
                                                                 act_pred,
                                                                 la.object_uri,
                                                                 item_type)
        return json_ld
    
    
    def get_db_assertions(self):
        """ gets assertions that describe an item, except for assertions about spatial containment """
        self.assertions = Assertion.objects.filter(uuid=self.manifest.uuid) \
                                           .exclude(predicate_uuid=Assertion.PREDICATES_CONTAINS)\
                                           .exclude(visibility__lt=1)\
                                           .order_by('obs_num', 'sort')
        # now that we have some assertions, go prepare
        # lists of observations, and get objects of assertions into memory
        self.prep_assertions_lists_and_objects()
    
    def prep_assertions_lists_and_objects(self):
        """ prepares lists and objects from assertions. this is needed
            to organize assertions into observations and get needed
            assertion objects into memory
        """
        string_uuids = []
        manifest_obj_uuids = []
        if self.assertions is not False:
            if len(self.assertions) > 0:
                for ass in self.assertions:
                    if ass.obs_num not in self.obs_list:
                        self.obs_list.append(ass.obs_num)
                    if ass.object_type == 'xsd:string':
                        if ass.object_uuid not in string_uuids:
                            string_uuids.append(ass.object_uuid)
                    elif ass.object_type in PartsJsonLD.ITEM_TYPE_MANIFEST_LIST:
                        if ass.object_uuid not in manifest_obj_uuids:
                            manifest_obj_uuids.append(ass.object_uuid)
        # now get the string objects that are the objects of some assertions                    
        self.get_db_string_objs(string_uuids)
        # now get manifest objects for objects of assertions
        self.get_db_related_manifest_objs(manifest_obj_uuids)
    
    def get_db_string_objs(self, string_uuids):
        """ gets strings associated with assertions. does it in 1 query to reduce time """
        if len(string_uuids) > 0:
            # we have assertions that reference strings, so now go and
            # retrieve all of these strings
            act_strings = OCstring.objects.filter(uuid__in=string_uuids)
            for act_string in act_strings:
                uuid = act_string.uuid
                self.string_obj_dict[uuid] = act_string
    
    def get_db_related_manifest_objs(self, manifest_obj_uuids):
        """ gets uuids of manifest objects associated with assertions.
            We prepare this list to reduce the number of database queries.
            Only some assertion object_types are OK
            (specified in the PartsJsonLD.ITEM_TYPE_MANIFEST_LIST), because
            other types of items need more queries than a simple manifest lookup.
        """
        if len(manifest_obj_uuids) > 0:
            parts_json_ld = PartsJsonLD()
            # get manifest objects items to use later in making JSON_LD
            parts_json_ld.get_manifest_objects_from_uuids(manifest_obj_uuids)
            self.manifest_obj_dict = parts_json_ld.manifest_obj_dict
    
    def get_db_link_anotations(self):
        """ gets linked data (using standard vocabularies, ontologies) assertions
            that describe an item
        """
        self.link_annotations = LinkAnnotation.objects\
                                              .filter(subject=self.manifest.uuid)\
                                              .order_by('predicate_uri', 'sort')
    
    def get_db_stable_ids(self):
        """ gets stable identifiers (DOIs, ARKs, ORCIDS) """
        self.stable_ids = StableIdentifer.objects.filter(uuid=self.manifest.uuid)
    
    