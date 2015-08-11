import hashlib
from django.db import IntegrityError
from django.db import models


# A version is a way of caching item data so changes can be
# undone
class VersionHistory(models.Model):

    change_uuid = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50)
    project_uuid = models.CharField(max_length=50)
    source_id = models.CharField(max_length=50)
    creator_uuid = models.CharField(max_length=50, db_index=True)  # who made the change
    change = modles.TextField()  # json data about the change
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique subject
        """
        super(Version, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_versionhistories'
