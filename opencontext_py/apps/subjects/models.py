from django.db import models
from opencontext_py.libs.manifest.models import Manifest as Manifest

class Subject(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    Manifest = False;
    class Meta:
        db_table = 'oc_subjects'
    def __str__(self):
        return "%s, %s" % (self.sManifest.label, self.sManifest.uuid)
    def getManifest(self, actUUID):
        self.Manifest = Manifest.objects.get(uuid = actUUID)
        return self.Manifest
