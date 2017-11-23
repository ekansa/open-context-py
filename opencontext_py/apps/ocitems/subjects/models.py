import hashlib
from django.db import IntegrityError
from django.db import models


# A subject is a generic item that is the subbject of observations
# A subject is the main type of record in open context for analytic data
# The main dependency for this app is for OCitems, which are used to generate
# Every type of item in Open Context, including subjects
class Subject(models.Model):
    HIEARCHY_DELIM = '/'
    uuid = models.CharField(max_length=50, primary_key=True)
    hash_id = models.CharField(max_length=50, unique=True)
    project_uuid = models.CharField(max_length=50)
    source_id = models.CharField(max_length=50)
    context = models.CharField(max_length=400, db_index=True)
    updated = models.DateTimeField(auto_now=True)

    def make_hash_id(self,
                     project_uuid,
                     context):
        """
        creates a hash-id to insure unique combinations of project_uuids and contexts
        """
        hash_obj = hashlib.sha1()
        concat_string = project_uuid + " " + context
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique subject
        """
        self.hash_id = self.make_hash_id(self.project_uuid,
                                         self.context)
        super(Subject, self).save(*args, **kwargs)

    def get_item(self):
        actItem = OCitem()
        self.ocitem = actItem.get_item(self.uuid)
        self.label = self.ocitem.label
        self.item_type = self.ocitem.item_type
        return self.ocitem

    class Meta:
        db_table = 'oc_subjects'
