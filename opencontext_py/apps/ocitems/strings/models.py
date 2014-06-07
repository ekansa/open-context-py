import uuid as GenUUID
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
        creates a hash-id to insure unique combinations of project_uuids and contexts
        """
        hash_obj = hashlib.sha1()
        concat_string = self.project_uuid + " " + self.content
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self):
        """
        creates the hash-id on saving to insure a unique assertion
        """
        self.hash_id = self.make_hash_id()
        super(OCstring, self).save()

    class Meta:
        db_table = 'oc_strings'


class StringManagement():
    """
    Handy functions for interacting with strings
    """
    SOURCE_ID = 'StringManagement'

    def __init__(self):
        self.oc_string = False
        self.project_uuid = False
        self.source_id = self.SOURCE_ID

    def get_make_string(self, content):
        """
        returns an oc_string object from the database if it already exists,
        or creates one if it does not yet exist
        """
        found = self.check_string_exists(content)
        if(found is False):
            # string is new to the project so make it.
            uuid = GenUUID.uuid1()
            newstring = OCstring()
            newstring.uuid = uuid
            newstring.project_uuid = self.project_uuid
            newstring.source_id = self.source_id
            newstring.content = content
            newstring.save()
            self.oc_string = newstring
        return self.oc_string

    def check_string_exists(self, content):
        """
        Checks to see if a given string exists in a project
        """
        found = False
        ch_string = OCstring()
        ch_string.project_uuid = self.project_uuid
        ch_string.content = content
        hash_id = OCstring.make_hash_id(ch_string)
        try:
            self.oc_string = OCstring.objects.get(hash_id=hash_id)
        except OCstring.DoesNotExist:
            self.oc_string = False
        if(self.oc_string is not False):
            found = True
        return found
