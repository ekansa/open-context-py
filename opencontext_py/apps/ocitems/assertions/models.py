import hashlib
from django.conf import settings
from django.db import models


# Assertions store descriptions and linking relations for Open Context items
# Assertion data mainly represents data contributed from data authors, not OC editors
class Assertion(models.Model):
    #stored in the database
    hash_id = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50, db_index=True)
    subject_type = models.CharField(max_length=50, choices=settings.ITEM_TYPES)
    project_uuid = models.CharField(max_length=50)
    source_id = models.CharField(max_length=50)
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
        concat_string = self.uuid + " " + str(self.obs_num) + " " + self.predicate_uuid + " "
        concat_string = concat_string + self.object_uuid + " " + str(self.data_num) + " " + str(self.data_date)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self):
        """
        creates the hash-id on saving to insure a unique assertion
        """
        self.hash_id = self.make_hash_id()
        super(Assertion, self).save()

    class Meta:
        db_table = 'oc_assertions'
        ordering = ['sort']


class Containment():
    PREDICATE_CONTAINS = "oc-gen:contains"
    recurse_count = 0
    contexts = []
    children = []

    def get_parents_by_child_uuid(self, child_uuid, recursive=True, visibile_only=True):
        """
        creates a list of parent uuids from the containment predicate, is defaults to a recursive function
        to get all parent uuids
        """
        parent_uuid = False
        try:
            parents = Assertion.objects.filter(object_uuid=child_uuid, predicate_uuid=self.PREDICATE_CONTAINS)
            for parent in parents:
                parent_uuid = parent.uuid
                self.contexts.append(parent_uuid)
            self.recurse_count += 1
        except Assertion.DoesNotExist:
            parent_uuid = False
        if(recursive and (parent_uuid is not False) and (self.recurse_count < 20)):
            self.contexts = self.get_parents_by_child_uuid(parent_uuid, recursive, visibile_only)
        return self.contexts

    def get_children_by_parent_uuid(self, parent_uuid, recursive=False, visibile_only=True):
        """
        creates a list of children uuids from the containment predicate, defaults to not being recursive function
        to get all children uuids
        """
        try:
            children = Assertion.objects.filter(uuid=parent_uuid, predicate_uuid=self.PREDICATE_CONTAINS)
            for child in children:
                child_uuid = child.object_uuid
                self.children.append(child_uuid)
                if(recursive and (self.recurse_count < 20)):
                    self.children = self.get_children_by_parent_uuid(child_uuid, recursive, visibile_only)
            self.recurse_count += 1
        except Assertion.DoesNotExist:
            child_uuid = False
        return self.children
