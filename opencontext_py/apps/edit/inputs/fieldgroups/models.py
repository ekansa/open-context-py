import reversion
import collections
from jsonfield import JSONField
from datetime import datetime
from django.utils import timezone
from django.db import models


# Stores information about groups of fields for a data entry form
@reversion.register
class InputFieldGroup(models.Model):

    GROUP_VIS = {'open': 'Show Field Group in an open panel',
                 'closed': 'Show Field Group in a closed panel',
                 'hidden': 'Field Group is not shown to the user until certain conditions are met'}

    uuid = models.CharField(max_length=50, primary_key=True)  # uuid for the rule itself
    project_uuid = models.CharField(max_length=50, db_index=True)
    profile_uuid = models.CharField(max_length=50, db_index=True)  # uuid for the input profile
    label = models.CharField(max_length=200)  # label for data entry form
    sort = models.IntegerField()  # sort value a field in a given cell
    visibility = models.CharField(max_length=50)  # label for data entry form
    note = models.TextField()  # note for instructions in data entry
    obs_num = models.IntegerField()  # value for the observation number for 
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    def validate_visibility(self, visibility):
        """ validates and updates the field group visibility """
        if visibility not in self.GROUP_VIS:
            # checks to make sure that
            for real_vis_key, value in self.GROUP_VIS.items():
                visibility = real_vis_key
                break;
        return visibility

    def save(self, *args, **kwargs):
        """
        saves the record with creation date
        """
        self.visibility = self.validate_visibility(self.visibility)
        if self.obs_num is None:
            self.obs_num = 1
        if self.created is None:
            self.created = datetime.now()
        super(InputFieldGroup, self).save(*args, **kwargs)

    class Meta:
        db_table = 'crt_fieldgroups'
        ordering = ['profile_uuid',
                    'sort',
                    'label']
