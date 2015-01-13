import uuid as GenUUID
import datetime
from django.conf import settings
from datetime import datetime, date, time
from django.db import models
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.octypes.models import OCtype


class TypeLookup():
    """ Class for helping with derefencing type entities
    """

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
        except OCtype.DoesNotExist:
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
