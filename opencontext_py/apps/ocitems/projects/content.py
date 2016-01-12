from django import db
from django.db import models
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.entities.entity.models import Entity


class ProjectContent():

    def __init__(self, project_uuid, project_slug, json_ld):
        self.project_uuid = project_uuid
        self.proj_slug = project_slug
        self.json_ld = json_ld
        self.subjects = False  # will be a list if there is content
        self.media = False
        self.projects = False
        self.documents = False
        self.subjects_list = []

    def get_project_content(self):
        """ gets content for a project (and its subprojects)
        """
        uuid = self.project_uuid
        self.subjects = False  # will be a list if there is content
        self.media = False
        self.projects = False
        self.documents = False
        self.subjects_list = []
        project_uuids = self.get_sub_project_uuids(uuid,
                                                   [])
        if uuid not in project_uuids:
            project_uuids.append(uuid)
        # don't get rid of this! Keeps memory issues from
        # screwing things up
        man_content = Manifest.objects\
                              .filter(project_uuid__in=project_uuids)\
                              .order_by('class_uri')\
                              .values_list('item_type',
                                           'class_uri')\
                              .distinct()
        if len(man_content) > 0:
            for content in man_content:
                item_type = content[0]
                class_uri = content[1]
                if item_type == 'subjects':
                    self.subjects = '/subjects-search/' \
                                    + '?proj=' + self.make_proj_query_term()
                    if len(class_uri) > 0:
                        ent = Entity()
                        found = ent.dereference(class_uri)
                        if found:
                            obj = {}
                            obj['label'] = ent.label
                            obj['slug'] = ent.slug
                            obj['link'] = self.subjects + '&prop=' + ent.slug
                            self.subjects_list.append(obj)
                elif item_type == 'media':
                    self.media = '/media-search/' \
                                 + '?proj=' + self.make_proj_query_term()
                elif item_type == 'documents':
                    self.documents = '/search/' \
                                     + '?proj=' + self.make_proj_query_term() \
                                     + '&type=documents'
                elif item_type == 'projects':
                    self.projects = '/projects-search/' \
                                    + '?proj=' + self.make_proj_query_term()
                else:
                    pass
        if len(project_uuids) < 2:
            # don't show sub projects if there's only 1 project
            self.projects = False
        output = {'subjects': self.subjects,
                  'media': self.media,
                  'documents': self.documents,
                  'projects': self.projects,
                  'subjects_list': self.subjects_list}
        return output

    def get_sub_project_uuids(self,
                              uuid,
                              sub_proj_uuids = [],
                              recursive=True):
        """ gets uuids for the current project
            and any sub projects
        """
        sub_projs = Project.objects\
                           .filter(project_uuid=uuid)\
                           .exclude(uuid=uuid)
        if len(sub_projs) > 0:
            for sub_proj in sub_projs:
                if sub_proj.uuid not in sub_proj_uuids:
                    sub_proj_uuids.append(sub_proj.uuid)
                    if recursive:
                        sub_proj_uuids = self.get_sub_project_uuids(sub_proj.uuid,
                                                                    sub_proj_uuids)
        return sub_proj_uuids

    def make_proj_query_term(self):
        """ makes a project query term, checking
            first if the project is a subproject
        """
        proj_slugs = []
        if isinstance(self.json_ld, dict):
            if 'dc-terms:isPartOf' in self.json_ld:
                for par_obj in self.json_ld['dc-terms:isPartOf']:
                    if '/projects/' in par_obj['id']:
                        if 'slug' in par_obj:
                            proj_slugs.append(par_obj['slug'])
        proj_slugs.append(self.proj_slug)
        return '---'.join(proj_slugs)
