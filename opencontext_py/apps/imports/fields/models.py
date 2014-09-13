import hashlib
from django.db import models


# Stores data about fields from imported tables
class ImportField(models.Model):
    DEFAULT_FIELD_TYPE = 'NOT DETERMINED'
    hash_id = models.CharField(max_length=50, primary_key=True)
    source_id = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    field_num = models.IntegerField()
    field_type = models.CharField(max_length=50)
    is_keycell = models.BooleanField()
    label = models.CharField(max_length=200, db_index=True)
    orig_label = models.CharField(max_length=200)
    f_uuid = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of uuids, obs_nums, predicates, and objects
        """
        hash_obj = hashlib.sha1()
        concat_string = str(self.source_id) + " " + str(self.field_num)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self):
        """
        creates the hash-id on saving to insure a unique assertion
        """
        self.hash_id = self.make_hash_id()
        super(ExpField, self).save()

    class Meta:
        db_table = 'exp_fields'
        ordering = ['source_id', 'field_num']
        unique_together = ('source_id', 'field_num')
