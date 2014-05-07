from django.db import models


# Assertions store descriptions and linking relations for Open Context items
# Assertion data mainly represents data contributed from data authors, not OC editors
class Assertion(models.Model):
    # constant for containment relation
    PREDICATE_CONTAINS = "oc-gen:contains"
    #stored in the database
    hash_id = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50, db_index=True)
    subject_type = models.CharField(max_length=50)
    project_uuid = models.CharField(max_length=50)
    source_id = models.CharField(max_length=50)
    obs_node = models.CharField(max_length=50)
    obs_num = models.IntegerField()
    sort = models.DecimalField(max_digits=8, decimal_places=3)
    visibility = models.IntegerField()
    predicate_uuid = models.CharField(max_length=50, db_index=True)
    object_uuid = models.CharField(max_length=50, db_index=True)
    object_type = models.CharField(max_length=50)
    data_num = models.DecimalField(max_digits=19, decimal_places=10)
    data_date = models.DateTimeField()
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oc_assertions'
        ordering = ['sort']


class Containment():
    PREDICATE_CONTAINS = "oc-gen:contains"
    recurse_count = 0
    contexts = []

    def get_parents_by_child_uuid(self, child_uuid, recursive=True, make_uris=True, visibile_only=True):
        parent_uuid = False
        try:
            parents = Assertion.objects.filter(object_uuid=child_uuid, predicate_uuid=self.PREDICATE_CONTAINS)
            for parent in parents:
                parent_uuid = parent.uuid
                self.contexts.append(parent_uuid)
            self.recurse_count += 1
        except Assertion.DoesNotExist:
            parent_uuid = False
        if((parent_uuid is not False) and (self.recurse_count < 20)):
            self.contexts = self.get_parents_by_child_uuid(parent_uuid, recursive, make_uris, visibile_only)
        return self.contexts
