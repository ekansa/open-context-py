import uuid as GenUUID
import datetime
from django.conf import settings
from django.db import models
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.strings.manage import StringManagement
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.octypes.models import OCtype


class TypeManagement():
    """ Class for helping to create and edit data about types
    """
    def __init__(self):
        self.oc_type = False
        self.project_uuid = False
        self.source_id = False
        self.content = False

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
        self.content = content
        self.get_make_type_pred_uuid_content_uuid(predicate_uuid, oc_string.uuid)
        return self.oc_type

    def get_make_type_pred_uuid_content_uuid(self, predicate_uuid, content_uuid):
        """
        gets a type, filtered by a given predicate_uuid and content string
        if a type does not exist, this function creates it, then returns the type
        """
        found = self.check_exists_pred_uuid_content_uuid(predicate_uuid, content_uuid)
        if(found is False):
            if self.content is False:
                try:
                    oc_string = OCstring.objects.get(uuid=content_uuid)
                    self.content = oc_string.content
                except OCstring.DoesNotExist:
                    self.content = False
            if self.content is not False:
                # make a new oc_type object!
                uuid = GenUUID.uuid4()
                newtype = OCtype()
                newtype.uuid = uuid
                newtype.project_uuid = self.project_uuid
                newtype.source_id = self.source_id
                newtype.predicate_uuid = predicate_uuid
                newtype.content_uuid = content_uuid
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
                newman.label = self.content
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
