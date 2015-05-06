from django.db import models
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.imports.sources.models import ImportSource


# Class to make template generation easier for navigating the import process
class ImportNavigation():

    PROJ_NAV = {'key': 'projects',
                'url': '../../imports/project/',
                'label': 'Project',
                'sublabel': False}
    SOURCE_NAVS = [{'key': 'field-types',
                    'url': '../../imports/field-types/',
                    'label': 'Classify Fields'},
                   {'key': 'field-types-more',
                    'url': '../../imports/field-types-more/',
                    'label': 'Classify Entities'},
                   {'key': 'field-entity-relations',
                    'url': '../../imports/field-entity-relations/',
                    'label': 'Relations'},
                   {'key': 'field-descriptions',
                    'url': '../../imports/field-descriptions/',
                    'label': 'Descriptions'},
                   {'key': 'finalize',
                    'url': '../../imports/finalize/',
                    'label': 'Finalize'}]

    def __init__(self):
        self.source_id = False
        self.project_uuid = False
        self.project_label = False
        self.source_label = False
        self.act_page = False
        self.act_source_navs = False
        self.prev_source_nav = False
        self.next_source_nav = False
        self.act_proj_nav = False

    def set_nav(self,
                act_page,
                project_uuid=False,
                source_id=False):
        self.source_id = source_id
        self.project_uuid = project_uuid
        self.act_page = act_page
        self.create_proj_nav()
        self.create_source_navs()
        output = {}
        output['act_page'] = self.act_page
        output['proj_nav'] = self.act_proj_nav
        output['prev_s'] = self.prev_source_nav
        output['next_s'] = self.next_source_nav
        output['source_navs'] = self.act_source_navs
        output['proj_label'] = self.project_label
        output['project_uuid'] = self.project_uuid
        output['s_label'] = self.source_label
        return output

    def create_proj_nav(self):
        """ Creates a navigation link to the project import """
        self.set_project_label()
        output = self.PROJ_NAV
        if self.project_uuid is False:
            output['class'] = 'disabled'
        else:
            if self.project_uuid not in output['url']:
                output['url'] += self.project_uuid
            output['sublabel'] = self.project_label
            output['sublabel'] = output['label']
            if self.act_page == 'project':
                output['class'] = 'active'
            else:
                output['class'] = None
        self.act_proj_nav = output
        return self.act_proj_nav

    def set_project_label(self):
        """ sets the project label """
        if self.project_uuid is not False and self.project_label is False:
            ent = Entity()
            found = ent.dereference(self.project_uuid)
            if found:
                self.project_label = ent.label

    def set_source_label(self):
        """ sets the label for the source table """
        if self.source_id is not False and self.source_label is False:
            try:
                p_source = ImportSource.objects.get(source_id=self.source_id)
            except ImportSource.DoesNotExist:
                p_source = False
            if p_source is not False:
                self.source_label = p_source.label

    def create_source_navs(self):
        """ Creates navivation for source import steps """
        self.set_source_label()
        i = 0
        act_index = False
        for act_nav in self.SOURCE_NAVS:
            if self.act_page == act_nav['key']:
                act_index = i
            i += 1
        navs = []
        # print('source-id: ' + str(self.source_id))
        for act_nav in self.SOURCE_NAVS:
            if 'ref:' in act_nav['url']:
                url_ex = act_nav['url'].split('/')
                if 'ref:' in url_ex[-1]:
                    url_ex[-1] = ''
                act_nav['url'] = '/'.join(url_ex)
            if self.source_id is False:
                act_nav['class'] = 'disabled'
            else:
                if self.source_id not in act_nav['url']:
                    act_nav['url'] += self.source_id
                if self.act_page == act_nav['key']:
                    act_nav['class'] = 'active'
                else:
                    act_nav['class'] = None
            navs.append(act_nav)
        print('Active nav index is: ' + str(act_index))
        if act_index is False or self.source_id is False:
            act_nav = {}
            act_nav['class'] = 'disabled'
            if self.project_uuid is not False:
                act_nav['class'] = None
                act_nav['url'] = '../../imports/'
            self.next_source_nav = act_nav
            self.prev_source_nav = act_nav
        else:
            if act_index < 1:
                self.prev_source_nav = self.create_proj_nav()
            else:
                self.prev_source_nav = navs[act_index - 1]
            if (act_index + 1) not in navs:
                print('Active nav index is: ' + str(act_index + 1) + ' not in: ' + str(len(navs)))
                self.next_source_nav = self.create_proj_nav()
            else:
                self.next_source_nav = navs[act_index + 1]
        self.act_source_navs = navs
        return self.act_source_navs
