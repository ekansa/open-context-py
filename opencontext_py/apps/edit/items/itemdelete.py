import time
import datetime
from dateutil.parser import parse
import uuid as GenUUID
from lxml import etree
import lxml.html
from django.db import models
from django.db.models import Q
from django.db.models import Count
from django.conf import settings
from django.core.cache import caches
from opencontext_py.libs.languages import Languages
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.strings.manage import StringManagement
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ldata.linkentities.models import LinkEntityGeneration
from opencontext_py.apps.edit.items.itembasic import ItemBasicEdit
from opencontext_py.apps.edit.versioning.deletion import DeletionRevision
from opencontext_py.apps.ocitems.editorials.manage import EditorialAction


class ItemDelete():
    """ This class contains methods
        for deleting items and previewing the concequences of deletion

from opencontext_py.apps.edit.items.itemdelete import ItemDelete
id = ItemDelete()
id.uuid = 'EEF8F6D6-3BFC-4521-99DF-CCCE89EF21E1'
id.get_predicate_uses()

from opencontext_py.apps.edit.items.itemdelete import ItemDelete
id = ItemDelete()
id.uuid = '6374d4eb-a6c8-45cb-8548-4173609e7cd7'
id.get_object_uses()

from opencontext_py.apps.edit.items.itemdelete import ItemDelete
id = ItemDelete()
id.uuid = '03C9B407-F3DD-4AF2-AFF3-7484FCD49F98'
id.rel_to_subject()

    """

    def __init__(self):
        self.uuid = False
        self.project_uuid = False
        self.item_type = False
        self.errors = []
        self.ok = True
        self.response = False

    def redo_hierarchies(self):
        """ redoes hierarchic relations
            if items have children items
            either in spatial containment
            or in SKOS / OWL taxonomies
        """
        pass
    
    def get_predicate_uses(self):
        """ gets numbers of distinct
            subjects used with a given predicate
        """
        sub_asses = Assertion.objects\
                             .filter(predicate_uuid=self.uuid)\
                             .distinct('uuid')\
                             .count()
        return sub_asses
    
    def get_object_uses(self):
        """ gets numbers of distinct
            subjects used with a given object
        """
        obj_asses = Assertion.objects\
                             .filter(object_uuid=self.uuid)\
                             .distinct('uuid')\
                             .count()
        return obj_asses

    def rel_to_subject(self):
        """ gets items related to the subject, and ONLY
            the subject
        """
        linking_types = ['subjects',
                         'media',
                         'documents']
        sub_asses = Assertion.objects\
                             .filter(uuid=self.uuid,
                                     object_type__in=linking_types)\
                             .exclude(predicate_uuid=Assertion.PREDICATES_CONTAINS)\
                             .distinct('object_uuid')\
                             .order_by('object_uuid')
        sub_only_count = 0
        for sub_ass in sub_asses:
            # The sub_asses list is a list of items linked (except for containment) to the
            # item to that may be deleted.
            # Below, the other_count checks to see if the linked item has links to
            # other items.
            other_count = Assertion.objects\
                                   .filter(object_uuid=sub_ass.object_uuid,
                                           subject_type__in=linking_types)\
                                   .exclude(uuid=self.uuid)\
                                   .count()
            if other_count == 0:
                # if the self.uuid item is deleted, then some related items
                # will be left as orphans, without any linking relations
                # to subjects, media, or documents
                # this will likely cause data integrity problems
                sub_only_count += 1
        return sub_only_count

    def clear_caches(self):
        """ clears all the caches """
        cache = caches['redis']
        cache.clear()
        cache = caches['default']
        cache.clear()
