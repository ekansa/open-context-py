from datetime import datetime
from django.db import models


# Stores metadata about export tables
class ExpTable(models.Model):
    table_id = models.CharField(max_length=50, primary_key=True)
    label = models.CharField(max_length=200, db_index=True)
    field_count = models.IntegerField()
    row_count = models.IntegerField()
    # meta_json = sort this out.
    short_des = models.CharField(max_length=200)
    abstract = models.TextField()
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        saves with created time if None
        """
        if self.created is None:
            self.created = datetime.now()
        super(ExpTable, self).save(*args, **kwargs)

    class Meta:
        db_table = 'exp_tables'
