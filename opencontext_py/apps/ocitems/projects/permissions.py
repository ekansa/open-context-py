from django.contrib.auth.models import User, Group
from django.db import models
from django.db.models import Q
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.entities.entity.models import Entity


class ProjectPermissions():
    """
    Checks on project relationships with subprojects
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
                    if request.user.is_authenticated():
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
        if request.user.is_authenticated():
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
