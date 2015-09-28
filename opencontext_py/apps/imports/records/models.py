import hashlib
from django.utils import timezone
from django.db import models


# Stores a single import data table cell
class ImportCell(models.Model):
    source_id = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    row_num = models.IntegerField(db_index=True)  # the row number
    field_num = models.IntegerField()  # the field number
    rec_hash = models.CharField(max_length=50, db_index=True) # hash value of the record
    fl_uuid = models.CharField(max_length=50)  # field-literal uuid, uuid unique to field - literals in a proj
    l_uuid = models.CharField(max_length=50)  # literal uuid, unique to literal values in a project
    cell_ok = models.BooleanField(default=None)  # is the record actually OK use as data, if False ignore it
    record = models.TextField()  # the actual cell value
    updated = models.DateTimeField(auto_now=True)

    def make_rec_hash(self, project_uuid, record):
        """
        creates a record hash value for easy comparisons
        """
        hash_obj = hashlib.sha1()
        concat_string = project_uuid + ' ' + record
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self, *args, **kwargs):
        """
        creates a record hash, 
        """
        self.rec_hash = self.make_rec_hash(self.project_uuid,
                                           self.record)
        super(ImportCell, self).save(*args, **kwargs)

    def uuids_save(self):
        """
        save only uuids
        """
        super(ImportCell, self).save(update_fields=['fl_uuid',
                                                    'l_uuid'])

    class Meta:
        db_table = 'imp_records'
        ordering = ['source_id', 'row_num', 'field_num']
        unique_together = ('source_id', 'row_num', 'field_num')
