from django.db import models


# Stores metadata about export tables
class ExpMetadata(models.Model):
    table_id = models.CharField(max_length=50, primary_key=True)
    label = models.CharField(max_length=200, db_index=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exp_metadata'
