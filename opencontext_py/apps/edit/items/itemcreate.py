import time
import uuid as GenUUID
from lxml import etree
import lxml.html
from django.db import models
from django.db.models import Q
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ocitems.assertions.sorting import AssertionSorting
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event


class ItemCreate():
    """ This class contains methods
        for mannually creating items into a project
    """

    def __init__(self,
                 project_uuid,
                 request=False):
        self.project_uuid = project_uuid
        self.oc_root_project = False
        self.request = request
        self.errors = {'params': False}
        self.response = {}
        try:
            self.project = Project.objects.get(uuid=project_uuid)
        except Project.DoesNotExist:
            self.project = False
        try:
            self.proj_manifest_obj = Manifest.objects.get(uuid=project_uuid)
        except Manifest.DoesNotExist:
            self.proj_manifest_obj = False
        if request is not False and self.project is not False:
            # check to make sure edit permissions OK
            pp = ProjectPermissions(project_uuid)
            self.edit_permitted = pp.edit_allowed(request)
        else:
            # default to no editting permissions
            self.edit_permitted = False
        if project_uuid == '0' \
           or project_uuid == ''  \
           or project_uuid == 'oc':
            self.oc_root_project = True
        else:
            self.oc_root_project = False

    def create_person(self, post_data):
        """ creates a person item into a project
        """
        ok = True
        required_params = ['source_id',
                           'item_type',
                           'foaf_type',
                           'combined_name',
                           'given_name',
                           'surname',
                           'mid_init',
                           'initials']
        for r_param in required_params:
            if r_param not in post_data:
                # we're missing some required data
                # don't create the item
                ok = False
                message = 'Missing paramater: ' + r_param + ''
                if self.errors['params'] is False:
                    self.errors['params'] = message
                else:
                    self.errors['params'] += '; ' + message
        if ok:
            label = post_data['combined_name']
            uuid = GenUUID.uuid4()
            uuid = str(uuid)
            new_pers = Person()
            new_pers.uuid = uuid
            new_pers.project_uuid = self.project_uuid
            new_pers.source_id = post_data['source_id']
            new_pers.foaf_type = post_data['foaf_type']
            new_pers.combined_name = post_data['combined_name']
            new_pers.given_name = post_data['given_name']
            new_pers.surname = post_data['surname']
            new_pers.mid_init = post_data['mid_init']
            new_pers.initials = post_data['initials']
            new_pers.save()
            new_man = Manifest()
            new_man.uuid = uuid
            new_man.project_uuid = self.project_uuid
            new_man.source_id = post_data['source_id']
            new_man.item_type = 'persons'
            new_man.repo = ''
            new_man.class_uri = post_data['foaf_type']
            new_man.label = post_data['combined_name']
            new_man.des_predicate_uuid = ''
            new_man.views = 0
            new_man.save()
        else:
            label = '[Item not created]'
            uuid = False
        self.response = {'action': 'create-item-into',
                         'ok': ok,
                         'change': {'uuid': uuid,
                                    'label': label,
                                    'note': self.add_creation_note(ok)}}
        return self.response

    def add_creation_note(self, ok):
        """ adds a note about the creation of a new item """
        if self.proj_manifest_obj is not False:
            proj_label = self.proj_manifest_obj.label
        else:
            proj_label = 'Open Context [General]'
        if ok:
            note = 'Item added into: ' + proj_label
        else:
            note = 'Failed to create item into: ' + proj_label
        return note