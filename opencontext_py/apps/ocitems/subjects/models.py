import hashlib
from django.db import IntegrityError
from django.db import models


# A subject is a generic item that is the subbject of observations
# A subject is the main type of record in open context for analytic data
# The main dependency for this app is for OCitems, which are used to generate
# Every type of item in Open Context, including subjects
class Subject(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    hash_id = models.CharField(max_length=50, unique=True)
    project_uuid = models.CharField(max_length=50)
    source_id = models.CharField(max_length=50)
    context = models.CharField(max_length=400)
    updated = models.DateTimeField(auto_now=True)

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of project_uuids and contexts
        """
        hash_obj = hashlib.sha1()
        concat_string = self.project_uuid + " " + self.context
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self):
        """
        creates the hash-id on saving to insure a unique subject
        """
        self.hash_id = self.make_hash_id()
        super(Subject, self).save()

    def get_item(self):
        actItem = OCitem()
        self.ocitem = actItem.get_item(self.uuid)
        self.label = self.ocitem.label
        self.item_type = self.ocitem.item_type
        return self.ocitem

    class Meta:
        db_table = 'oc_subjects'
