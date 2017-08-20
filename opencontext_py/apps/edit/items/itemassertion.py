import time
import datetime
from dateutil.parser import parse
import uuid as GenUUID
from lxml import etree
import lxml.html
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.cache import caches
from opencontext_py.libs.languages import Languages
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.strings.manage import StringManagement
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ldata.linkentities.models import LinkEntityGeneration
from opencontext_py.apps.edit.items.itembasic import ItemBasicEdit
from opencontext_py.apps.edit.versioning.deletion import DeletionRevision


class ItemAssertion():
    """ This class contains methods
        creating, editing, and deleting
        assertions
    """

    def __init__(self):
        self.hash_id = False
        self.uuid = False
        self.project_uuid = False
        self.item_type = False
        self.source_id = False
        self.obs_node = False
        self.obs_num = 1
        self.sort = 1
        self.note_sort = 1000  # default to last
        self.errors = {}
        self.manifest_items = {}
        self.predicate_items = {}
        self.user_id = False
        self.ok = True
        self.response = False
        self.global_predicates = {
            Assertion.PREDICATES_LINK: {'data_type': 'id',
                                        'label': 'Link'},
            Assertion.PREDICATES_NOTE: {'data_type': 'xsd:string',
                                        'label': 'Has note'},
            'skos:note': {'data_type': 'xsd:string',
                          'label': 'Has note'}
        }

    def add_edit_assertions(self, field_data, item_man=False):
        """ adds or edits assertion data """
        additions = LastUpdatedOrderedDict()
        new_data = LastUpdatedOrderedDict()
        self.ok = True
        note = ''
        if item_man is False:
            item_man = self.get_manifest_item(self.uuid)
        if item_man is False:
            self.ok = False
            label = 'Item not found'
            self.errors['uuid'] = 'Cannot find the item for editing assertions: ' + str(self.uuid)
            note = self.errors['uuid']
        else:
            label = item_man.label
            self.uuid = item_man.uuid
            for field_key, field in field_data.items():
                new_field_data = []
                if 'id' in field:
                    field_id = field['id']
                else:
                    field_id = field_key
                if 'predicate_uuid' not in field:
                    self.ok = False
                    self.errors[field_key] = 'Missing a predicate_uuid for the field'
                elif field['predicate_uuid'] == 'oc-gen:label':
                    # special case of updating an item label
                    if 'values' in field:
                        if 'literal' in field['values'][0]:
                            label = field['values'][0]['literal']
                            i_basic = ItemBasicEdit(self.uuid)
                            i_basic.edit_permitted = True
                            resp = i_basic.update_label(label, {})
                            if resp['ok']:
                                self.ok = True
                                additions = []
                                new_data = resp
                                note = 'Item Label updated to ' + label
                elif field['predicate_uuid'] == 'oc-gen:class_uri':
                    # special case of updating an item label
                    if 'values' in field:
                        if 'id' in field['values'][0]:
                            class_uri = field['values'][0]['id']
                            i_basic = ItemBasicEdit(self.uuid)
                            i_basic.edit_permitted = True
                            resp = i_basic.update_class_uri(class_uri)
                            if resp['ok']:
                                self.ok = True
                                additions = []
                                new_data = resp
                                note = 'Item class_uri updated to ' + class_uri
                else:
                    predicate_uuid = field['predicate_uuid']
                    data_type = False
                    pred_label = False
                    if predicate_uuid in self.global_predicates:
                        # a global predicate, so get from dictionary set above
                        data_type = self.global_predicates[predicate_uuid]['data_type']
                        pred_label = self.global_predicates[predicate_uuid]['label']
                    else:
                        # not a global predicate, so look up values
                        data_type = self.get_predicate_data_type(predicate_uuid)
                        pred_man = self.get_manifest_item(predicate_uuid)
                        if data_type is False or pred_man is False:
                            self.ok = False
                            self.errors['uuid'] = 'Cannot find records for predicate_uuid: ' + predicate_uuid
                            note = self.errors['uuid']
                        else:
                            pred_label = pred_man.label
                    if self.ok:
                        if 'label' not in field:
                            field['label'] = pred_label
                        if 'sort' not in field:
                            field['sort'] = self.get_predicate_sort(predicate_uuid)
                        if field['sort'] == 0 and 'draft_sort' in field:
                            try:
                                field['sort'] = int(float(field['draft_sort']))
                            except:
                                field['sort'] = 0
                        if 'replace_all' in field:
                            if field['replace_all']:
                                drev = DeletionRevision()
                                drev.project_uuid = item_man.project_uuid
                                drev.uuid = item_man.uuid
                                drev.item_type = item_man.item_type
                                drev.user_id = self.user_id
                                rev_label = 'Updated ' + item_man.label
                                rev_label += ', field: ' + field['label']
                                del_objs = Assertion.objects\
                                                    .filter(uuid=item_man.uuid,
                                                            obs_num=field['obs_num'],
                                                            predicate_uuid=predicate_uuid)
                                for del_obj in del_objs:
                                    drev.assertion_keys.append(del_obj.hash_id)
                                    del_obj.delete()
                                drev.save_delete_revision(rev_label, '')
                        if 'values' in field:
                            i = 0
                            additions[field_id] = []
                            for field_value_dict in field['values']:
                                i += 1
                                if 'value_num' not in field_value_dict:
                                    value_num = i
                                else:
                                    try:
                                        value_num = int(float(field_value_dict['value_num']))
                                    except:
                                        value_num = i
                                valid = self.validate_save_field_value(item_man,
                                                                       field,
                                                                       field_value_dict,
                                                                       value_num)
                                add_outcome = LastUpdatedOrderedDict()
                                add_outcome['value_num'] = value_num
                                add_outcome['valid'] = valid
                                add_outcome['errors'] = False
                                if valid is False:
                                    self.ok = False
                                    note = 'Validation error in creating an assertion'
                                    add_outcome['errors'] = True
                                    error_key = str(field['id']) + '-' + str(value_num)
                                    if error_key in self.errors:
                                        add_outcome['errors'] = self.errors[error_key]
                                additions[field_id].append(add_outcome)
                        new_field_data = self.get_assertion_values(item_man.uuid,
                                                                   field['obs_num'],
                                                                   field['predicate_uuid'])
                    new_data[field_key] = new_field_data
        if self.ok:
            # now clear the cache a change was made
            self.clear_caches()
        self.response = {'action': 'add-edit-item-assertions',
                         'ok': self.ok,
                         'additions': additions,
                         'data': new_data,
                         'change': {'uuid': self.uuid,
                                    'label': label,
                                    'note': note}}
        return self.response

    def add_edit_containment(self, field_data, item_man=False):
        """ adds or edits containment data """
        pred_uuid = Assertion.PREDICATES_CONTAINS
        self.ok = True
        note = ''
        if item_man is False:
            item_man = self.get_manifest_item(self.uuid)
        if item_man is False:
            self.ok = False
            label = 'Item not found'
            self.errors['uuid'] = 'Cannot find the item for editing assertions: ' + str(self.uuid)
            note = self.errors['uuid']
        else:
            label = item_man.label
            self.uuid = item_man.uuid
            if item_man.item_type != 'subjects':
                self.ok = False
                self.errors['uuid'] = 'Can only add containment to "subjects" items: ' + str(self.uuid)
            else:
                for field_key, field in field_data.items():
                    new_field_data = []
                    if 'id' in field:
                        field_id = field['id']
                    else:
                        field_id = field_key
                    if 'predicate_uuid' not in field:
                        self.ok = False
                        self.errors[field_key] = 'Missing a predicate_uuid for the field'
                    elif field['predicate_uuid'] != 'oc-gen:contained-in':
                        self.ok = False
                        self.errors[field_key] = 'Must have predicate_uuid with "oc-gen:contained-in".'
                    else:
                        parent_uuid = False
                        if 'label' not in field:
                            field['label'] = 'Containment'
                        if 'sort' not in field:
                            field['sort'] = 1
                        if 'values' in field:
                            for field_value_dict in field['values']:
                                if 'id' in field_value_dict:
                                    parent_uuid = field_value_dict['id']
                                    if parent_uuid != 'ROOT':
                                        parent = self.get_manifest_item(parent_uuid)
                                        if parent is not False:
                                            if parent.item_type != 'subjects':
                                                parent_uuid = False
                                                self.ok = False
                                                self.errors[field_key] = 'Parent must be a "subjects" item.'
                                            else:
                                                self.ok = True
                                        else:
                                            parent_uuid = False
                                        if parent_uuid is False:
                                            self.ok = False
                                            note = 'Could not find parent'
                                            self.errors[field_key] = 'Missing the parent_uuid in manifest'
                                else:
                                    self.errors[field_key] = 'Missing a "id" for parent_uuid'
                        if self.ok and parent_uuid is not False:
                            # first delete the old containment relationship
                            drev = DeletionRevision()
                            drev.project_uuid = item_man.project_uuid
                            drev.uuid = item_man.uuid
                            drev.item_type = item_man.item_type
                            drev.user_id = self.user_id
                            rev_label = 'Updated ' + item_man.label
                            rev_label += ', field: ' + field['label']
                            # delete prior containment relationship
                            del_objs = Assertion.objects\
                                                .filter(object_uuid=item_man.uuid,
                                                        predicate_uuid=pred_uuid)
                            for del_obj in del_objs:
                                drev.assertion_keys.append(del_obj.hash_id)
                                del_obj.delete()
                            drev.save_delete_revision(rev_label, '')
                            if parent_uuid != 'ROOT':
                                # now add the new containment relationship
                                new_ass = Assertion()
                                new_ass.uuid = parent_uuid
                                new_ass.subject_type = 'subjects'
                                new_ass.project_uuid = item_man.project_uuid
                                new_ass.source_id = 'web-form'
                                new_ass.obs_node = '#contents-' + str(1)
                                new_ass.obs_num = 1
                                new_ass.sort = 1
                                new_ass.visibility = 1
                                new_ass.predicate_uuid = pred_uuid
                                new_ass.object_type = item_man.item_type
                                new_ass.object_uuid = item_man.uuid
                                try:
                                    new_ass.save()
                                except:
                                    self.ok = False
                                    self.errors[error_key] = 'Same containment assertion '
                                    self.errors[error_key] += 'already exists.'
                            if self.ok:
                                # now change the path information for the Subjects
                                sg = SubjectGeneration()
                                sg.generate_save_context_path_from_uuid(item_man.uuid,
                                                                        True)
        if self.ok:
            # now clear the cache a change was made
            self.clear_caches()
        self.response = {'action': 'add-edit-item-containment',
                         'ok': self.ok,
                         'data': {'parent_uuid': parent_uuid},
                         'change': {'uuid': self.uuid,
                                    'label': label,
                                    'note': note}}
        return self.response

    def add_assertion(self, post_data):
        """ adds an assertion to an item
            based on posted data
        """
        return post_data

    def rank_assertion_value(self, post_data, item_man=False):
        """ adds an assertion to an item
            based on posted data
        """
        self.ok = True
        note = 'Re-rank an assertion'
        new_data = False
        uuid = False
        obs_num = False
        predicate_uuid = False
        if item_man is False:
            item_man = self.get_manifest_item(self.uuid)
        if item_man is False:
            self.ok = False
            label = 'Item not found'
            self.errors['uuid'] = 'Cannot find the item for editing assertions: ' + str(self.uuid)
        else:
            label = item_man.label
        if 'hash_id' in post_data \
           and 'sort_change' in post_data:
            hash_id = post_data['hash_id']
            sort_change = 0
            try:
                sort_change = int(float(post_data['sort_change']))
            except:
                sort_change = 0
                self.ok = False
                note += 'Error, sort_change needs to be an integer value. '
        else:
            self.ok = False
            self.errors['hash_id'] = 'Need a hash_id parameter and a sort_change paramenter to change assertion value sorting'
            note = self.errors['hash_id']
        if self.ok:
            try:
                sort_ass = Assertion.objects.get(hash_id=hash_id)
            except Assertion.DoesNotExist:
                sort_ass = False
                self.ok = False
                self.errors['hash_id'] = 'Cannot find ' + str(hash_id) + ' do sort'
            if sort_ass is not False:
                uuid = sort_ass.uuid
                obs_num = sort_ass.obs_num
                predicate_uuid = sort_ass.predicate_uuid
                rel_asses = Assertion.objects\
                                     .filter(uuid=uuid,
                                             obs_num=obs_num,
                                             predicate_uuid=predicate_uuid)
                max_sort = None
                min_sort = None
                for rel_ass in rel_asses:
                    if rel_ass.sort is None:
                        rel_ass.sort = 0
                    if max_sort is None or rel_ass.sort > max_sort:
                        max_sort = rel_ass.sort
                    if min_sort is None or rel_ass.sort < min_sort:
                        min_sort = rel_ass.sort
                pseudo_sort = 0  # used to make a sort value if none was given
                i = -1
                current_hash_index = False
                for rel_ass in rel_asses:
                    pseudo_sort += .001
                    i += 1
                    if rel_ass.sort is None:
                        rel_ass.sort = 0
                    if max_sort == min_sort \
                       and rel_ass.sort == 0:
                        rel_ass.sort = float(rel_ass.sort) + pseudo_sort
                        rel_ass.save()
                    elif max_sort == min_sort \
                       and rel_ass.sort > 0:
                        rel_ass.sort = float(rel_ass.sort) + pseudo_sort
                        rel_ass.save()
                    if rel_ass.hash_id == hash_id:
                        current_hash_index = i
                if current_hash_index is not False:
                    item_b_index = current_hash_index + sort_change
                    if item_b_index >= 0 and item_b_index < len(rel_asses):
                        rec_a = rel_asses[current_hash_index]
                        rec_b = rel_asses[item_b_index]
                        new_sort_rec_b = float(rec_a.sort)
                        new_sort_rec_a = float(rec_b.sort)
                        if new_sort_rec_a == new_sort_rec_b:
                            # so we don't have exactly the same values
                            new_sort_rec_a += float((float(sort_change) / 1000))
                        rec_a.sort = new_sort_rec_a
                        rec_a.save()
                        rec_b.sort = new_sort_rec_b
                        rec_b.save()
                        ok = True
                        note += 'Assertion value successfully resorted. '
                    else:
                        ok = False
                        note += 'Cannot change sorting, as at limit of the list of objects.'
                        note += ' Current_hash_index: ' + str(current_hash_index)
                        note += ' Exchange with index: ' + str(item_b_index)
                else:
                    ok = False
                    note += 'A truly bizzare something happened. '
            if uuid is not False \
               and obs_num is not False\
               and predicate_uuid is not False:
                new_data = LastUpdatedOrderedDict()
                new_field_data = self.get_assertion_values(uuid,
                                                           obs_num,
                                                           predicate_uuid)
                new_data[post_data['id']] = new_field_data
        if self.ok:
            # now clear the cache a change was made
            self.clear_caches()
        self.response = {'action': 'rank-item-assertion-value',
                         'ok': self.ok,
                         'data': new_data,
                         'change': {'uuid': self.uuid,
                                    'label': label,
                                    'note': note}}
        return self.response

    def delete_assertion(self, post_data, item_man=False):
        """ adds an assertion to an item
            based on posted data
        """
        self.ok = True
        note = 'Delete an assertion'
        new_data = False
        if item_man is False:
            item_man = self.get_manifest_item(self.uuid)
        if item_man is False:
            self.ok = False
            label = 'Item not found'
            self.errors['uuid'] = 'Cannot find the item for editing assertions: ' + str(self.uuid)
        else:
            label = item_man.label
        if 'hash_id' not in post_data:
            self.ok = False
            self.errors['hash_id'] = 'Need a hash_id parameter to delete'
            note = self.errors['hash_id']
        if self.ok:
            hash_id = post_data['hash_id']
            try:
                del_ass = Assertion.objects.get(hash_id=hash_id)
            except Assertion.DoesNotExist:
                del_ass = False
                self.ok = False
                self.errors['hash_id'] = 'Cannot find ' + str(hash_id) + ' do delete'
            if del_ass is not False:
                self.hash_id = hash_id
                del_ass.delete()
            if 'id' in post_data \
               and 'predicate_uuid' in post_data\
               and 'obs_num' in post_data:
                new_data = LastUpdatedOrderedDict()
                new_field_data = self.get_assertion_values(item_man.uuid,
                                                           post_data['obs_num'],
                                                           post_data['predicate_uuid'])
                new_data[post_data['id']] = new_field_data
        if self.ok:
            # now clear the cache a change was made
            self.clear_caches()
        self.response = {'action': 'delete-item-assertion',
                         'ok': self.ok,
                         'data': new_data,
                         'change': {'uuid': self.uuid,
                                    'label': label,
                                    'note': note}}
        return self.response

    def get_predicate_data_type(self, predicate_uuid):
        """ gets a predicate data type """
        pred = self.get_predicate_item(predicate_uuid)
        if pred is not False:
            data_type = pred.data_type
        else:
            data_type = False
        return data_type

    def get_predicate_sort(self, predicate_uuid):
        """ gets a predicate data type """
        pred = self.get_predicate_item(predicate_uuid)
        if pred is not False:
            try:
                sort = float(pred.sort)
            except:
                sort = 0
        else:
            sort = 0
        return sort

    def get_predicate_item(self, predicate_uuid):
        """ gets a predicate item """
        if predicate_uuid not in self.predicate_items:
            try:
                pred = Predicate.objects.get(uuid=predicate_uuid)
            except Predicate.DoesNotExist:
                pred = False
            self.predicate_items[predicate_uuid] = pred
        return self.predicate_items[predicate_uuid]

    def get_manifest_item(self, uuid):
        """ gets the manifest item, if present """
        if uuid not in self.manifest_items:
            try:
                item_man = Manifest.objects.get(uuid=uuid)
            except Manifest.DoesNotExist:
                item_man = False
            self.manifest_items[uuid] = item_man
        else:
            item_man = self.manifest_items[uuid]
        return item_man

    def get_assertion_values(self, uuid, obs_num, predicate_uuid):
        """ gets the current assertion values
            in a format for easy use by
            the item-field.js object
        """
        output = []
        ass_list = Assertion.objects\
                            .filter(uuid=uuid,
                                    obs_num=obs_num,
                                    predicate_uuid=predicate_uuid)
        i = 0
        for ass in ass_list:
            i += 1
            error_key = 'obs-' + str(obs_num) + '-pred-' + predicate_uuid + '-val-' + str(i)
            item = LastUpdatedOrderedDict()
            item['hash_id'] = ass.hash_id
            item['id'] = None
            item['uuid'] = None
            item['slug'] = None
            item['label'] = None
            item['literal'] = None
            item_ok = False
            if any(ass.object_type in item_type for item_type in settings.ITEM_TYPES):
                id_man = self.get_manifest_item(ass.object_uuid)
                if id_man is not False:
                    item_ok = True
                    item['id'] = URImanagement.make_oc_uri(id_man.uuid, id_man.item_type)
                    item['uuid'] = id_man.uuid
                    item['slug'] = id_man.slug
                    item['label'] = id_man.label
                else:
                    self.errors[error_key] = 'Cannot find object_uuid: ' + ass.object_uuid
            elif ass.object_type == 'xsd:string':
                try:
                    act_string = OCstring.objects.get(uuid=ass.object_uuid)
                except OCstring.DoesNotExist:
                    act_string = False
                if act_string is not False:
                    item_ok = True
                    item['uuid'] = act_string.uuid
                    item['literal'] = act_string.content
                else:
                    self.errors[error_key] = 'Cannot find string_uuid: ' + ass.object_uuid
            elif ass.object_type == 'xsd:date':
                item_ok = True
                item['literal'] = ass.data_date.date().isoformat()
            else:
                item_ok = True
                item['literal'] = ass.data_num
            if item_ok:
                output.append(item)
        return output

    def validate_save_field_value(self,
                                  item_man,  # subject manifest object
                                  field,
                                  field_value_dict,
                                  value_num):
        """ Valididates a field value for a field and
            then saves it to the database if valid
        """
        error_key = str(field['id']) + '-' + str(value_num)
        valid = True
        id_val = None
        literal_val = None
        if isinstance(field_value_dict, dict):
            if 'id' in field_value_dict:
                id_val = field_value_dict['id']
            if 'literal' in field_value_dict:
                literal_val = field_value_dict['literal']
        else:
            valid = False
            self.errors[error_key] = 'Value submitted to ' + field['label'] + ' has the wrong format'
        data_type = self.get_predicate_data_type(field['predicate_uuid'])
        object_uuid = None
        object_type = data_type
        data_num = None
        data_date = None
        if field['predicate_uuid'] in self.global_predicates:
            # a global predicate, so get from dictionary set above
            data_type = self.global_predicates[field['predicate_uuid']]['data_type']
        else: 
            pred_man = self.get_manifest_item(field['predicate_uuid'])
            if pred_man is False or data_type is False:
                # could not find a predicate_uuid!!
                valid = False
                self.errors[error_key] = 'Problem with: ' + field['label'] + ' '
                self.errors[error_key] += '(' + field['predicate_uuid'] + ') is not found.'
        if valid:
            # predicate_uuid exists
            str_obj = None
            if data_type == 'xsd:string':
                str_man = StringManagement()
                str_man.project_uuid = item_man.project_uuid
                str_man.source_id = item_man.source_id
                str_obj = str_man.get_make_string(str(literal_val))
                object_uuid = str_obj.uuid
                object_type = data_type
            elif data_type == 'id':
                # first check is to see if the field_value exists in the manifest
                val_man = self.get_manifest_item(id_val)
                if val_man is False:
                    valid = False
                    self.errors[error_key] = 'Problem with: ' + field['label'] + '; cannot find: ' + str(id_val)
                if valid:
                    # OK, the field_value is an ID in the manifest
                    # so let's check to make sure it is OK to associate
                    object_type = val_man.item_type
                    object_uuid = val_man.uuid
                    if val_man.class_uri == 'variable' \
                       and val_man.item_type != 'types':
                        # we've got a variable that does not link to a type!
                        self.errors[error_key] = 'Problem with: ' + field['label'] + '; '
                        self.errors[error_key] += val_man.label + ' (' + val_man.uuid + ') is not a type/category.'
                        valid = False
            elif data_type == 'xsd:boolean':
                data_num = self.validate_convert_boolean(literal_val)
                if t_f_data is None:
                    self.errors[error_key] = 'Problem with: ' + field['label'] + '; '
                    self.errors[error_key] += '"' + str(literal_val) + '" is not a recognized boolean (T/F) value.'
                    valid = False
            elif data_type == 'xsd:integer':
                try:
                    data_num = int(float(literal_val))
                except:
                    self.errors[error_key] = 'Problem with: ' + field['label'] + '; '
                    self.errors[error_key] += '"' + str(literal_val) + '" is not an integer.'
                    valid = False
            elif data_type == 'xsd:double':
                try:
                    data_num = float(literal_val)
                except:
                    self.errors[error_key] = 'Problem with: ' + field['label'] + '; '
                    self.errors[error_key] += '"' + str(literal_val) + '" is not a number.'
                    valid = False
            elif data_type == 'xsd:date':
                try:
                    data_date = parse(literal_val)
                except Exception as e:
                    self.errors[error_key] = 'Problem with: ' + field['label'] + '; '
                    self.errors[error_key] += '"' + str(literal_val) + '" is not a yyyy-mm-dd date'
                    valid = False
            if valid:
                # we've validated the field_value data. Now to save the assertions!
                new_ass = Assertion()
                new_ass.uuid = item_man.uuid
                new_ass.subject_type = item_man.item_type
                new_ass.project_uuid = item_man.project_uuid
                new_ass.source_id = self.source_id
                new_ass.obs_node = '#obs-' + str(field['obs_num'])
                new_ass.obs_num = field['obs_num']
                new_ass.sort = field['sort'] + (value_num / 1000)
                new_ass.visibility = 1
                new_ass.predicate_uuid = field['predicate_uuid']
                new_ass.object_type = object_type
                if object_uuid is not None:
                    new_ass.object_uuid = object_uuid
                if data_num is not None:
                    new_ass.data_num = data_num
                if data_date is not None:
                    new_ass.data_date = data_date
                try:
                    new_ass.save()
                except:
                    valid = False
                    self.errors[error_key] = 'Same assertion for: ' + field['label'] + ' '
                    self.errors[error_key] += 'already exists.'
        return valid

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

    def add_edit_string_translation(self, string_uuid, post_data):
        """ adds or edits assertion data """
        self.ok = True
        note = ''
        if 'language' in post_data:
            language = post_data['language']
        else:
            self.ok = False
            language = None
            error = 'POST data needs a "language" parameter'
            self.errors['language'] = error
            note += error
        if 'script' in post_data:
            script = post_data['script']
        else:
            script = None
        if 'content' in post_data:
            trans_text = post_data['content']
        else:
            self.ok = False
            error = 'POST data needs a "content" parameter'
            self.errors['content'] = error
            note += error
        if self.ok:
            self.ok = self.add_translation(string_uuid,
                                           language,
                                           script,
                                           trans_text)
            if self.ok is False:
                error = 'Could not find string content to edit for "' + str(string_uuid) + '".'
                self.errors['uuid'] = error
                note += error
        if self.ok:
            # now clear the cache a change was made
            self.clear_caches()
        self.response = {'action': 'add-edit-string-translation',
                         'ok': self.ok,
                         'change': {'string_uuid': string_uuid,
                                    'language': language,
                                    'script': script,
                                    'note': note}}
        return self.response

    def add_translation(self,
                        string_uuid,
                        language,
                        script,
                        trans_text
                        ):
        """ adds translation to a string
        """
        ok = False
        trans_text = str(trans_text)
        trans_text = trans_text.strip()
        try:
            str_obj = OCstring.objects.get(uuid=string_uuid)
        except OCstring.DoesNotExist:
            str_obj = False
        if str_obj is not False:
            # found the string object
            if language != Languages.DEFAULT_LANGUAGE:
                # editing in another language, so save to localization object
                lan_obj = Languages()
                key = lan_obj.get_language_script_key(language, script)
                str_obj.localized_json = lan_obj.modify_localization_json(str_obj.localized_json,
                                                                          key,
                                                                          trans_text)
                str_obj.save()
            else:
                str_obj.content = trans_text
                str_obj.save()
            ok = True
        return ok

    def add_description_note(self, note):
        """ adds a description note about a new item
        """
        # first make sure the has-note predicate exists
        self.create_note_entity()
        note = str(note)
        if len(note) > 1:
            # save the note as a string
            str_man = StringManagement()
            str_man.project_uuid = self.project_uuid
            str_man.source_id = self.source_id
            str_obj = str_man.get_make_string(str(note))
            # now make the assertion
            new_ass = Assertion()
            new_ass.uuid = self.uuid
            new_ass.subject_type = self.item_type
            new_ass.project_uuid = self.project_uuid
            new_ass.source_id = self.source_id
            if self.obs_node is False:
                new_ass.obs_node = '#obs-' + str(self.obs_num)
            else:
                new_ass.obs_node = self.obs_node
            new_ass.obs_num = self.obs_num
            new_ass.sort = self.note_sort
            new_ass.visibility = 1
            new_ass.predicate_uuid = Assertion.PREDICATES_NOTE
            new_ass.object_type = 'xsd:string'
            new_ass.object_uuid = str_obj.uuid
            new_ass.save()
            # now clear the cache a change was made
            self.clear_caches()

    def create_note_entity(self):
        """ creates a note predicate entity if it does not yet
            exist
        """
        leg = LinkEntityGeneration()
        leg.check_add_note_pred()

    def clear_caches(self):
        """ clears all the caches """
        cache = caches['redis']
        cache.clear()
        cache = caches['default']
        cache.clear()
