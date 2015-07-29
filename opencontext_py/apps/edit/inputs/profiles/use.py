import re
import json
import time
import datetime
from dateutil.parser import parse
import uuid as GenUUID
from django.db import models
from django.db.models import Q, Count
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.edit.inputs.profiles.models import InputProfile
from opencontext_py.apps.edit.inputs.fieldgroups.models import InputFieldGroup
from opencontext_py.apps.edit.inputs.inputrelations.models import InputRelation
from opencontext_py.apps.edit.inputs.inputfields.models import InputField
from opencontext_py.apps.edit.inputs.rules.models import InputRule
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.octypes.manage import TypeManagement
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.strings.manage import StringManagement
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.documents.models import OCdocument


class InputProfileUse():
    """ This class contains methods
        to assist in manual data entry for a project
    """

    def __init__(self):
        self.errors = {}
        self.ok = True
        self.create_ok = False
        self.edit_uuid = False
        self.item_type = False
        self.project_uuid = False
        self.profile_uuid = False
        self.profile_obj = False
        self.creator_uuid = False
        self.context_uuid = False
        self.response = False
        self.recusion_count = 0
        self.visibility = 1
        self.contain_obs_node = '#contents-1'
        self.contain_obs_num = 1
        self.contain_sort = 1

    def test(self, field_data):
        output = {'field_data': field_data}
        output['required'] = self.get_required_make_data(field_data)
        output['ok'] = False
        for field_uuid, field_values in field_data.items():
            self.profile_field_update(field_uuid, field_values)
        return output

    def create_update(self, field_data):
        """ creates or updates an item with post data """
        # we're dealing with a new item to be created
        required_make_data = self.get_required_make_data(field_data)
        # first check to see if the item exists
        try:
            item_man = Manifest.objects.get(uuid=self.edit_uuid)
        except Manifest.DoesNotExist:
            item_man = False
        if item_man is not False:
            # we've found a record for this item, so we can
            # update any of the required fields.
            self.update_required_make_data(item_man, required_make_data)
        else:
            item_man = self.create_item(required_make_data)
        for field_uuid, field_values in field_data.items():
            self.profile_field_update(field_uuid, field_values)

    def profile_field_update(self, field_uuid, field_values):
        """ lookup the object for the profile's input field
            based on the field_uuid

            Only returns a field that is NOT
            required by open context,
            since those get special handling
        """
        output = True
        done = False
        for fgroup in self.profile_obj['fgroups']:
            for field in fgroup['fields']:
                if field['oc_required'] is False \
                   and field['id'] == field_uuid:
                    # we've found the field!
                    value_index = 0
                    for field_value in field_values:
                        valid = self.validate_field_value(field, field_value, value_index)
                        value_index += 1
                    done = True
                    break
            if done:
                break
        return output

    def validate_field_value(self, field, field_value, value_index):
        """ validates a field_value for a field,
            the value_index parameter is useful if there is a
            limit in the number of values for a field
        """
        error_key = field['id'] + '-' + str(value_index)
        valid = True  # default to optimism
        if field['data_type'] == 'id':
            # first check is to see if the field_value exists in the manifest
            try:
                val_man = Manifest.objects.get(uuid=field_value)
            except Manifest.DoesNotExist:
                valid = False
                self.errors[error_key] = 'Problem with: ' + field['label'] + '; cannot find: ' + str(field_value)
            if valid:
                # OK, the field_value is an ID in the manifest
                # so let's check to make sure it is OK to associate
                try:
                    pred_man = Manifest.objects.get(uuid=field['predicate_uuid'])
                except Manifest.DoesNotExist:
                    pred_man = False
                if pred_man is not False:
                    if pred_man.class_uri == 'variable' \
                       and val_man.item_type != 'types':
                        # we've got a variable that does not link to a type!
                        self.errors[error_key] = 'Problem with: ' + field['label'] + '; '
                        self.errors[error_key] += val_man.label + ' (' + val_man.uuid + ') is not a type/category.'
                        valid = False
        elif field['data_type'] == 'xsd:integer':
            try:
                int_data = int(float(field_value))
            except:
                self.errors[error_key] = 'Problem with: ' + field['label'] + '; '
                self.errors[error_key] += '"' + str(field_value) + '" is not an integer.'
                valid = False
        elif field['data_type'] == 'xsd:double':
            try:
                float_data = float(field_value)
            except:
                self.errors[error_key] = 'Problem with: ' + field['label'] + '; '
                self.errors[error_key] += '"' + str(field_value) + '" is not a number.'
                valid = False
        elif field['data_type'] == 'xsd:date':
            try:
                date_obj = parse(field_value)
            except:
                self.errors[error_key] = 'Problem with: ' + field['label'] + '; '
                self.errors[error_key] += '"' + str(field_value) + '" is not a yyyy-mm-dd date.'
                valid = False
        return valid

    def update_required_make_data(self, item_man, required_make_data):
        """ updates items based on required make data
            we don't need to have these data complete if
            the item already exists.
            Required fields get some special handling
            We don't update with the other (not required) fields
            NOTE: the required fields list can be empty without an error
            since this is for update only, not creation
        """
        for req_field in required_make_data:
            if req_field['predicate_uuid'] == 'oc-gen:label':
                item_man.label = req_field['value']
                item_man.save()
            elif req_field['predicate_uuid'] == 'oc-gen:content':
                # string content, as in for documents
                content = req_field['value']
                if item_man.item_type == 'documents':
                    # save the content to the document
                    try:
                        doc = OCdocument.objects.get(uuid=item_man.uuid)
                    except OCdocument.DoesNotExist:
                        doc = OCdocument()
                        doc.uuid = item_man.uuid
                        doc.project_uuid = item_man.project_uuid
                        doc.source_id = item_man.source_id
                    doc.content = content
                    doc.save()
            elif req_field['predicate_uuid'] == 'oc-gen:contained-in':
                context_uuid = req_field['value']
                if item_man.item_type == 'subjects':
                    self.save_contained_subject(content_uuid, item_man)
            elif req_field['predicate_uuid'] == 'oc-gen:class_uri':
                item_man.class_uri = req_field['value']
                item_man.save()

    def create_item(self, required_make_data):
        """ creates an item based on required data """
        if self.create_ok:
            # we've got the required data to make the item
            label = False
            context_uuid = False
            content = False
            class_uri = ''
            for req_field in required_make_data:
                if req_field['predicate_uuid'] == 'oc-gen:label':
                    label = req_field['value']
                elif req_field['predicate_uuid'] == 'oc-gen:content':
                    content = req_field['value']
                elif req_field['predicate_uuid'] == 'oc-gen:contained-in':
                    context_uuid = req_field['value']
                elif req_field['predicate_uuid'] == 'oc-gen:class_uri':
                    class_uri = req_field['value']
            item_man = Manifest()
            item_man.uuid = self.edit_uuid
            item_man.project_uuid = self.project_uuid
            item_man.source_id = self.make_source_id()
            item_man.item_type = self.item_type
            item_man.repo = ''
            item_man.class_uri = class_uri
            item_man.label = label
            item_man.des_predicate_uuid = ''
            item_man.views = 0
            item_man.save()
            if context_uuid is not False \
               and self.item_type == 'subjects':
                self.save_contained_subject(context_uuid, item_man)
            if content is not False \
               and self.item_type == 'documents':
                doc = OCdocument()
                doc.uuid = item_man.uuid
                doc.project_uuid = item_man.project_uuid
                doc.source_id = item_man.source_id
                doc.content = content
                doc.save()
        else:
            item_man = False
        return item_man

    def save_contained_subject(self, context_uuid, item_man):
        """ create a containment relationship and a subject item """
        try:
            parent = Manifest.objects.get(uuid=context_uuid)
        except Manifest.DoesNotExist:
            parent = False
            self.ok = False
            self.errors['context_uuid'] = 'The parent context: ' + str(context_uuid) + ' does not exist.'
        if parent is not False:
            if parent.item_type == 'subjects' \
               and item_man.item_type == 'subjects':
                # the parent context exists, so we can create a containment relationship with it.
                # first delete any existing containment relations
                Assertion.objects\
                         .filter(predicate_uuid=Assertion.PREDICATES_CONTAINS,
                                 object_uuid=item_man.uuid)\
                         .delete()
                # now create the new containment assertion
                con_ass = Assertion()
                con_ass.uuid = parent.uuid
                con_ass.subject_type = parent.item_type
                con_ass.project_uuid = self.project_uuid
                con_ass.source_id = self.make_source_id()
                con_ass.obs_node = self.contain_obs_node
                con_ass.obs_num = self.contain_obs_num
                con_ass.sort = self.contain_sort
                con_ass.visibility = self.visibility
                con_ass.predicate_uuid = Assertion.PREDICATES_CONTAINS
                con_ass.object_uuid = item_man.uuid
                con_ass.object_type = item_man.item_type
                con_ass.save()
                # now make or update the subject record with context path for this item
                sg = SubjectGeneration()
                sq.generate_save_context_path_from_uuid(item_man.uuid)
            else:
                self.ok = False
                self.errors['context'] = 'Parent context ' + parent.label + ' (' + parent.uuid + ') is: '
                self.errors['context'] += parent.item_type + ', and '
                self.errors['context'] += 'child item ' + item_man.label + ' (' + item_man.uuid + ') is: '
                self.errors['context'] += item_man.item_type + '. Both need to be "subjects" items.'

    def get_required_make_data(self, field_data):
        """ gets data for required fields """
        required_make_data = [];
        missing_required = False
        for fgroup in self.profile_obj['fgroups']:
            for field in fgroup['fields']:
                if field['oc_required']:
                    missing_data = True
                    if field['id'] in field_data:
                        if len(field_data[field['id']]) > 0:
                            # field data comes in a list.
                            # required fields can only have 1 value, so use the first
                            act_field_data = field_data[field['id']][0]
                            if len(act_field_data) > 0:
                                # we have the required data!
                                missing_data = False
                                field['value'] = act_field_data
                                required_make_data.append(field)
                    if missing_data:
                        missing_required = True
                        self.errors[field['predicate_uuid']] = 'Missing required data for: ' + field['label']
        if missing_required is False:
            self.create_ok = True
        else:
            self.create_ok = False
        return required_make_data

    def make_source_id(self):
        """ makes a source id based on the profile_uuid """
        return 'profile:' + self.profile_uuid
