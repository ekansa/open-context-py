import json
import datetime
from django.conf import settings
from django.utils.http import urlencode
from django.core.paginator import Paginator
from django.utils import feedgenerator
from opencontext_py.apps.ocitems.manifest.pagedfeed import PagedFeedMaker
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.projects.models import Project


class ManifestFeed():
    """
    This class creates a feed for the manifest
    """
    DEFAULT_ENTRIES_PER_PAGE = 25
    DEFAULT_PAGE = 1

    def __init__(self):
        self.entries_per_page = self.DEFAULT_ENTRIES_PER_PAGE
        self.page = self.DEFAULT_PAGE
        self.count = 0
        self.updated = False
        self.last_page = False
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.projects_list = []
        self.limit_item_types = []

    def make_feed(self, get_data):
        """ makes a feed based on paging data """
        self.set_request_paging(get_data)
        self.get_public_projects_list()
        self.get_manifest_basics()
        self.set_last_page()
        page_items = self.get_manifest_page()
        if page_items is False:
            return False
        else:
            if len(self.limit_item_types) > 0:
                type_list_str = ','.join(self.limit_item_types)
                item_type_suffix = '?' + urlencode({'type' : type_list_str})
            else:
                item_type_suffix = ''
            f = PagedFeedMaker(
                title="Open Context Paged Manifest Feed",
                link=self.base_url + '/manifest/.atom' + item_type_suffix,
                subtitle=self.make_feed_subtitle(),
                pubdate=self.updated,
                updateddate=self.date_convert(self.updated),
                language="en",
                author_name="Open Context",
                author_link="http://opencontext.org",
                description="Open Context Manifest Feed.",
                feed_url=self.base_url + '/manifest/.atom' + item_type_suffix)
            f.base_url = self.base_url + '/manifest/.atom'
            f.page = self.page
            f.count = self.count
            f.entries_per_page = self.entries_per_page
            f.default_recs = self.DEFAULT_ENTRIES_PER_PAGE
            f.limit_item_types = self.limit_item_types
            for man_obj in page_items:
                url = '/'.join([self.base_url,
                                man_obj.item_type,
                                man_obj.uuid])
                json_ld = self.get_json_ld_obj(man_obj.uuid)
                item_project = self.get_project(json_ld)
                f.add_item(title=self.get_item_tile(json_ld),
                           link=url,
                           unique_id=self.get_item_id(json_ld, url),
                           pubdate=self.date_convert(man_obj.published),
                           updateddate=self.date_convert(man_obj.revised),
                           project=item_project,
                           authors=self.make_entry_authors(json_ld),
                           files=self.get_media_files(json_ld),
                           stable_ids=self.get_stable_ids(json_ld),
                           description=self.make_item_description(json_ld,
                                                                  man_obj.item_type))
            return f.writeString('UTF-8')

    def get_json_ld_obj(self, uuid):
        """ gets the item's JSON-LD """
        ocitem = OCitem().get_item(uuid)
        return ocitem.json_ld

    def get_item_tile(self, json_ld):
        """ returns the title, if not, the label """
        if 'dc-terms:title' in json_ld:
            output = json_ld['dc-terms:title']
        else:
            output = json_ld['label']
        return output

    def make_item_description(self, json_ld, item_type):
        """ makes an item description """
        item_type_rec_type = {'subjects': 'Subject of Observation Record',
                              'media': 'Media Record',
                              'documents': 'Document Record',
                              'projects': 'Project Record',
                              'predicates': 'Descriptive Property or Linking Relation Record',
                              'types': 'Descriptive Category Record',
                              'persons': 'Person or Organization Record',
                              'tables': 'Data Table Record',
                              'vocabularies': 'Vocabulary or Ontology Record'}
        if item_type in item_type_rec_type:
            record = item_type_rec_type[item_type]
        else:
            record = ''
        item_project = self.get_project(json_ld)
        if item_project is not False \
           and item_type != 'projects':
                des = ' '.join([
                    record,
                    'from the project: '
                    '"' + item_project['label'] + '",',
                    self.get_item_tile(json_ld)
                    ])
        else:
            des = self.get_item_tile(json_ld)
        return des

    def get_item_id(self, json_ld, url):
        """ returns the title, if not, the label """
        if 'id' in json_ld:
            output = json_ld['id']
        else:
            output = url
        return output

    def make_entry_authors(self, json_ld):
        """ makes JSON-LD authors by getting
            items of dc-terms:contributors and dc-terms:creators
        """
        author_ids = []
        authors = []
        if 'dc-terms:contributor' in json_ld:
            for dc_obj in json_ld['dc-terms:contributor']:
                item_id = self.get_json_ld_node_id(dc_obj)
                if 'label' in dc_obj:
                    if item_id is not False \
                       and item_id not in author_ids:
                        author_ids.append(item_id)
                        item = {'id': item_id,
                                'label': dc_obj['label']}
                        authors.append(item)
        if 'dc-terms:creator' in json_ld:
            for dc_obj in json_ld['dc-terms:creator']:
                item_id = self.get_json_ld_node_id(dc_obj)
                if 'label' in dc_obj:
                    if item_id is not False \
                       and item_id not in author_ids:
                        author_ids.append(item_id)
                        item = {'id': item_id,
                                'label': dc_obj['label']}
                        authors.append(item)
        return authors

    def get_stable_ids(self, json_ld):
        """ gets stable identifiers """
        output = []
        id_parts = ['ark:',
                    'doi.org',
                    'orcid.org']
        if 'owl:sameAs' in json_ld:
            for id_obj in json_ld['owl:sameAs']:
                id_str = self.get_json_ld_node_id(id_obj)
                if id_str is not False:
                    for id_part in id_parts:
                        if id_part in id_str:
                            output.append(id_str)
        return output

    def get_media_files(self, json_ld):
        """ gets media file references """
        output = []
        if 'oc-gen:has-files' in json_ld:
            output = json_ld['oc-gen:has-files']
        return output

    def get_project(self, json_ld):
        """gets the project for an item """
        output = False
        if 'dc-terms:isPartOf' in json_ld:
            for p_item in json_ld['dc-terms:isPartOf']:
                p_id = self.get_json_ld_node_id(p_item)
                if p_id is not False \
                   and 'label' in p_item:
                    if '/projects/' in p_id:
                        output = {'id': p_id,
                                  'label': p_item['label']}
                        break
        return output

    def get_json_ld_node_id(self, json_ld_node):
        """gets the ID string value from a JSON-LD node
        """
        if 'id' in json_ld_node:
            output = json_ld_node['id']
        elif '@id' in json_ld_node:
            output = json_ld_node['id']
        else:
            output = False
        return output

    def make_feed_subtitle(self):
        """ makes a string of the feed's subtitle """
        start_index = (self.page - 1) * self.entries_per_page + 1
        end_index = (self.page) * self.entries_per_page
        if end_index > self.count:
            end_index = self.count
        subtitle = ' '.join(['This update-time sorted (most recent first)',
                             'feed provides a comprehensive list',
                             'of all content in Open Context.',
                             'Digital archives can use this paged feed',
                             'to retrieve all resources relevant to data',
                             'curation from Open Context. This page',
                             'includes entries',
                             str(start_index),
                             'to',
                             str(end_index),
                             'of',
                             str(self.count),
                             'entries.'])
        return subtitle

    def get_public_projects_list(self):
        """ gets a list of projects that are active
            public and ready for archiving
        """
        self.projects_list = ['0']
        all_projs = Project.objects\
                           .all()
        for proj in all_projs:
            if proj.view_group_id is not None:
                if proj.view_group_id <= 0:
                    self.projects_list.append(proj.uuid)

    def set_request_paging(self, get_data):
        """ sets the current page number """
        if 'page' in get_data:
            page = self.return_integer_value(get_data['page'])
            if page is not False:
                self.page = page
        if 'recs' in get_data:
            recs = self.return_integer_value(get_data['recs'])
            if recs is not False:
                self.entries_per_page = recs
        if 'type' in get_data:
            raw_type = get_data['type']
            if ',' in raw_type:
                self.limit_item_types = raw_type.split(',')
            else:
                self.limit_item_types = [raw_type]

    def get_manifest_basics(self):
        """ gets the count of manifest items """
        if len(self.limit_item_types) < 1:
            self.count = Manifest.objects\
                                 .filter(indexed__isnull=False,
                                         project_uuid__in=self.projects_list)\
                                 .count()
            man_list = Manifest.objects\
                               .filter(indexed__isnull=False,
                                       project_uuid__in=self.projects_list)\
                               .order_by('-revised')[:1]
        else:
            self.count = Manifest.objects\
                                 .filter(indexed__isnull=False,
                                         project_uuid__in=self.projects_list,
                                         item_type__in=self.limit_item_types)\
                                 .count()
            man_list = Manifest.objects\
                               .filter(indexed__isnull=False,
                                       project_uuid__in=self.projects_list,
                                       item_type__in=self.limit_item_types)\
                               .order_by('-revised')[:1]
        if len(man_list) > 0:
            self.updated = man_list[0].revised

    def get_manifest_page(self):
        """ gets the manifest list """
        if len(self.limit_item_types) < 1:
            man_list = Manifest.objects\
                               .filter(indexed__isnull=False,
                                       project_uuid__in=self.projects_list)\
                               .order_by('-revised')
        else:
            man_list = Manifest.objects\
                               .filter(indexed__isnull=False,
                                       project_uuid__in=self.projects_list,
                                       item_type__in=self.limit_item_types)\
                               .order_by('-revised')
        paginator = Paginator(man_list, self.entries_per_page)
        try:
            page_list = paginator.page(self.page)
        except:
            page_list = False
        return page_list

    def set_last_page(self):
        """ sets the last page """
        last = self.count / self.entries_per_page
        if last == round(last, 0):
            self.last_page = int(round(last))
        else:
            self.last_page = int(round(last)) + 1

    def return_integer_value(self, raw_value):
        """ returns an integer value or false
        """
        try:
            value = int(float(raw_value))
        except:
            value = False
        return value

    def date_convert(self, date_val):
        """ converts to a python datetime if not already so """
        if isinstance(date_val, str):
            print('Date is ' + date_val)
            date_val = date_val.replace('Z', '')
            dt = datetime.datetime.strptime(date_val, '%Y-%m-%dT%H:%M:%S')
        else:
            # print('Non-string date is: ' + str(date_val))
            dt = date_val
        return dt
