import json
import time
import uuid as GenUUID
from django.db import models
from django.db.models import Q, Count
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.edit.inputs.profiles.models import InputProfile
from opencontext_py.apps.edit.inputs.fieldgroups.models import InputFieldGroup
from opencontext_py.apps.edit.inputs.inputrelations.models import InputRelation
from opencontext_py.apps.edit.inputs.inputfields.models import InputField
from opencontext_py.apps.edit.inputs.rules.models import InputRule


class ManageInputField():
    """ This class contains methods
        manage creation, edits, and deletion of field groups
    """

    def __init__(self):
        self.errors = {}
        self.profile_uuid = False
        self.project_uuid = False
        self.fgroup_uuid = False
        self.response = False
        self.field_obj = None

    def get_field(self, field_uuid):
        """ Get the field object, if it exists
            if it doesn't exist, return false
        """
        if self.field_obj is None:
            try:
                inp_obj = InputField.objects.get(uuid=field_uuid)
                self.profile_uuid = inp_obj.profile_uuid
                self.project_uuid = inp_obj.project_uuid
                self.fgroup_uuid = inp_obj.fgroup_uuid
            except InputField.DoesNotExist:
                inp_obj = False
            self.field_obj = inp_obj
        else:
            inp_obj = self.field_obj
        return inp_obj

    def create_update_from_post(self, post, field_uuid=False):
        """ Creates or updates an input field from posted data
        """
        ok = True
        sort_val = 0
        note = ''
        action = ''
        if 'sort' in post:
            try:
                sort_val = int(float(post['sort']))
            except:
                sort_val = self.make_default_sort_val(self.profile_uuid)
        if 'label' in post:
            label = post['label'].strip()
        else:
            label = ''
        if 'note' in post:
            data_note = post['note'].strip()
        else:
            data_note = ''
        predicate_uuid = False
        if 'predicate_uuid' in post:
            predicate_uuid = post['predicate_uuid'].strip()
            # check first to see if the predicate is in the list of required fields
            if predicate_uuid not in InputField.PREDICATE_ITEMS:
                # check to make sure the predicate actually exists
                try:
                    pred_man = Manifest.objects.get(uuid=predicate_uuid)
                except Manifest.DoesNotExist:
                    # we have a problem with the predicate
                    pred_man = False
                    ok = False
                    self.errors['predicate_uuid'] = 'predicate_uuid: ' + predicate_uuid + ' not found.'
                    note = self.errors['predicate_uuid']
                if pred_man is not False:
                    if pred_man.item_type != 'predicates':
                        pred_man = False
                        ok = False
                        self.errors['predicate_uuid'] = 'predicate_uuid: ' + predicate_uuid + ' is the wrong item_type.'
                        note = self.errors['predicate_uuid']
        validaton_json = self.make_validation_json_from_post(post)
        if ok:
            if field_uuid is False:
                label = self.check_make_valid_label(label)
                action = 'create-input-field'
                note = ' field created.'
                uuid = GenUUID.uuid4()
                field_uuid = str(uuid)
                inp_field = InputField()
                inp_field.uuid = field_uuid
                inp_field.project_uuid = self.project_uuid
                inp_field.profile_uuid = self.profile_uuid
                inp_field.fgroup_uuid = self.fgroup_uuid
                inp_field.predicate_uuid = predicate_uuid
                note = ' created.'
            else:
                action = 'update-input-field'
                inp_field = self.get_field(field_uuid)
                note = ' updated.'
            if inp_field is False:
                label = field_uuid + ' not found'
                note = 'Input Field ' + field_uuid + ' does not exist'
            else:
                if label != inp_field.label:
                    # the user is updating the item label
                    # so validate it
                    label = self.check_make_valid_label(label)
                inp_field.sort = sort_val
                inp_field.label = label
                inp_field.note = data_note
                inp_field.predicate_uuid = predicate_uuid
                inp_field.validation = validaton_json
                inp_field.save()
                inp_check = InputField.objects.get(uuid=field_uuid)
                note = 'Input Field "' + label + '" (' + field_uuid + ')' + note
        self.response = {'action': action,
                         'ok': ok,
                         'change': {'uuid': field_uuid,
                                    'label': label,
                                    'note': note}}
        return self.response

    def make_validation_json_from_post(self, post):
        """ makes validation json from post data """
        validation = {}
        if 'min' in post:
            validation['min'] = post['min']
        if 'max' in post:
            validation['max'] = post['max']
        validation_json = json.dumps(validation,
                                     indent=4,
                                     ensure_ascii=False)
        return validation_json

    def delete(self, field_uuid):
        """ Deletes a field a field
        """
        sub_rules = InputRelation.objects\
                                 .filter(subject_type='rules',
                                         object_uuid=field_uuid)
        for rel_rule in sub_rules:
            # delete the subject related rule
            InputRule.objects\
                     .filter(uuid=rel_rule.subject_uuid)\
                     .delete()
        obj_rules = InputRelation.objects\
                                 .filter(object_type='rules',
                                         subject_uuid=field_uuid)
        for rel_rule in obj_rules:
            # delete the object related rule
            InputRule.objects\
                     .filter(uuid=rel_rule.object_uuid)\
                     .delete()
        # now delete relations for these fields
        InputRelation.objects\
                     .filter(subject_uuid=field_uuid)\
                     .delete()
        InputRelation.objects\
                     .filter(object_uuid=field_uuid)\
                     .delete()
        inp_obj = self.get_field(field_uuid)
        if inp_obj is not False:
            ok = True
            label = inp_obj.label
            note = 'Deleted Field: "' + label + '" (' + field_uuid + ')'
            try:
                inp_obj.delete()
            except:
                pass
        else:
            ok = False
            label = field_uuid + ' not found'
            note = label
        self.response = {'action': 'delete-input-field',
                         'ok': ok,
                         'change': {'uuid': field_uuid,
                                    'label': label,
                                    'note': note}}
        return self.response

    def check_make_valid_label(self, label, attempt=1):
        """ Checks to see we don't use the same label
            for a field group in a given
            profile
        """
        if len(label) < 1:
            label = 'Unamed data entry profile'
        if attempt > 1:
            label_check = label + ' [' + str(attempt) + ']'
        else:
            label_check = label
        imp_labs = InputFieldGroup.objects\
                                  .filter(profile_uuid=self.profile_uuid,
                                          label=label_check)
        if len(imp_labs) > 0 and attempt <= 20:
            # we have the same label
            label = self.check_make_valid_label(label,
                                                attempt + 1)
        else:
            label = label_check
        return label

    def make_default_sort_val(self, fgroup_uuid):
        """
        makes a default sort value for a field group
        """
        sort_vals = [0]
        fs = InputField.objects\
                       .filter(fgroup_uuid=fgroup_uuid)
        for f in fs:
            sort_vals.append(f.sort)
        return max(sort_vals) + 1
