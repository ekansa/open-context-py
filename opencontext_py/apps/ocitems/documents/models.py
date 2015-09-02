import reversion  # version control object
from django.db import models


# OCdocument stores the content of a document resource (structured text)
@reversion.register  # records in this model under version control
class OCdocument(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    updated = models.DateTimeField(auto_now=True)
    content = models.TextField()

    class Meta:
        db_table = 'oc_documents'
