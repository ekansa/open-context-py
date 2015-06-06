import time
import uuid as GenUUID
from lxml import etree
from django.db import models
from django.db.models import Q
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ocitems.assertions.sorting import AssertionSorting
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event


# Help organize the code, with a class to make editing items easier
class ItemBasicEdit():
    """ This class contains methods
        for basic item eding
    """

    def __init__(self,
                 uuid,
                 request=False):
        self.uuid = uuid
        self.request = request
        self.errors = {'uuid': False,
                       'html': False}
        self.response = {}
        try:
            self.manifest = Manifest.objects.get(uuid=uuid)
        except Manifest.DoesNotExist:
            self.manifest = False
            self.errors['uuid'] = 'Item ' + uuid + ' not in manifest'
        if request is not False and self.manifest is not False:
            # check to make sure edit permissions OK
            pp = ProjectPermissions(self.manifest.project_uuid)
            self.edit_permitted = pp.edit_allowed(request)
        else:
            # default to no editting permissions
            self.edit_permitted = False

    def update_label(self, label):
        """ Updates an item's label. Generally straightforward
            except for subjects
        """
        ok = True
        old_label = self.manifest.label
        self.manifest.label = label
        self.manifest.save()
        note = ''
        if self.manifest.item_type == 'projects':
            try:
                cobj = Project.objects.get(uuid=self.manifest.uuid)
                cobj.label = label
                cobj.save()
                ok = True
            except Project.DoesNotExist:
                self.errors['uuid'] = self.manifest.uuid + ' not in projects'
                ok = False
        elif self.manifest.item_type == 'subjects':
            # we need to adjust context paths for this subject + its children
            subj_gen = SubjectGeneration()
            subj_gen.generate_save_context_path_from_uuid(self.manifest.uuid)
            note = str(subj_gen.changes) + ' items affected'
        self.response = {'action': 'update-label',
                         'ok': ok,
                         'change': {'prop': 'label',
                                    'new': label,
                                    'old': old_label,
                                    'note': note}}
        return self.response

    def update_class_uri(self, class_uri):
        """ Updates an item's label. Generally straightforward
            except for subjects
        """
        ok = True
        old_class_uri = self.manifest.class_uri
        entity = Entity()
        found = entity.dereference(class_uri)
        if found:
            note = 'Updated to class: ' + str(entity.label)
            self.manifest.class_uri = class_uri
            self.manifest.save()
        else:
            note = 'Cannot dereference the class-uri'
            ok = False
        self.response = {'action': 'update-class-uri',
                         'ok': ok,
                         'change': {'prop': 'class_uri',
                                    'new': class_uri,
                                    'old': old_class_uri,
                                    'note': note}}
        return self.response

    def update_string_content(self, content):
        """ Updates the main string content of an item
            (project, document, or table abstract)
        """
        html_ok = self.valid_as_html(content)  # check if valid, but allow invalid
        if html_ok:
            note = ''
        else:
            note = self.errors['html']
        if self.manifest is not False:
            if self.manifest.item_type == 'projects':
                try:
                    cobj = Project.objects.get(uuid=self.manifest.uuid)
                    cobj.content = content
                    cobj.save()
                    ok = True
                except Project.DoesNotExist:
                    self.errors['uuid'] = self.manifest.uuid + ' not in projects'
                    ok = False
            elif self.manifest.item_type == 'documents':
                try:
                    cobj = OCdocument.objects.get(uuid=self.manifest.uuid)
                    cobj.content = content
                    cobj.save()
                    ok = True
                except OCdocument.DoesNotExist:
                    self.errors['uuid'] = self.manifest.uuid + ' not in documents'
                    ok = False
            else:
                ok = False
        self.response = {'action': 'update-string-content',
                         'ok': ok,
                         'change': {'prop': 'content',
                                    'new': content,
                                    'old': '[Old content]',
                                    'note': note}}
        return self.response

    def valid_as_html(self, check_str):
        """ checks to see if a string is OK as HTML """
        ok = True
        check_str = '<div>' + check_str + '</div>'
        try:
            parser = etree.XMLParser()
            tree = etree.XML(check_str, parser)
            self.errors['html'] = False
        except:
            self.errors['html'] = str(len(parser.error_log)) + ' HTML validation errors,'
            self.errors['html'] += ' 1st error is: ' + str(parser.error_log[0].message)
            ok = False
        return ok

    def request_param_val(self, request, param, default=False):
        """ Gets the value for a request paramater, if parameter
            does not exist, it returns a default value
        """
        output = default
        if param in request:
            output = output[param]
        return output
