from django.db import models
from opencontext_py.apps.ocitems.ocitem.models import OCitem as OCitem

# A subject is a generic item that is the subbject of observations
# A subject is the main type of record in open context for analytic data
# The main dependency for this app is for OCitems, which are used to generate
# Every type of item in Open Context, including subjects
class Subject(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    class Meta:
        db_table = 'oc_manifest'
    def getItem(self):
        actItem = OCitem()
        self.ocitem = actItem.getItem(self.uuid)
        self.label = self.ocitem.label
        self.itemType = self.ocitem.itemType
        return self.ocitem