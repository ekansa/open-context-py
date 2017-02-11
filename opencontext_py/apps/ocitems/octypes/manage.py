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
        self.suggested_uuid = False  # make sure this is not already used!
        self.suggested_content_uuid = False  # make sure this is not already used!
        self.sup_dict = None
        self.sup_reconcile_key = None  # key to check for reconciling sup_json
        self.sup_reconcile_value = None  # value for key to check in sup_json

    def get_make_type_within_pred_uuid(self,
                                       predicate_uuid,
                                       content,
                                       content_suffix_num=1):
        """
        gets a type, filtered by a given predicate_uuid and content string
        if a type does not exist, this function creates it, then returns the type
        """
        original_content = content
        str_manage = StringManagement()
        str_manage.project_uuid = self.project_uuid
        str_manage.source_id = self.source_id
        str_manage.suggested_uuid = self.suggested_content_uuid
        # get an existing or create a new string object
        if content_suffix_num > 1:
            # add a numeric suffix for content, in case we need to
            # increment up to in rare cases when different types have the same string content
            content += ' [' + str(content_suffix_num) + ']'
        oc_string = str_manage.get_make_string(content)
        self.content = content
        self.get_make_type_pred_uuid_content_uuid(predicate_uuid, oc_string.uuid)
        if self.sup_reconcile_key is not None and\
           self.sup_reconcile_value is not None:
            # checks to see if the manifest supplemental JSON has a matching key, value pair
            # this lets us further constrain reconciliation, say with FAIMS attributes (types) 
            man_obj = False
            try:
                man_obj = Manifest.objects.get(uuid=self.oc_type.uuid)
            except Manifest.DoesNotExist:
                man_obj = False
            if man_obj is not False:
                match_ok = man_obj.check_sup_json_key_value(self.sup_reconcile_key,
                                                            self.sup_reconcile_value)
                if match_ok is False:
                    self.oc_type = False
                    content_suffix_num += 1
                    if content_suffix_num <= 10:
                        # so we don't get into endless loops
                        self.oc_type = self.get_make_type_within_pred_uuid(predicate_uuid,
                                                                           original_content,
                                                                           content_suffix_num)
        return self.oc_type

    def get_make_type_pred_uuid_content_uuid(self, predicate_uuid, content_uuid):
        """
        gets a type, filtered by a given predicate_uuid and content string
        if a type does not exist, this function creates it, then returns the type
        """
        found = self.check_exists_pred_uuid_content_uuid(predicate_uuid, content_uuid)
        if found is False:
            if self.content is False:
                try:
                    oc_string = OCstring.objects.get(uuid=content_uuid)
                    self.content = oc_string.content
                except OCstring.DoesNotExist:
                    self.content = False
            # print('Content: ' + str(self.content))
            if self.content is not False:
                # make a new oc_type object!
                if self.suggested_uuid is not False:
                    uuid = self.suggested_uuid
                else:
                    # string is new to the project so make it.
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
                newman.sup_json = self.sup_dict
                newman.revised = datetime.datetime.now()
                newman.save()
        return self.oc_type

    def check_exists_pred_uuid_content(self,
                                       predicate_uuid,
                                       content,
                                       show_uuid=False):
        """
        Checks if a predicate_uuid and a content string already
        exists
        This is useful, since it does not change anything in the database,
        it just checks to see if a content string is used with a predicate
        """
        found = False
        str_manage = StringManagement()
        str_manage.project_uuid = self.project_uuid
        # get an existing or create a new string object
        content_uuid = str_manage.check_string_exists(content,
                                                      True)
        if content_uuid is not False:
            # we've seen the string before, so
            # now check if
            found = self.check_exists_pred_uuid_content_uuid(predicate_uuid,
                                                             content_uuid,
                                                             show_uuid)
        return found

    def check_exists_pred_uuid_content_uuid(self,
                                            predicate_uuid,
                                            content_uuid,
                                            show_uuid=False):
        """
        Checks if a predicate_uuid and content_uuid already exists
        """
        found = False
        try:
            self.oc_type = OCtype.objects.get(predicate_uuid=predicate_uuid,
                                              content_uuid=content_uuid)
        except OCtype.DoesNotExist:
            self.oc_type = False
        if self.oc_type is not False:
            found = True
            if show_uuid:
                found = self.oc_type.uuid
        return found
