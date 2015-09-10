from reversion.models import Revision
from django.db import models
from django.conf import settings
from datetime import datetime
from django.utils import timezone


# Version history metadata to help track editing changes and
# enable roll-back of changes
class VersionMetadata(models.Model):

    # There must be a relationship with Revision called `revision`.
    revision = models.ForeignKey(Revision)
    project_uuid = models.CharField(max_length=50, db_index=True)
    label = models.CharField(max_length=200, db_index=True, null=True)
    note = models.TextField()  # information about the revision
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'edit_version_metadata'
