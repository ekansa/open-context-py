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


class ProjectRels():
    """
    Checks on project relationships with subprojects
    """

    def __init__(self):
        self.sub_projects = False

    def get_sub_projects(self, uuid):
        """
        Gets (child) sub-projects from the current project uuid
        """
        sub_projs = Project.objects.filter(project_uuid=uuid).exclude(uuid=uuid)
        if(len(sub_projs) > 0):
            self.sub_projects = sub_projs
        else:
            self.sub_projects = False
        return self.sub_projects
