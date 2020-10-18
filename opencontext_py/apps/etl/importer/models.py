import hashlib
import pytz
import time
import re

import uuid as GenUUID

from datetime import datetime
from math import pow
from time import sleep
from unidecode import unidecode

from django.conf import settings
from django.core.cache import caches

from django.db import models
from django.db.models import Q

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

# These are the "target schema" models.
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items.legacy_all import update_old_id



# Records data sources for ETL (extract transform load)
# processes that ingest data into Open Context
class DataSource(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    publisher = models.ForeignKey(
        AllManifest, 
        db_column='publisher_uuid',
        related_name='+', 
        on_delete=models.CASCADE, 
        default=configs.OPEN_CONTEXT_PUB_UUID,
    )
    project = models.ForeignKey(
        AllManifest, 
        db_column='project_uuid', 
        related_name='+', 
        on_delete=models.CASCADE, 
        default=configs.OPEN_CONTEXT_PROJ_UUID,
    )
    source_id = models.TextField(unique=True)
    label = models.TextField()
    field_count = models.IntegerField()
    row_count = models.IntegerField()
    source_type = models.TextField()
    is_current = models.BooleanField(default=None)
    status = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)

    def primary_key_create(self, source_id):
        """Converts a source_id into a UUID deterministically"""
        _, uuid = update_old_id(source_id)
        return uuid
    
    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the subject"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid
        return self.primary_key_create(self.source_id)
    
    def save(self, *args, **kwargs):
        # Defaults the primary key uuid to value deterministically
        # generated.
        self.uuid = self.primary_key_create_for_self()
        super(DataSource, self).save(*args, **kwargs)
    
    class Meta:
        db_table = 'etl_sources'
        ordering = ['-updated']



# Records data source fields for ETL (extract transform load)
# processes that ingest data into Open Context
class DataSourceField(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    data_source = models.ForeignKey(
        DataSource, 
        db_column='source_uuid', 
        related_name='+', 
        on_delete=models.CASCADE, 
    )
    field_num = models.IntegerField()
    label = models.TextField()
    ref_name = models.TextField()
    ref_orig_name = models.TextField()
    item_type = models.TextField()
    data_type = models.TextField()
    item_class = models.ForeignKey(
        AllManifest, 
        db_column='item_class_uuid', 
        related_name='+', 
        on_delete=models.CASCADE, 
        default=configs.DEFAULT_CLASS_UUID,
    )
    value_prefix = models.TextField()
    unique_count = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)

    def primary_key_create(self, data_source_id, field_num):
        """Converts a source_id into a UUID deterministically"""
        data_source_id = str(data_source_id)
        source_field = f'{data_source_id }-{field_num}'
        _, uuid_from_field = update_old_id(source_field)
        
        # Now assemble a uuid that has the first part of the
        # data source id and the unique part generated from the
        # data source id and the field num
        id_prefix = data_source_id.split('-')[0]
        new_parts = uuid_from_field.split('-')
        uuid = '-'.join(
            ([id_prefix] + new_parts[1:])
        )
        return uuid
    
    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the subject"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid
        return self.primary_key_create(self.data_source.uuid, self.field_num)

    def save(self, *args, **kwargs):
        # Defaults the primary key uuid to value deterministically
        # generated.
        self.uuid = self.primary_key_create_for_self()
        super(DataSourceField, self).save(*args, **kwargs)

    class Meta:
        db_table = 'etl_fields'
        ordering = ['data_source', 'field_num']
        unique_together = ('data_source', 'field_num')



