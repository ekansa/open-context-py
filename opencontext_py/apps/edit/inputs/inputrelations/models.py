import reversion
import hashlib
from datetime import datetime
from django.utils import timezone
from django.db import models


# Models relationships between profiles, field groups, fields
# and rules
@reversion.register
class InputRelation(models.Model):

    OK_TYPES = ['profiles',
                'fieldgroups',
                'fields',
                'rules']

    hash_id = models.CharField(max_length=50, primary_key=True)  # uuid for the rule itself
    project_uuid = models.CharField(max_length=50, db_index=True)
    profile_uuid = models.CharField(max_length=50, db_index=True)  # uuid for the input profile
    sort = models.IntegerField()  # sort value a field in a given cell
    subject_uuid = models.CharField(max_length=50, db_index=True)
    subject_type = models.CharField(max_length=50)
    predicate = models.CharField(max_length=50, db_index=True)
    object_uuid = models.CharField(max_length=50, db_index=True)
    object_type = models.CharField(max_length=50)
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    def make_hash_id(self, subject_uuid, predicate_uuid, object_uuid):
        """
        creates a hash-id to insure unique combinations of subjects, predicates, and objects
        """
        hash_obj = hashlib.sha1()
        concat_string = str(subject_uuid) + " " + str(predicate_uuid) + " " + str(object_uuid)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self, *args, **kwargs):
        """
        saves the import relation with a unique hash
        """
        self.hash_id = self.make_hash_id(self.subject_uuid,
                                         self.predicate_uuid,
                                         self.object_uuid)
        if self.created is None:
            self.created = datetime.now()
        super(InputRelation, self).save(*args, **kwargs)

    class Meta:
        db_table = 'crt_relations'
        ordering = ['profile_uuid',
                    'sort',
                    'subject_uuid',
                    'predicate',
                    'object_uuid']
