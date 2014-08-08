from django.db import models


# Stores data about fields for research
class ExpField(models.Model):
    table_id = models.CharField(max_length=50, db_index=True)
    field_num = models.IntegerField()
    field_label = models.CharField(max_length=50)
    field_rels = models.TextField(db_index=True)
    label = models.CharField(max_length=200, db_index=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exp_fields'
