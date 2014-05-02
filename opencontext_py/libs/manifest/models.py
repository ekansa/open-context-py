from django.db import models

class Manifest(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    label = models.CharField(max_length=200)
    class Meta:
        db_table = 'oc_manifest'