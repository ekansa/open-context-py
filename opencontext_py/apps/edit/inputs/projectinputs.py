import time
import uuid as GenUUID
from django.db import models
from django.db.models import Q, Count
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.edit.inputs.profiles.models import InputProfile
from opencontext_py.apps.edit.inputs.fieldgroups.models import InputFieldGroup
from opencontext_py.apps.edit.inputs.inputfields.models import InputField


class ProjectInputs():
    """ This class contains methods
        to assist in manual data entry for a project
    """

    def __init__(self,
                 project_uuid,
                 request):
        self.errors = {}
        self.project_uuid = project_uuid
        try:
            self.manifest = Manifest.objects.get(uuid=project_uuid,
                                                 item_type='projects')
        except Manifest.DoesNotExist:
            self.manifest = False
            self.errors['uuid'] = 'No project ' + project_uuid + ' not in manifest'
        if self.manifest is not False:
            pp = ProjectPermissions(project_uuid)
            self.edit_permitted = pp.edit_allowed(request)
        else:
            self.edit_permitted = False
        self.creator_uuid = False

    def get_profiles(self):
        """ gets the Input Profiles associated with a project """
        output = []
        profs = InputProfile.objects\
                            .filter(project_uuid=self.project_uuid)
        for prof in profs:
            item = LastUpdatedOrderedDict()
            item['id'] = prof.uuid
            item['label'] = prof.label
            item['item_type'] = prof.item_type
            item['note'] = prof.note
            fgroups = InputFieldGroup.objects\
                                     .filter(profile_uuid=prof.uuid)
            item['fgroup_count'] = len(fgroups)
            fields = InputField.objects\
                               .filter(profile_uuid=prof.uuid)
            item['field_count'] = len(fields)
            item['created'] = prof.created.date().isoformat()
            item['updated'] = prof.updated.date().isoformat()
            output.append(item)
        return output

    def mint_new_uuid(self):
        """ Creates a new UUID """
        uuid = GenUUID.uuid4()
        return str(uuid)
