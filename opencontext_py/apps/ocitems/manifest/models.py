import pytz
import time
import re
import roman
import reversion  # version control object
import collections
from jsonfield import JSONField  # json field for complex objects
from django.conf import settings
from datetime import datetime
from django.utils import timezone
from math import pow
from unidecode import unidecode
from django.db import models
from django.template.defaultfilters import slugify
from opencontext_py.apps.ocitems.projects.models import Project


# Manifest provides basic item metadata for all open context items that get a URI
@reversion.register  # records in this model under version control
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
    sort = models.SlugField(max_length=70, db_index=True)
    views = models.IntegerField()
    indexed = models.DateTimeField(blank=True, null=True)
    vcontrol = models.DateTimeField(blank=True, null=True)
    archived = models.DateTimeField(blank=True, null=True)
    published = models.DateTimeField(db_index=True)
    revised = models.DateTimeField(db_index=True)
    record_updated = models.DateTimeField(auto_now=True)
    localized_json = JSONField(default={},
                               load_kwargs={'object_pairs_hook': collections.OrderedDict},
                               blank=True)
    sup_json = JSONField(default={},
                         load_kwargs={'object_pairs_hook': collections.OrderedDict},
                         blank=True)

    def validate_label(self):
        if self.item_type == 'subjects':
            # so as not to screw up depth of contexts.
            self.label = self.label.replace('/', '--')
        if len(self.label) > 175:
            self.label = self.label[:172] + '...'
        return self.label

    def make_slug_and_sort(self):
        """ Makes both a slug and a sort value, done this way
           with the same ManifiestGeneration object so
           we don't have to look up the project index twice """
        man_gen = ManifestGeneration()
        slug = man_gen.make_manifest_slug(self.uuid,
                                          self.label,
                                          self.item_type,
                                          self.project_uuid)
        sort = man_gen.gen_sort_from_label(self.label,
                                           self.class_uri,
                                           self.item_type,
                                           self.project_uuid)
        self.slug = slug
        self.sort = sort
        if len(slug) > 70:
            raise Exception(str(unidecode(slug))
                            + ' a slug, has wrong length (Chars: '
                            + str(len(slug)))
        if len(sort) > 70:
            raise Exception(str(unidecode(sort))
                            + ' a sort, has wrong length (Chars: '
                            + str(len(sort)))

    def make_slug(self, project_indices=False):
        """
        creates a unique slug for a label with a given type
        """
        man_gen = ManifestGeneration()
        if project_indices is not False:
            man_gen.project_indices = project_indices
        slug = man_gen.make_manifest_slug(self.uuid,
                                          self.label,
                                          self.item_type,
                                          self.project_uuid)
        if len(slug) > 70:
            raise Exception(str(unidecode(slug))
                            + ' a slug, has wrong length (Chars: '
                            + str(len(slug)))
        return slug

    def make_sort(self, project_indices=False):
        """
        creates a unique slug for a label with a given type
        """
        man_gen = ManifestGeneration()
        if project_indices is not False:
            man_gen.project_indices = project_indices
        sort = man_gen.gen_sort_from_label(self.label,
                                           self.class_uri,
                                           self.item_type,
                                           self.project_uuid)
        if len(sort) != man_gen.DEFAULT_EXPECTED_SORT_LEN:
            raise Exception(str(unidecode(self.label))
                            + ' wrong length (Chars: '
                            + str(len(sort)) + ', Dashes: '
                            + str(sort.count('-'))
                            + ') for sort: ' + sort)
        return sort

    def save(self, *args, **kwargs):
        """
        saves a manifest item with a good slug
        """
        if self.views is None:
            self.views = 0
        self.label = self.validate_label()
        self.make_slug_and_sort()
        if self.revised is None:
            self.revised = timezone.now()
        elif isinstance(self.revised, datetime):
            if timezone.is_naive(self.revised):
                self.revised = pytz.utc.localize(self.revised)
        if isinstance(self.indexed, datetime):
            if timezone.is_naive(self.indexed):
                self.indexed = pytz.utc.localize(self.indexed)
        if isinstance(self.vcontrol, datetime):
            if timezone.is_naive(self.vcontrol):
                self.vcontrol = pytz.utc.localize(self.vcontrol)
        if isinstance(self.archived, datetime):
            if timezone.is_naive(self.archived):
                self.archived = pytz.utc.localize(self.archived)
        if isinstance(self.published, datetime):
            if timezone.is_naive(self.published):
                self.published = pytz.utc.localize(self.published)
        if isinstance(self.record_updated, datetime):
            if timezone.is_naive(self.record_updated):
                self.record_updated = pytz.utc.localize(self.record_updated)
        super(Manifest, self).save(*args, **kwargs)

    def indexed_save(self):
        """
        Updates with the last indexed time
        """
        self.indexed = timezone.now()
        if self.published is None or self.published == '':
            self.published = timezone.now()
            super(Manifest, self).save(update_fields=['indexed', 'published'])
        else:
            super(Manifest, self).save(update_fields=['indexed'])

    def published_save(self, published_datetime_obj=None):
        """
        Updates with the published time
        """
        if published_datetime_obj is not None:
            self.published = published_datetime_obj
        if self.published is None or self.published == '':
            self.published = timezone.now()
        super(Manifest, self).save(update_fields=['published'])

    def archived_save(self):
        """
        Updates with the last indexed time
        """
        super(Manifest, self).save(update_fields=['archived'])

    def revised_save(self):
        """
        Updates with the last indexed time
        """
        self.revised = timezone.now()
        super(Manifest, self).save(update_fields=['revised'])

    def slug_save(self, project_indices=False):
        """
        save only slug value
        """
        self.label = self.validate_label()
        self.slug = self.make_slug()
        super(Manifest, self).save(update_fields=['slug'])

    def sort_save(self, project_indices=False):
        """
        save only slug value
        """
        self.sort = self.make_sort()
        # print(str(unidecode(self.label)) + ' has sort: ' + str(self.sort))
        super(Manifest, self).save(update_fields=['sort'])

    def check_sup_json_key_value(self, key, check_val):
        """ checks to see if a key and value are in the sup_json dict """
        matched = False
        if isinstance(self.sup_json, dict):
            if key in self.sup_json:
                if self.sup_json[key] == check_val:
                    matched = True
        return matched

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

    DEFAULT_LABEL_SORT_LEN = 6
    DEFAULT_LABEL_DELIMS = 9
    DEFAULT_EXPECTED_SORT_LEN = 63

    def __init__(self):
        self.project_indices = {}

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
            raw_slug = str(act_proj_short_id) + '-' + raw_slug
        if(raw_slug[-1:] == '-'):
            raw_slug = raw_slug + 'x'  # slugs don't end with dashes
        raw_slug = re.sub(r'([-]){2,}', r'-', raw_slug)  # slugs can't have more than 1 dash characters
        slug = self.raw_to_final_slug(uuid, raw_slug)  # function for making sure unique slugs
        return slug

    def raw_to_final_slug(self, uuid, raw_slug):
        """ Converts a raw to a final slug, checks if the slug exists. If it does, add a suffix.
        If the suffixed slug already exists, try the next suffix until we get one that does not exist.
        """
        raw_slug = raw_slug[:66]
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
            no_slugs = Manifest.objects.filter(item_type='projects').exclude(slug__isnull=False)
            print('Making slugs for projects: ' + str(len(no_slugs)))
        except Manifest.DoesNotExist:
            no_slugs = False
        if(no_slugs is not False):
            for nslug in no_slugs:
                # build up project_indices to avoid future database lookups
                self.get_project_index(nslug.uuid)
                nslug.slug_save(self.project_indices)
                cc += 1
        print('Working on everything else...')
        no_slugs = Manifest.objects\
                           .all()\
                           .values_list('uuid', flat=True)\
                           .exclude(slug__isnull=False)\
                           .iterator()
        for nslug_uuid in no_slugs:
            nslug = Manifest.objects.get(uuid=nslug_uuid)
            nslug.slug_save(self.project_indices)
            print('Item: ' + nslug.label + ' has slug: ' + nslug.slug)
            cc += 1
        return cc

    def redo_slugs_for_source_id(self, source_id):
        """ makes slugs for manifest items from a given source """
        man_objs = Manifest.objects.filter(source_id=source_id)
        for man in man_objs:
            # build up project_indices to avoid future database lookups
            self.get_project_index(man.project_uuid)
            man.slug_save(self.project_indices)

    def fix_blank_sorts(self):
        cc = 0
        try:
            no_sorts = Manifest.objects.filter(item_type='projects')
            print('Making sorts for projects: ' + str(len(no_sorts)))
        except Manifest.DoesNotExist:
            no_sorts = False
        if(no_sorts is not False):
            for nsort in no_sorts:
                # build up project_indices to avoid future database lookups
                self.get_project_index(nsort.uuid)
                nsort.sort_save(self.project_indices)
                cc += 1
        print('Working on everything else...')
        no_sorts = Manifest.objects\
                           .all()\
                           .values_list('uuid', flat=True)\
                           .exclude(sort__isnull=False)\
                           .iterator()
        for nsort_uuid in no_sorts:
            nsort = Manifest.objects.get(uuid=nsort_uuid)
            nsort.sort_save(self.project_indices)
            cc += 1
        return cc

    def get_project_index(self, project_uuid):
        """ Gets the sort - index number for a project """
        act_proj_short_id = False
        if project_uuid != '0':
            if project_uuid in self.project_indices:
                act_proj_short_id = self.project_indices[project_uuid]
            else:
                try:
                    act_proj = Project.objects.get(uuid=project_uuid)
                    act_proj_short_id = act_proj.short_id
                except Project.DoesNotExist:
                    act_proj_short_id = 0
                self.project_indices[project_uuid] = act_proj_short_id
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
        if proj_index is False:
            proj_index = 0
        prefix += '-' + self.prepend_zeros(proj_index, 4)
        label_part = self.make_label_sortval(label)
        act_label = prefix + '-' + label_part
        if act_label.count('-') < self.DEFAULT_LABEL_DELIMS:
            while act_label.count('-') < self.DEFAULT_LABEL_DELIMS:
                act_label += '-' + self.prepend_zeros(0)
        if act_label.count('-') > self.DEFAULT_LABEL_DELIMS:
            label_list = act_label.split('-')
            act_label = '-'.join(label_list[:(self.DEFAULT_LABEL_DELIMS+1)])
        return act_label

    def make_label_sortval(self, rawlabel):
        """ Make a sort value from a label """
        rawlabel = unidecode(rawlabel)
        rawlabel = str(rawlabel)
        label = ''
        i = 0
        prev_type = False
        if len(rawlabel) > 0:
            # this section checks for changes between numbers and letters, adds a
            # break if there's a change
            while i < len(rawlabel):
                act_char = rawlabel[i]
                char_val = ord(act_char)
                if char_val >= 49 and char_val <= 57:
                    act_type = 'number'
                elif char_val >= 65 and char_val <= 122:
                    act_type = 'letter'
                else:
                    act_type = False
                if act_type is not False and\
                   prev_type is not False:
                    if act_type != prev_type:
                        # case where switching between number and letter
                        # so add a seperator to make it a hierarchy
                        act_char = '-' + act_char
                label += act_char
                prev_type = act_type
                i += 1
        else:
            label = '0'
        print('Sort label is: ' + label)
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
                        part_sort = ''
                        part_sort_parts = []
                        num_char_found = False
                        while continue_sort:
                            if char_index < len(part):
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
                            else:
                                continue_sort = False
                            if char_index >= max_char_index:
                                continue_sort = False
                        if len(part_sort) > self.DEFAULT_LABEL_SORT_LEN and\
                           num_char_found:
                            # print('Gotta split: ' + part_sort)
                            start_index = 0
                            max_index = len(part_sort)
                            while start_index < max_index:
                                end_index = start_index + self.DEFAULT_LABEL_SORT_LEN
                                if end_index > max_index:
                                    end_index = max_index
                                new_part = part_sort[start_index:end_index]
                                new_part = self.prepend_zeros(new_part)
                                sorts.append(new_part)
                                start_index = end_index
                        elif len(part_sort) > self.DEFAULT_LABEL_SORT_LEN and\
                                num_char_found is False:
                            part_sort = part_sort[:self.DEFAULT_LABEL_SORT_LEN]
                            sorts.append(part_sort)
                        else:
                            part_sort = self.prepend_zeros(part_sort)
                            sorts.append(part_sort)
        final_sort = []
        for sort_part in sorts:
            if len(sort_part) > self.DEFAULT_LABEL_SORT_LEN:
                sort_part = sort_part[:self.DEFAULT_LABEL_SORT_LEN]
            elif len(sort_part) < self.DEFAULT_LABEL_SORT_LEN:
                sort_part = self.prepend_zeros(sort_part, self.DEFAULT_LABEL_SORT_LEN)
            final_sort.append(sort_part)
        if len(final_sort) < 1:
            final_sort.append(self.prepend_zeros(0, self.DEFAULT_LABEL_SORT_LEN))
        return '-'.join(final_sort)

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

    def sort_digits(self, index, digit_length=False):
        """ Makes a 3 digit sort friendly string from an index """
        if digit_length is False:
            digit_length = self.DEFAULT_LABEL_SORT_LEN
        if index >= pow(10, digit_length):
            index = pow(10, digit_length) - 1
        sort = str(index)
        sort = self.prepend_zeros(sort, digit_length)
        return sort

    def prepend_zeros(self, sort, digit_length=False):
        """ prepends zeros if too short """
        if digit_length is False:
            digit_length = self.DEFAULT_LABEL_SORT_LEN
        sort = str(sort)
        if len(sort) < digit_length:
            while len(sort) < digit_length:
                sort = '0' + sort
        return sort
