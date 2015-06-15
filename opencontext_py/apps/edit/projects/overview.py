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

    def __init__(self,
                 project_uuid):
        self.project_uuid = project_uuid
        try:
            self.manifest = Manifest.objects.get(uuid=project_uuid,
                                                 item_type='projects')
        except Manifest.DoesNotExist:
            self.manifest = False
            self.errors['uuid'] = 'No project ' + project_uuid + ' not in manifest'
        self.manifest_summary = False
        self.class_summary = {}

    def get_manifest_summary(self):
        """ gets a summary of items in the manifest """
        type_keys = ['subjects',
                     'media',
                     'documents',
                     'persons',
                     'predicates',
                     'types',
                     'tables']
        output = LastUpdatedOrderedDict()
        man_sum = Manifest.objects\
                          .filter(project_uuid=self.project_uuid)\
                          .values('item_type')\
                          .annotate(total=Count('item_type'))\
                          .order_by('-total')
        for sum_type in man_sum:
            item_type = sum_type['item_type']
            if item_type in type_keys:
                output[item_type] = sum_type['total']
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
