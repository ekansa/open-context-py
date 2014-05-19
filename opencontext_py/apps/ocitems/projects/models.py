from django.db import models


# Project stores the content of a project resource (structured text)
class Project(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    updated = models.DateTimeField(auto_now=True)
    short_id = models.IntegerField(unique=True)
    edit_status = models.IntegerField()
    label = models.CharField(max_length=200)
    short_des = models.CharField(max_length=200)
    content = models.TextField()

    class Meta:
        db_table = 'oc_projects'
