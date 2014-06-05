import hashlib
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

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of project_uuids and contexts
        """
        hash_obj = hashlib.sha1()
        concat_string = self.uuid + " " + self.predicate_uri + " " + self.object_uri
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self):
        """
        creates the hash-id on saving to insure a unique assertion
        """
        self.hash_id = self.make_hash_id()
        super(LinkAnnotation, self).save()

    class Meta:
        db_table = 'link_annotations'
