import re
import json
import time
import datetime
from dateutil.parser import parse
import uuid as GenUUID
from django.db import models
from django.db.models import Q, Count
from django.core.cache import caches
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.edit.inputs.profiles.models import InputProfile
from opencontext_py.apps.edit.inputs.fieldgroups.models import InputFieldGroup
from opencontext_py.apps.edit.inputs.inputrelations.models import InputRelation
from opencontext_py.apps.edit.inputs.inputfields.models import InputField
from opencontext_py.apps.edit.inputs.rules.models import InputRule
from opencontext_py.apps.edit.items.itemassertion import ItemAssertion
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
from opencontext_py.apps.indexer.reindex import SolrReIndex


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
        self.solr_reindex_uuids = []

    def test(self, field_data):
        output = {'field_data': field_data}
        output['required'] = self.get_required_make_data(field_data)
        output['ok'] = False
        return output

    def create_update(self, field_data):
        """ creates or updates an item with post data """
        # first check to see if the item exists
        item_type = None
        label = None
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
        if isinstance(field_data, dict):
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
                item_type = item_man.item_type
                # the act_sub_field below is a field from field_data
                # submitted by the user
                for sub_field_key, act_sub_field in field_data.items():
                    self.profile_field_update(item_man, sub_field_key, act_sub_field)
                if self.do_solr_index:
                    if item_man.uuid not in self.solr_reindex_uuids:
                        self.solr_reindex_uuids.append(item_man.uuid)
                    sri = SolrReIndex()
                    num_reindexed = sri.reindex_uuids(self.solr_reindex_uuids)
                    note += ' Indexed ' + str(num_reindexed) + ' items.'
            else:
                self.ok = False
                label = 'No item'
                note += '.. FAILED!'
        else:
            self.ok = False
            label = 'No item'
            note += '.. "field_data" needs to be a dictionary object (parsed from JSON)'
        if self.ok:
            # now clear the cache a change was made
            self.clear_caches()
        self.response = {'action': action,
                         'ok': self.ok,
                         'change': {'uuid': self.edit_uuid,
                                    'item_type': item_type,
                                    'label': label,
                                    'note': note}}
        return self.response

    def profile_field_update(self, item_man, sub_field_key, act_sub_field):
        """ lookup the object for the profile's input field
            based on the field_uuid

            Only returns a field that is NOT
            required by open context,
            since those get special handling
        """
        # field_uuid is the field identifier from the data
        # submitted by the user
        field_uuid = act_sub_field['field_uuid']
        for fgroup in self.profile_obj['fgroups']:
            obs_num = fgroup['obs_num']
            for field in fgroup['fields']:
                if field['oc_required'] is False \
                   and field['id'] == field_uuid:
                    if 'obs_num' not in act_sub_field:
                        act_sub_field['obs_num'] = obs_num
                    # we've found the field!
                    # first delete existing uses of this field
                    item_ass = ItemAssertion()
                    item_ass.source_id = item_man.source_id
                    add_edit_field_data = {sub_field_key: act_sub_field}
                    item_ass.add_edit_assertions(add_edit_field_data, item_man)
                        

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
                if item_man.item_type == 'subjects':
                    subj_gen = SubjectGeneration()
                    subj_gen.generate_save_context_path_from_uuid(item_man.uuid)
                # now get uuids for solr reindexing, including child items impacted by the changes
                self.collect_solr_reindex_uuids(item_man.uuid)
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
                # now get uuids for solr reindexing, including child items impacted by the changes
                self.collect_solr_reindex_uuids(item_man.uuid)
            elif req_field['predicate_uuid'] == 'oc-gen:subjects-link':
                subject_uuid = req_field['value']
                self.save_subject_link(subject_uuid, item_man)
                # now get uuids for solr reindexing, including child items impacted by the changes
                self.collect_solr_reindex_uuids(item_man.uuid)
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
            subject_uuid = False
            for req_field in required_make_data:
                if req_field['predicate_uuid'] == 'oc-gen:label':
                    label = req_field['value']
                elif req_field['predicate_uuid'] == 'oc-gen:content':
                    content = req_field['value']
                elif req_field['predicate_uuid'] == 'oc-gen:contained-in':
                    context_uuid = req_field['value']
                elif req_field['predicate_uuid'] == 'oc-gen:class_uri':
                    class_uri = req_field['value']
                elif req_field['predicate_uuid'] == 'oc-gen:subjects-link':
                    subject_uuid = req_field['value']
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
            if subject_uuid is not False:
                self.save_subject_link(subject_uuid, item_man)
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

    def save_subject_link(self, subject_uuid, item_man):
        """ create a containment relationship and a subject item """
        try:
            l_subject = Manifest.objects.get(uuid=subject_uuid)
        except Manifest.DoesNotExist:
            l_subject = False
            self.ok = False
            self.errors['subject_uuid'] = 'The linked subject (location or object): '
            self.errors['subject_uuid'] += str(subject_uuid) + ' does not exist.'
        if l_subject is not False:
            if l_subject.item_type == 'subjects':
                # the parent context exists, so we can create a containment relationship with it.
                # first delete any existing containment relations
                Assertion.objects\
                         .filter(predicate_uuid=Assertion.PREDICATES_LINK,
                                 object_uuid=item_man.uuid)\
                         .delete()
                # now create the new containment assertion
                subl_ass = Assertion()
                subl_ass.uuid = l_subject.uuid
                subl_ass.subject_type = l_subject.item_type
                subl_ass.project_uuid = self.project_uuid
                subl_ass.source_id = self.make_source_id()
                subl_ass.obs_node = '#obs-1'
                subl_ass.obs_num = 1
                subl_ass.sort = 1
                subl_ass.visibility = self.visibility
                subl_ass.predicate_uuid = Assertion.PREDICATES_LINK
                subl_ass.object_uuid = item_man.uuid
                subl_ass.object_type = item_man.item_type
                subl_ass.save()
            else:
                self.ok = False
                self.errors['context'] = 'Linked Subject ' + l_subject.label
                self.errors['context'] += ' (' + l_subject.uuid + ') is: '
                self.errors['context'] += l_subject.item_type
                self.errors['context'] += '. It needs to be a "subjects" item.'

    def get_required_make_data(self, field_data):
        """ gets data for required fields """
        required_make_data = [];
        missing_required = False
        for fgroup in self.profile_obj['fgroups']:
            for field in fgroup['fields']:
                if field['oc_required']:
                    missing_data = True
                    # in the profile dict object, the field['id']
                    # is the field's UUID
                    required_field_uuid = field['id']
                    # the act_sub_field below is a field from field_data
                    # submitted by the user
                    for sub_field_key, act_sub_field in field_data.items():
                        if act_sub_field['field_uuid'] == required_field_uuid:
                            # we have matching required_field_uuid with field
                            # data submitted by the user
                            if len(act_sub_field['values']) > 0:
                                # field data comes in a list.
                                # required fields can only have 1 value, so use the first
                                act_sub_value_obj = act_sub_field['values'][0] 
                                if field['predicate_uuid'] == 'oc-gen:class_uri':
                                    # check to make sure the class_uri is valid
                                    # since this is an ID field, get the value from the ID
                                    act_value = act_sub_value_obj['id']
                                    man_class = ManifestClasses()
                                    if self.item_type == 'subjects':
                                        man_class.allow_blank = False
                                    class_uri = man_class.validate_class_uri(act_value)
                                    if class_uri is not False:
                                        missing_data = False
                                        field['value'] = class_uri
                                        required_make_data.append(field)
                                    else:
                                        self.ok = False
                                        self.errors[act_sub_field['predicate_uuid']] = 'Cannot find "' + str(act_field_data)
                                        self.errors[act_sub_field['predicate_uuid']] += '" for ' + field['label']
                                elif field['predicate_uuid'] == 'oc-gen:contained-in':
                                    # since this is an ID field, get the value from the ID
                                    act_value = act_sub_value_obj['id']
                                    missing_data = False
                                    field['value'] = act_value
                                    required_make_data.append(field)
                                elif field['predicate_uuid'] == 'oc-gen:label':
                                    # since this is an string field, get the value from the literal
                                    act_value = act_sub_value_obj['literal']
                                    missing_data = False
                                    field['value'] = act_value
                                    required_make_data.append(field)
                                else:
                                    # we don't know if it is an ID or literal, so use the
                                    # non-null value as the value
                                    if act_sub_value_obj['id'] is not None:
                                        act_value = act_sub_value_obj['id']
                                    else:
                                        act_value = act_sub_value_obj['literal']
                                    missing_data = False
                                    field['value'] = act_value
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

    def collect_solr_reindex_uuids(self, uuid):
        """ collects uuids for solr to reindex """
        sri = SolrReIndex()
        uuids = sri.get_related_uuids(uuid)
        for solr_uuid in uuids:
            if solr_uuid not in self.solr_reindex_uuids:
                self.solr_reindex_uuids.append(solr_uuid)
        return self.solr_reindex_uuids

    def make_source_id(self):
        """ makes a source id based on the profile_uuid """
        return 'profile:' + self.profile_uuid

    def clear_caches(self):
        """ clears all the caches """
        cache = caches['redis']
        cache.clear()
        cache = caches['default']
        cache.clear()
