from django.db import models


# Geodata provides geospatial feature data for an item. These get used through spatial
# inheritance for items without their own geospatial data.
class Geodata(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50)
    path = models.CharField(max_length=200)
    ftype = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=24, decimal_places=21)
    longitude = models.DecimalField(max_digits=24, decimal_places=21)
    specificity = models.IntegerField()
    updated = models.DateTimeField(auto_now=True)
    geo_json = models.TextField()
    note = models.TextField()

    class Meta:
        db_table = 'oc_geodata'
