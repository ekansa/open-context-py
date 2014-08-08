from django.db import models


# Stores data about fields for research
class ExpRecord(models.Model):
    table_id = models.CharField(max_length=50, db_index=True)
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    row_num = models.IntegerField(db_index=True)  # the row number
    field_num = models.IntegerField()  # the field number
    record = models.TextField()  # the actual cell value
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exp_records'
        ordering = ['table_id', 'row_num', 'field_num']
        unique_together = ('table_id', 'row_num', 'field_num')
