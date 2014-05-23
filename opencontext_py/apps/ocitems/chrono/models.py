import hashlib
from django.db import models


# Chronology provides (eventually)topo-time modeling of time range information for an item
class Chrono(models.Model):
    hash_id = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    meta_type = models.CharField(max_length=50)
    # lc means "least confidence", c means "confidence"
    start_lc = models.DecimalField(max_digits=19, decimal_places=5)
    start_c = models.DecimalField(max_digits=19, decimal_places=5)
    end_c = models.DecimalField(max_digits=19, decimal_places=5)
    end_lc = models.DecimalField(max_digits=19, decimal_places=5)
    updated = models.DateTimeField(auto_now=True)
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
        super(Chrono, self).save()

    class Meta:
        db_table = 'oc_chrono'
