from django.db import models


# Manifest provides basic item metadata for all open context items that get a URI
class Manifest(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    label = models.CharField(max_length=200)
    sourceID = models.CharField(max_length=50)
    itemType = models.CharField(max_length=50)
    repo = models.CharField(max_length=200)
    classURI = models.CharField(max_length=200)
    desPredicateUUID = models.CharField(max_length=50)
    views = models.IntegerField()
    indexed = models.DateTimeField()
    vcontrol = models.DateTimeField()
    archived = models.DateTimeField()
    published = models.DateTimeField()
    revised = models.DateTimeField()
    recordUpdated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oc_manifest'
