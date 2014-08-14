from django.db import models


# OCtype stores a type, or an item from a project's controlled vocabulary
class OCtype(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    predicate_uuid = models.CharField(max_length=50, db_index=True)
    content_uuid = models.CharField(max_length=50, db_index=True)
    rank = models.DecimalField(max_digits=8, decimal_places=3)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oc_types'
        ordering = ['rank']
        unique_together = ("predicate_uuid", "content_uuid")
