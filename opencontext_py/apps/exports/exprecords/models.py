import hashlib
from django.db import models


# Stores a single export data table cell
class ExpCell(models.Model):
    hash_id = models.CharField(max_length=50, primary_key=True)
    table_id = models.CharField(max_length=50, db_index=True)
    uuid = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    row_num = models.IntegerField(db_index=True)  # the row number
    field_num = models.IntegerField()  # the field number
    record = models.TextField()  # the actual cell value
    updated = models.DateTimeField(auto_now=True)

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of uuids, obs_nums, predicates, and objects
        """
        hash_obj = hashlib.sha1()
        concat_string = str(self.table_id) + " "\
                                           + str(self.uuid)\
                                           + " " + str(self.row_num)\
                                           + " " + str(self.field_num)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self):
        """
        creates the hash-id on saving to insure a unique assertion
        """
        self.hash_id = self.make_hash_id()
        super(ExpCell, self).save()

    class Meta:
        db_table = 'exp_records'
        ordering = ['table_id', 'row_num', 'field_num']
        unique_together = ('table_id', 'row_num', 'field_num')
