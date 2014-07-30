from django.db import models
from django.db.models import Avg, Max, Min
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.libs.chronotiles import ChronoTile
from opencontext_py.libs.globalmaptiles import GlobalMercator


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


class ProjectMeta():
    """
    Generates geospatial and chronological summaries for project metadata
    """

    def __init__(self):
        self.geo_ents = False
        self.event_ents = False
        self.geo_range = False

    def get_geo_range(self, uuids):
        """
        Gets summary geospatial information for a string or a list
        of project uuids. Accepts a list to get sub-projects
        """
        if uuids is not list:
            uuids = [uuids]  # make a list
        proj_geo = Geospace.objects.filter(project_uuid__in=uuids)\
                           .exclude(latitude=0, longitude=0)\
                           .aggregate(Max('latitude'),
                                      Max('longitude'),
                                      Min('latitude'),
                                      Min('longitude'))
        if(proj_geo['latitude__max'] is not None):
            """
            self.max_lat = proj_geo['latitude__max']
            self.min_lat = proj_geo['latitude__min']
            self.max_lon = proj_geo['longitude__max']
            self.min_lon = proj_geo['longitude__min']
            """
            self.geo_range = proj_geo

