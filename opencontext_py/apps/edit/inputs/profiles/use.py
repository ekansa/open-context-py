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
from opencontext_py.apps.ocitems.manifest.classes import ManifestClasses
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.indexer.crawler import Crawler


class InputProfileUse():
    """ This class contains methods
        to assist in manual data entry for a project
    """

    def __init__(self):
        self.errors = {}
        self.ok = True
        self.new_item = False
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
        self.do_solr_index = True

    def test(self, field_data):
        output = {'field_data': field_data}
        output['required'] = self.get_required_make_data(field_data)
        output['ok'] = False
        return output

    def create_update(self, field_data):
        """ creates or updates an item with post data """
        # first check to see if the item exists
        try:
            item_man = Manifest.objects.get(uuid=self.edit_uuid)
            action = 'update-profle-item'
            note = 'Item found, updating.'
            self.new_item = False
        except Manifest.DoesNotExist:
            item_man = False
            action = 'create-profle-item'
            note = 'Item not found, creating.'
            self.new_item = True
        # now collect the required field data
        required_make_data = self.get_required_make_data(field_data)
        if item_man is not False:
            # we've found a record for this item, so we can
            # update any of the required fields.
            self.update_required_make_data(item_man, required_make_data)
        else:
            item_man = self.create_item(required_make_data)
        if item_man is not False:
            label = item_man.label
            for field_uuid, field_values in field_data.items():
                self.profile_field_update(item_man, field_uuid, field_values)
            if self.do_solr_index:
                crawler = Crawler()
                crawler.index_single_document(item_man.uuid)
        else:
            self.ok = False
            label = 'No item'
            note += '.. FAILED!'
        self.response = {'action': action,
                         'ok': self.ok,
                         'change': {'uuid': self.edit_uuid,
                                    'label': label,
                                    'note': note}}
        return self.response

    def profile_field_update(self, item_man, field_uuid, field_values):
        """ lookup the object for the profile's input field
            based on the field_uuid

            Only returns a field that is NOT
            required by open context,
            since those get special handling
        """
        for fgroup in self.profile_obj['fgroups']:
            obs_num = fgroup['obs_num']
            for field in fgroup['fields']:
                if field['oc_required'] is False \
                   and field['id'] == field_uuid:
                    # we've found the field!
                    # first delete existing uses of this field
                    Assertion.objects\
                             .filter(uuid=item_man.uuid,
                                     predicate_uuid=field['predicate_uuid'])\
                             .delete()
                    value_index = 0
                    for field_value in field_values:
                        self.validate_save_field_value(item_man,
                                                       obs_num,
                                                       field,
                                                       field_value,
                                                       value_index)
                        value_index += 1

    def validate_save_field_value(self,
                                  item_man,
                                  obs_num,
                                  field,
                                  field_value,
                                  value_index):
        """ Valididates a field value for a field and
            then saves it to the database if valid
        """
        error_key = field['id'] + '-' + str(value_index)
        valid = True
        object_uuid = None
        object_type = field['data_type']
        data_num = None
        data_date = None
        if field['data_type'] == 'xsd:string':
            str_man = StringManagement()
            str_man.project_uuid = item_man.project_uuid
            str_man.source_id = item_man.source_id
            object_uuid = str_man.get_make_string(str(field_value))
        elif field['data_type'] == 'id':
            # first check is to see if the field_value exists in the manifest
            try:
                val_man = Manifest.objects.get(uuid=field_value)
            except Manifest.DoesNotExist:
                valid = False
                self.errors[error_key] = 'Problem with: ' + field['label'] + '; cannot find: ' + str(field_value)
            if valid:
                # OK, the field_value is an ID in the manifest
                # so let's check to make sure it is OK to associate
                object_type = val_man.item_type
                object_uuid = val_man.uuid
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
        elif field['data_type'] == 'xsd:boolean':
            data_num = self.validate_convert_boolean(field_value)
            if t_f_data is None:
                self.errors[error_key] = 'Problem with: ' + field['label'] + '; '
                self.errors[error_key] += '"' + str(field_value) + '" is not a recognized boolean (T/F) value.'
                valid = False
        elif field['data_type'] == 'xsd:integer':
            try:
                data_num = int(float(field_value))
            except:
                self.errors[error_key] = 'Problem with: ' + field['label'] + '; '
                self.errors[error_key] += '"' + str(field_value) + '" is not an integer.'
                valid = False
        elif field['data_type'] == 'xsd:double':
            try:
                data_num = float(field_value)
            except:
                self.errors[error_key] = 'Problem with: ' + field['label'] + '; '
                self.errors[error_key] += '"' + str(field_value) + '" is not a number.'
                valid = False
        elif field['data_type'] == 'xsd:date':
            try:
                data_date = parse(field_value)
            except:
                self.errors[error_key] = 'Problem with: ' + field['label'] + '; '
                self.errors[error_key] += '"' + str(field_value) + '" is not a yyyy-mm-dd date.'
                valid = False
        if valid:
            # we've validated the field_value data. Now to save the assertions!
            new_ass = Assertion()
            new_ass.uuid = item_man.uuid
            new_ass.subject_type = item_man.item_type
            new_ass.project_uuid = item_man.project_uuid
            new_ass.source_id = item_man.source_id
            new_ass.obs_node = '#obs-' + str(obs_num)
            new_ass.obs_num = obs_num
            new_ass.sort = field['sort'] + (value_index / 100)
            new_ass.visibility = 1
            new_ass.predicate_uuid = field['predicate_uuid']
            new_ass.object_type = object_type
            if object_uuid is not None:
                new_ass.object_uuid = object_uuid
            if data_num is not None:
                new_ass.data_num = data_num
            if data_date is not None:
                new_ass.data_date = data_date
            new_ass.save()
        else:
            if self.new_item is False:
                # we're updating an item and
                # encoutered some wrong data. indicate error
                self.ok = False

    def validate_convert_boolean(self, field_value):
        """ Validates boolean values for a record
            returns a boolean 0 or 1 if
        """
        output = None
        record = str(field_value).lower()
        booleans = {'n': 0,
                    'no': 0,
                    'none': 0,
                    'absent': 0,
                    'a': 0,
                    'false': 0,
                    'f': 0,
                    '0': 0,
                    'y': 1,
                    'yes': 1,
                    'present': 1,
                    'p': 1,
                    'true': 1,
                    't': 1}
        if record in booleans:
            output = booleans[record]
        return output

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
                    self.save_contained_subject(context_uuid, item_man)
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
        if self.create_ok:
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
                subgen = SubjectGeneration()
                subgen.generate_save_context_path_from_uuid(item_man.uuid)
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
                                if field['predicate_uuid'] == 'oc-gen:class_uri':
                                    # check to make sure the class_uri is valid
                                    man_class = ManifestClasses()
                                    if self.item_type == 'subjects':
                                        man_class.allow_blank = False
                                    class_uri = man_class.validate_class_uri(act_field_data)
                                    if class_uri is not False:
                                        missing_data = False
                                        field['value'] = class_uri
                                        required_make_data.append(field)
                                    else:
                                        self.ok = False
                                        self.errors[field['predicate_uuid']] = 'Cannot find "' + str(act_field_data)
                                        self.errors[field['predicate_uuid']] += '" for ' + field['label']
                                else:
                                    missing_data = False
                                    field['value'] = act_field_data
                                    required_make_data.append(field)
                    if missing_data:
                        missing_required = True
                        if field['predicate_uuid'] not in self.errors\
                           and self.new_item:
                            # only add the error if it's not present, since it maybe about a
                            # bad class
                            self.errors[field['predicate_uuid']] = 'Missing required data for: ' + field['label']
        if missing_required is False:
            self.create_ok = True
        else:
            self.create_ok = False
        return required_make_data

    def make_source_id(self):
        """ makes a source id based on the profile_uuid """
        return 'profile:' + self.profile_uuid