# Records data source annotations for modeling ETL (extract transform load)
# processes that ingest data into Open Context
class DataSourceAnnotation(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    data_source = models.ForeignKey(
        DataSource, 
        db_column='source_uuid', 
        related_name='+', 
        on_delete=models.CASCADE, 
    )
    subject_field = models.ForeignKey(
        DataSourceField, 
        db_column='subject_field_uuid', 
        related_name='+', 
        on_delete=models.CASCADE,
    )
    predicate = models.ForeignKey(
        AllManifest, 
        db_column='predicate_uuid', 
        related_name='+', 
        on_delete=models.CASCADE,
        null=True,
    )
    predicate_field = models.ForeignKey(
        DataSourceField,
        db_column='predicate_field_uuid', 
        related_name='+', 
        on_delete=models.CASCADE,
        null=True,
    )
    object = models.ForeignKey(
        AllManifest, 
        db_column='object_uuid', 
        related_name='+', 
        on_delete=models.CASCADE,
        null=True,
    )
    object_field = models.ForeignKey(
        DataSourceField,
        db_column='object_field_uuid', 
        related_name='+', 
        on_delete=models.CASCADE,
        null=True,
    )
    # Observations are nodes for grouping related assertions.
    observation = models.ForeignKey(
        AllManifest,  
        db_column='observation_uuid', 
        related_name='+', 
        on_delete=models.PROTECT,
        default=configs.DEFAULT_OBS_UUID,
    )
    observation_field = models.ForeignKey(
        DataSourceField,
        db_column='observation_field_uuid', 
        related_name='+', 
        on_delete=models.CASCADE,
        null=True,
    )
    # Events are nodes for identifying specific space-time grouped
    # assertions.
    event = models.ForeignKey(
        AllManifest,  
        db_column='event_uuid', 
        related_name='+', 
        on_delete=models.PROTECT,
        default=configs.DEFAULT_EVENT_UUID,
    )
    event_field = models.ForeignKey(
        DataSourceField,
        db_column='event_field_uuid', 
        related_name='+', 
        on_delete=models.CASCADE,
        null=True,
    )
    # Attribute groups are for modeling predicate and object values
    # that need to be understood as a group. For example, a ratio
    # with a numerator and a denominator are 3 grouped assertions that
    # would make sense together in an attribute group.
    attribute_group = models.ForeignKey(
        AllManifest, 
        db_column='attribute_group_uuid', 
        related_name='+', 
        on_delete=models.PROTECT,
        default=configs.DEFAULT_ATTRIBUTE_GROUP_UUID,
    )
    attribute_group_field = models.ForeignKey(
        DataSourceField,
        db_column='attribute_group_field_uuid', 
        related_name='+', 
        on_delete=models.CASCADE,
        null=True,
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    meta_json = JSONField(default=dict)



# Records data source individual records for ETL (extract transform load)
# processes that ingest data into Open Context
class DataSourceRecord(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=True)
    data_source = models.ForeignKey(
        DataSource, 
        db_column='source_uuid', 
        related_name='+', 
        on_delete=models.CASCADE, 
    )
    row_num = models.IntegerField()
    field_num = models.IntegerField()
    context_uuid = models.ForeignKey(
        AllManifest, 
        db_column='context_uuid', 
        related_name='+', 
        on_delete=models.CASCADE,
        null=True,
    )
    record_uuid = models.ForeignKey(
        AllManifest, 
        db_column='record_uuid', 
        related_name='+', 
        on_delete=models.CASCADE,
        null=True,
    )
    record = models.TextField(default='')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def primary_key_create(self, data_source_id, row_num, field_num):
        """Converts a source_id into a UUID deterministically"""
        data_source_id = str(data_source_id)
        source_row_field = f'{data_source_id }-{row_num}-{field_num}'
        _, uuid_from_field = update_old_id(source_row_field)
        
        # Now assemble a uuid that has the first part of the
        # data source id and the unique part generated from the
        # data source id and the field num
        id_prefix = data_source_id.split('-')[0]
        new_parts = uuid_from_field.split('-')
        uuid = '-'.join(
            ([id_prefix] + new_parts[1:])
        )
        return uuid
    
    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the subject"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid
        return self.primary_key_create(
            self.data_source.uuid, 
            self.row_num, 
            self.field_num
        )
    
    def save(self, *args, **kwargs):
        # Defaults the primary key uuid to value deterministically
        # generated.
        self.uuid = self.primary_key_create_for_self()
        super(DataSourceRecord, self).save(*args, **kwargs)

    class Meta:
        db_table = 'etl_records'
        ordering = ['data_source', 'row_num', 'field_num']
        unique_together = ('data_source', 'row_num', 'field_num')