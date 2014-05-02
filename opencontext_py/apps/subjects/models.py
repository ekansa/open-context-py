from django.db import models
from opencontext_py.apps.itemapps.ocitem.models import OCitem as OCitem

class Subject(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    ocitem = models.ForeignKey(OCitem,  db_column = 'uuid', to_field='uuid', unique=True)
    class Meta:
        db_table = 'oc_manifest'
    def outputMeta(self):
        return "%s, %s" % (self.ocitem.manifest.label, self.uuid)