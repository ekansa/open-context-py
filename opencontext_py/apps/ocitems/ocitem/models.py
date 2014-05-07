from django.db import models
from opencontext_py.apps.ocitems.manifest.models import Manifest as Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion as Assertion
from opencontext_py.apps.ocitems.assertions.models import Containment as Containment
from collections import OrderedDict


# OCitem is a very general class for all Open Context items.
# This class is used to make a JSON-LD output from data returned from the database via other apps
class OCitem():
    PREDICATES_DCTERMS_PUBLISHED = "dc-terms:published"
    PREDICATES_DCTERMS_CREATOR = "dc-terms:creator"
    PREDICATES_DCTERMS_CONTRIBUTOR = "dc-terms:contributor"
    PREDICATES_DCTERMS_ISPARTOF = "dc-terms:isPartOf"

    def get_item(self, actUUID):
        """
        gets data for an item
        """
        self.uuid = actUUID
        self.get_manifest()
        self.get_assertions()
        self.get_parent_context()
        self.construct_json_ld()
        return self

    def get_manifest(self):
        """
        gets basic metadata about the item from the Manifest app
        """
        self.manifest = Manifest.objects.get(uuid=self.uuid)
        self.label = self.manifest.label
        self.item_type = self.manifest.item_type
        self.published = self.manifest.published
        return self.manifest

    def get_assertions(self):
        """
        gets item descriptions and linking relations for the item from the Assertion app
        """
        self.assertions = Assertion.objects.filter(uuid=self.uuid)
        return self.assertions

    def get_parent_context(self):
        """
        gets item parent context
        """
        _act_contain = Containment()
        self.contexts = _act_contain.get_parents_by_child_uuid(self.uuid)
        return self.contexts

    def construct_json_ld(self):
        """
        creates JSON-LD documents for an item
        currently, it's just here to make some initial JSON while we learn python
        """
        json_ld = LastUpdatedOrderedDict()
        json_ld['@context'] = {"id": "@id",
                               "type": "@type"}

        # this is just temporary, just to play with list handling in Python
        # it is not part of the planned final json-ld output
        assertion_list = list()
        for assertion in self.assertions:
            prop_assertion = {'hash_id': assertion.hash_id,
                              'source_id': assertion.source_id,
                              'obs_num': assertion.obs_num}
            assertion_list.append(prop_assertion)

        json_ld['id'] = self.uuid
        json_ld['label'] = self.label
        json_ld[self.PREDICATES_DCTERMS_PUBLISHED] = self.published.date().isoformat()
        json_ld['assertions'] = assertion_list
        json_ld['parentUUID'] = self.contexts
        self.json_ld = json_ld
        return self.json_ld


class LastUpdatedOrderedDict(OrderedDict):
    """
    Stores items in the order the keys were last added'
    """
    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        OrderedDict.__setitem__(self, key, value)
