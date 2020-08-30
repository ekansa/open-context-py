import hashlib
import pytz
import time
import re
import roman
import requests
import reversion  # version control object
import uuid as GenUUID

from datetime import datetime
from math import pow
from time import sleep
from unidecode import unidecode

from django.core.cache import caches

from django.db import models
from django.db.models import Q

from django.contrib.postgres.fields import ArrayField, JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.template.defaultfilters import slugify
from django.utils import timezone

from django.conf import settings


from opencontext_py.apps.all_items import configs

DEFAULT_LABEL_SORT_LEN = 6

# ---------------------------------------------------------------------
# Generally used validation functions
# ---------------------------------------------------------------------
def validate_related_manifest_item_type(
    man_obj, 
    allowed_types, 
    obj_role, 
    raise_on_fail=True
):
    if not isinstance(allowed_types, list):
        allowed_types = [allowed_types]
    if man_obj.item_type in allowed_types:
        return True
    if raise_on_fail:
        raise ValueError(
            f'{obj_role} has item_type {man_obj.item_type} '
            f'but must be: {str(allowed_types)}'
        )
    return False

def validate_related_project(project_obj, raise_on_fail=True):
    return validate_related_manifest_item_type(
        man_obj=project_obj, 
        allowed_types=['projects'], 
        obj_role='project',
        raise_on_fail=raise_on_fail
    )

def web_protocol_check(uri):
    """Checks if a URI responds to https:// or http://"""
    sleep(0.25)
    protocols = ['https://', 'http://',]
    for protocol in protocols:
        check_uri = protocol + AllManifest().clean_uri(uri)
        try:
            r = requests.head(check_uri)
            if (
                (r.status_code == requests.codes.ok) 
                or
                (r.status_code >= 300 and r.status_code <= 310)
            ):
                return check_uri
        except:
            pass
    return uri

# ---------------------------------------------------------------------
#  Functions used with the Manifest Model
# ---------------------------------------------------------------------
def prepend_zeros(sort, digit_length=DEFAULT_LABEL_SORT_LEN):
    """ prepends zeros if too short """
    sort = str(sort)
    while len(sort) < digit_length:
        sort = '0' + sort
    return sort


def sort_digits(index, digit_length=DEFAULT_LABEL_SORT_LEN):
    """ Makes a 3 digit sort friendly string from an index """
    if index >= pow(10, digit_length):
        index = pow(10, digit_length) - 1
    return prepend_zeros(str(index), digit_length)


def make_label_sort_val(raw_label):
    """Extract a sortable value"""
    raw_label = unidecode(str(raw_label))
    sort_label = ''
    prev_type = None
    for act_char in raw_label:
        char_val = ord(act_char)
        if char_val >= 49 and char_val <= 57:
            act_type = 'number'
        elif char_val >= 65 and char_val <= 122:
            act_type = 'letter'
        else:
            act_type = None
        if act_type and prev_type:
            if act_type != prev_type:
                act_char = '-' + act_char
        sort_label += act_char
        prev_type = act_type
    # Split the label by different delims.
    label_parts = re.split(
        ':|\ |\.|\,|\;|\-|\(|\)|\_|\[|\]|\/',
        sort_label
    )
    sorts = []
    for part in label_parts:
        if not len(part):
            # Skip, the part has nothing in it.
            continue
        if part.isdigit():
            # A numeric part
            num_part = int(float(part))
            part_sort = sort_digits(num_part)
            sorts.append(part_sort)
            # Continue, we're done with sorting
            # this part.
            continue

        # The part is a string, so process as
        # string
        part = unidecode(part)
        part = re.sub(r'\W+', '', part)
        try:
            roman_num = roman.fromRoman(part)
        except:
            roman_num = None
        if roman_num:
            part_sort = sort_digits(roman_num)
            sorts.append(part_sort)
            # Continue, we're done with sorting
            # this part.
            continue
        part_sort_parts = []
        for act_char in part:
            char_val = ord(act_char) - 48
            if char_val > 9:
                act_part_sort_part = sort_digits(char_val, 3)
            else:
                act_part_sort_part = str(char_val)
            part_sort_parts.append(act_part_sort_part)
        # Now bring together the part_sort_parts
        part_sort = ''.join(part_sort_parts)
        sorts.append(part_sort)
    # Now do the final  
    final_sort = []
    for sort_part in sorts:
        sort_part = str(sort_part)
        if len(sort_part) > DEFAULT_LABEL_SORT_LEN:
            sort_part = sort_part[:DEFAULT_LABEL_SORT_LEN]
        elif len(sort_part) < DEFAULT_LABEL_SORT_LEN:
            sort_part = prepend_zeros(
                sort_part, 
                DEFAULT_LABEL_SORT_LEN
            )
        final_sort.append(sort_part)
    if not len(final_sort):
        final_sort.append(prepend_zeros(0, DEFAULT_LABEL_SORT_LEN))
    return '-'.join(final_sort)


def get_project_short_id(project_id, not_found_default=0):
    """Get a project short id """
    # Get the project id
    proj = None
    if project_id:
        proj = AllManifest.objects.filter(uuid=project_id).first()
    if proj:
        return proj.meta_json.get('short_id', not_found_default)
    return not_found_default


def make_sort_label(label, item_type, project_id, item_type_list):
    """Makes a sort value for a record as a numeric string"""
    sort_parts = []
    if item_type not in item_type_list: 
        item_type_num = len(item_type_list)
    else:
        item_type_num = item_type_list.index(item_type)
    sort_parts.append(
        prepend_zeros(item_type_num, 2)
    )
    project_short_id = get_project_short_id(project_id)
    sort_parts.append(
        prepend_zeros(project_short_id, 4)
    )
    sort_parts.append(
        make_label_sort_val(label)
    )
    final_sort = '-'.join(sort_parts)
    return final_sort


def make_slug_from_label(label, project_id):
    """Makes a slug from a label for a project item"""
    label = label.strip()
    label = label.replace('_', ' ')
    raw_slug = slugify(unidecode(label[:60]))
    project_sort_id = get_project_short_id(project_id)
    if raw_slug == '-' or not len(raw_slug):
        # Slugs are not a dash or are empty
        raw_slug = 'x'
    raw_slug = str(project_sort_id) + '-' + raw_slug
    return raw_slug


def make_slug_from_uri(uri):
    """Makes a slug from a label for a project item"""
    uri = AllManifest().clean_uri(uri)

    # Remove any www. prefix to a URI.
    for bad_prefix in ['www.']:
        if not uri.startswith(bad_prefix):
            continue
        uri = uri[len(bad_prefix):]
    
    # Now look for uri_roots to convert to a slug prefix based on
    # configuration.
    for uri_root, slug_prefix in configs.LINKED_DATA_URI_PREFIX_TO_SLUGS.items():
        if not uri.startswith(uri_root):
            continue
        # Replace the uri_root with the slug prefix.
        uri = slug_prefix + uri[len(uri_root):]
        break
    
    replaces = [
        ('/', '-',),
        ('.', '-',),
        ('#', '-'),
        ('%20', '-'),
        ('q=', '-'),
        ('+', '-'),
        ('_', '-'),
    ]
    for f, r in replaces:
        uri = uri.replace(f, r)
    raw_slug = slugify(unidecode(uri[:55]))

    # Slugs can't have more than 1 dash characters
    raw_slug = re.sub(r'([-]){2,}', r'--', raw_slug)
    return raw_slug


