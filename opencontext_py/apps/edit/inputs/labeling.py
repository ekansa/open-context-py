import re
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
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.manifest.models import Manifest


class InputLabeling():
    """ This class contains methods
        to assist in manual data entry for a project.

        It specifically works on checking and suggesting item labels
    """

    def __init__(self):
        self.item_type = False
        self.project_uuid = False
        self.context_uuid = False
        self.recusion_count = 0

    def check_make_valid_label(self,
                               label,
                               prefix='',
                               num_id_len=False):
        """ Checks a label,
            if not valid suggests an alternative
            based on the prefix.
            If unique_in_project is True then
            validate uniqueness within the project,
            if false then the label will be checked
            for uniqueness within a context
        """
        output = LastUpdatedOrderedDict()
        if isinstance(label, str):
            if len(label) < 1:
                label = False
        output['checked'] = label
        if label is False:
            output['exists'] = None
        else:
            output['exists'] = self.check_label_exists_in_scope(label)
        if output['exists'] \
           or output['exists'] is None:
            output['suggested'] = self.suggest_valid_label(prefix,
                                                           num_id_len)
        else:
            output['suggested'] = label
        return output

    def suggest_valid_label(self,
                            prefix,
                            num_id_len=False,
                            label_increment=1):
        """ Suggests a valid label,
            unique for the whole project or
            for a context
        """
        man_list = []
        if self.context_uuid is not False:
            uuids = []
            if self.item_type == 'subjects':
                # get items with the same parent context
                # that will be the scope for a unique label
                cont = Containment()
                cont.get_children_by_parent_uuid(self.context_uuid)
                for tree_key, children in cont.contents.items():
                    for child_uuid in children:
                        if child_uuid not in uuids:
                            uuids.append(child_uuid)
            else:
                # get items (of the same item_type) related to a context
                # that will be the scope for a unique label
                rel_list = Assertion.objects\
                                    .filter(uuid=self.context_uuid,
                                            object_type=self.item_type)
                for rel in rel_list:
                    if rel.uuid not in uuids:
                        uuids.append(rel.uuid)
            if len(uuids) > 0:
                if len(prefix) < 1:
                    man_list = Manifest.objects\
                                       .filter(project_uuid=self.project_uuid,
                                               uuid__in=uuids)\
                                       .order_by('-label')
                else:
                    man_list = Manifest.objects\
                                       .filter(project_uuid=self.project_uuid,
                                               label__contains=prefix,
                                               uuid__in=uuids)\
                                       .order_by('-label')
        else:
            if len(prefix) < 1:
                man_list = Manifest.objects\
                                   .filter(project_uuid=self.project_uuid,
                                           item_type=self.item_type)\
                                   .order_by('-label')[:5]
            else:
                man_list = Manifest.objects\
                                   .filter(project_uuid=self.project_uuid,
                                           label__contains=prefix,
                                           item_type=self.item_type)\
                                   .order_by('-label')[:5]
        if len(man_list) > 0:
            if len(prefix) > 0:
                label_id_part = man_list[0].label.replace(prefix, '')
            else:
                label_id_part = man_list[0].label
            vals = []
            # get the numbers out
            q_nums_strs = re.findall(r'[-+]?\d*\.\d+|\d+', label_id_part)
            for q_num_str in q_nums_strs:
                vals.append(q_num_str)
            last_id = float(''.join(vals))
            new_id = last_id + label_increment
        else:
            new_id = label_increment
        new_label = prefix + self.prepend_zeros(new_id, num_id_len)
        new_label_exists = self.check_label_exists_in_scope(new_label)
        if new_label_exists:
            # despite our best efforts, we made a new label that already exists
            # try again
            self.recusion_count += 1
            if self.recusion_count <= 20:
                # do this recursively to make a new label
                new_label = self.suggest_valid_label(unique_in_project,
                                                     prefix,
                                                     num_id_len,
                                                     label_increment + 1)
        return new_label

    def check_label_exists_in_scope(self, label):
        """ checks to see if a label already exists
            within the scope of a project or related context
        """
        man_list = []
        if self.context_uuid is not False:
            uuids = []
            if self.item_type == 'subjects':
                # get items with the same parent context
                # that will be the scope for a unique label
                cont = Containment()
                child_trees = cont.get_children_by_parent_uuid(self.context_uuid)
                for tree_key, children in child_trees.items():
                    for child_uuid in children:
                        if child_uuid not in uuids:
                            uuids.append(child_uuid)
            else:
                # get items (of the same item_type) related to a context
                # that will be the scope for a unique label
                rel_list = Assertion.objects\
                                    .filter(uuid=self.context_uuid,
                                            object_type=self.item_type)
                for rel in rel_list:
                    if rel.uuid not in uuids:
                        uuids.append(rel.uuid)
            if len(uuids) > 0:
                man_list = Manifest.objects\
                                   .filter(project_uuid=self.project_uuid,
                                           label=label,
                                           uuid__in=uuids)
        else:
            man_list = Manifest.objects\
                               .filter(project_uuid=self.project_uuid,
                                       label=label)
        if len(man_list) > 0:
            label_exists = True
        else:
            label_exists = False
        return label_exists

    def prepend_zeros(self, num_id_part, digit_length):
        """ prepends zeros if too short """
        try:
            numeric_part = float(num_id_part)
            if int(numeric_part) == numeric_part:
                num_id_part = int(numeric_part)
        except:
            pass
        num_id_part = str(num_id_part)
        if digit_length is not False:
            if len(num_id_part) < digit_length:
                while len(num_id_part) < digit_length:
                    num_id_part = '0' + num_id_part
        return num_id_part
