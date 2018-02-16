import reversion  # version control object
import collections
from jsonfield import JSONField  # json field for complex objects
from django.db import models
from django.db.models import Avg, Max, Min
from opencontext_py.apps.ocitems.geospace.models import Geospace


# Project stores the content of a project resource (structured text)
@reversion.register  # records in this model under version control
class Project(models.Model):
    
    META_KEY_GEO_SPECIFICITY = 'geo_specificity'  # metadata key for geospatial specificity for a project
    META_KEY_GEO_NOTE = 'geo_note'  # metadata key for geospatial note associated with a project
    
    uuid = models.CharField(max_length=50, primary_key=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    updated = models.DateTimeField(auto_now=True)
    short_id = models.IntegerField(unique=True)
    view_group_id = models.IntegerField()
    edit_group_id = models.IntegerField()
    edit_status = models.IntegerField()
    label = models.CharField(max_length=200)
    short_des = models.CharField(max_length=200)
    content = models.TextField()
    sm_localized_json = JSONField(default={},
                                  load_kwargs={'object_pairs_hook': collections.OrderedDict},
                                  blank=True)
    lg_localized_json = JSONField(default={},
                                  load_kwargs={'object_pairs_hook': collections.OrderedDict},
                                  blank=True)
    meta_json = JSONField(default={},
                          load_kwargs={'object_pairs_hook': collections.OrderedDict},
                          blank=True)

    def save(self, *args, **kwargs):
        """
        creates a short ID for the project if it does not yet
        exist
        """
        if self.short_id is None:
            p_short_id = ProjectShortID()
            self.short_id = p_short_id.get_make_short_id(self.uuid,
                                                         self.short_id)
        super(Project, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_projects'


class ProjectShortID():
    """ methods to make short-ids for projects
        on creation
    """
    def __init__(self):
        pass

    def get_make_short_id(self, uuid, short_id=False):
        """ gets the current short ID or makes one
        """
        if not isinstance(short_id, int):
            # short ID is not an integer
            pobj = False
            try:
                pobj = Project.objects.get(uuid=uuid)
                short_id = pobj.short_id
            except Project.DoesNotExist:
                pobj = False
            if pobj is False:
                sumps = Project.objects\
                               .filter(short_id__gte=0)\
                               .aggregate(Max('short_id'))
                try:
                    short_id = sumps['short_id__max'] + 1
                except:
                    short_id = 1
        return short_id

