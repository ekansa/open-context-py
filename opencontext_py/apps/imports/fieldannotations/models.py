from django.db import models


# Stores data about fields from imported tables
class ImportFieldAnnotation(models.Model):

    source_id = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    field_num = models.IntegerField()
    predicate_rel = models.CharField(max_length=50, db_index=True)
    object_num = models.IntegerField()
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'imp_field_annotations'
        ordering = ['source_id', 'field_num']
        unique_together = ('source_id', 'field_num', 'predicate_rel', 'object_num')
