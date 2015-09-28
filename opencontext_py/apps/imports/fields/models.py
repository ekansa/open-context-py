from datetime import datetime
from django.utils import timezone
from django.db import models


# Stores data about fields from imported tables
class ImportField(models.Model):

    DEFAULT_FIELD_TYPE = 'Type not assigned'
    DEFAULT_DATA_TYPE = ''
    DEFAULT_VALUE_CAT = ''

    source_id = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    field_num = models.IntegerField()
    is_keycell = models.BooleanField(default=False)
    ref_name = models.CharField(max_length=200, db_index=True)
    ref_orig_name = models.CharField(max_length=200)
    field_type = models.CharField(max_length=50)
    field_data_type = models.CharField(max_length=50)
    field_value_cat = models.CharField(max_length=50)
    obs_num = models.IntegerField()
    label = models.CharField(max_length=200, db_index=True)
    value_prefix = models.CharField(max_length=50)
    unique_count = models.IntegerField()
    f_uuid = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'imp_fields'
        ordering = ['source_id', 'field_num']
        unique_together = ('source_id', 'field_num')
