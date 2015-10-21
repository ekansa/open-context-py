from django.conf import settings
from datetime import datetime
from django.utils import timezone
from django.db import models
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.manifest.models import Manifest


class ManifestTimeStamp():
    """
    Adds date information to the manifest if it does not yet exist
    for publically available projects

from opencontext_py.apps.ocitems.manifest.timestamps import ManifestTimeStamp
mts = ManifestTimeStamp()
mts.update_manifest_objects_by_project('0')
mts.update_published_records()

    """

    def __init__(self):
        self.projects_list = []
    
    def update_published_records(self):
        """ updates time information on public records
        """
        self.get_public_projects_list()
        for project_uuid in self.projects_list:
            self.update_manifest_objects_by_project(project_uuid)
    
    def update_manifest_objects_by_project(self, project_uuid):
        """ updates the objects in the manifest for
            a given project
        """
        proj_changed = False
        man_proj = self.get_project_manifest_obj(project_uuid)
        if project_uuid == '0':
            man_proj = Manifest()
            man_proj.published = timezone.now()
            man_proj.revised = timezone.now()
        if man_proj is not False:
            print('-------------------------------------------')
            print('UPDATE proj: ' + project_uuid)
            print('-------------------------------------------')
            if man_proj.published is None:
                proj_changed = True
                man_proj.published = timezone.now()
            if man_proj.revised is None:
                proj_changed = True
                man_proj.revised = timezone.now()
            if proj_changed and project_uuid != '0':
                man_proj.save()
            man_list = Manifest.objects\
                               .filter(project_uuid=project_uuid)\
                               .exclude(item_type='projects')\
                               .iterator()
            for man in man_list:
                item_changed = False
                if man.published is None:
                    item_changed = True
                    man.published = man_proj.published
                if man.revised is None:
                    item_changed = True
                    man.revised = man.record_updated
                if item_changed:
                    print('Updating timestamps on ' + str(man.uuid))
                    man.save()
    
    def get_project_manifest_obj(self, uuid):
        """ gets the manifest object for a project """
        try:
            man_proj = Manifest.objects.get(uuid=uuid)
        except Manifest.DoesNotExist:
            man_proj = False
        return man_proj
        
    def get_public_projects_list(self):
        """ gets a list of projects that are active
            public and ready for archiving
        """
        self.projects_list = ['0']
        all_projs = Project.objects\
                           .all()
        for proj in all_projs:
            if proj.view_group_id is not None:
                if proj.view_group_id <= 0:
                    self.projects_list.append(proj.uuid)
        return self.projects_list
