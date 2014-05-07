from django.db import models


# Manifest provides basic item metadata for all open context items that get a URI
class Manifest(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    label = models.CharField(max_length=200)
    source_id = models.CharField(max_length=50)
    item_type = models.CharField(max_length=50)
    repo = models.CharField(max_length=200)
    class_uri = models.CharField(max_length=200)
    des_predicate_uuid = models.CharField(max_length=50)
    views = models.IntegerField()
    indexed = models.DateTimeField()
    vcontrol = models.DateTimeField()
    archived = models.DateTimeField()
    published = models.DateTimeField()
    revised = models.DateTimeField()
    record_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oc_manifest'
