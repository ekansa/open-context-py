import re
import roman
from math import pow
from unidecode import unidecode
from django.utils import timezone
from django.db import models
from django.template.defaultfilters import slugify
from opencontext_py.apps.ocitems.projects.models import Project


# Manifest provides basic item metadata for all open context items that get a URI
class Manifest(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50)
    repo = models.CharField(max_length=200)
    class_uri = models.CharField(max_length=200)
    slug = models.SlugField(max_length=70, unique=True)
    label = models.CharField(max_length=200)
    des_predicate_uuid = models.CharField(max_length=50)
    views = models.IntegerField()
    indexed = models.DateTimeField(blank=True, null=True)
    vcontrol = models.DateTimeField(blank=True, null=True)
    archived = models.DateTimeField(blank=True, null=True)
    published = models.DateTimeField(db_index=True)
    revised = models.DateTimeField(db_index=True)
    record_updated = models.DateTimeField(auto_now=True)

    def validate_label(self):
        if(len(self.label) > 175):
            self.label = self.label[:172] + '...'
        return self.label

    def make_slug(self):
        """
        creates a unique slug for a label with a given type
        """
        man_gen = ManifestGeneration()
        slug = man_gen.make_manifest_slug(self.uuid,
                                          self.label,
                                          self.item_type,
                                          self.project_uuid)
        return slug

    def save(self, *args, **kwargs):
        """
        saves a manifest item with a good slug
        """
        self.label = self.validate_label()
        self.slug = self.make_slug()
        super(Manifest, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_manifest'
        unique_together = (("item_type", "slug"),)


class ManifestGeneration():

    # used in generating values for the sort field
    DEFAULT_SORT = [{'item_type': 'projects',
                     'class_uri': False},
                    {'item_type': 'tables',
                     'class_uri': False},
                    {'item_type': 'vocabularies',
                     'class_uri': False},
                    {'item_type': 'subjects',
                     'class_uri': False},
                    {'item_type': 'media',
                     'class_uri': False},
                    {'item_type': 'documents',
                     'class_uri': False},
                    {'item_type': 'persons',
                     'class_uri': False},
                    {'item_type': 'predicates',
                     'class_uri': 'variable'},
                    {'item_type': 'predicates',
                     'class_uri': 'link'},
                    {'item_type': 'types',
                     'class_uri': False}]

    def make_manifest_slug(self, uuid, label, item_type, project_uuid):
        """
        gets the most recently updated Subject date
        """
        label = label.replace('_', ' ')
        raw_slug = slugify(unidecode(label[:55]))
        act_proj_short_id = self.get_project_index(project_uuid)
        if(raw_slug == '-' or len(raw_slug) < 1):
            raw_slug = 'x'  # slugs are not a dash or are empty
        if(act_proj_short_id is not False):
            raw_slug = str(act_proj_short_id) + '--' + raw_slug
        if(raw_slug[-1:] == '-'):
            raw_slug = raw_slug + 'x'  # slugs don't end with dashes
        raw_slug = re.sub(r'([-]){3,}', r'--', raw_slug)  # slugs can't have more than 2 dash characters
        slug = self.raw_to_final_slug(uuid, raw_slug)  # function for making sure unique slugs
        return slug

    def raw_to_final_slug(self, uuid, raw_slug):
        """ Converts a raw to a final slug, checks if the slug exists. If it does, add a suffix.
        If the suffixed slug already exists, try the next suffix until we get one that does not exist.
        """
        slug_exists = False
        try:
            slug_exists_res = Manifest.objects\
                                      .filter(slug=raw_slug)\
                                      .exclude(uuid=uuid)[:1]
            if(len(slug_exists_res) > 0):
                slug_exists = True
            else:
                slug = raw_slug
        except Manifest.DoesNotExist:
            slug_exists = False
            slug = raw_slug
        if slug_exists:
            test_slug = raw_slug
            counter = 0
            while slug_exists:
                slug_count = Manifest.objects.filter(slug__startswith=test_slug).count()
                if(slug_count > 0):
                    test_slug = test_slug + "-" + str(slug_count + counter)  # ok because a slug does not end in a dash
                    counter += 1
                else:
                    slug = test_slug
                    slug_exists = False
        return slug

    def fix_blank_slugs(self):
        cc = 0
        try:
            no_slugs = Manifest.objects.all().exclude(slug__isnull=False)
        except Manifest.DoesNotExist:
            no_slugs = False
        if(no_slugs is not False):
            for nslug in no_slugs:
                nslug.save()
                cc += 1
        return cc

    def get_project_index(self, project_uuid):
        """ Gets the sort - index number for a project """
        act_proj_short_id = False
        if(project_uuid != '0'):
            try:
                act_proj = Project.objects.get(uuid=project_uuid)
                act_proj_short_id = act_proj.short_id
            except Project.DoesNotExist:
                act_proj_short_id = 0
        return act_proj_short_id

    def gen_sort_from_label(self,
                            label,
                            class_uri,
                            item_type,
                            project_uuid):
        """
        Makes a sort value for a manifet item.
        Sort orders are recorded in numeric strings as so:

        '00-0000-000000-000000-000000-000000-000000-000000-000000'

        This first two digits record are highest level organizers for
        sorting in the oc_assertions table (so containment comes before
        variable predicates, which come before linking predicates, etc.)

        The next 4 digits store sort order based on project sort index.
        The rest of the digits store sort order in a nested hiearchy.
        """
        type_index = self.get_type_sort_val(item_type, class_uri)
        prefix = self.prepend_zeros(type_index, 2)
        proj_index = self.get_project_index(project_uuid)
        prefix += '-' + self.prepend_zeros(proj_index, 4)

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

    def get_type_sort_val(self, item_type, class_uri=False):
        """ Gets the index number (sort) for a given item_type """
        output = len(self.DEFAULT_SORT)
        i = 0
        for sort_type in self.DEFAULT_SORT:
            if (item_type == sort_type['item_type']) and\
               (sort_type['class_uri'] is False):
                output = i
                break
            elif (item_type == sort_type['item_type']) and\
                 (class_uri in sort_type['class_uri']):
                output = i
                break
            i += 1
        return output

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