from django.db import models
from opencontext_py.apps.itemapps.manifest.models import Manifest as Manifest
from opencontext_py.apps.itemapps.assertions.models import Assertion as Assertion

# OCitem is a very general class for all Open Context items.
# This class is used to make a JSON-LD output from data returned from the database via other apps
class OCitem():
    def getItem(self, actUUID):
        self.uuid = actUUID
        self.getManifest()
        self.getAssertions()
        return self
    def getManifest(self):
        self.manifest = Manifest.objects.get(uuid = self.uuid)
        self.label = self.manifest.label
        self.itemType = self.manifest.itemType
        return self.manifest
    def getAssertions(self):
        self.assertions = Assertion.objects.filter(uuid = self.uuid)
        return self.assertions
