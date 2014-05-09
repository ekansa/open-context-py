from django.db import models


# Manifest provides basic item metadata for all open context items that get a URI
class Manifest(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50)
    repo = models.CharField(max_length=200)
    class_uri = models.CharField(max_length=200)
    label = models.CharField(max_length=200)
    des_predicate_uuid = models.CharField(max_length=50)
    views = models.IntegerField()
    indexed = models.DateTimeField(blank=True, null=True)
    vcontrol = models.DateTimeField(blank=True, null=True)
    archived = models.DateTimeField(blank=True, null=True)
    published = models.DateTimeField(db_index=True)
    revised = models.DateTimeField(db_index=True)
    record_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oc_manifest'
