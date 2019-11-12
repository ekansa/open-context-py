import pytz
import time
import hashlib
import reversion  # version control object
import collections
from jsonfield import JSONField  # json field for complex objects
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from django.db import models


# Assertions store descriptions and linking relations for Open Context items
# Assertion data mainly represents data contributed from data authors, not OC editors
@reversion.register  # records in this model under version control
class Assertion(models.Model):
    # standard predicate for project root children
    PREDICATES_PROJ_ROOT = 'oc-gen:contains-root'
    # standard predicate for spatial containment
    PREDICATES_CONTAINS = 'oc-gen:contains'
    # standard predicate for generic link
    PREDICATES_LINK = 'oc-3'
    # standard predicate for a note
    PREDICATES_NOTE = 'oc-gen:has-note'
    # standard predicate for a link relation that's from the object
    # use this to not make the subject too cluttered with visible links
    # this is provisional, I may decide this is stupid beyond hope
    PREDICATES_LINKED_FROM = 'oc-gen:is-linked-from'
    # standard predicate for a link between an item and a geospatial bitmap image
    PREDICATES_GEO_OVERLAY = 'oc-gen:has-geo-overlay'
    
    hash_id = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50, db_index=True)
    subject_type = models.CharField(max_length=50, choices=settings.ITEM_TYPES)
    project_uuid = models.CharField(max_length=50)
    source_id = models.CharField(max_length=50, db_index=True)
    obs_node = models.CharField(max_length=50)
    obs_num = models.IntegerField()
    sort = models.DecimalField(max_digits=8, decimal_places=3)
    visibility = models.IntegerField()
    # estimated probability for an assertion (with 1 as 100% certain, .001 for very uncertain), 0 for not determined.
    certainty = models.DecimalField(max_digits=4, decimal_places=3)
    predicate_uuid = models.CharField(max_length=50, db_index=True)
    object_uuid = models.CharField(max_length=50, db_index=True)
    object_type = models.CharField(max_length=50)
    data_num = models.DecimalField(max_digits=19, decimal_places=10, blank=True)
    data_date = models.DateTimeField(blank=True)
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)
    sup_json = JSONField(default={},
                         load_kwargs={'object_pairs_hook': collections.OrderedDict},
                         blank=True)

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of uuids, obs_nums, predicates, and objects
        """
        uuid = str(self.uuid)
        hash_obj = hashlib.sha1()
        concat_string = uuid + " " + str(self.obs_num) + " " + str(self.predicate_uuid) + " "
        concat_string = concat_string + str(self.object_uuid) + " " + str(self.data_num) + " " + str(self.data_date)
        hash_obj.update(concat_string.encode('utf-8'))
        raw_hash = hash_obj.hexdigest()
        if len(uuid) > 8:
            # this helps keep uuids together on the table, reduces DB lookup time
            hash_id = uuid[0:8] + '-' + raw_hash[0:34]
        else:
            hash_id = uuid + '-' + raw_hash
        return hash_id

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique assertion
        """
        self.hash_id = self.make_hash_id()
        if self.created is None:
            self.created = timezone.now()
        if self.certainty is None:
            self.certainty = 0
        if isinstance(self.data_date, datetime):
            if timezone.is_naive(self.data_date):
                self.data_date = pytz.utc.localize(self.data_date)
        if isinstance(self.created, datetime):
            if timezone.is_naive(self.created):
                self.created = pytz.utc.localize(self.created)
        if isinstance(self.updated, datetime):
            if timezone.is_naive(self.updated):
                self.updated = pytz.utc.localize(self.updated)
        super(Assertion, self).save(*args, **kwargs)

    def sort_save(self):
        """
        save only sorting value
        """
        super(Assertion, self).save(update_fields=['sort'])

    class Meta:
        db_table = 'oc_assertions'
        ordering = ['uuid', 'sort']
