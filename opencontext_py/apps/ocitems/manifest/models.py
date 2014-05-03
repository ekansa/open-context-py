from django.db import models

class Manifest(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    label = models.CharField(max_length=200)
    sourceID = models.CharField(max_length=50)
    itemType = models.CharField(max_length=50)
    repo = models.CharField(max_length=200)
    classURI = models.CharField(max_length=200)
    desPredicateUUID = models.CharField(max_length=50)
    class Meta:
        db_table = 'oc_manifest'