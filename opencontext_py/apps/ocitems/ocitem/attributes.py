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
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.authorship import Authorship
from opencontext_py.apps.ldata.linkannotations.licensing import Licensing


# OCitem is a very general class for all Open Context items.
# This class is used to make a JSON-LD output from data returned from the database via other apps
class OCitemAttributes():
    PREDICATES_DCTERMS_PUBLISHED = 'dc-terms:issued'
    PREDICATES_DCTERMS_MODIFIED = 'dc-terms:modified'
    PREDICATES_DCTERMS_CREATOR = 'dc-terms:creator'
    PREDICATES_DCTERMS_CONTRIBUTOR = 'dc-terms:contributor'
    PREDICATES_DCTERMS_ISPARTOF = 'dc-terms:isPartOf'
    PREDICATES_DCTERMS_TITLE = 'dc-terms:title'
    PREDICATES_OCGEN_PREDICATETYPE = 'oc-gen:predType'
    PREDICATES_OCGEN_HASCONTEXTPATH = 'oc-gen:has-context-path'
    PREDICATES_OCGEN_HASLINKEDCONTEXTPATH = 'oc-gen:has-linked-context-path'
    PREDICATES_OCGEN_HASPATHITEMS = 'oc-gen:has-path-items'
    PREDICATES_OCGEN_HASCONTENTS = 'oc-gen:has-contents'
    PREDICATES_OCGEN_CONTAINS = 'oc-gen:contains'
    PREDICATES_OCGEN_HASOBS = 'oc-gen:has-obs'
    PREDICATES_OCGEN_SOURCEID = 'oc-gen:sourceID'
    PREDICATES_OCGEN_OBSTATUS = 'oc-gen:obsStatus'
    PREDICATES_OCGEN_OBSLABEL = 'label'
    PREDICATES_OCGEN_OBSNOTE = 'oc-gen:obsNote'
    PREDICATES_FOAF_PRIMARYTOPICOF = 'foaf:isPrimaryTopicOf'

    def __init__(self):
        self.project_uuid = None
        self.manifest = None
        dc_terms_obj = DCterms()
        self.DC_META_PREDS = dc_terms_obj.get_dc_terms_list()
        self.item_gen_cache = ItemGenerationCache()
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.geo_meta = False
        self.temporal_meta = False
        self.event_meta = False
        self.class_uri_list = []  # uris of item classes used in this item
        self.parent_context_list = []  # list of parent context labels, used for making a dc-terms:Title
    
    def get_spatial_temporal_context(self):
        """ gets the item spatial context """
        act_contain = Containment()
        if self.manifest.item_type == 'subjects':
            # get item geospatial and chronological metadata if subject item
            # will do it differently if not a subject item
            parents = act_contain.get_parents_by_child_uuid(self.manifest.uuid)
            self.contexts = parents
            # prepare a list of contexts (including the current item) to check for
            # geospatial and event / chronology metadata
            subject_list = act_contain.contexts_list
            subject_list.insert(0, self.manifest.uuid)
            self.geo_meta = act_contain.get_geochron_from_subject_list(subject_list, 'geo')
            self.temporal_meta = act_contain.get_geochron_from_subject_list(subject_list, 'temporal')
            self.event_meta = act_contain.get_geochron_from_subject_list(subject_list, 'event')
        else:
            parents = act_contain.get_related_context(self.manifest.uuid)
            self.linked_contexts = parents
            if self.manifest.item_type == 'projects':
                # get project metadata objects directly
                pm = ProjectMeta()
                self.geo_meta = pm.get_project_geo_from_db(self.uuid)
            act_contain = Containment()
            if self.geo_meta is False:
                self.geo_meta = act_contain.get_related_geochron(self.uuid,
                                                                 self.item_type,
                                                                 'geo')
            if self.temporal_meta is False:
                self.temporal_meta = act_contain.get_related_geochron(self.uuid,
                                                                      self.item_type,
                                                                      'temporal')
                if self.temporal_meta is False:
                    # now look in the project for temporal metadata
                    self.temporal_meta = act_contain.get_temporal_from_project(self.project_uuid)
            if self.event_meta is False:
                self.event_meta = act_contain.get_related_geochron(self.uuid,
                                                                   self.item_type,
                                                                   'event')
    def add_json_ld_contexts(self, json_ld):
        """ adds context information if present """
        if isinstance(self.contexts, dict):
            if len(self.contexts) > 0:
                # add spatial context, direct parents of a given subject item
                json_ld = self.add_spatial_contexts(json_ld,
                                                    self.PREDICATES_OCGEN_HASCONTEXTPATH,
                                                    self.contexts)
        elif isinstance(self.linked_contexts, dict):
            if len(self.linked_contexts) > 0:
                # add related spatial contexts (related to a linked subject)
                json_ld = self.add_spatial_contexts(json_ld,
                                                    self.PREDICATES_OCGEN_HASLINKEDCONTEXTPATH,
                                                    self.linked_contexts)
        return json_ld
    
    def add_spatial_contexts(self, json_ld, act_pred_key, raw_contexts):
        """ adds context information, if present """
        #adds parent contents, with different treenodes
        first_node = True
        act_context = LastUpdatedOrderedDict()
        for tree_node, r_parents in raw_contexts.items():
            act_context = LastUpdatedOrderedDict()
            # change the parent node to context not contents
            tree_node = tree_node.replace('contents', 'context')
            act_context['id'] = tree_node
            act_context['type'] = 'oc-gen:contexts'
            # now reverse the list of parent contexts, so top most parent context is first,
            # followed by children contexts
            parents = r_parents[::-1]
            for parent_uuid in parents:
                parts_json_ld = PartsJsonLD()
                parts_json_ld.class_uri_list += self.class_uri_list
                act_context = parts_json_ld.addto_predicate_list(act_context,
                                                                 self.PREDICATES_OCGEN_HASPATHITEMS,
                                                                 parent_uuid,
                                                                 'subjects')
                self.class_uri_list += parts_json_ld.class_uri_list
            json_ld[act_pred_key] = act_context
            if first_node:
                # set aside a list of parent labels to use for making a dc-term:title
                first_node = False
                if self.PREDICATES_OCGEN_HASPATHITEMS in act_context:
                    for parent_obj in act_context[self.PREDICATES_OCGEN_HASPATHITEMS]:
                        self.parent_context_list.append(parent_obj['label'])
        return json_ld