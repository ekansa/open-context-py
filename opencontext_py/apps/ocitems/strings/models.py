import hashlib
from django.db import models


# OCstring stores string content, with each string unique to a project
class OCstring(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    hash_id = models.CharField(max_length=50, unique=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    updated = models.DateTimeField(auto_now=True)
    content = models.TextField()

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of project_uuids and content
        """
        hash_obj = hashlib.sha1()
        concat_string = self.project_uuid + " " + self.content
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique string for a project
        """
        self.hash_id = self.make_hash_id()
        super(OCstring, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_strings'
