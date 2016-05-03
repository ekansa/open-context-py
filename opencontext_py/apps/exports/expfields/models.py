import hashlib
import collections
from django.db import models
from jsonfield import JSONField


# Stores data about fields for research
class ExpField(models.Model):

    hash_id = models.CharField(max_length=50, primary_key=True)
    table_id = models.CharField(max_length=50, db_index=True)
    field_num = models.IntegerField()
    label = models.CharField(max_length=200, db_index=True)
    rel_ids = JSONField(default={},
                        db_index=True,
                        load_kwargs={'object_pairs_hook': collections.OrderedDict})
    updated = models.DateTimeField(auto_now=True)

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of uuids, obs_nums, predicates, and objects
        """
        hash_obj = hashlib.sha1()
        concat_string = str(self.table_id) + " " + str(self.field_num)
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
        ordering = ['table_id', 'field_num']
        unique_together = ('table_id', 'field_num')
