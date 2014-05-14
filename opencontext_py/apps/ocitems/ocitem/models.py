from django.conf import settings
from django.db import models
from opencontext_py.apps.ocitems.manifest.models import Manifest as Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion as Assertion
from opencontext_py.apps.ocitems.assertions.models import Containment as Containment
from collections import OrderedDict


# OCitem is a very general class for all Open Context items.
# This class is used to make a JSON-LD output from data returned from the database via other apps
class OCitem():
    PREDICATES_DCTERMS_PUBLISHED = 'dc-terms:published'
    PREDICATES_DCTERMS_CREATOR = 'dc-terms:creator'
    PREDICATES_DCTERMS_CONTRIBUTOR = 'dc-terms:contributor'
    PREDICATES_DCTERMS_ISPARTOF = 'dc-terms:isPartOf'
    PREDICATES_OCGEN_HASCONTEXTPATH = 'oc-gen:has-context-path'
    PREDICATES_OCGEN_HASPATHITEMS = 'oc-gen:has-path-items'
    PREDICATES_OCGEN_HASCONTENTS = 'oc-gen:has-contents'
    PREDICATES_OCGEN_CONTAINS = 'oc-gen:contains'

    def get_item(self, actUUID):
        """
        gets data for an item
        """
        self.uuid = actUUID
        self.get_manifest()
        self.get_assertions()
        self.get_parent_contexts()
        self.get_contained()
        self.construct_json_ld()
        return self

    def get_manifest(self):
        """
        gets basic metadata about the item from the Manifest app
        """
        self.manifest = Manifest.objects.get(uuid=self.uuid)
        self.slug = self.manifest.slug
        self.label = self.manifest.label
        self.project_uuid = self.manifest.project_uuid
        self.item_type = self.manifest.item_type
        self.published = self.manifest.published
        return self.manifest

    def get_assertions(self):
        """
        gets item descriptions and linking relations for the item from the Assertion app
        """
        act_contain = Containment()
        self.assertions = Assertion.objects.filter(uuid=self.uuid) \
                                           .exclude(predicate_uuid=act_contain.PREDICATE_CONTAINS)
        return self.assertions

    def get_parent_contexts(self):
        """
        gets item parent context
        """
        act_contain = Containment()
        r_contexts = act_contain.get_parents_by_child_uuid(self.uuid)
        # now reverse the list of contexts, so top most context is first, followed by children contexts
        self.contexts = r_contexts[::-1]
        return self.contexts

    def get_contained(self):
        """
        gets item containment children
        """
        act_contain = Containment()
        self.children = act_contain.get_children_by_parent_uuid(self.uuid)

    def construct_json_ld(self):
        """
        creates JSON-LD documents for an item
        currently, it's just here to make some initial JSON while we learn python
        """
        item_con = ItemConstruction()
        json_ld = item_con.intialize_json_ld()

        # this is just temporary, just to play with list handling in Python
        # it is not part of the planned final json-ld output
        assertion_list = list()
        for assertion in self.assertions:
            prop_assertion = {'hash_id': assertion.hash_id,
                              'source_id': assertion.source_id,
                              'obs_num': assertion.obs_num}
            assertion_list.append(prop_assertion)

        json_ld['id'] = item_con.make_oc_uri(self.uuid, self.item_type)
        json_ld['label'] = self.label
        json_ld[self.PREDICATES_DCTERMS_PUBLISHED] = self.published.date().isoformat()
        json_ld['assertions'] = assertion_list
        if(len(self.contexts) > 0):
            act_context = LastUpdatedOrderedDict()
            for parent_uuid in self.contexts:
                act_context = item_con.add_json_predicate_list_ocitem(act_context,
                                                                      self.PREDICATES_OCGEN_HASPATHITEMS,
                                                                      parent_uuid, 'subjects')
            json_ld[self.PREDICATES_OCGEN_HASCONTEXTPATH] = act_context
        if(len(self.children) > 0):
            act_children = LastUpdatedOrderedDict()
            for child_uuid in self.children:
                act_children = item_con.add_json_predicate_list_ocitem(act_children,
                                                                       self.PREDICATES_OCGEN_CONTAINS,
                                                                       child_uuid, 'subjects')
            json_ld[self.PREDICATES_OCGEN_HASCONTENTS] = act_children
        json_ld = item_con.add_json_predicate_list_ocitem(json_ld,
                                                          self.PREDICATES_DCTERMS_ISPARTOF,
                                                          self.project_uuid, 'projects')
        item_con.add_item_labels = False
        json_ld = item_con.add_json_predicate_list_ocitem(json_ld,
                                                          'owl:sameAs',
                                                          self.slug, self.item_type)
        self.json_ld = json_ld
        return self.json_ld


