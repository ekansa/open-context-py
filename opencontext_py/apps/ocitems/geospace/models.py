import hashlib
from django.db import models


# Geodata provides geospatial feature data for an item. These get used through spatial
# inheritance for items without their own geospatial data.
class Geospace(models.Model):
    hash_id = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    meta_type = models.CharField(max_length=50)
    ftype = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=24, decimal_places=21)
    longitude = models.DecimalField(max_digits=24, decimal_places=21)
    specificity = models.IntegerField()
    updated = models.DateTimeField(auto_now=True)
    coordinates = models.TextField()
    note = models.TextField()

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of uuids and location types
        """
        hash_obj = hashlib.sha1()
        concat_string = self.uuid + " " + str(self.meta_type)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self):
        """
        creates the hash-id on saving to insure a unique assertion
        """
        self.hash_id = self.make_hash_id()
        super(Geospace, self).save()

    class Meta:
        db_table = 'oc_geospace'
