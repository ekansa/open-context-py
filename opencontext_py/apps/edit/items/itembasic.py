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


# Help organize the code, with a class to make editing items easier
class ItemBasicEdit():
    """ This class contains methods
        for basic item eding
    """
    UI_ICONS = {'persons': '<span class="glyphicon glyphicon-user" aria-hidden="true"></span>',
                'projects': '<i class="fa fa-database"></i>',
                'profiles': '<span class="glyphicon glyphicon-list-alt" aria-hidden="true"></span>'}

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

    def update_label(self, label, post_data):
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
        elif self.manifest.item_type == 'persons':
            # we need to adjust person's combined name
            try:
                cobj = Person.objects.get(uuid=self.manifest.uuid)
                cobj.combined_name = label
                if 'given_name' in post_data:
                    cobj.given_name = post_data['given_name']
                if 'surname' in post_data:
                    cobj.surname = post_data['surname']
                if 'initials' in post_data:
                    cobj.initials = post_data['initials']
                cobj.save()
                ok = True
            except Person.DoesNotExist:
                self.errors['uuid'] = self.manifest.uuid + ' not in projects'
                ok = False
        self.response = {'action': 'update-label',
                         'ok': ok,
                         'change': {'prop': 'label',
                                    'new': label,
                                    'old': old_label,
                                    'note': note}}
        return self.response

    def update_project_sensitives(self, post_data):
        """ Updates an some of the more sensitive information
            about a project that requires super-user privelages
        """
        ok = True
        note = ''
        if 'project_uuid' in post_data:
            action = 'update-project-uuid'
            new_project_uuid = post_data['project_uuid']
            if new_project_uuid != self.manifest.uuid and new_project_uuid != '0':
                # check to see if the new_project_uuid actually exists
                try:
                    m_obj = Manifest.objects.get(uuid=new_project_uuid)
                except Manifest.DoesNotExist:
                    m_obj = False
                    note += ' Manifest missing: ' + new_project_uuid
                try:
                    p_obj = Project.objects.get(uuid=new_project_uuid)
                except Project.DoesNotExist:
                    p_obj = False
                    note += ' Project missing: ' + new_project_uuid
                if m_obj is False or p_obj is False:
                    ok = False
            if ok:
                if self.manifest.item_type == 'projects':
                    if new_project_uuid == '0':
                        new_project_uuid = self.manifest.uuid
                    try:
                        cobj = Project.objects.get(uuid=self.manifest.uuid)
                        cobj.project_uuid = new_project_uuid
                        cobj.save()
                        ok = True
                    except Project.DoesNotExist:
                        self.errors['uuid'] = self.manifest.uuid + ' not in projects'
                        ok = False
                self.manifest.project_uuid = new_project_uuid
                self.manifest.save()
        elif 'edit_status' in post_data:
            action = 'update-edit-status'
            try:
                edit_status = int(float(post_data['edit_status']))
            except:
                edit_status = False
            if edit_status is not False:    
                if edit_status >= 0 and edit_status <=5:
                    if self.manifest.item_type == 'projects':
                        try:
                            cobj = Project.objects.get(uuid=self.manifest.uuid)
                            cobj.edit_status = edit_status
                            cobj.save()
                            ok = True
                        except Project.DoesNotExist:
                            self.errors['uuid'] = self.manifest.uuid + ' not in projects'
                            ok = False
                    else:
                        ok = False
                        note += ' This type of item doesnot have a editorial status.'
                else:
                    ok = False
                    note += ' Edit status must be an integer between 0 and 5 inclusively.'
            else:
                ok = False
                note += ' Edit status must be an integer between 0 and 5 inclusively.'
        self.response = {'action': action,
                         'ok': ok,
                         'change': {'note': note}}
        return self.response

    def update_class_uri(self, class_uri):
        """ Updates an item's label. Generally straightforward
            except for subjects
        """
        ok = True
        old_class_uri = self.manifest.class_uri
        entity = Entity()
        found = entity.dereference(class_uri)
        if found and self.manifest.item_type != 'persons':
            note = 'Updated to class: ' + str(entity.label)
            self.manifest.class_uri = class_uri
            self.manifest.save()
        elif (class_uri == 'foaf:Person'\
             or class_uri == 'foaf:Organization')\
             and self.manifest.item_type == 'persons':
            note = 'Updated to class: ' + str(class_uri)
            self.manifest.class_uri = class_uri
            self.manifest.save()
            try:
                cobj = Person.objects.get(uuid=self.manifest.uuid)
                cobj.foaf_type = class_uri
                cobj.save()
                ok = True
            except Person.DoesNotExist:
                self.errors['uuid'] = self.manifest.uuid + ' not in projects'
                ok = False
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

    def update_string_content(self, content, content_type='content'):
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
                    if content_type == 'short_des':
                        cobj.short_des = content
                    else:
                        cobj.content = content
                    cobj.save()
                    ok = True
                except Project.DoesNotExist:
                    self.errors['uuid'] = self.manifest.uuid + ' not in projects'
                    ok = False
            elif self.manifest.item_type == 'documents'\
                and content_type == 'content':
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
                         'change': {'prop': content_type,
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
