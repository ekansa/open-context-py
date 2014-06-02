from django.db import models


# Mediafile has basic metadata about media resources (binary files) associated with a media resource item
class Mediafile(models.Model):
    uuid = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    file_type = models.CharField(max_length=50, db_index=True)
    mime_type_uri = models.CharField(max_length=200)
    file_uri = models.CharField(max_length=200)
    filesize = models.DecimalField(max_digits=19, decimal_places=3)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oc_mediafiles'
        unique_together = (('uuid', 'file_type'),)
