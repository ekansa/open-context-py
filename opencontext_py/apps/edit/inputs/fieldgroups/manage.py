import json
import time
import uuid as GenUUID
from django.db import models
from django.db.models import Q, Count
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.edit.inputs.profiles.models import InputProfile
from opencontext_py.apps.edit.inputs.fieldgroups.models import InputFieldGroup
from opencontext_py.apps.edit.inputs.inputrelations.models import InputRelation
from opencontext_py.apps.edit.inputs.inputfields.models import InputField
from opencontext_py.apps.edit.inputs.rules.models import InputRule


class ManageInputFieldGroup():
    """ This class contains methods
        manage creation, edits, and deletion of field groups
    """

    def __init__(self):
        self.errors = {}
        self.profile_uuid = False
        self.project_uuid = False
        self.response = False
        self.field_group_obj = None

    def get_field_group(self, fgroup_uuid):
        """ Get the field group object, if it exists
            if it doesn't exist, return false
        """
        if self.field_group_obj is None:
            try:
                inp_obj = InputFieldGroup.objects.get(uuid=fgroup_uuid)
                self.profile_uuid = inp_obj.profile_uuid
                self.project_uuid = inp_obj.project_uuid
            except InputFieldGroup.DoesNotExist:
                inp_obj = False
            self.field_group_obj = inp_obj
        else:
            inp_obj = self.field_group_obj
        return inp_obj

    def create_update_from_post(self, post, fgroup_uuid=False):
        """ Creates or updates an input field group from posted data
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
        if 'visibility' in post:
            visibility = post['visibility']
        else:
            visibility = 'Not given'
        if 'label' in post:
            label = post['label'].strip()
        else:
            label = ''
        if 'note' in post:
            data_note = post['note'].strip()
        else:
            data_note = ''
        if ok:
            if fgroup_uuid is False:
                label = self.check_make_valid_label(label)
                action = 'create-input-field-group'
                note = 'Field Group created.'
                uuid = GenUUID.uuid4()
                fgroup_uuid = str(uuid)
                inp_obj = InputFieldGroup()
                inp_obj.uuid = fgroup_uuid
                inp_obj.project_uuid = self.project_uuid
                inp_obj.profile_uuid = self.profile_uuid
                note = ' created.'
            else:
                action = 'update-input-field-group'
                inp_obj = self.get_field_group(fgroup_uuid)
                note = ' updated.'
            if inp_obj is False:
                label = fgroup_uuid + ' not found'
                note = 'Input Field Group ' + fgroup_uuid + ' does not exist'
            else:
                if label != inp_obj.label:
                    # the user is updating the item label
                    # so validate it
                    label = self.check_make_valid_label(label)
                inp_obj.visibility = visibility
                inp_obj.sort = sort_val
                inp_obj.label = label
                inp_obj.note = data_note
                inp_obj.save()
                note = 'Input Field Group "' + label + '" (' + fgroup_uuid + ')' + note;
        self.response = {'action': action,
                         'ok': ok,
                         'change': {'uuid': fgroup_uuid,
                                    'label': label,
                                    'note': note}}
        return self.response

    def delete(self, fgroup_uuid):
        """ Deletes a field group, including
            the fields it contains
        """
        gfields = InputField.objects\
                            .filter(fgroup_uuid=fgroup_uuid)
        for gfield in gfields:
            sub_rules = InputRelation.objects\
                                     .filter(subject_type='rules',
                                             object_uuid=gfield.uuid)
            for rel_rule in sub_rules:
                # delete the subject related rule
                InputRule.objects\
                         .filter(uuid=rel_rule.subject_uuid)\
                         .delete()
            obj_rules = InputRelation.objects\
                                     .filter(object_type='rules',
                                             subject_uuid=gfield.uuid)
            for rel_rule in obj_rules:
                # delete the object related rule
                InputRule.objects\
                         .filter(uuid=rel_rule.object_uuid)\
                         .delete()
            # now delete relations for these fields
            InputRelation.objects\
                         .filter(subject_uuid=gfield.uuid)\
                         .delete()
            InputRelation.objects\
                         .filter(object_uuid=gfield.uuid)\
                         .delete()
        # now finally delete the fields in this field group
        gfields = InputField.objects\
                            .filter(fgroup_uuid=fgroup_uuid)\
                            .delete()
        # now delete the field group itself
        inp_obj = self.get_field_group(fgroup_uuid)
        if inp_obj is not False:
            ok = True
            label = inp_obj.label
            note = 'Deleted Field Group: "' + label + '" (' + fgroup_uuid + ')'
            inp_obj.delete()
        else:
            ok = False
            label = fgroup_uuid + ' not found'
            note = label
        self.response = {'action': 'delete-input-field-group',
                         'ok': ok,
                         'change': {'uuid': fgroup_uuid,
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

    def make_default_sort_val(self, profile_uuid):
        """
        makes a default sort value for a field group
        """
        sort_vals = [0]
        fgs = InputFieldGroup.objects\
                             .filter(profile_uuid=profile_uuid)
        for fg in fgs:
            sort_vals.append(fg.sort)
        return max(sort_vals) + 1
