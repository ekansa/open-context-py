from django.db import models


# Stores data about relationships between fields of imported data
class ImportFieldAnnotation(models.Model):

    PRED_CONTAINED_IN = 'oc-gen:contained-in'
    PRED_DESCRIBES = 'oc-gen:describes'
    PRED_VALUE_OF = 'oc-gen:value-of'

    source_id = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    field_num = models.IntegerField()
    predicate = models.CharField(max_length=50, db_index=True)
    predicate_field_num = models.IntegerField()
    object_field_num = models.IntegerField()
    object_uuid = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'imp_field_annotations'
        ordering = ['source_id', 'field_num']
        unique_together = ('source_id',
                           'field_num',
                           'predicate',
                           'predicate_field_num',
                           'object_field_num',
                           'object_uuid')
