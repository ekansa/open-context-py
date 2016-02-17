import time
import uuid as GenUUID
from lxml import etree
import lxml.html
from django.db import models
from django.db.models import Q
from django.core.cache import cache
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ocitems.assertions.sorting import AssertionSorting
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.indexer.reindex import SolrReIndex
from opencontext_py.apps.edit.moddata import DeleteMerge


# Help organize the code, with a class to make editing items easier
class ItemBasicEdit():
    """ This class contains methods
        for basic item eding
    """
    UI_ICONS = {'persons': '<span class="glyphicon glyphicon-user" aria-hidden="true"></span>',
                'media': '<span class="glyphicon glyphicon-camera" aria-hidden="true"></span>',
                'projects': '<i class="fa fa-database"></i>',
                'predicates': '<span class="glyphicon glyphicon-stats" aria-hidden="true"></span>',
                'types': '<i class="fa fa-sitemap"></i>',
                'profiles': '<span class="glyphicon glyphicon-list-alt" aria-hidden="true"></span>'}

    def __init__(self,
                 uuid,
                 request=False):
        self.uuid = uuid
        self.request = request
        self.errors = {'uuid': False,
                       'html': False}
        self.response = {}
        if uuid is not False:
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
        self.manifest.revised_save()
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
                if 'mid_init' in post_data:
                    cobj.mid_init = post_data['mid_init']
                cobj.save()
                ok = True
            except Person.DoesNotExist:
                self.errors['uuid'] = self.manifest.uuid + ' not in projects'
                ok = False
        # now reindex for solr, including child items impacted by the changes
        sri = SolrReIndex()
        sri.reindex_related(self.manifest.uuid)
        if ok:
            # now clear the cache a change was made
            cache.clear()
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
        if ok:
            # now clear the cache a change was made
            cache.clear()
        self.response = {'action': action,
                         'ok': ok,
                         'change': {'note': note}}
        return self.response

    def update_project_hero(self, post_data):
        """ Updates a project's hero picture """
        ok = True
        errors = []
        note = ''
        required_params = ['source_id',
                           'file_uri']
        for r_param in required_params:
            if r_param not in post_data:
                # we're missing some required data
                # don't create the item
                ok = False
                message = 'Missing paramater: ' + r_param + ''
                errors.append(message)
                note = '; '.join(errors)
        if self.manifest.item_type != 'projects':
            ok = False
            message = 'Item type must be a project'
            errors.append(message)
            note = '; '.join(errors)
        if ok:
            file_uri = post_data['file_uri'].strip()
            source_id = post_data['source_id'].strip()
            if 'http://' in file_uri or 'https://' in file_uri:
                ok = True
            else:
                ok = False
                message = 'Need "http://" or "https://" in file_uri: ' + file_uri
                errors.append(message)
                note = '; '.join(errors)
            if ok:
                # delete the old hero picture
                # doing this in a complicated way
                # to trace why project hero files disappear!
                med_check = Mediafile.objects\
                                     .filter(uuid=self.manifest.uuid,
                                             file_type='oc-gen:hero')
                if len(med_check) > 0:
                    for med_old in med_check:
                        med_old.delete()
                new_hero = Mediafile()
                new_hero.uuid = self.manifest.uuid
                new_hero.project_uuid = self.manifest.project_uuid
                new_hero.source_id = source_id
                new_hero.file_type = 'oc-gen:hero'
                new_hero.file_uri = file_uri
                new_hero.save()
                note = 'Updated hero image for project'
        if ok:
            # now clear the cache a change was made
            cache.clear()
        self.response = {'action': 'update-project-hero',
                         'ok': ok,
                         'change': {'note': note}}
        return self.response

    def update_media_file(self, post_data):
        """ Updates a file associated with a media item """
        ok = True
        errors = []
        note = ''
        file_list = []
        required_params = ['source_id',
                           'file_type',
                           'file_uri']
        for r_param in required_params:
            if r_param not in post_data:
                # we're missing some required data
                # don't create the item
                ok = False
                message = 'Missing paramater: ' + r_param + ''
                errors.append(message)
                note = '; '.join(errors)
        if self.manifest.item_type != 'media':
            ok = False
            message = 'Item type must be a media item'
            errors.append(message)
            note = '; '.join(errors)
        if ok:
            file_type = post_data['file_type'].strip()
            file_uri = post_data['file_uri'].strip()
            source_id = post_data['source_id'].strip()
            if 'http://' in file_uri or 'https://' in file_uri:
                ok = True
            else:
                ok = False
                message = 'Need "http://" or "https://" in file_uri: ' + file_uri
                errors.append(message)
                note = '; '.join(errors)
            if ok:
                # delete the file of the same type for this media item
                med_check = Mediafile.objects\
                                     .filter(uuid=self.manifest.uuid,
                                             file_type=file_type)
                if len(med_check) > 0:
                    for med_old in med_check:
                        med_old.delete()
                new_file = Mediafile()
                new_file.uuid = self.manifest.uuid
                new_file.project_uuid = self.manifest.project_uuid
                new_file.source_id = source_id
                new_file.file_type = file_type
                new_file.file_uri = file_uri
                new_file.save()
                note = 'Updated file for this media item'
        if ok:
            # now clear the cache a change was made
            cache.clear()
        # now return the full list of media files for this item
        media_files = Mediafile.objects\
                               .filter(uuid=self.manifest.uuid)
        for media_file in media_files:
            file_obj = {'id': media_file.file_uri,
                        'type': media_file.file_type,
                        'dcat:size': float(media_file.filesize),
                        'dc-terms:hasFormat': media_file.mime_type_uri}
            file_list.append(file_obj)
        self.response = {'action': 'update-media-file',
                         'ok': ok,
                         'file_list': file_list,
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
        elif (class_uri == 'foaf:Person' \
              or class_uri == 'foaf:Organization') \
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
        if ok:
            # now clear the cache a change was made
            cache.clear()
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
            elif self.manifest.item_type == 'documents' \
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
        if ok:
            # now clear the cache a change was made
            cache.clear()
        self.response = {'action': 'update-string-content',
                         'ok': ok,
                         'change': {'prop': content_type,
                                    'new': content,
                                    'old': '[Old content]',
                                    'note': note}}
        return self.response

    def merge_same_contexts_by_project(self,
                                       del_project_uuid,
                                       merge_into_project_uuid):
        """ merge same contexts, deleting contexts from a given
            project and keeping contexts from a given project
        """
        check_subjs = Subject.objects\
                             .filter(project_uuid=del_project_uuid)
        for check_sub in check_subjs:
            delete_uuid = check_sub.uuid
            context = check_sub.context
            old_subs = Subject.objects\
                              .filter(project_uuid=merge_into_project_uuid,
                                      context=context)[:1]
            if len(old_subs) > 0:
                # OK, so there's an old context with the identical path
                # delete the delete version, merge it into the version
                # from the keep project
                merge_into_uuid = old_subs[0].uuid
                dm = DeleteMerge()
                dm.merge_by_uuid(delete_uuid, merge_into_uuid)

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
