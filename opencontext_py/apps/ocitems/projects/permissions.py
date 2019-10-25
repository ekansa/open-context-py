import datetime
from django.contrib.auth.models import User, Group
from django.db import models
from django.db.models import Q
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.entities.entity.models import Entity


class ProjectPermissions():
    """
    Checks on project relationships with subprojects

from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
pp = ProjectPermissions()
pp.create_perm_groups_by_uuid('27e90af3-6bf7-4da1-a1c3-7b2f744e8cf7')

from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
pp = ProjectPermissions()
pp.publish_project('27e90af3-6bf7-4da1-a1c3-7b2f744e8cf7')

from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
pp = ProjectPermissions()
pp.publish_project('d1c85af4-c870-488a-865b-b3cf784cfc60', '2016-03-01')

    """

    def __init__(self, project_uuid=False):
        self.project_uuid = project_uuid

    def view_allowed(self, request):
        """ Checks to see if a user is allowed to edit a project """
        output = True  # default to visible
        projs = Project.objects\
                       .filter(uuid=self.project_uuid)[:1]
        if len(projs) > 0:
            proj = projs[0]
            if proj.view_group_id is not None:
                if proj.view_group_id <= 0:
                    output = True
                else:
                    print('Project view permission in group: ' + str(proj.view_group_id))
                    if request.user.is_authenticated:
                        if request.user.is_superuser:
                            # super users are super!
                            output = True
                        else:
                            # check to see if the user is in a view_group
                            output = request.user.groups\
                                            .filter(Q(id=proj.view_group_id) | Q(id=proj.edit_group_id))\
                                            .exists()
                    else:
                        output = False
        return output

    def edit_allowed(self, request):
        """ Checks to see if a user is allowed to edit a project """
        output = False
        if request.user.is_authenticated:
            if request.user.is_superuser:
                # super users are super!
                output = True
            else:
                projs = Project.objects\
                               .filter(uuid=self.project_uuid)[:1]
                if len(projs) > 0:
                    output = user.groups\
                                 .filter(id=projs[0].edit_group_id)\
                                 .exists()
        return output

    def create_perm_groups_by_uuid(self, project_uuid):
        """ Creates permissions groups for a project
            identified by a UUID
        """
        output = False
        projs = Project.objects\
                       .filter(uuid=project_uuid)[:1]
        if len(projs) > 0:
            proj = projs[0]
            output = self.create_proj_object_perm_groups(proj)
        return output

    def create_proj_object_perm_groups(self, project_obj):
        """ Creates permissions groups for a project object """
        output = False
        ent = Entity()
        found = ent.dereference(project_obj.uuid)
        if found:
            view_group = Group()
            view_group.name = str(ent.label[:60]) + ' [Can View]'
            view_group.save()
            project_obj.view_group_id = view_group.id
            edit_group = Group()
            edit_group.name = str(ent.label[:60]) + ' [Can Edit]'
            edit_group.save()
            project_obj.edit_group_id = edit_group.id
            project_obj.save()
            output = project_obj
        return output

    def create_missing_groups(self):
        """ Creates user groups for viewing and editing permissions """
        output = []
        projs = Project.objects\
                       .filter(short_id__gt=0)\
                       .exclude(view_group_id=-1)\
                       .order_by('short_id')
        projs = Project.objects\
                       .all()\
                       .order_by('short_id')
        print('Found projects: ' + str(len(projs)))
        for proj in projs:
            output.append(self.create_proj_object_perm_groups(proj))
        return output

    def set_project_view_edit_groups(self,
                                     project_uuid,
                                     view_group_id,
                                     edit_group_id=False):
        """ sets view and edit group ids for a project """
        proj = False
        try:
            proj = Project.objects.get(uuid=project_uuid)
        except Project.DoesNotExist:
            proj = False
        if proj is not False:
            proj.view_group_id = view_group_id
            if isinstance(edit_group_id, int):
                proj.edit_group_id = edit_group_id
            proj.save()
            return True
        else:
            return False

    def publish_project(self, project_uuid, pub_date=None):
        """ publishes a project by making its view group 0
            and by updating the published date in the manifest
        """
        pub_date_obj = None
        if pub_date is not None:
            try:
                pub_date_obj = self.date_convert(pub_date)
            except:
                raise ValueError('Cannot understand the date value')
        public = self.set_project_view_edit_groups(project_uuid, 0)
        if public:
            man_list = Manifest.objects\
                               .filter(project_uuid=project_uuid)\
                               .iterator()
            for man_obj in man_list:
                # save the current publication time
                man_obj.published_save(pub_date_obj)
            return True
        else:
            return False

    def date_convert(self, date_val):
        """ converts to a python datetime if not already so """
        if isinstance(date_val, str):
            date_val = date_val.replace('Z', '')
            if len(date_val) > 10:
                dt = datetime.datetime.strptime(date_val, '%Y-%m-%dT%H:%M:%S')
            else:
                dt = datetime.datetime.strptime(date_val, '%Y-%m-%d')
        else:
            dt = date_val
        return dt
