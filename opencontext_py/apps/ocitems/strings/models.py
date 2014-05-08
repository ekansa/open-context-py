from django.db import models


# OCstring stores string content, with each string unique to a project
class OCstring(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    hash_id = models.CharField(max_length=50, unique=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    updated = models.DateTimeField(auto_now=True)
    content = models.TextField()

    class Meta:
        db_table = 'oc_strings'