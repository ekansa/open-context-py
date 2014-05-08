from django.db import models


# This class stores linked data annotations made on the data contributed to open context
class LinkEntity(models.Model):
    uri = models.CharField(max_length=200, primary_key=True)
    label = models.CharField(max_length=200, db_index=True)
    alt_label = models.CharField(max_length=200, db_index=True)
    vocab_uri = models.CharField(max_length=200)
    ent_type = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'link_entities'
