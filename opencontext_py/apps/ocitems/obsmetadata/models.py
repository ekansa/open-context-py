import reversion  # version control object
from django.db import models


# Stores metadata about observation nodes to further annotate bundles of asserions
# an observation bundles assertions
@reversion.register  # records in this model under version control
class ObsMetadata(models.Model):
    source_id = models.CharField(max_length=200, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    obs_num = models.IntegerField()
    label = models.CharField(max_length=200)
    obs_type = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)
    note = models.TextField()

    class Meta:
        db_table = 'oc_obsmetadata'
        unique_together = (('source_id', 'obs_num'),)
