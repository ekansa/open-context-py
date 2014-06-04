import hashlib
from django.db import models


# OCstring stores stable identifiers of various types
class StableIdentifer(models.Model):
    stable_id = models.CharField(max_length=200, primary_key=True)
    stable_type = models.CharField(max_length=50)
    uuid = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oc_identifiers'