def make_uri_for_oc_item_types(uuid, item_type):
    if item_type not in configs.OC_ITEM_TYPES:
        return None
    return f'{configs.OC_URI_ROOT}/{item_type}/{uuid}'

def make_manifest_slug(label, item_type, uri, project_id):
    """Makes a sort value for a record as a numeric string"""
    if item_type in configs.OC_ITEM_TYPES:
        # The item_type is in the type that has the
        # project_short_id as a slug prefix.
        raw_slug = make_slug_from_label(label, project_id)

    if item_type in configs.URI_ITEM_TYPES:
        # Check for a publisher specific config for
        # this kind of item type.
        raw_slug = make_slug_from_uri(uri)

    # Make sure no triple dashes, conflicts with solr hierarchy
    # delims.
    raw_slug = raw_slug.replace('---', '--')
    keep_trimming = True
    while keep_trimming and len(raw_slug):
        if raw_slug.endswith('-'):
            # slugs don't end with dashes
            raw_slug = raw_slug[:-1]
        else:
            keep_trimming = False
            break
    
    if raw_slug == '-' or not len(raw_slug):
        # Slugs are not a dash or are empty
        raw_slug = 'x'

    # Slugs can't have more than 1 dash characters
    slug_prefix = re.sub(r'([-]){2,}', r'-', raw_slug)
    q_slug = slug_prefix

    # Check to see if this slug is in use.
    m_slug = AllManifest.objects.filter(
        slug=q_slug
    ).first()
    if not m_slug:
        # This slug is not yet used, so skip out.
        return q_slug
    # Make a prefix based on the length the number of
    # slugs.
    m_slug_count = AllManifest.objects.filter(
        slug__startswith=slug_prefix
    ).count()
    return '{}-{}'.format(
        slug_prefix,
        (m_slug_count + 1) 
    )



