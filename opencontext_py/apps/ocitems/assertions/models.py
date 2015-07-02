import hashlib
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from django.db import models


# Assertions store descriptions and linking relations for Open Context items
# Assertion data mainly represents data contributed from data authors, not OC editors
class Assertion(models.Model):
    # standard predicate for project root children
    PREDICATES_PROJ_ROOT = 'oc-gen:contains-root'
    # standard predicate for spatial containment
    PREDICATES_CONTAINS = 'oc-gen:contains'
    # standard predicate for generic link
    PREDICATES_LINK = 'oc-3'
    # standard predicate for a link relation that's from the object
    # use this to not make the subject too cluttered with visible links
    # this is provisional, I may decide this is stupid beyond hope
    PREDICATES_LINKED_FROM = 'oc-gen:is-linked-from'
    hash_id = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50, db_index=True)
    subject_type = models.CharField(max_length=50, choices=settings.ITEM_TYPES)
    project_uuid = models.CharField(max_length=50)
    source_id = models.CharField(max_length=50, db_index=True)
    obs_node = models.CharField(max_length=50)
    obs_num = models.IntegerField()
    sort = models.DecimalField(max_digits=8, decimal_places=3)
    visibility = models.IntegerField()
    predicate_uuid = models.CharField(max_length=50, db_index=True)
    object_uuid = models.CharField(max_length=50, db_index=True)
    object_type = models.CharField(max_length=50)
    data_num = models.DecimalField(max_digits=19, decimal_places=10, blank=True)
    data_date = models.DateTimeField(blank=True)
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of uuids, obs_nums, predicates, and objects
        """
        hash_obj = hashlib.sha1()
        concat_string = str(self.uuid) + " " + str(self.obs_num) + " " + str(self.predicate_uuid) + " "
        concat_string = concat_string + str(self.object_uuid) + " " + str(self.data_num) + " " + str(self.data_date)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique assertion
        """
        self.hash_id = self.make_hash_id()
        if self.created is None:
            self.created = timezone.now()
        super(Assertion, self).save(*args, **kwargs)

    def sort_save(self):
        """
        save only sorting value
        """
        super(Assertion, self).save(update_fields=['sort'])

    class Meta:
        db_table = 'oc_assertions'
        ordering = ['uuid', 'sort']
