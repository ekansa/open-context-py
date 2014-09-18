from django.db import models


# Stores data about fields from imported tables
class ImportFieldType(models.Model):

    DEFAULT_FIELD_TYPE = 'NOT DETERMINED'
    source_id = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    field_num = models.IntegerField()
    field_type = models.CharField(max_length=50)
    field_data_type = models.CharField(max_length=50)
    field_value_cat = models.CharField(max_length=50)
    label = models.CharField(max_length=200, db_index=True)
    value_prefix = models.CharField(max_length=50)
    unique_count = models.IntegerField()
    f_uuid = models.CharField(max_length=50, db_index=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'imp_field_types'
        ordering = ['source_id', 'field_num']
        unique_together = ('source_id', 'field_num')
