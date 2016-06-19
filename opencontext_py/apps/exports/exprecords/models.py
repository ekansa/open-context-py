import hashlib
from django.db import models


# Stores a single export data table cell
class ExpCell(models.Model):
    rec_id = models.CharField(max_length=200, primary_key=True)
    table_id = models.CharField(max_length=50, db_index=True)
    uuid = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    row_num = models.IntegerField(db_index=True)  # the row number
    field_num = models.IntegerField()  # the field number
    record = models.TextField()  # the actual cell value
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        saves with created time if None
        """
        if self.rec_id is None:
            self.rec_id = str(self.row_num) + '-' + str(self.field_num) + '-' + self.table_id 
        else:
            if len(self.rec_id) < 4:
                self.rec_id = str(self.row_num) + '-' + str(self.field_num) + '-' + self.table_id  
        super(ExpCell, self).save(*args, **kwargs)

    class Meta:
        db_table = 'exp_records'
        ordering = ['table_id', 'row_num', 'field_num']
        unique_together = ('table_id', 'row_num', 'field_num')
