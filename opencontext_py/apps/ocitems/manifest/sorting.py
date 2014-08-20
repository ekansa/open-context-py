import re
import roman
from unidecode import unidecode
from math import pow
from django.db import models
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.sorting import LinkEntitySorter


# This class prepares item sorting for Solr indexing and item display in Open Context
class ManifestSorter():
    """ Sort orders are recorded in numeric strings as so:

    '00-0000-000000-000000-000000-000000-000000-000000-000000'

    This first two digits record are highest level organizers for
    sorting in the oc_assertions table (so containment comes before
    variable predicates, which come before linking predicates, etc.)

    The next 4 digits store sort order based on project sort index.
    The rest of the digits store sort order in a nestet hiearchy.
    """

    def __init__(self):
        self.sorted_uris = []
        self.sorted_slugs = []

    def sort_subjects(self, project_uuid):
        pass

    def make_label_sortval(self, label):
        """ Make a sort value from a label """
        try_roman = True
        label_parts = re.split(':|\ |\.|\,|\;|\-|\(|\)|\_|\[|\]|\/',
                               label)
        sorts = []
        if len(label_parts) > 2:
            try_roman = False
        for part in label_parts:
            if len(part) > 0:
                if part.isdigit():
                    num_part = int(float(part))
                    part_sort = self.sort_digits(num_part)
                    sorts.append(part_sort)
                else:
                    part = unidecode(part)
                    part = re.sub(r'\W+', '', part)
                    roman_num = False
                    if try_roman:
                        try:
                            num_part = roman.fromRoman(part)
                            part_sort = self.sort_digits(num_part)
                            sorts.append(part_sort)
                            roman_num = True
                        except:
                            roman_num = False
                    if roman_num is False:
                        max_char_index = len(part)
                        continue_sort = True
                        char_index = 0
                        part_sort_parts = []
                        num_char_found = False
                        while continue_sort:
                            act_char = part[char_index]
                            char_val = ord(act_char) - 48
                            if char_val > 9:
                                act_part_sort_part = self.sort_digits(char_val, 3)
                            else:
                                num_char_found = True
                                act_part_sort_part = str(char_val)
                            part_sort_parts.append(act_part_sort_part)
                            part_sort = ''.join(part_sort_parts)
                            char_index += 1
                            if char_index >= max_char_index:
                                continue_sort = False
                        if len(part_sort) > 6 and num_char_found:
                            # print('Gotta split: ' + part_sort)
                            start_index = 0
                            max_index = len(part_sort)
                            while start_index < max_index:
                                end_index = start_index + 6
                                if end_index > max_index:
                                    end_index = max_index
                                new_part = part_sort[start_index:end_index]
                                new_part = self.prepend_zeros(new_part)
                                sorts.append(new_part)
                                start_index = end_index
                        elif len(part_sort) > 6 and num_char_found is False:
                            part_sort = part_sort[:6]
                            sorts.append(part_sort)
                        else:
                            part_sort = self.prepend_zeros(part_sort)
                            sorts.append(part_sort)
        return '-'.join(sorts)

    def first_pass_sort(self, project_uuid):
        uuids = UUIDListProjectNoSort(project_uuid).uuids
        for uuid in uuids:
            man = Manifest.objects.get(uuid=uuid)
            label_parts = re.split(':|\ |\.|\,|\;|\-|\(|\)', man.label)

    def get_project_index(self, project_uuid):
        """ Gets the sort - index number for a project """
        act_proj_short_id = 0
        if(project_uuid != '0'):
            try:
                act_proj = Project.objects.get(uuid=project_uuid)
                act_proj_short_id = act_proj.short_id
            except Project.DoesNotExist:
                act_proj_short_id = 0
        return act_proj_short_id

    def sort_digits(self, index, digit_length=6):
        """ Makes a 3 digit sort friendly string from an index """
        if index >= pow(10, digit_length):
            index = pow(10, digit_length) - 1
        sort = str(index)
        sort = self.prepend_zeros(sort, digit_length)
        return sort

    def prepend_zeros(self, sort, digit_length=6):
        """ prepends zeros if too short """
        if len(sort) < digit_length:
            while len(sort) < digit_length:
                sort = '0' + sort
        return sort


class UUIDListProjectItemType:
    '''
    The list of UUIDs for sorting
    '''
    def __init__(self, project_uuid, item_type):
        self.uuids = Manifest.objects\
                             .values_list('uuid', flat=True)\
                             .filter(project_uuid=project_uuid,
                                     item_type=item_type)\
                             .iterator()


class UUIDListProjectNoSort:
    '''
    The list of UUIDs for sorting
    '''
    def __init__(self, project_uuid, item_type):
        self.uuids = Manifest.objects\
                             .values_list('uuid', flat=True)\
                             .filter(project_uuid=project_uuid,
                                     sort='')\
                             .iterator()

