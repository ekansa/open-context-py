from django.db import models


# Stores data about fields from imported tables
class ImportSource(models.Model):

    source_id = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    label = models.CharField(max_length=200)
    field_count = models.IntegerField()
    row_count = models.IntegerField()
    source_type = models.CharField(max_length=50)
    is_current = models.BooleanField()
    imp_status = models.CharField(max_length=50)
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'imp_sources'
        ordering = ['-updated']
