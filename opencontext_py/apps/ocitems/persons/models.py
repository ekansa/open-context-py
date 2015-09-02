import reversion  # version control object
from django.db import models


# OCdocument stores the content of a document resource (structured text)
@reversion.register  # records in this model under version control
class Person(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    foaf_type = models.CharField(max_length=50)
    combined_name = models.CharField(max_length=200)
    given_name = models.CharField(max_length=200)
    surname = models.CharField(max_length=200)
    mid_init = models.CharField(max_length=5)
    initials = models.CharField(max_length=50)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oc_persons'
