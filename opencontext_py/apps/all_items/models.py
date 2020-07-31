import hashlib
import pytz
import time
import re
import roman
import reversion  # version control object
import uuid as GenUUID
from datetime import datetime
from math import pow
from unidecode import unidecode

from django.db import models
from django.contrib.postgres.fields import ArrayField, JSONField
from django.template.defaultfilters import slugify
from django.utils import timezone

from django.conf import settings

# Manifest provides basic item metadata for all open context items that get a URI
@reversion.register  # records in this model under version control
class AllManifest(models.Model):

    # Item types with UUIDs as the main identifier for Open Context.
    UUID_ITEM_TYPES = [
        'subjects',
        'media',
        'documents',
        'projects', 
        'persons',
        'types',
        'predicates',
        'tables',
    ]

    # Item types that are not resolvable on their own (they are nodes
    # in some context of another item type)
    NODE_ITEM_TYPES = [
        'observations',
        'attribute-groups',
    ]

    # Item type with full URIs as the main identifer.
    URI_ITEM_TYPES = [
        'vocabularies',
        'publishers',
        'class', # A classification type
        'property', # An attribute or linking relation.
        'uri',  # Usually for an instance.
    ]

    ITEM_TYPES = UUID_ITEM_TYPES + NODE_ITEM_TYPES + URI_ITEM_TYPES

    DATA_TYPES = [
        'id',
        'group',
        'xsd:boolean',
        'xsd:date',
        'xsd:double',
        'xsd:integer',
        'xsd:string',
    ]

    uuid = models.UUIDField(primary_key=True, default=GenUUID.uuid4, editable=True)
    publisher = models.ForeignKey(
        'self', 
        db_column='publisher_uuid', 
        related_name='+', 
        on_delete=models.PROTECT, 
        null=True
    )
    project = models.ForeignKey(
        'self', 
        db_column='project_uuid', 
        related_name='+', 
        on_delete=models.PROTECT, 
        null=True
    )
    item_class = models.ForeignKey(
        'self',
        db_column='item_class_uuid', 
        related_name='+', 
        on_delete=models.PROTECT, 
        null=True
    )
    source_id = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50)
    data_type = models.CharField(max_length=50, default='id')
    slug = models.SlugField(max_length=70, unique=True)
    label = models.CharField(max_length=200)
    sort = models.SlugField(max_length=70, db_index=True)
    views = models.IntegerField()
    indexed = models.DateTimeField(blank=True, null=True)
    vcontrol = models.DateTimeField(blank=True, null=True)
    archived = models.DateTimeField(blank=True, null=True)
    published = models.DateTimeField(db_index=True)
    revised = models.DateTimeField(db_index=True)
    updated = models.DateTimeField(auto_now=True)
    # Note the URI will strip the https:// or http://.
    uri = models.CharField(max_length=300, unique=True)
    # Preferred key when used in JSON-LD.
    item_key = models.CharField(max_length=300, blank=True, null=True)
    identifiers = ArrayField(models.CharField(max_length=200), blank=True, null=True)
    # Hash ID has special logic to ensure context dependent uniqueness
    # especially based on the contents of the context field.
    hash_id = models.CharField(max_length=50, unique=True)
    context = models.ForeignKey(
        'self', 
        db_column='context_uuid', 
        related_name='+', 
        on_delete=models.PROTECT, 
        blank=True, 
        null=True
    )
    path = models.CharField(max_length=500, db_index=True)
    # Meta_json is where we store occasionally used attributes, such
    # as multi-lingual localization values or some metadata about
    # data loading, etc.
    meta_json = JSONField(default=dict)

    def clean_label(self, label, item_type='subjects'):
        label = label.trim()
        if item_type == 'subjects':
            # So as not to screw up depth of contexts.
            label = label.replace('/', '--')
        if len(label) > 195:
            label = label[:192] + '...'
        return label
    
    def clean_uri(self, uri):
        if not uri:
            return None
        uri = uri.trim()
        # Trim off the http: or https: prefix.
        for prefix in ['http://', 'https://']:
            if not uri.startswith(prefix):
                continue
            uri = self.uri[len(prefix):]
        # Remove trailing suffixes that have no meaning.
        for suffix in ['/', '#']:
            if not uri.endswith(suffix):
                continue
            uri = self.uri[0:-1]
        return uri

    def make_hash_id(self):
        """
        Creates a hash-id to insure context dependent uniqueness
        """
        hash_obj = hashlib.sha1()
        concat_string = "{} {} {} {} {} {}".format(
            self.project_uuid,
            self.context_uuid,
            self.item_type,
            self.data_type,
            self.label,
            self.path
        )
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def validate_from_list(self, option, options, raise_on_error=True):
        if option in options:
            # This is a valid option
            return True
        if raise_on_error:
            raise ValueError('{} not valid, must be in {}'.format(option, str(options)))
        # This is not a valid option
        return False

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique string for a project
        """
        self.label = self.clean_label(self.label, self.item_type)
        self.uri = self.clean_uri(self.uri)
        self.hash_id = self.make_hash_id()
        # Make sure the item_type is valid.
        self.validate_from_list(
            self.item_type, self.ITEM_TYPES

        )
        # Make sure the data_type is valid.
        self.validate_from_list(
            self.data_type, self.DATA_TYPES

        )
        super(AllManifest, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_all_manifest'
        unique_together = (("item_type", "slug"),)


# OCstring stores string content, with each string unique to a project
@reversion.register  # records in this model under version control
class AllString(models.Model):
    uuid = models.UUIDField(primary_key=True, default=GenUUID.uuid4, editable=True)
    hash_id = models.CharField(max_length=50, unique=True)
    project = models.ForeignKey(AllManifest, on_delete=models.CASCADE)
    source_id = models.CharField(max_length=50, db_index=True)
    updated = models.DateTimeField(auto_now=True)
    content = models.TextField()
    meta_json = JSONField(default=dict)

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of project_uuids and content
        """
        hash_obj = hashlib.sha1()
        concat_string = self.project_uuid + " " + self.content
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique string for a project
        """
        self.hash_id = self.make_hash_id()
        super(AllString, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_all_strings'


# AllAssertion stores data about "assertions" made about and using items in the AllManifest
# model. It's a very schema-free / graph like model for representing relationships and
# attributes of items from different sources. But it is not a triple store because we
# have several metadata attributes (publisher, project, observation, attribute_group, etc)
# that 
@reversion.register  # records in this model under version control
class AllAssertion(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    publisher = models.ForeignKey(
        AllManifest, 
        db_column='publisher_uuid',
        related_name='+', 
        on_delete=models.PROTECT, 
        null=True
    )
    project = models.ForeignKey(
        AllManifest, 
        db_column='project_uuid', 
        related_name='+', 
        on_delete=models.PROTECT, 
        null=True
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
        on_delete=models.PROTECT
    )
    obs_sort = models.IntegerField()
    attribute_group = models.ForeignKey(
        AllManifest, 
        db_column='attribute_group_uuid', 
        related_name='+', 
        on_delete=models.PROTECT
    )
    attribute_group_sort = models.IntegerField()
    predicate = models.ForeignKey(
        AllManifest, 
        db_column='predicate_uuid',
        related_name='+', 
        on_delete=models.CASCADE
    )
    sort = models.DecimalField(
        max_digits=8, 
        decimal_places=3
    )
    visible = models.BooleanField(default=True)
    # Estimated probability for an assertion 
    # (with 1 as 100% certain, .001 for very uncertain), 0 for not determined.
    certainty = models.DecimalField(max_digits=4, decimal_places=3, blank=True, null=True)
    object = models.ForeignKey(
        AllManifest, 
        db_column='object_uuid', 
        related_name='+', 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True
    )
    obj_string = models.ForeignKey(
        AllString, 
        db_column='obj_string_uuid', 
        related_name='+', 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True
    )
    obj_boolean = models.BooleanField(blank=True, null=True)
    obj_integer = models.BigIntegerField(blank=True, null=True)
    obj_double = models.DecimalField(max_digits=19, decimal_places=10, blank=True)
    obj_datetime = models.DateTimeField(blank=True, null=True)
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)

    def primary_key_create(self):
        """Makes a primary key using a prefix from the subject"""
        if self.uuid:
            return self.uuid
        subject_uuid = str(self.subject_uuid)
        subject_prefix = subject_uuid.split('-')[0]
        new_uuid = str(GenGenUUID.uuid4())
        new_parts = new_uuid.split('-')
        self.uuid = '-'.join(
            ([subject_prefix] + new_parts[1:])
        )

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique string for a project
        """
        self.uuid = self.primary_key_create()
        self.hash_id = self.make_hash_id()
        super(AllAssertion, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_all_assertions'
        unique_together = (
            (
                "subject", 
                "observation", 
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

# Records a hash history of an item for use in version control.
@reversion.register  # records in this model under version control
class AllHistory(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    hash_item = models.CharField(max_length=50, unique=True)
    project = models.ForeignKey(
        AllManifest, 
        db_column='project_uuid', 
        related_name='+', 
        on_delete=models.PROTECT, 
        null=True
    )
    subject = models.ForeignKey(
        AllManifest, 
        db_column='subject_uuid', 
        related_name='subject_uuid', 
        on_delete=models.CASCADE
    )
    updated = models.DateTimeField(auto_now=True)

    def primary_key_create(self):
        """Makes a primary key using a prefix from the subject"""
        if self.uuid:
            return self.uuid
        subject_uuid = str(self.subject_uuid)
        subject_prefix = subject_uuid.split('-')[0]
        new_uuid = str(GenGenUUID.uuid4())
        new_parts = new_uuid.split('-')
        self.uuid = '-'.join(
            ([subject_prefix] + new_parts[1:])
        )

    def save(self, *args, **kwargs):
        """
        Makes the primary key sorted for the first part
        of the subject uuid
        """
        self.uuid = self.primary_key_create()
        super(AllHistory, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_all_history'