from django.db import models
from opencontext_py.apps.ocitems.manifest.models import Manifest as Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion as Assertion

# OCitem is a very general class for all Open Context items.
# This class is used to make a JSON-LD output from data returned from the database via other apps
class OCitem():
    
    # get data for an item
    def getItem(self, actUUID):
        self.uuid = actUUID
        self.getManifest()
        self.getAssertions()
        self.constructJSONld()
        return self
    
    # get basic metadata about the item from the Manifest app
    def getManifest(self):
        self.manifest = Manifest.objects.get(uuid = self.uuid)
        self.label = self.manifest.label
        self.itemType = self.manifest.itemType
        return self.manifest
    
    # get item descriptions and linking relations for the item from the Assertion app
    def getAssertions(self):
        self.assertions = Assertion.objects.filter(uuid = self.uuid)
        return self.assertions
    
    # this will be the function for creating JSON-LD documents for an item
    # currently, it's just here to make some initial JSON while we learn python
    def constructJSONld(self):
        jsonLD = {}
        jsonLD['@context'] ={"id":"@id",
        "type":"@type"}
        
        # this is just temporary, just to play with list handling in Python
        # it is not part of the planned final json-ld output
        assertionList = list()
        for assertion in self.assertions:
            propAssertion = {'hashID': assertion.hashID,
            'sourceID': assertion.sourceID,
            'obsNum': assertion.obsNum}
            assertionList.append(propAssertion)
        
        jsonLD['id'] = self.uuid
        jsonLD['label'] = self.label
        jsonLD['assertions'] =  assertionList
        self.jsonLD = jsonLD
        return self.jsonLD
        
