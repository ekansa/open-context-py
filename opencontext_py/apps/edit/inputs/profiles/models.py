import reversion  # version control object
from datetime import datetime
from django.utils import timezone
from django.db import models


# Stores information about a type of data record to be created through
# manual user data entry
@reversion.register  # records in this model under version control
class InputProfile(models.Model):
    #  item types allowed for profiles
    PROFILE_TYPES = ['subjects',
                     'media',
                     'documents',
                     'persons']

    uuid = models.CharField(max_length=50, primary_key=True)  # uuid for the profile itself
    project_uuid = models.CharField(max_length=50, db_index=True)
    item_type = models.CharField(max_length=50)  # type of item for this profile
    sort = models.IntegerField()  # sort value
    label = models.CharField(max_length=200)  # name of the profile
    note = models.TextField()  # note to guide data entry
    creator_uuid = models.CharField(max_length=50)  # user responsible for creating this
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        saves the item with creation date
        """
        if self.created is None:
            self.created = datetime.now()
        super(InputProfile, self).save(*args, **kwargs)

    class Meta:
        db_table = 'crt_profiles'
        ordering = ['sort',
                    'item_type',
                    'label']
