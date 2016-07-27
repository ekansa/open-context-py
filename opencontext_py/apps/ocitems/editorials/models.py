import time
import reversion  # version control object
import uuid as GenUUID
import collections
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.db import models
from jsonfield import JSONField

# Documents editorial actions that mat beed documenting. 
@reversion.register  # records in this model under version control
class Editorial(models.Model):

    EDITORIAL_TYPES ={
        'dispute-redaction' : {
            'label': 'Dispute Redaction',
            'skos:note': 'Content redacted, removed because of a dispute.'
        },
        'policy-redaction' : {
            'label': 'Policy Redaction',
            'skos:note': 'Content redacted, removed because of editorial policy decision.'
        },
        'error-redaction' : {
            'label': 'Error Correction Redaction',
            'skos:note': 'Content redacted, removed because of content or processing error.'
        },
        'edit-deletion' : {
            'label': 'Edting Deletion',
            'skos:note': 'Content deletion for editing purposes.'
        }
    }
    
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    user_id = models.IntegerField()
    label = models.CharField(max_length=200, db_index=True)
    class_uri = models.CharField(max_length=200, db_index=True)  # type of editorial from controlled vocabulary
    restore_json = JSONField(default={},
                             load_kwargs={'object_pairs_hook': collections.OrderedDict})  # JSON for serialized data to be restored
    note = models.TextField()
    created = models.DateTimeField()
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        saves with created time if None
        """
        if self.uuid is None:
            self.uuid = str(GenUUID.uuid4())
        else:
            if len(self.uuid) < 4:
                self.uuid = str(GenUUID.uuid4())
        if self.created is None:
            self.created = datetime.now()
        super(Editorial, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_editorials'

            
        
        