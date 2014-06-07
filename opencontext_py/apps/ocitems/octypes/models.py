import uuid as GenUUID
import datetime
from django.conf import settings
from datetime import datetime, date, time
from django.db import models
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.strings.models import OCstring, StringManagement
from opencontext_py.apps.entities.uri.models import URImanagement


# OCtype stores a type, or an item from a project's controlled vocabulary
class OCtype(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    predicate_uuid = models.CharField(max_length=50, db_index=True)
    content_uuid = models.CharField(max_length=50, db_index=True)
    rank = models.DecimalField(max_digits=8, decimal_places=3)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oc_types'
        ordering = ['rank']
        unique_together = ("predicate_uuid", "content_uuid")


class TypeLookup():

    def __init__(self):
        self.uuid = False
        self.label = False
        self.project_uuid = False
        self.predicate_uuid = False
        self.predicate_label = False
        self.content_uuid = False
        self.content = False
        self.oc_type = False
        self.manifest = False
        self.oc_string = False
        self.super_classes = False
        self.show_super_classes = False
        self.show_predicate_label = False

    def get_whole_octype(self, uuid):
        """ get a type item including lots of useful related data
        """
        try:
            self.manifest = Manifest.objects.get(uuid=uuid)
        except Manifest.DoesNotExist:
            self.manifest = False
        if(self.manifest is not False):
            self.uuid = self.manifest.uuid
            self.label = self.manifest.label
            self.project_uuid = self.manifest.project_uuid
        self.get_octype_without_manifest(uuid)

    def get_octype_without_manifest(self, uuid):
        """ get a type item information, except data in manifest
        """
        try:
            self.oc_type = OCtype.objects.get(uuid=uuid)
        except OCType.DoesNotExist:
            self.oc_type = False
        if(self.oc_type is not False):
            self.predicate_uuid = self.oc_type.predicate_uuid
            self.content_uuid = self.oc_type.content_uuid
            try:
                self.oc_string = OCstring.objects.get(uuid=self.content_uuid)
            except OCstring.DoesNotExist:
                self.oc_string = False
            if(self.show_predicate_label):
                try:
                    pred_man = Manifest.objects.get(uuid=self.predicate_uuid)
                    self.predicate_label = pred_man.label
                except Manifest.DoesNotExist:
                    self.predicate_label = False
        if(self.oc_string is not False):
            self.content = self.oc_string.content


class TypeManagement():
    """ Class for helping to create and edit data about types
    """
    def __init__(self):
        self.oc_type = False
        self.project_uuid = False
        self.source_id = False

    def get_make_type_within_pred_uuid(self, predicate_uuid, content):
        """
        gets a type, filtered by a given predicate_uuid and content string
        if a type does not exist, this function creates it, then returns the type
        """
        str_manage = StringManagement()
        str_manage.project_uuid = self.project_uuid
        str_manage.source_id = self.source_id
        # get an existing or create a new string object
        oc_string = str_manage.get_make_string(content)
        found = self.check_exists_pred_uuid_content_uuid(predicate_uuid, oc_string.uuid)
        if(found is False):
            # make a new oc_type object!
            uuid = GenUUID.uuid1()
            newtype = OCtype()
            newtype.uuid = uuid
            newtype.project_uuid = self.project_uuid
            newtype.source_id = self.source_id
            newtype.predicate_uuid = predicate_uuid
            newtype.content_uuid = oc_string.uuid
            newtype.rank = 0
            newtype.save()
            self.oc_type = newtype
            #now make a manifest record for the item
            newman = Manifest()
            newman.uuid = uuid
            newman.project_uuid = self.project_uuid
            newman.source_id = self.source_id
            newman.item_type = 'types'
            newman.repo = ''
            newman.class_uri = ''
            newman.label = content
            newman.des_predicate_uuid = ''
            newman.views = 0
            newman.revised = datetime.datetime.now()
            newman.save()
        return self.oc_type

    def check_exists_pred_uuid_content_uuid(self, predicate_uuid, content_uuid):
        """
        Checks if a predicate_uuid and content_uuid already exists
        """
        found = False
        try:
            self.oc_type = OCtype.objects.get(predicate_uuid=predicate_uuid,
                                              content_uuid=content_uuid)
        except OCtype.DoesNotExist:
            self.oc_type = False
        if(self.oc_type is not False):
            found = True
        return found
