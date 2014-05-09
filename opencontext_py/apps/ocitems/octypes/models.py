from django.db import models
from opencontext_py.apps.ocitems.ocitem.models import OCitem as OCitem


# OCtype stores a type, or an item from a project's controlled vocabulary
class OCtype(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    hash_id = models.CharField(max_length=50, unique=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    predicate_uuid = models.CharField(max_length=50, db_index=True)
    content_uuid = models.CharField(max_length=50, db_index=True)
    rank = models.DecimalField(max_digits=8, decimal_places=3)
    label = models.CharField(max_length=200)
    updated = models.DateTimeField(auto_now=True)

    def get_item(self):
        act_item = OCitem()
        self.ocitem = act_item.get_item(self.uuid)
        self.label = self.ocitem.label
        self.item_type = self.ocitem.item_type
        return self.ocitem

    class Meta:
        db_table = 'oc_types'
        ordering = ['rank']
        unique_together = ("predicate_uuid", "content_uuid")
