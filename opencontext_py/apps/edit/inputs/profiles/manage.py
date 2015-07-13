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


class ManageInputProfile():
    """ This class contains methods
        to assist in manual data entry for a project
    """

    def __init__(self):
        self.errors = {}
        self.project_uuid = False
        self.creator_uuid = False
        self.response = False

    def check_make_valid_label(self, label, attempt=1):
        """ Checks to see we don't use the same label for a
            profile
        """
        if len(label) < 1:
            label = 'Unamed data entry profile'
        if attempt > 1:
            label_check = label + ' [' + str(attempt) + ']'
        else:
            label_check = label
        imp_labs = InputProfile.objects\
                               .filter(project_uuid=self.project_uuid,
                                       label=label_check)
        if len(imp_labs) > 0 and attempt <= 20:
            # we have the same label
            label = self.check_make_valid_label(label,
                                                attempt + 1)
        else:
            label = label_check
        return label

    def create_update_from_post(self, post, profile_uuid=False):
        """ Creates or updates an input profile from posted data
        """
        ok = True
        sort_val = 0
        note = ''
        action = ''
        if 'sort' in post:
            try:
                sort_val = int(float(post['sort']))
            except:
                sort_val = 0
        if 'item_type' in post:
            item_type = post['item_type']
            if item_type not in InputProfile.PROFILE_TYPES:
                is_valid = False
                self.errors['item_type'] = item_type + ' is not a valid type for a profile. '
                note += self.errors['item_type']
        else:
            item_type = False
            ok = False
            self.errors['item_type'] = 'Missing parameter. '
            note += self.errors['item_type']
        if 'label' in post:
            label = post['label'].strip()
        else:
            label = ''
        if 'note' in post:
            data_note = post['note'].strip()
        else:
            data_note = ''
        if ok:
            if profile_uuid is False:
                label = self.check_make_valid_label(label)
                action = 'create-input-profile'
                note = 'Profile created.'
                uuid = GenUUID.uuid4()
                profile_uuid = str(uuid)
                inp_prof = InputProfile()
                inp_prof.uuid = profile_uuid
                inp_prof.project_uuid = self.project_uuid
            else:
                action = 'update-input-profile'
                try:
                    inp_prof = InputProfile.objects.get(uuid=profile_uuid)
                except InputProfile.DoesNotExist:
                    inp_prof = False
                    ok = False
            if inp_prof is False:
                label = profile_uuid + ' not found'
                note = 'Input profile ' + profile_uuid + ' does not exist'
            else:
                if label != inp_prof.label:
                    # the user is updating the item label
                    # so validate it
                    label = self.check_make_valid_label(label)
                inp_prof.item_type = item_type
                inp_prof.sort = sort_val
                inp_prof.label = label
                inp_prof.note = data_note
                inp_prof.creator_uuid = self.creator_uuid
                inp_prof.save()
                self.make_mandatory_fields(self.project_uuid,
                                           profile_uuid,
                                           item_type)
        self.response = {'action': action,
                         'ok': ok,
                         'change': {'uuid': profile_uuid,
                                    'label': label,
                                    'note': note}}
        return self.response

    def make_mandatory_fields(self,
                              project_uuid,
                              profile_uuid,
                              item_type):
        """ makes mandatory predicates for a profile
            depending on it's type
        """
        if item_type in InputField.PREDICATES_OC:
            mandatory_predicates = InputField.PREDICATES_OC[item_type]
            exist_man_fields = InputField.objects\
                                         .filter(profile_uuid=profile_uuid,
                                                 predicate_uuid__in=mandatory_predicates)[:1]
            if len(exist_man_fields) > 0:
                # at least one of the mandatory fields already exists,
                # we sould add missing mandatory fields to this field-group
                fgroup_uuid = exist_man_fields[0].fgroup_uuid
            else:
                # we don't have any mandatory fields for this profile,
                # so create a group for the mandatory fields
                fgroup_uuid = GenUUID.uuid4()
                fgroup_uuid = str(fgroup_uuid)
                fgroup = InputFieldGroup()
                fgroup.uuid = fgroup_uuid
                fgroup.project_uuid = project_uuid
                fgroup.profile_uuid = profile_uuid
                fgroup.label = 'Open Context Required Fields'
                fgroup.visibility = 'open'
                fgroup.sort = 0
                fgroup.note = 'Automatically generated group of mandatory fields for ' + item_type + ' records.'
                fgroup.save()
            new_field = 1
            for man_pred in mandatory_predicates:
                # now check to see if the current mandatory predicate is already present
                exist_man_field = InputField.objects\
                                            .filter(profile_uuid=profile_uuid,
                                                    predicate_uuid=man_pred)
                if len(exist_man_field) < 1:
                    # only create the mandatory fields if they don't already exist for this profile
                    f_uuid = GenUUID.uuid4()
                    f_uuid = str(f_uuid)
                    inp_field = InputField()
                    inp_field.uuid = f_uuid
                    inp_field.project_uuid = project_uuid
                    inp_field.profile_uuid = profile_uuid
                    inp_field.fgroup_uuid = fgroup_uuid
                    inp_field.row_num = 1
                    inp_field.col_num = 1
                    inp_field.sort = new_field
                    inp_field.predicate_uuid = man_pred
                    preset = InputField.PREDICATE_ITEMS[inp_field.predicate_uuid]
                    inp_field.label = preset['label']
                    inp_field.note = preset['note']
                    inp_field.validation = json.dumps(preset['validation'],
                                                      indent=4,
                                                      ensure_ascii=False)
                    inp_field.save()
                    new_field += 1

    def delete(self, profile_uuid):
        """ Creates an input profile from posted data
        """
        ok = True
        try:
            inp_prof = InputProfile.objects.get(uuid=profile_uuid)
            label = inp_prof.label
            note = 'Input profile ' + label + ' (' + profile_uuid + ') deleted.'
        except InputProfile.DoesNotExist:
            inp_prof = False
            ok = False
            label = profile_uuid + ' not found'
            note = 'Input profile ' + profile_uuid + ' does not exist'
        InputRelation.objects\
                     .filter(profile_uuid=profile_uuid)\
                     .delete()
        InputFieldGroup.objects\
                       .filter(profile_uuid=profile_uuid)\
                       .delete()
        InputRule.objects\
                 .filter(profile_uuid=profile_uuid)\
                 .delete()
        InputField.objects\
                  .filter(profile_uuid=profile_uuid)\
                  .delete()
        InputProfile.objects\
                    .filter(uuid=profile_uuid)\
                    .delete()
        self.response = {'action': 'delete-input-profile',
                         'ok': ok,
                         'change': {'uuid': profile_uuid,
                                    'label': label,
                                    'note': note}}
        return self.response

    def duplicate(self, post, profile_uuid):
        """ duplicates an import profile, including
            fields and rules
        """
        ok = True
        try:
            inp_prof = InputProfile.objects.get(uuid=profile_uuid)
            if 'label' in post:
                label = post['label']
            else:
                label = inp_prof.label
        except InputProfile.DoesNotExist:
            inp_prof = False
        if inp_prof is False:
            ok = False
            label = profile_uuid + ' not found'
            new_profile_label = label
            note = 'Input profile ' + profile_uuid + ' does not exist'
            self.errors['uuid'] = note
        else:
            # now copy the existing found input profile object
            # and save with a new uuid and new label
            new_profile_label = self.check_make_valid_label(label)
            new_profile_uuid = GenUUID.uuid4()
            new_profile_uuid = str(new_profile_uuid)
            new_inp_prof = inp_prof
            new_inp_prof.uuid = new_profile_uuid
            new_imp_prof.label = new_profile_label
            new_imp_prof.save()
            # now copy the input field groups associated with the input profile object
            # and save them with new uuids and associtions with the new
            # input profile object
            inp_fgroups = InputFieldGroup.objects\
                                         .filter(profile_uuid=profile_uuid)
            for fgroup in inp_fgroups:
                old_uuid = data_rec.uuid
                new_uuid = GenUUID.uuid4()
                new_uuid = str(new_uuid)
                new_data_rec = data_rec
                new_data_rec.uuid = new_uuid
                new_data_rec.profile_uuid = new_profile_uuid
                new_data_rec.save()
                # now copy the input fields associated with the input profile object
                # and save them with new uuids and associtions with the new
                # input profile object
                inp_fields = InputField.objects\
                                       .filter(profile_uuid=profile_uuid,
                                               fgroup_uuid=old_uuid)
                # update the fields in their field groups with a the new
                # profile_uuid and the new fgroup_uuid
                self.copy_profile_related_data(inp_fields,
                                               new_profile_uuid,
                                               new_uuid)
            # now copy the input rules associated with the input profile object
            # and save them with new uuids and associtions with the new
            # input profile object
            inp_rules = InputRule.objects\
                                 .filter(profile_uuid=profile_uuid)
            self.copy_profile_related_data(inp_fields, new_profile_uuid)
            note = 'Input profile ' + label + ' (' + profile_uuid + ') copied to: '
            note += new_profile_label + ' (' + new_profile_uuid + ')'
            # close by making sure the new template has the required fields
            self.make_mandatory_fields(self.project_uuid,
                                       new_profile_uuid,
                                       new_imp_prof.item_type)
        self.response = {'action': 'duplicates-input-profile',
                         'ok': ok,
                         'change': {'uuid': new_profile_uuid,
                                    'label': new_profile_label,
                                    'note': note}}
        return self.response

    def copy_profile_related_data(self, data_recs, new_profile_uuid, field_group=False):
        """ copies a data record object,
            and its relationships
            saves the copied record with a new uuid
        """
        for data_rec in data_recs:
            old_uuid = data_rec.uuid
            new_uuid = GenUUID.uuid4()
            new_uuid = str(new_uuid)
            new_data_rec = data_rec
            new_data_rec.uuid = new_uuid
            new_data_rec.profile_uuid = new_profile_uuid
            if field_group is not False:
                new_data_rec.fgroup_uuid = field_group
            new_data_rec.save()
            # now duplicate the replationships
            self.duplicate_relationships(old_uuid, new_uuid, new_profile_uuid)

    def duplicate_relationships(self, old_uuid, new_uuid, new_profile_uuid):
        """ copies relationships in the inputs relations table
        """
        old_subjects = InputRelation.objects\
                                    .filter(subject_uuid=old_uuid)
        for old_rel in old_subjects:
            new_rel = old_rel
            new_rel.profile_uuid = new_profile_uuid
            new_rel.subject_uuid = new_uuid
            try:
                new_rel.save()
            except:
                # relationship probably already exists
                pass
        old_objects = InputRelation.objects\
                                   .filter(object_uuid=old_uuid)
        for old_rel in old_subjects:
            new_rel = old_rel
            new_rel.profile_uuid = new_profile_uuid
            new_rel.object_uuid = new_uuid
            try:
                new_rel.save()
            except:
                # relationship probably already exists
                pass
