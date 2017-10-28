import uuid as GenUUID
import hashlib
from django.db import models
from opencontext_py.apps.ocitems.strings.models import OCstring


class StringManagement():
    """
    Handy functions for interacting with strings
    """
    SOURCE_ID = 'StringManagement'

    def __init__(self):
        self.oc_string = False
        self.project_uuid = False
        self.source_id = self.SOURCE_ID
        self.suggested_uuid = False  # make sure this is not already used!

    def get_make_string(self, content):
        """
        returns an oc_string object from the database if it already exists,
        or creates one if it does not yet exist
        """
        found = self.check_string_exists(content)
        if found is False:
            if self.suggested_uuid is not False:
                uuid = self.suggested_uuid
            else:
                # string is new to the project so make it.
                uuid = GenUUID.uuid4()
            newstring = OCstring()
            newstring.uuid = uuid
            newstring.project_uuid = self.project_uuid
            newstring.source_id = self.source_id
            newstring.content = content
            newstring.save()
            self.oc_string = newstring
        return self.oc_string

    def check_string_exists(self, content, show_uuid=False):
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
            if show_uuid:
                found = self.oc_string.uuid
        return found
