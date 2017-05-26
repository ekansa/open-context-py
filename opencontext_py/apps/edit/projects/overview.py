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


class ProjectOverview():
    """ This class contains methods
        for assisting in the workflows of publishing
        projects
    """

    TYPE_KEYS = ['subjects',
                 'media',
                 'documents',
                 'persons',
                 'predicates',
                 'types',
                 'tables']

    def __init__(self,
                 project_uuid):
        self.errors = {}
        self.project_uuid = project_uuid
        try:
            self.manifest = Manifest.objects.get(uuid=project_uuid,
                                                 item_type='projects')
        except Manifest.DoesNotExist:
            self.manifest = False
            self.errors['uuid'] = 'No project ' + project_uuid + ' not in manifest'
        self.manifest_summary = False
        self.project_persons = []
        self.class_summary = LastUpdatedOrderedDict()
        self.data_type_summary = []  # summary datatype
        self.blank_items = LastUpdatedOrderedDict()  # items with no description
        self.no_context_items = LastUpdatedOrderedDict()  # items with no context
        self.mem_entities = {}  # entities kept in memory to reduce database lookups

    def get_manifest_summary(self):
        """ gets a summary of items in the manifest """
        output = LastUpdatedOrderedDict()
        man_sum = Manifest.objects\
                          .filter(project_uuid=self.project_uuid)\
                          .values('item_type')\
                          .annotate(total=Count('item_type'))\
                          .order_by('-total')
        for sum_type in man_sum:
            item_type = sum_type['item_type']
            if item_type in self.TYPE_KEYS:
                output[item_type] = sum_type['total']
                self.get_class_uri_summary(item_type)
        self.manifest_summary = output
        return output

    def get_class_uri_summary(self, item_type='subjects'):
        """ gets a summary of the different class_uris
            used in a project
        """
        output = []
        man_sum = Manifest.objects\
                          .filter(project_uuid=self.project_uuid,
                                  item_type=item_type)\
                          .values('class_uri')\
                          .annotate(total=Count('class_uri'))\
                          .order_by('-total')
        for sum_class in man_sum:
            res_item = LastUpdatedOrderedDict()
            res_item['id'] = sum_class['class_uri']
            ent = Entity()
            found = ent.dereference(res_item['id'])
            if found:
                res_item['label'] = ent.label
            else:
                res_item['label'] = False
            res_item['count'] = sum_class['total']
            output.append(res_item)
        self.class_summary[item_type] = output
        return output
    
    def get_person_list(self):
        """ gets a summary of the different class_uris
            used in a project
        """
        output = []
        man_sum = Manifest.objects\
                          .filter(project_uuid=self.project_uuid,
                                  item_type='persons')\
                          .order_by('sort')
        for man_pers in man_sum:
            self.project_persons.append(man_pers)
        return self.project_persons

    def get_data_type_summary(self):
        """ gets a summary for
            predicates of different data types
        """
        filter_predicates = 'oc_manifest.uuid = oc_predicates.uuid \
                             AND oc_manifest.class_uri = \'variable\' '
        l_tables = 'oc_manifest'
        pred_sum = Predicate.objects\
                            .filter(project_uuid=self.project_uuid)\
                            .extra(tables=[l_tables], where=[filter_predicates])\
                            .values('data_type')\
                            .annotate(total=Count('data_type'))\
                            .order_by('-total')
        for pred in pred_sum:
            item = LastUpdatedOrderedDict()
            item['id'] = pred['data_type']
            if item['id'] in Predicate.DATA_TYPES_HUMAN:
                item['label'] = Predicate.DATA_TYPES_HUMAN[item['id']]
            else:
                item['label'] = pred['data_type'].replace('xsd:', '')
            item['count'] = pred['total']
            self.data_type_summary.append(item)
        return self.data_type_summary

    def get_no_context_items(self):
        """ returns a list of subject items
            that lack containment
            relattions
        """
        item_type = 'subjects'
        assertion_limit = ' AND oc_assertions.predicate_uuid ='
        assertion_limit += '\''+ Assertion.PREDICATES_CONTAINS + '\'' 
        sql = 'SELECT oc_manifest.uuid AS uuid, \
               oc_manifest.label AS label, \
               oc_manifest.item_type AS item_type, \
               oc_manifest.class_uri AS class_uri \
               FROM oc_manifest \
               LEFT JOIN oc_assertions ON \
               (oc_manifest.uuid = oc_assertions.object_uuid \
               ' + assertion_limit + ') \
               WHERE oc_manifest.project_uuid = \
               \'' + self.project_uuid + '\' \
               AND oc_manifest.item_type = \
               \'' + item_type + '\' \
               AND oc_assertions.uuid IS NULL \
               ORDER BY oc_manifest.sort; '
        no_context = Manifest.objects.raw(sql)
        for nc_man in no_context:
            class_uri = nc_man.class_uri
            if class_uri not in self.no_context_items[item_type]:
                class_dict = LastUpdatedOrderedDict()
                ent = Entity()
                found = ent.dereference(class_uri)
                if found:
                    class_dict['label'] = ent.label
                else:
                    class_dict['label'] = item_type
                class_dict['items'] = []
                self.no_context_items[class_uri] = class_dict
            item = LastUpdatedOrderedDict()
            item['uuid'] = nc_man.uuid
            item['label'] = nc_man.label
            self.no_context_items[class_uri]['items'].append(item)
        return self.no_context_items

    def get_orphan_items(self,
                         item_type,
                         consider=['contain',
                                   'link']):
        """ gets a list of items
            that do not have descriptions
        """
        assertion_limit = ''
        if 'contain' in consider:
            assertion_limit += ' AND oc_assertions.predicate_uuid !='
            assertion_limit += '\''+ Assertion.PREDICATES_CONTAINS + '\''   
        if 'link' in consider:
            assertion_limit += ' AND oc_assertions.predicate_uuid !='
            assertion_limit += '\''+ Assertion.PREDICATES_LINK + '\'' 
        sql = 'SELECT oc_manifest.uuid AS uuid, \
               oc_manifest.label AS label, \
               oc_manifest.item_type AS item_type, \
               oc_manifest.class_uri AS class_uri \
               FROM oc_manifest \
               LEFT JOIN oc_assertions ON \
               (oc_manifest.uuid = oc_assertions.uuid \
               ' + assertion_limit + ') \
               WHERE oc_manifest.project_uuid = \
               \'' + self.project_uuid + '\' \
               AND oc_manifest.item_type = \
               \'' + item_type + '\' \
               AND oc_assertions.uuid IS NULL \
               ORDER BY oc_manifest.sort; '
        non_descript = Manifest.objects.raw(sql)
        for dull_man in non_descript:
            item_type = dull_man.item_type
            class_uri = dull_man.class_uri
            if len(class_uri) < 1:
                class_uri = item_type
            if item_type not in self.blank_items:
                self.blank_items[item_type] = LastUpdatedOrderedDict()
            if class_uri not in self.blank_items[item_type]:
                class_dict = LastUpdatedOrderedDict()
                ent = Entity()
                found = ent.dereference(class_uri)
                if found:
                    class_dict['label'] = ent.label
                else:
                    class_dict['label'] = item_type
                class_dict['items'] = []
                self.blank_items[item_type][class_uri] = class_dict
            item = LastUpdatedOrderedDict()
            item['uuid'] = dull_man.uuid
            item['label'] = dull_man.label
            self.blank_items[item_type][class_uri]['items'].append(item)
        return self.blank_items

    def get_cache_entity(self, identifier, get_icon=False):
        """ gets an entity either from memory or
            from the database, if from the database, 
            cache the entity in memory to make lookups faster
        """
        output = False
        if identifier in self.mem_entities:
            # found in memory
            output = self.mem_entities[identifier]
        else:
            ent = Entity()
            ent.get_icon = get_icon
            found = ent.dereference(identifier)
            if found:
                self.mem_entities[identifier] = ent
                output = ent
        return output