class LastUpdatedOrderedDict(OrderedDict):
    """
    Stores items in the order the keys were last added
    """
    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        OrderedDict.__setitem__(self, key, value)


class ItemConstruction():
    """
    General purpose functions for building Open Context items
    """
    add_item_labels = True
    add_media_thumnails = True
    add_subject_class = True
    cannonical_uris = True

    def __init__(self):
        add_item_labels = True
        add_media_thumnails = True
        add_subject_class = True
        cannonical_uris = True

    def intialize_json_ld(self):
        """
        creates a json_ld (ordered) dictionary with a context
        """
        json_ld = LastUpdatedOrderedDict()
        json_ld['@context'] = {"id": "@id",
                               "type": "@type",
                               "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                               "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                               "label": "rdfs:label",
                               "xsd": "http://www.w3.org/2001/XMLSchema#",
                               "skos": "http://www.w3.org/2004/02/skos/core#",
                               "owl": "http://www.w3.org/2002/07/owl#",
                               "dc-terms": "http://purl.org/dc/terms/",
                               "uuid": "dc-terms:identifier",
                               "bibo": "http://purl.org/ontology/bibo/",
                               "foaf": "http://xmlns.com/foaf/0.1/",
                               "cidoc-crm": "http://www.cidoc-crm.org/cidoc-crm/",
                               "oc-gen": "http://opencontext.org/vocabularies/oc-general/"
                               }
        return json_ld

    def add_descriptive_assertions(self, act_dict, assertions):
        """
        adds descriptive assertions (descriptive properties, non spatial containment links)
        to items
        """
        variable_list = list()
        link_list = list()
        for assertion in self.assertions:
            prop_assertion = {'hash_id': assertion.hash_id,
                              'source_id': assertion.source_id,
                              'obs_num': assertion.obs_num}
            assertion_list.append(prop_assertion)
        return act_dict

    def add_json_predicate_list_ocitem(self, act_dict, act_pred_key, uuid, item_type):
        """
        creates a list for an act_predicate of the json_ld dictionary object if it doesn't exist
        adds a list item of a dictionary object for a linked Open Context item
        """
        if act_pred_key in act_dict:
            act_list = act_dict[act_pred_key]
        else:
            act_list = []
        new_object_item = LastUpdatedOrderedDict()
        new_object_item['id'] = self.make_oc_uri(uuid, item_type)
        if self.add_item_labels:
            manifest_item = self.get_item_metadata(uuid)
            if(manifest_item is not False):
                new_object_item['label'] = manifest_item.label
            else:
                new_object_item['label'] = 'item not in manifest'
        act_list.append(new_object_item)
        act_dict[act_pred_key] = act_list
        return act_dict

    def make_oc_uri(self, uuid, item_type):
        """
        creates a URI for an item based on its uuid and its item_type
        """
        uri = False
        uuid = str(uuid)
        item_type = str(item_type)
        if(self.cannonical_uris):
            uri = settings.CANONICAL_HOST + "/" + item_type + "/" + uuid
        else:
            uri = "http://" + settings.HOSTNAME + "/" + item_type + "/" + uuid
        return uri

    def get_item_metadata(self, uuid):
        """
        gets metadata about an item from the manifest table
        """
        try:
            manifest_item = Manifest.objects.get(uuid=uuid)
            return manifest_item
        except Manifest.DoesNotExist:
            return False
