from django.db import models


# This class stores linked data annotations made on the data contributed to open context
class LinkAnnotation(models.Model):
    hash_id = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50, db_index=True)
    subject_type = models.CharField(max_length=50)
    project_uuid = models.CharField(max_length=50)
    source_id = models.CharField(max_length=50)
    predicate_uri = models.CharField(max_length=200, db_index=True)
    object_uri = models.CharField(max_length=200, db_index=True)
    creator_uuid = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'link_annotations'
