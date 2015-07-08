import time
from django.db import models
from django.db.models import Q, Count
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ocitems.assertions.sorting import AssertionSorting
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event


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
