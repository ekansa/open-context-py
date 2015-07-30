import json
import time
import uuid as GenUUID
from django.db import models
from django.db.models import Q, Count
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.edit.inputs.profiles.models import InputProfile
from opencontext_py.apps.edit.inputs.profiles.manage import ManageInputProfile
from opencontext_py.apps.edit.inputs.fieldgroups.models import InputFieldGroup
from opencontext_py.apps.edit.inputs.inputrelations.models import InputRelation
from opencontext_py.apps.edit.inputs.inputfields.models import InputField
from opencontext_py.apps.edit.inputs.rules.models import InputRule


class InputProfileTemplating():
    """ This class contains methods
        to assist in manual data entry for a project
    """

    def __init__(self):
        self.uuid = False
        self.label = False
        self.project_uuid = False
        self.project_man = False
        self.project = False
        self.inp_prof = False
        self.mandatory_fields = []
        self.field_groups = []
        self.exists_ok = None

    def make_json(self, uuid):
        """ makes JSON for the profile item """
        ok = self.check_exists(uuid)
        if ok:
            # makes mandatory fields if they don't exist
            mip = ManageInputProfile()
            mip.make_mandatory_fields(self.project_uuid,
                                      self.inp_prof.uuid,
                                      self.inp_prof.item_type)
            profile = LastUpdatedOrderedDict()
            profile['id'] = self.uuid
            profile['label'] = self.inp_prof.label
            profile['note'] = self.inp_prof.note
            profile['item_type'] = self.inp_prof.item_type
            profile['project'] = LastUpdatedOrderedDict()
            profile['project']['uuid'] = self.project.uuid
            profile['project']['label'] = self.project.label
            profile['fgroups'] = self.get_field_groups_and_fields()
        else:
            profile = False
        return profile

    def check_exists(self, uuid):
        """ checks to see if the input profile exists """
        if self.exists_ok is None:
            self.uuid = uuid
            ok = True
            try:
                self.inp_prof = InputProfile.objects.get(uuid=uuid)
                self.label = self.inp_prof.label
                self.project_uuid = self.inp_prof.project_uuid
            except InputProfile.DoesNotExist:
                self.inp_prof = False
                ok = False
            if ok:
                try:
                    self.project_man = Manifest.objects.get(uuid=self.project_uuid,
                                                            item_type='projects')
                except Manifest.DoesNotExist:
                    self.project_man = False
                    ok = False
            if ok:
                try:
                    self.project = Project.objects.get(uuid=self.project_uuid)
                    self.project.label = self.project_man.label
                    self.project.slug = self.project_man.slug
                except Project.DoesNotExist:
                    self.project = False
                    ok = False
            self.exists_ok = ok
        else:
            ok = self.exists_ok
        return ok

    def get_field_groups_and_fields(self):
        """ gets fields used in this import profile,
            it's not super efficient but it doesn't have to be
            because it is querying very small data
        """
        mandatory_predicates = []
        if self.inp_prof.item_type in InputField.PREDICATES_OC:
            # exclude the mandatory fields for this type of item
            mandatory_predicates = InputField.PREDICATES_OC[self.inp_prof.item_type]
        bad_field_uuids = []
        groups = []
        if self.inp_prof is not False:
            inp_groups = InputFieldGroup.objects\
                                        .filter(profile_uuid=self.uuid)
            index = 0
            for inp_group in inp_groups:
                index += 1
                group = LastUpdatedOrderedDict()
                group['id'] = inp_group.uuid
                group['label'] = inp_group.label
                group['visibility'] = inp_group.visibility
                group['vis_note'] = InputFieldGroup.GROUP_VIS[inp_group.visibility]
                if len(group['label']) < 1:
                    group['label'] = 'Field group: ' + str(index)
                group['note'] = inp_group.note
                group['obs_num'] = inp_group.obs_num
                group['fields'] = []
                inp_group_fields = InputField.objects\
                                             .filter(profile_uuid=self.uuid,
                                                     fgroup_uuid=inp_group.uuid)
                for inp_field in inp_group_fields:
                    add_ok = False
                    field = LastUpdatedOrderedDict()
                    field['id'] = inp_field.uuid
                    field['sort'] = inp_field.sort
                    field['predicate_uuid'] = inp_field.predicate_uuid
                    if inp_field.predicate_uuid not in InputField.PREDICATE_ITEMS:
                        ent = Entity()
                        found = ent.dereference(inp_field.predicate_uuid)
                        if found:
                            add_ok = True
                            if len(inp_field.label) < 1:
                                inp_field.label = ent.label
                                inp_field.save()
                            field['label'] = inp_field.label
                            field['data_type'] = ent.data_type
                            field['oc_required'] = False
                        else:
                            # we've got data entry fields that don't exist, so delete them
                            add_ok = False
                            bad_field_uuids.append(inp_field.uuid)
                    else:
                        add_ok = True
                        preset = InputField.PREDICATE_ITEMS[inp_field.predicate_uuid]
                        field['label'] = preset['label']
                        field['data_type'] = preset['data_type']
                        field['oc_required'] = True
                    field['note'] = inp_field.note
                    try:
                        val_obj = json.loads(inp_field.validation)
                    except:
                        val_obj = LastUpdatedOrderedDict()
                    field['validation'] = val_obj
                    if add_ok:
                        # ok to add this to the list
                        group['fields'].append(field)
                groups.append(group)
        if len(bad_field_uuids) > 0:
            # delete the bad fields
            InputField.objects\
                      .filter(uuid__in=bad_field_uuids)\
                      .delete()
        self.field_groups = groups
        return self.field_groups
