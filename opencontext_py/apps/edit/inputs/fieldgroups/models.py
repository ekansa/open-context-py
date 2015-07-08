import collections
from jsonfield import JSONField
from datetime import datetime
from django.utils import timezone
from django.db import models


# Stores information about fields for a data entry form
class InputFieldGroup(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)  # uuid for the rule itself
    project_uuid = models.CharField(max_length=50, db_index=True)
    profile_uuid = models.CharField(max_length=50, db_index=True)  # uuid for the input profile
    label = models.CharField(max_length=200)  # label for data entry form
    note = models.TextField()  # note for instructions in data entry
    sort = models.IntegerField()  # sort value a field in a given cell
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        saves the record with creation date
        """
        if self.created is None:
            self.created = datetime.now()
        super(InputFieldGroup, self).save(*args, **kwargs)

    class Meta:
        db_table = 'crt_fieldgroups'
        ordering = ['profile_uuid',
                    'sort',
                    'label']
