from django.db import models


# Stores data about fields from imported tables
class ImportField(models.Model):
    DEFAULT_FIELD_TYPE = 'NOT DETERMINED'
    source_id = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    field_num = models.IntegerField()
    field_type = models.CharField(max_length=50)
    is_keycell = models.BooleanField()
    label = models.CharField(max_length=200, db_index=True)
    ref_name = models.CharField(max_length=200, db_index=True)
    ref_orig_name = models.CharField(max_length=200)
    f_uuid = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'imp_fields'
        ordering = ['source_id', 'field_num']
        unique_together = ('source_id', 'field_num')
