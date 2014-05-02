from django.db import models
from opencontext_py.apps.itemapps.manifest.models import Manifest as Manifest

class OCitem(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    manifest = models.ForeignKey(Manifest, db_column = 'uuid', to_field='uuid', unique=True)
    class Meta:
        db_table = 'oc_manifest'