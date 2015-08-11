import hashlib
from django.db import IntegrityError
from django.db import models


# A version is a way of caching item data so changes can be
# undone
class Version(models.Model):

    change_uuid = models.CharField(max_length=50, db_index=True)
    uuid = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50)
    project_uuid = models.CharField(max_length=50)
    source_id = models.CharField(max_length=50)
    json_data = modles.TextField()  # serialization from Django
    json_ld = modles.TextField()  # JSON-LD output
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique subject
        """
        super(Version, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_versions'
