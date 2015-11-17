from reversion.models import Revision
from django.db import models
from django.conf import settings
from datetime import datetime
from django.utils import timezone


# Version history metadata to help track editing changes and
# enable roll-back of changes
class VersionMetadata(models.Model):

    # There must be a relationship with Revision called `revision`.
    revision = models.ForeignKey(Revision, null=True)  # allow nulls so as to record deletes also
    project_uuid = models.CharField(max_length=50, db_index=True)
    uuid = models.CharField(max_length=200, db_index=True, null=True)
    item_type = models.CharField(max_length=50, null=True)
    label = models.CharField(max_length=200, db_index=True, null=True)
    user_id = models.CharField(max_length=50, db_index=True)
    deleted_ids = models.TextField(null=True)  # JSON object of deleted items
    json_note = models.TextField()  # information about the revision
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reversion_metadata'
