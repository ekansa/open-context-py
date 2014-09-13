import hashlib
from django.db import models


# Stores a single import data table cell
class ImportCell(models.Model):
    hash_id = models.CharField(max_length=50, primary_key=True)
    source_id = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    row_num = models.IntegerField(db_index=True)  # the row number
    field_num = models.IntegerField()  # the field number
    fl_uuid = models.CharField(max_length=50)  # field-literal uuid, uuid unique to field - literals in a proj
    l_uuid = models.CharField(max_length=50)  # literal uuid, unique to literal values in a project
    record = models.TextField()  # the actual cell value
    updated = models.DateTimeField(auto_now=True)

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of uuids, obs_nums, predicates, and objects
        """
        hash_obj = hashlib.sha1()
        concat_string = str(self.source_id) + " " + str(self.row_num)\
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
        db_table = 'imp_records'
        ordering = ['source_id', 'row_num', 'field_num']
        unique_together = ('source_id', 'row_num', 'field_num')