# Manifest provides basic item metadata for all open context items that get a URI
@reversion.register  # records in this model under version control
class AllManifest(models.Model):

    OK_FOR_MISSING_REFS = [
        configs.OPEN_CONTEXT_PROJ_UUID, 
        configs.OPEN_CONTEXT_PUB_UUID,
        configs.OC_GEN_VOCAB_UUID,
        configs.DEFAULT_CLASS_UUID,
    ]

    uuid = models.UUIDField(primary_key=True, editable=True)
    publisher = models.ForeignKey(
        'self', 
        db_column='publisher_uuid', 
        related_name='+', 
        on_delete=models.CASCADE, 
        null=True,
        default=configs.OPEN_CONTEXT_PUB_UUID,
    )
    project = models.ForeignKey(
        'self', 
        db_column='project_uuid', 
        related_name='+', 
        on_delete=models.CASCADE, 
        null=True,
        default=configs.OPEN_CONTEXT_PROJ_UUID,
    )
    item_class = models.ForeignKey(
        'self',
        db_column='item_class_uuid', 
        related_name='+', 
        on_delete=models.CASCADE, 
        null=True,
        default=configs.DEFAULT_CLASS_UUID,
    )
    source_id = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50)
    data_type = models.CharField(max_length=50, default='id')
    slug = models.SlugField(max_length=70, unique=True)
    label = models.CharField(max_length=200)
    sort = models.SlugField(max_length=100, db_index=True)
    views = models.IntegerField(default=0)
    indexed = models.DateTimeField(blank=True, null=True)
    vcontrol = models.DateTimeField(blank=True, null=True)
    archived = models.DateTimeField(blank=True, null=True)
    published = models.DateTimeField(db_index=True, null=True)
    revised = models.DateTimeField(db_index=True, auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    # Note the URI will strip the https:// or http://.
    uri = models.CharField(max_length=300, unique=True)
    # Preferred key when used in JSON-LD.
    item_key = models.CharField(max_length=300, blank=True, null=True)
    # Hash ID has special logic to ensure context dependent uniqueness
    # especially based on the contents of the context field.
    hash_id = models.CharField(max_length=50, unique=True)
    # Context is needed in entity reconciliation, to help determine if
    # a labeled entity is unique within the scope of a given context. 
    # Also for URI identified linked-data entities (typically published
    # by sources outside of Open Context, a context is used to note
    # the vocabulary (name-space) that owns / contains a URI identified
    # entity.
    context = models.ForeignKey(
        'self', 
        db_column='context_uuid', 
        related_name='+', 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True,
        default=configs.OPEN_CONTEXT_PROJ_UUID,
    )
    # A path is a string / text representation of an entity in a context
    # defined hierarchy. It is used especially for lookups and entity
    # reconciliation of subjects item_types.
    path = models.CharField(max_length=500, db_index=True, blank=True, null=True)
    # Meta_json is where we store occasionally used attributes, such
    # as metadata about projects, persons, languages, etc.
    meta_json = JSONField(default=dict)

    def clean_label(self, label, item_type='subjects'):
        label = label.strip()
        if item_type == 'subjects':
            # So as not to screw up depth of contexts.
            label = label.replace('/', '--')
        if len(label) > 195:
            label = label[:192] + '...'
        return label
    
    def clean_uri(self, uri):
        if not uri:
            return None
        uri = uri.strip()
        # Trim off the http: or https: prefix.
        for prefix in ['http://', 'https://']:
            if not uri.startswith(prefix):
                continue
            uri = uri[len(prefix):]
        # Remove trailing suffixes that have no meaning.
        for suffix in ['.html', '/', '#']:
            if not uri.endswith(suffix):
                continue
            uri = uri[0:-(len(suffix))]
        return uri

    def make_hash_id(
        self, 
        item_type, 
        data_type, 
        label, 
        uri=None, 
        path='', 
        project_uuid=configs.OPEN_CONTEXT_PROJ_UUID, 
        context_uuid=configs.OPEN_CONTEXT_PROJ_UUID,
    ):
        """
        Creates a hash-id to ensure context dependent uniqueness
        """
        hash_obj = hashlib.sha1()
        if item_type in configs.URI_ITEM_TYPES:
            concat_string = ' '.join(
                [
                    str(project_uuid),
                    str(context_uuid),
                    str(item_type),
                    str(data_type),
                    str(label),
                    str(uri),
                ]
            )
        else:
            concat_string = ' '.join(
                [
                    str(project_uuid),
                    str(context_uuid),
                    str(item_type),
                    str(data_type),
                    str(label),
                    str(path),
                ]
            )
        concat_string = concat_string.strip()
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def make_hash_id_for_self(self):
        """Makes a hash-id to ensure context dependent uniqueness of this obj"""
        project_uuid = configs.OPEN_CONTEXT_PROJ_UUID
        context_uuid = configs.OPEN_CONTEXT_PROJ_UUID
        if self.project:
            project_uuid = self.project.uuid
        if self.context:
            context_uuid = self.context.uuid
        path = ''
        if self.path:
            path = self.path
        return self.make_hash_id(
            item_type=self.item_type,
            data_type=self.data_type,
            label=self.label,
            uri=self.uri,
            path=path,
            project_uuid=project_uuid,
            context_uuid=context_uuid,
        )

    def validate_project(self):
        """Checks to make sure a project is actually a project"""
        if self.uuid in self.OK_FOR_MISSING_REFS:
            # Skip this validation because we have
            # a special uuid.
            return True
        # For most cases, check that this a project.
        return validate_related_project(project_obj=self.project)

    def validate_from_list(self, option, options, raise_on_error=True):
        if option in options:
            # This is a valid option
            return True
        if raise_on_error:
            raise ValueError('{} not valid, must be in {}'.format(option, str(options)))
        # This is not a valid option
        return False

    def dereference_keys(self):
        """Looks up references to keys"""
        if self.uuid not in self.OK_FOR_MISSING_REFS:
            # Skip out. A manifest object for
            # every uuid except those listed above in
            # ok_for_missing_refs needs to have references to
            # manifest objects that actually exist.
            return None
        
        # This is a special case for the ok_for_missing_refs
        # list above.
        try:
            self.publisher = self.publisher
        except ObjectDoesNotExist:
            self.publisher = None
        try:
            self.project = self.project
        except ObjectDoesNotExist:
            self.project = None
        try:
            self.item_class = self.item_class
        except ObjectDoesNotExist:
            self.item_class= None
        try:
            self.context = self.context
        except ObjectDoesNotExist:
            self.context = None
    
    def make_slug_and_sort(self):
        """Make slug and sorting values"""
        # Make the slug and sorting
        if self.project:
            project_id = self.project.uuid
        else:
            project_id = None

        if not self.slug:
            # Generate the item's slug.
            self.slug = make_manifest_slug(
                self.label, 
                self.item_type,
                self.uri, 
                project_id,
            )

        # Make the item's sorting.
        sort = make_sort_label(
            self.label, 
            self.item_type, 
            project_id, 
            item_type_list=configs.ITEM_TYPES
        )
        self.sort = sort[:100]
    
    def primary_key_create(
        self,
        item_type,
        project_id=None, 
        context_id=None,
        uri=None,
    ):
        """Make a primary key, sometimes deterministically depending on the item_type"""

        if (item_type in configs.OC_ITEM_TYPES 
            or project_id is None
            or context_id is None):
            # Do not make a deterministic uuid because these are for
            # formal public publication of items where we have an expectation
            # globally unique identifiers.
            return str(GenUUID.uuid4())

        if item_type in configs.NODE_ITEM_TYPES:
            # Because this is generated randomly, node item types won't
            # have predictable uuids. Only the first part of the uuid will
            # be predictable.
            hash_val = str(GenUUID.uuid4())
        else:
            # This will make a predictable uuid. 
            hash_val = self.clean_uri(uri)

        # NOTE: Everything in this function below is for deterministically
        # making a uuid based on the uri, the project_id or the context id.
        hash_obj = hashlib.sha1()
        hash_obj.update(hash_val.encode('utf-8'))
        hash_id =  hash_obj.hexdigest()
        # Now convert that hash into a uuid. Note, we're only using
        # the first 32 characters. This should still be enough to have
        # really, really high certainty we won't have hash-collisions on
        # data that should not be considered unique. If we run into a problem
        # we can always override this.
        uuid_from_hash_id = str(
            GenUUID.UUID(hex=hash_id[:32])
        )
        new_parts = uuid_from_hash_id.split('-')

        # Make the first part from the project uuid.
        project_id = str(project_id)
        uuid_prefix = project_id.split('-')[0]

        if item_type in configs.URI_CONTEXT_PREFIX_ITEM_TYPES:
            # Make the first part from the context uuid
            context_id = str(context_id)
            # Grab the second part of the context.
            context_parts = context_id.split('-')
            # project-context-uri_parts...
            uuid = '-'.join(
                [
                    uuid_prefix, 
                    context_parts[1],
                    new_parts[2],
                    new_parts[3],
                    new_parts[4],
                ]
            )
        else:
            # project-uri_parts...
            uuid = '-'.join(
                ([uuid_prefix] + new_parts[1:])
            )
        return uuid


    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the subject"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid
        return self.primary_key_create(
            item_type=self.item_type,
            project_id=self.project.uuid, 
            context_id=self.context.uuid,
            uri=self.uri,
        )
        

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique string for a project
        """
        self.label = self.clean_label(self.label, self.item_type)
        self.uri = self.clean_uri(self.uri)

        # Dereferences keys:
        self.dereference_keys()

        # Depending on the item type, make a random, semi-random,
        # or totally predicable uuid for this manifest obj.
        self.uuid = self.primary_key_create_for_self()

        # Make the URI for Open Context item types.
        if self.uri is None and self.item_type in configs.OC_ITEM_TYPES:
            self.uri = make_uri_for_oc_item_types(
                self.uuid, 
                self.item_type
            )

        # Make sure the project is actually a project
        self.validate_project()

        self.hash_id = self.make_hash_id_for_self()
        # Make sure the item_type is valid.
        self.validate_from_list(
            self.item_type, configs.ITEM_TYPES
        )
        # Make sure the data_type is valid.
        self.validate_from_list(
            self.data_type, configs.DATA_TYPES
        )
        # Make the slug and sort values.
        self.make_slug_and_sort()
        super(AllManifest, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_all_manifest'



# OCstring stores string content, with each string unique to a project
@reversion.register  # records in this model under version control
class AllSpaceTime(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    publisher = models.ForeignKey(
        AllManifest, 
        db_column='publisher_uuid',
        related_name='+', 
        on_delete=models.PROTECT, 
        default=configs.OPEN_CONTEXT_PUB_UUID,
    )
    project = models.ForeignKey(
        AllManifest, 
        db_column='project_uuid', 
        related_name='+', 
        on_delete=models.PROTECT, 
        default=configs.OPEN_CONTEXT_PROJ_UUID,
    )
    source_id = models.CharField(max_length=50, db_index=True)
    item = models.ForeignKey(
        AllManifest, 
        db_column='item_uuid', 
        related_name='item_uuid', 
        on_delete=models.CASCADE
    )
    event = models.ForeignKey(
        AllManifest,  
        db_column='event_uuid', 
        related_name='+', 
        on_delete=models.PROTECT,
        default=configs.DEFAULT_EVENT_UUID,
    )
    # An integer ID, used for sorting, that is unique to the
    # specific item.
    feature_id = models.IntegerField()
    # Describes the spatial component of this record. The event_class
    # describes how the chronology and spatial information go together.
    event_class = models.ForeignKey(
        AllManifest,  
        db_column='event_class_uuid', 
        related_name='+', 
        on_delete=models.PROTECT,
        default=configs.OC_EVENT_TYPE_GENERAL_UUID,
    )

    # Time span information. 
    earliest = models.DecimalField(max_digits=19, decimal_places=5, null=True)
    start = models.DecimalField(max_digits=19, decimal_places=5, null=True)
    stop = models.DecimalField(max_digits=19, decimal_places=5, null=True)
    latest = models.DecimalField(max_digits=19, decimal_places=5, null=True)

    # Location information.
    geometry_type = models.CharField(max_length=50, null=True)
    latitude = models.DecimalField(max_digits=24, decimal_places=21, null=True)
    longitude = models.DecimalField(max_digits=24, decimal_places=21, null=True)
    geo_specificity = models.IntegerField(default=0, null=True)
    geometry = JSONField(default=dict, null=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)

    def validate_times(
        self, 
        earliest=None,
        start=None,
        stop=None,
        latest=None,
    ):
        """
        makes sure time data is properly validated
        """
        raw_time_list = [earliest, start, stop, latest]
        time_list = list(
            set([t for t in raw_time_list if t is not None])
        )
        if not len(time_list):
            return (
                None,
                None,
                None,
                None,
            )

        # Sort the list, then fill in any blanks.
        time_list.sort()
        while len(time_list) < 4:
            time_list.append(max(time_list))

        return (
            min(time_list),
            time_list[1],
            time_list[2],
            max(time_list),
        )
    
    def make_hash_id(
        self, 
        item_id,
        event_id=configs.DEFAULT_EVENT_UUID,
        event_class_id=configs.OC_EVENT_TYPE_GENERAL_UUID,
        earliest=None,
        start=None,
        stop=None,
        latest=None,
        latitude=None,
        longitude=None,
        geometry=None,
    ):
        """Makes a hash_id for an assertion"""
        earliest, start, stop, latest = self.validate_times(
            earliest,
            start,
            stop,
            latest,
        )
        hash_obj = hashlib.sha1()
        concat_string = " ".join(
            [
                str(item_id),
                str(event_id),
                str(event_class_id),
                str(earliest),
                str(start),
                str(stop),
                str(latest),
                str(latitude),
                str(longitude),
                str(geometry),
            ]
        )
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def primary_key_create(
        self, 
        item_id,
        event_id=configs.DEFAULT_EVENT_UUID,
        event_class_id=configs.OC_EVENT_TYPE_GENERAL_UUID,
        earliest=None,
        start=None,
        stop=None,
        latest=None,
        latitude=None,
        longitude=None,
        geometry=None,
    ):
        """Makes a primary key using a prefix from the item"""
        item_uuid = str(item_id)
        item_prefix = item_uuid.split('-')[0]
        
        hash_id = self.make_hash_id(
            item_id=item_id,
            event_id=configs.DEFAULT_EVENT_UUID,
            event_class_id=configs.OC_EVENT_TYPE_GENERAL_UUID,
            earliest=None,
            start=None,
            stop=None,
            latest=None,
            latitude=None,
            longitude=None,
            geometry=None,
        )
        uuid_from_hash_id = str(
            GenUUID.UUID(hex=hash_id[:32])
        )
        new_parts = uuid_from_hash_id.split('-')
        uuid = '-'.join(
            ([item_prefix] + new_parts[1:])
        )
        return uuid

    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the item"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid
        return self.primary_key_create(
            item_id=self.item.uuid,
            event_id=self.event.uuid,
            event_class_id=self.event_class,
            earliest=self.earliest,
            start=self.start,
            stop=self.stop,
            latest=self.latest,
            latitude=self.latitude,
            longitude=self.longitude,
            geometry=self.longitude,
        )
    
    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique event
        """
        self.earliest, self.start, self.stop, self.latest = self.validate_times(
            self.earliest,
            self.start,
            self.stop,
            self.latest,
        )
        # Make sure the project is really a project.
        validate_related_project(project_obj=self.project)
        # Projects, subjects, and types (for periods) can have time space information.
        validate_related_manifest_item_type(
            man_obj=self.item,
            allowed_types= ['projects', 'subjects', 'types', 'uri', 'class'],
            obj_role='item',
        )

        # Validate the event.
        validate_related_manifest_item_type(
            man_obj=self.event,
            allowed_types=['events'],
            obj_role='event',
        )

        # Validate the event type.
        if str(self.event_class.uuid) not in configs.OC_EVENT_TYPE_UUIDS:
            raise ValueError(
                f'{self.event_class.label} is not in allowed event types '
                f'must be: {str(configs.OC_EVENT_TYPE_UUIDS)}'
            )

        self.primary_key_create_for_self()
        super(AllSpaceTime, self).save(*args, **kwargs)
    
    class Meta:
        db_table = 'oc_all_spacetime'
        unique_together = (
            (
                "item", 
                "event",
            ),
            (
                "item",
                "feature_id",
            ),
        )
        ordering = ["item", "feature_id",]

# OCstring stores string content, with each string unique to a project
@reversion.register  # records in this model under version control
class AllString(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    hash_id = models.CharField(max_length=50, unique=True)
    project = models.ForeignKey(
        AllManifest,
        db_column='project_uuid', 
        related_name='+', 
        on_delete=models.CASCADE
    )
    source_id = models.CharField(max_length=50, db_index=True)
    # Note for multilingual text, choose the main language.
    language =  models.ForeignKey(
        AllManifest,
        db_column='language_uuid', 
        related_name='+', 
        on_delete=models.PROTECT, 
        default=configs.DEFAULT_LANG_UUID
    )
    updated = models.DateTimeField(auto_now=True)
    content = models.TextField()
    meta_json = JSONField(default=dict)

    def make_hash_id(
        self, 
        project_id, 
        content, 
        language_id=configs.DEFAULT_LANG_UUID
    ):
        """
        Creates a hash-id to insure unique content for a project and language
        """
        hash_obj = hashlib.sha1()
        concat_string = " ".join(
            [
                str(project_id),
                str(language_id),
                content.strip(),
            ]
        )
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def primary_key_create(
        self, 
        project_id, 
        content, 
        language_id=configs.DEFAULT_LANG_UUID
    ):
        """Deterministically make a primary key using a prefix from the project"""

        # Make the first part from the subject's uuid.
        project_id = str(project_id)
        uuid_prefix = project_id.split('-')[0]

        # Make a hash for this Assertion based on all those parts
        # that need to be unique.
        hash_id = self.make_hash_id(
            project_id=project_id,
            content=content,
            language_id=language_id,
        )
        # Now convert that hash into a uuid. Note, we're only using
        # the first 32 characters. This should still be enough to have
        # really, really high certainty we won't have hash-collisions on
        # data that should not be considered unique. If we run into a problem
        # we can always override this.
        uuid_from_hash_id = str(
            GenUUID.UUID(hex=hash_id[:32])
        )
        new_parts = uuid_from_hash_id.split('-')
        uuid = '-'.join(
            ([uuid_prefix] + new_parts[1:])
        )
        return uuid
    
    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the subject"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid
        return self. primary_key_create(
            project_id=self.project.uuid,
            content=self.content,
            language_id=self.language.uuid,
        )

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique string for a project
        """
        # Make sure the project is really a project.
        validate_related_project(project_obj=self.project)
        # Make sure the language has the right
        # manifest object item_type
        validate_related_manifest_item_type(
            man_obj=self.language,
            allowed_types=['languages'],
            obj_role='language'
        )
        self.content = self.content.strip()
        self.hash_id = self.make_hash_id(
            project_id=self.project.uuid,
            content=self.content,
            language_id=self.language.uuid,
        )
        self.uuid = self.primary_key_create_for_self()
        super(AllString, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_all_strings'
        unique_together = (
            (
                "project", 
                "language",
                "content"
            ),
        )




# ---------------------------------------------------------------------
#  Functions used with the Assertion Model
# ---------------------------------------------------------------------
def get_immediate_concept_parent_objs_db(child_obj):
    """Get the immediate parents of a child manifest object using DB"""
    subj_super_qs = AllAssertion.objects.filter(
        object=child_obj,
        predicate_id__in=(
            configs.PREDICATE_LIST_SBJ_IS_SUPER_OF_OBJ
            + configs.PREDICTATE_LIST_CONTEXT_SBJ_IS_SUPER_OF_OBJ
        ),
    )
    subj_subord_qs = AllAssertion.objects.filter(
        subject=child_obj,
        predicate_id__in=configs.PREDICATE_LIST_SBJ_IS_SUBORD_OF_OBJ,
    )
    all_parents = [a.subject for a in subj_super_qs]
    all_parents += [a.object for a in subj_subord_qs if a.object not in all_parents]
    return all_parents

def get_immediate_concept_children_objs_db(parent_obj):
    """Get the immediate children of a parent manifest object using DB"""
    subj_super_qs = AllAssertion.objects.filter(
        subject=parent_obj,
        predicate_id__in=(
            configs.PREDICATE_LIST_SBJ_IS_SUPER_OF_OBJ
            + configs.PREDICTATE_LIST_CONTEXT_SBJ_IS_SUPER_OF_OBJ
        ),
    )
    subj_subord_qs = AllAssertion.objects.filter(
        object=parent_obj,
        predicate_id__in=configs.PREDICATE_LIST_SBJ_IS_SUBORD_OF_OBJ,
    )
    all_children = [a.object for a in subj_super_qs]
    all_children += [a.subject for a in subj_subord_qs if a.subject not in all_children]
    return all_children

def get_immediate_context_parent_obj_db(child_obj):
    """Get the immediate (spatial) context parent of a child_obj"""
    return AllAssertion.objects.filter(
        predicate_id=configs.PREDICATE_CONTAINS_UUID,
        object=child_obj
    ).first()

def get_immediate_context_children_objs_db(parent_obj):
    """Get the immediate (spatial) context children of a parent_obj"""
    return [
        a.object 
        for a in AllAssertion.objects.filter(
            subject=parent_obj,
            predicate_id=configs.PREDICATE_CONTAINS_UUID,
        )
    ]

def get_immediate_concept_parent_obs(child_obj, use_cache=True):
    """Get the immediate parents of a child manifest object"""
    if not use_cache:
        return get_immediate_concept_parent_objs_db(child_obj)
    cache_key = f'concept-parents-{child_obj.uuid}'
    cache = caches['memory']
    all_parents = cache.get(cache_key)
    if all_parents is not None:
        return all_parents
    # We don't have this cached yet, so get the result from
    # the cache.
    all_parents = get_immediate_concept_parent_objs_db(child_obj)
    try:
        cache.set(cache_key, all_parents)
    except:
        pass
    return all_parents

def get_immediate_concept_children_obs(parent_obj, use_cache=True):
    """Get the immediate children of a parent manifest object"""
    if not use_cache:
        return get_immediate_concept_children_objs_db(parent_obj)
    cache_key = f'concept-children-{parent_obj.uuid}'
    cache = caches['memory']
    all_children = cache.get(cache_key)
    if all_children is not None:
        return all_children
    # We don't have this cached yet, so get the result from
    # the cache.
    all_children = get_immediate_concept_children_objs_db(parent_obj)
    try:
        cache.set(cache_key, all_children)
    except:
        pass
    return all_children

def get_immediate_context_parent_obj(child_obj, use_cache=True):
    """Get the immediate parents of a child manifest object"""
    if not use_cache:
        return get_immediate_context_parent_obj_db(child_obj)
    cache_key = f'context-parent-{child_obj.uuid}'
    cache = caches['memory']
    parent_obj = cache.get(cache_key)
    if parent_obj is not None:
        return parent_obj
    # We don't have this cached yet, so get the result from
    # the cache.
    parent_obj = get_immediate_concept_parent_objs_db(child_obj)
    try:
        cache.set(cache_key, parent_obj)
    except:
        pass
    return parent_obj

def get_immediate_context_children_obs(parent_obj, use_cache=True):
    """Get the immediate children of a parent manifest object"""
    if not use_cache:
        return get_immediate_context_children_objs_db(parent_obj)
    cache_key = f'context-children-{parent_obj.uuid}'
    cache = caches['memory']
    all_children = cache.get(cache_key)
    if all_children is not None:
        return all_children
    # We don't have this cached yet, so get the result from
    # the cache.
    all_children = get_immediate_context_children_objs_db(parent_obj)
    try:
        cache.set(cache_key, all_children)
    except:
        pass
    return all_children


def check_if_obj_is_concept_parent(
    is_a_parent_obj, 
    of_obj, 
    use_cache=True, 
    max_depth=configs.MAX_HIERARCHY_DEPTH
):
    """Checks if is_a_parent_obj is a parent of the of_obj"""
    check_objs = [of_obj]
    i = 0
    while i <= max_depth and len(check_objs):
        i += 1
        parent_objs = []
        for check_obj in check_objs:
            # Add to the list of all the parents.
            parent_objs += get_immediate_concept_parent_obs(
                child_obj=check_obj, 
                use_cache=use_cache
            )
        # Consolidate so to parent objs are unique.
        check_objs = list(set(parent_objs)) 
        for check_obj in check_objs:
            if check_obj == is_a_parent_obj:
               return True
    
    if i > max_depth:
        raise ValueError(
            f'Object {child_obj.uuid} too deep in hierarchy'
        )
    return False


def validate_context_subject_objects(subject_obj, object_obj):
    """Validates the correct item-types for context relations"""
    if subject_obj.item_type != "subjects":
        # Spatial context must be between 2
        # subjects items.
        raise ValueError(
            f'Subject must be item_type="subjects", not '
            f'{subject_obj.item_type} for {subject_obj.uuid}'
        )
    if object_obj.item_type != "subjects":
        # Spatial context must be between 2
        # subjects items.
        raise ValueError(
            f'Object must be item_type="subjects", not '
            f'{object_obj.item_type} for {object_obj.uuid}'
        )
    return True


def validate_context_assertion(
    subject_obj, 
    object_obj,
    max_depth=configs.MAX_HIERARCHY_DEPTH
):
    """Validates a spatial context assertion"""
    validate_context_subject_objects(subject_obj, object_obj)

    obj_parent = get_immediate_context_parent_obj(
        child_obj=object_obj, 
        use_cache=False
    )
    if obj_parent and obj_parent != subject_obj:
        # The child object already has a parent, and
        # we allow only 1 parent.
        raise ValueError(
            f'Object {object_obj.uuid} already contained in '
            f'{obj_parent.label} {obj_parent.uuid}'
        )
    subj_parent = subject_obj
    i = 0
    while i <= max_depth and subj_parent is not None:
        i += 1
        subj_parent = get_immediate_context_parent_obj(
            child_obj=subj_parent, 
            use_cache=False
        )
        if subj_parent == object_obj:
            raise ValueError(
                'Circular containment error. '
                f'(Child) object {object_obj.uuid}: {object_obj.label} is a '
                f'parent object for {subject_obj.uuid}: {subject_obj.label}'
            )
    if i > max_depth:
        raise ValueError(
            f'Parent object {subject_obj.uuid} too deep in hierarchy'
        )
    print(
        f'Context containment OK: '
        f'{subject_obj.uuid}: {subject_obj.label} -> contains -> '
        f'{object_obj.uuid}: {object_obj.label}'
    )
    return True


def validate_hierarchy_assertion(
    subject_obj, 
    predicate_obj, 
    object_obj,
    max_depth=configs.MAX_HIERARCHY_DEPTH,
    use_cache=False,
):
    """Validates an assertion about a hierarchy relationship"""
    subjects_preds = [
        configs.PREDICATE_CONTAINS_UUID,
        configs.PREDICATE_ALSO_CONTAINS_UUID,
    ]
    predicate_uuid = str(predicate_obj.uuid)
    check_preds = (
        configs.PREDICTATE_LIST_CONTEXT_SBJ_IS_SUPER_OF_OBJ
        + configs.PREDICATE_LIST_SBJ_IS_SUBORD_OF_OBJ
        + configs.PREDICATE_LIST_SBJ_IS_SUPER_OF_OBJ
    )
    if predicate_uuid not in check_preds:
        # Valid, not a hierarchy relationship that we
        # need to check
        return True

    if subject_obj == object_obj:
        raise ValueError(
            'An item cannot have a hierarchy relation to itself.'
        )

    if predicate_uuid in configs.PREDICTATE_LIST_CONTEXT_SBJ_IS_SUPER_OF_OBJ:
        # Spatial context relations only allowed between item_type 'subjects'
        validate_context_subject_objects(subject_obj, object_obj)
    
    if predicate_uuid == configs.PREDICATE_CONTAINS_UUID:
        # Do a special spatial context check.
        return validate_context_assertion(
            subject_obj, 
            object_obj,
            predicate_uuid=predicate_uuid,
            max_depth=max_depth
        )
    
    # Everything below is to validate concept hierarchies.
    if predicate_uuid in configs.PREDICATE_LIST_SBJ_IS_SUBORD_OF_OBJ:
        # The subject item is subordinate to the object (parent) item.
        parent_obj = object_obj
        child_obj = subject_obj
    else:
        # The object item is subordinate to the subject (parent) item.
        # This will also apply for checking assertions about the
        # secondary spatial context PREDICATE_ALSO_CONTAINS_UUID
        parent_obj = subject_obj
        child_obj = object_obj
    
    # Check to see if this would be a circular hierarchy. A circular
    # hierarchy would happen if the child_obj happens to be a 
    # parent concept of the parent_obj.
    is_circular = check_if_obj_is_concept_parent(
        is_a_parent_obj=child_obj, 
        of_obj=parent_obj, 
        use_cache=use_cache, 
        max_depth= max_depth
    )
    if is_circular: 
        raise ValueError(
            'Circular hierarchy error. '
            f'(Child) object {child_obj.uuid}: {child_obj.label} is a '
            f'parent object for {parent_obj.uuid}: {parent_obj.label}'
        )

    print(
        f'Concept hierarchy OK: '
        f'{parent_obj.uuid}: {parent_obj.label} -> has child -> '
        f'{child_obj.uuid}: {child_obj.label}'
    )
    return True


def validate_has_unit_assertion(predicate_obj, object_obj):
    """Checks that the object of a cidoc-crm:P91_has_unit is a unit"""
    if str(predicate_obj.uuid) != configs.PREDICATE_CIDOC_HAS_UNIT_UUID:
        # Not a cidoc-crm:P91_has_unit assertion, so skip this
        # validation check.
        return True
    if object_obj.item_type != 'units':
        raise ValueError(
            f'Object {child_obj.label} ({child_obj.uuid}) has item_type of '
            f'"{ object_obj.item_type}"" not "units".'
        )

# AllAssertion stores data about "assertions" made about and using items in the AllManifest
# model. It's a very schema-free / graph like model for representing relationships and
# attributes of items from different sources. But it is not a triple store because we
# have several metadata attributes (publisher, project, observation, event, 
# attribute_group, etc.) that provide additional context to make things hopefully
# easier to manage. 
@reversion.register  # records in this model under version control
class AllAssertion(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    publisher = models.ForeignKey(
        AllManifest, 
        db_column='publisher_uuid',
        related_name='+', 
        on_delete=models.PROTECT, 
        default=configs.OPEN_CONTEXT_PUB_UUID,
    )
    project = models.ForeignKey(
        AllManifest, 
        db_column='project_uuid', 
        related_name='+', 
        on_delete=models.PROTECT, 
        default=configs.OPEN_CONTEXT_PROJ_UUID,
    )
    source_id = models.CharField(max_length=50, db_index=True)
    subject = models.ForeignKey(
        AllManifest, 
        db_column='subject_uuid', 
        related_name='subject_uuid', 
        on_delete=models.CASCADE
    )
    observation = models.ForeignKey(
        AllManifest,  
        db_column='observation_uuid', 
        related_name='+', 
        on_delete=models.PROTECT,
        default=configs.DEFAULT_OBS_UUID,
    )
    obs_sort = models.IntegerField(default=1)
    event = models.ForeignKey(
        AllManifest,  
        db_column='event_uuid', 
        related_name='+', 
        on_delete=models.PROTECT,
        default=configs.DEFAULT_EVENT_UUID,
    )
    event_sort = models.IntegerField(default=1)
    attribute_group = models.ForeignKey(
        AllManifest, 
        db_column='attribute_group_uuid', 
        related_name='+', 
        on_delete=models.PROTECT,
        default=configs.DEFAULT_ATTRIBUTE_GROUP_UUID,
    )
    attribute_group_sort = models.IntegerField(default=1)
    predicate = models.ForeignKey(
        AllManifest, 
        db_column='predicate_uuid',
        related_name='+', 
        on_delete=models.CASCADE
    )
    sort = models.DecimalField(
        max_digits=8, 
        decimal_places=3,
        default=0,
    )
    visible = models.BooleanField(default=True)
    # Estimated probability for an assertion 
    # (with 1 as 100% certain, .001 for very uncertain), null for not determined.
    certainty = models.DecimalField(max_digits=4, decimal_places=3, blank=True, null=True)
    object = models.ForeignKey(
        AllManifest, 
        db_column='object_uuid', 
        related_name='+', 
        on_delete=models.CASCADE, 
        default=configs.DEFAULT_NULL_OBJECT_UUID,
    )
    obj_string = models.ForeignKey(
        AllString, 
        db_column='obj_string_uuid', 
        related_name='+', 
        on_delete=models.CASCADE, 
        default=configs.DEFAULT_NULL_STRING_UUID,
    )
    obj_boolean = models.BooleanField(null=True)
    obj_integer = models.BigIntegerField(null=True)
    obj_double = models.DecimalField(max_digits=19, decimal_places=10, null=True)
    obj_datetime = models.DateTimeField(null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)

    def validate_node_refs(self):
        """Validates references to 'node' manifest objects"""
        checks = [
            (self.observation, ['observations'], 'observation',),
            (self.event, ['events'], 'event',),
            (self.attribute_group, ['attribute-groups'], 'attribute_group',),
        ]
        for relate_obj, allowed_types, obj_role in checks:
            validate_related_manifest_item_type(
                man_obj=relate_obj,
                allowed_types=allowed_types,
                obj_role=obj_role
            )
    
    def validate_predicate(self):
        """Validates predicate is an OK type to be a predicate"""
        # NOTE: For the purposes of this validation, a 
        # an item_type='class' item can act as a predicate (attribute) to make
        # it easier to represent measurements, which are defined as classes
        # in the CIDOC-CRM (see: http://erlangen-crm.org/current/E54_Dimension )
        # In this case, an assertion using a predicate object that is a 
        # measurement class would be read something like:
        # 
        # subject -> has_measurement::dimension::has-value -> 1.1
        #
        # where the has_measurement::dimension::has-value is all implied by
        # within the predicate object of this assertion.
        validate_related_manifest_item_type(
            man_obj=self.predicate,
            allowed_types= ['predicates', 'property', 'class'],
            obj_role='predicate',
        )
    
    def validate_predicate_objects(self):
        """Validates that predicates have objects of the correct type"""
        object_expectations = [
            (
                (self.object.uuid == GenUUID.UUID(str(configs.DEFAULT_NULL_OBJECT_UUID))),
                (self.predicate.data_type == 'id'),
            ),
            (
                (self.obj_string.uuid == GenUUID.UUID(str(configs.DEFAULT_NULL_STRING_UUID))), 
                (self.predicate.data_type == 'xsd:string'),
            ),
            (
                (self.obj_boolean is None),
                (self.predicate.data_type == 'xsd:boolean'),
            ),
            (
                (self.obj_integer is None),
                (self.predicate.data_type == 'xsd:integer'),
            ),
            (
                (self.obj_double is None),
                (self.predicate.data_type == 'xsd:double'),
            ),
            (
                (self.obj_datetime is None),
                (self.predicate.data_type == 'xsd:date'),
            ),
        ]
        for data_type_is_none, should_exist in object_expectations:
            if should_exist:
                assert not data_type_is_none
            else:
                assert data_type_is_none
    
    def make_hash_id(
        self, 
        subject_id,
        predicate_id,
        object_id=None,
        obj_string_id=None,
        obj_boolean=None,
        obj_integer=None,
        obj_double=None,
        obj_datetime=None,
        observation_id=configs.DEFAULT_OBS_UUID,
        event_id=configs.DEFAULT_EVENT_UUID,
        attribute_group_id=configs.DEFAULT_ATTRIBUTE_GROUP_UUID,
    ):
        """Makes a hash_id for an assertion"""
        hash_obj = hashlib.sha1()
        concat_string = " ".join(
            [
                str(subject_id),
                str(observation_id),
                str(event_id),
                str(attribute_group_id),
                str(predicate_id),
                str(object_id),
                str(obj_string_id),
                str(obj_boolean),
                str(obj_integer),
                str(obj_double),
                str(obj_datetime),
            ]
        )
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def primary_key_create(
        self, 
        subject_id,
        predicate_id,
        object_id=None,
        obj_string_id=None,
        obj_boolean=None,
        obj_integer=None,
        obj_double=None,
        obj_datetime=None,
        observation_id=configs.DEFAULT_OBS_UUID,
        event_id=configs.DEFAULT_EVENT_UUID,
        attribute_group_id=configs.DEFAULT_ATTRIBUTE_GROUP_UUID,
    ):
        """Deterministically make a primary key using a prefix from the subject"""

        # Make the first part from the subject's uuid.
        subject_id = str(subject_id)
        uuid_prefix = subject_id.split('-')[0]

        # Make a hash for this Assertion based on all those parts
        # that need to be unique.
        hash_id = self.make_hash_id(
            subject_id=subject_id,
            predicate_id=predicate_id,
            object_id=object_id,
            obj_string_id=obj_string_id,
            obj_boolean=obj_boolean,
            obj_integer=obj_integer,
            obj_double=obj_double,
            obj_datetime=obj_datetime,
            observation_id=observation_id,
            event_id=event_id,
            attribute_group_id=attribute_group_id
        )
        # Now convert that hash into a uuid. Note, we're only using
        # the first 32 characters. This should still be enough to have
        # really, really high certainty we won't have hash-collisions on
        # data that should not be considered unique. If we run into a problem
        # we can always override this.
        uuid_from_hash_id = str(
            GenUUID.UUID(hex=hash_id[:32])
        )
        new_parts = uuid_from_hash_id.split('-')
        uuid = '-'.join(
            ([uuid_prefix] + new_parts[1:])
        )
        return uuid

    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the subject"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid

        object_id = None
        obj_string_id = None,
        if self.object is not None:
            object_id = self.object.uuid
        if self.obj_string is not None:
            obj_string_id = self.obj_string.uuid

        self.uuid = self.primary_key_create(
            subject_id=self.subject.uuid,
            predicate_id=self.predicate.uuid,
            object_id=object_id,
            obj_string_id=obj_string_id,
            obj_boolean=self.obj_boolean,
            obj_integer=self.obj_integer,
            obj_double=self.obj_double,
            obj_datetime=self.obj_datetime,
            observation_id=self.observation.uuid,
            event_id=self.event.uuid,
            attribute_group_id=self.attribute_group.uuid
        )
        return self.uuid 

    def save(self, *args, **kwargs):
        """
        Creates the hash-id on saving to insure a unique string for a project
        """
        # Make sure the project is really a project.
        validate_related_project(project_obj=self.project)
        # Make sure that nodes in this assertion have the expected item_types.
        self.validate_node_refs()
        # Make sure the predicate is a predicate or property item_type
        self.validate_predicate()

        self.uuid = self.primary_key_create_for_self()
        # Make sure that the data_type expected of the predicate is enforced.
        self.validate_predicate_objects()
        # Make sure hierarchy assertions are valid, not circular
        validate_hierarchy_assertion(
            subject_obj=self.subject, 
            predicate_obj=self.predicate, 
            object_obj=self.object,
        )
        # Make sure assertions about units of measure are valid.
        validate_has_unit_assertion(
            predicate_obj=self.predicate,
            object_obj=self.object
        )

        super(AllAssertion, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_all_assertions'
        unique_together = (
            (
                "subject", 
                "observation",
                "event",
                "attribute_group",
                "predicate",
                "object", 
                "obj_string",
                "obj_boolean",
                "obj_integer",
                "obj_double",
                "obj_datetime"
            ),
        )
        ordering = ["subject", "obs_sort", "event_sort", "attribute_group_sort", "sort"]



# ---------------------------------------------------------------------
# Functions for Resources
# ---------------------------------------------------------------------
def validate_resourcetype_id(resourcetype_id, raise_on_fail=True):
    """Validates the resource type against a configured list of valid class entities"""
    resourcetype_id = str(resourcetype_id)
    if resourcetype_id in configs.OC_RESOURCE_TYPES_UUIDS:
        return True
    if not raise_on_fail:
        return False
    raise ValueError(
        f'Resourcetype {resourcetype_id} not in valid list: {str(configs.OC_RESOURCE_TYPES_UUIDS)}'
    )


def get_media_type_obj(uri, raw_media_type):
    """Gets a media-type manifest object"""
    media_type_qs = AllManifest.objects.filter(
        item_type='media-types'
    )
    if raw_media_type:
        media_type_obj = media_type_qs.filter(
                Q(meta_json__template=raw_media_type)
                | 
                Q(item_key=f'media-type:{raw_media_type}')
            ).first()
        return media_type_obj

    # Guess by file extension. We can add to this as needed,
    # but for now, we're only guessing media type of Nexus
    # 3D format file extensions.
    guesses = [
        ('nxs', configs.MEDIA_NEXUS_3D_NXS_UUID, ),
        ('nxz', configs.MEDIA_NEXUS_3D_NXZ_UUID, ),
    ]
    uri = uri.lower()
    for extension, uuid in guesses:
        if not uri.endswith(f'.{extension}'):
            continue
        # Return the media_object for this extention
        return media_type_qs.filter(
            uuid=uuid
        ).first()
    return None


def get_web_resource_head_info(uri, redirect_ok=False, retry=True, protocol='https://'):
    """Gets header information about a web resource"""
    sleep(0.3)
    output = {}
    try:
        raw_media_type = None
        uri = AllManifest().clean_uri(uri)
        uri = protocol + uri
        r = requests.head(uri)
        if (
            (r.status_code == requests.codes.ok) 
            or
            (redirect_ok and r.status_code >= 300 and r.status_code <= 310)
        ):
            if r.headers.get('Content-Length'):
                output['filesize'] = int(r.headers['Content-Length'])
            if r.headers.get('Content-Type'):
                raw_media_type = r.headers['Content-Type']
                if ':' in raw_media_type:
                    raw_media_type = raw_media_type.split(':')[-1].strip()
            output['mediatype'] = get_media_type_obj(uri, raw_media_type)
    except:
        pass
    
    if retry and not output.get('filesize'):
        output = get_web_resource_head_info(
            uri,
            redirect_ok=redirect_ok,
            retry= False
        )
        if not output.get('filesize'):
            # Now try again without the https.
            output = get_web_resource_head_info(
                uri,
                redirect_ok=redirect_ok,
                retry= False,
                protocol='http://'
            )
    return output


# Records files (usually media files, like images, but )
@reversion.register  # records in this model under version control
class AllResource(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    item = models.ForeignKey(
        AllManifest, 
        db_column='item_uuid', 
        related_name='+', 
        on_delete=models.PROTECT
    )
    project = models.ForeignKey(
        AllManifest, 
        db_column='project_uuid', 
        related_name='+', 
        on_delete=models.PROTECT, 
    )
    resourcetype = models.ForeignKey(
        AllManifest, 
        db_column='resourcetype_uuid', 
        related_name='+', 
        on_delete=models.PROTECT,
    )
    mediatype = models.ForeignKey(
        AllManifest, 
        db_column='mediatype_uuid', 
        related_name='+', 
        on_delete=models.PROTECT, 
        null=True
    )
    source_id = models.CharField(max_length=50, db_index=True)
    uri = models.CharField(max_length=400)
    sha256_checksum = models.CharField(max_length=200, null=True)
    filesize = models.DecimalField(max_digits=19, decimal_places=3, null=True)
    rank = models.IntegerField(default=0)
    is_static = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)

    def make_hash_id(
        self, 
        item_id,
        resourcetype_id,
        rank=0,
    ):
        """Makes a hash_id for an assertion"""
        hash_obj = hashlib.sha1()
        concat_string = " ".join(
            [
                str(item_id),
                str(resourcetype_id),
                str(rank),
            ]
        )
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def primary_key_create(self, item_id, resourcetype_id, rank=0):
        """Makes a primary key using a prefix from the item"""
        item_uuid = str(item_id)
        item_prefix = item_uuid.split('-')[0]
        
        hash_id = self.make_hash_id(
            item_id=item_id,
            resourcetype_id=resourcetype_id,
            rank=rank,
        )
        uuid_from_hash_id = str(
            GenUUID.UUID(hex=hash_id[:32])
        )
        new_parts = uuid_from_hash_id.split('-')
        uuid = '-'.join(
            ([item_prefix] + new_parts[1:])
        )
        return uuid

    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the item"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid
        return self.primary_key_create(
            item_id=self.item.uuid,
            resourcetype_id=self.resourcetype.uuid,
            rank=self.rank
        )

    def save(self, *args, **kwargs):
        """
        Makes the primary key sorted for the first part
        of the item uuid
        """
        self.uuid = self.primary_key_create_for_self()
        self.uri = AllManifest().clean_uri(self.uri)
        # Make sure the project is really a project.
        validate_related_project(project_obj=self.project)
        # Make sure the associated item has the right types
        validate_related_manifest_item_type(
            man_obj=self.item,
            allowed_types=['media', 'uri',],
            obj_role='item'
        )
        # Make sure the resource type is in a pre-configured
        # list of valid resource types.
        validate_resourcetype_id(
            resourcetype_id=self.resourcetype.uuid
        )
        
        # Make an HTTP head request to get filesize and/or
        # mediatype if missing.
        head = None
        if not self.filesize or not self.mediatype:
            head = get_web_resource_head_info(
                self.uri
            )
        if head is not None and not self.filesize:
            self.filesize = head.get('filesize')
        if head is not None and not self.mediatype:
            self.mediatype = head.get('mediatype')

        # If given, make sure the item mimetype
        # has the correct manifest item_type.
        if self.mediatype:
            validate_related_manifest_item_type(
                man_obj=self.mediatype,
                allowed_types=['media-types'],
                obj_role='mediatype'
            )

        super(AllResource, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_all_resources'
        unique_together = (
            (
                "item", 
                "resourcetype",
                "rank",
            ),
        )
        ordering = ["item", "rank", "resourcetype",]


# Records a hash history of an item for use in version control.
@reversion.register  # records in this model under version control
class AllHistory(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    sha1_hash = models.CharField(max_length=50, unique=True)
    item = models.ForeignKey(
        AllManifest, 
        db_column='item_uuid', 
        related_name='+', 
        on_delete=models.CASCADE
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)

    def primary_key_create(self, item_id, sha1_hash):
        """Makes a primary key using a prefix from the item"""
        item_uuid = str(item_id)
        item_prefix = item_uuid.split('-')[0]
        
        uuid_from_hash_id = str(
            GenUUID.UUID(hex=sha1_hash[:32])
        )
        new_parts = uuid_from_hash_id.split('-')
        uuid = '-'.join(
            ([item_prefix] + new_parts[1:])
        )
        return uuid

    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the item"""
        if self.uuid:
            return self.uuid
        return self.primary_key_create(
            item_id=self.item.uuid, 
            sha1_hash=self.sha1_hash,
        )

    def save(self, *args, **kwargs):
        """
        Makes the primary key sorted for the first part
        of the subject uuid
        """
        self.uuid = self.primary_key_create_for_self()
        # Make sure the item has the right
        # manifest object item_type (open context items)
        validate_related_manifest_item_type(
            man_obj=self.item,
            allowed_types=configs.OC_ITEM_TYPES,
            obj_role='item'
        )
        super(AllHistory, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_all_history'
        ordering = ["item", "updated",]


# Records identifiers associated with oc_items.
@reversion.register  # records in this model under version control
class AllIdentifier(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    item = models.ForeignKey(
        AllManifest, 
        db_column='item_uuid', 
        related_name='+', 
        on_delete=models.CASCADE
    )
    scheme = models.CharField(max_length=10)
    rank = models.IntegerField(default=0)
    id =  models.CharField(max_length=300)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)

    def make_hash_id(self, item_id, scheme, rank=0):
        """Makes a hash_id for an assertion"""
        hash_obj = hashlib.sha1()
        concat_string = " ".join(
            [
                str(item_id),
                str(scheme),
                str(rank),
            ]
        )
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def primary_key_create(self, item_id, scheme, rank=0):
        """Makes a primary key using a prefix from the item"""
        item_uuid = str(item_id)
        item_prefix = item_uuid.split('-')[0]
        
        hash_id = self.make_hash_id(
            item_id=item_id,
            scheme=scheme,
            rank=rank,
        )
        uuid_from_hash_id = str(
            GenUUID.UUID(hex=hash_id[:32])
        )
        new_parts = uuid_from_hash_id.split('-')
        uuid = '-'.join(
            ([item_prefix] + new_parts[1:])
        )
        return uuid

    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the item"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid
        return self.primary_key_create(
            item_id=self.item.uuid,
            scheme=self.scheme,
            rank=self.rank
        )

    def save(self, *args, **kwargs):
        """
        Makes the primary key sorted for the first part
        of the subject uuid
        """
        self.uuid = self.primary_key_create_for_self()
        if self.scheme not in configs.IDENTIFIER_SCHEMES:
            raise ValueError(
                f'ID scheme {self.scheme} not in {str(configs.IDENTIFIER_SCHEMES)}'
            )
        # Make sure the item has the right
        # manifest object item_type (open context items)
        validate_related_manifest_item_type(
            man_obj=self.item,
            allowed_types=configs.OC_ITEM_TYPES,
            obj_role='item'
        )
        super(AllIdentifier, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_all_identifiers'
        unique_together = (
            (
                "item", 
                "scheme",
                "rank",
            ),
            (
                "scheme",
                "id",
            ),
        )
        ordering = ["item", "rank", "scheme",]