from django.db import models


# Assertions store descriptions and linking relations for Open Context items
# Assertion data mainly represents data contributed from data authors, not OC editors
class Assertion(models.Model):
    hashID = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50)
    subjectType = models.CharField(max_length=50)
    projectUUID = models.CharField(max_length=50)
    sourceID = models.CharField(max_length=50)
    obsNode = models.CharField(max_length=50)
    obsNum = models.IntegerField()
    sort = models.DecimalField(max_digits=8, decimal_places=3)
    visibility = models.IntegerField()
    predicateUUID = models.CharField(max_length=50)
    objectUUID = models.CharField(max_length=50)
    objectType = models.CharField(max_length=50)
    dataNum = models.DecimalField(max_digits=19, decimal_places=10)
    dataDate = models.DateTimeField()
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oc_assertions'
        ordering = ['sort']
