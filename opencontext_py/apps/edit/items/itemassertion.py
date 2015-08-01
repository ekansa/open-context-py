import time
import uuid as GenUUID
from lxml import etree
import lxml.html
from django.db import models
from django.db.models import Q
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.strings.manage import StringManagement
from opencontext_py.apps.ldata.linkentities.models import LinkEntityGeneration


class ItemAssertion():
    """ This class contains methods
        creating, editing, and deleting
        assertions
    """

    def __init__(self):
        self.uuid = False
        self.project_uuid = False
        self.item_type = False
        self.source_id = False
        self.obs_node = False
        self.obs_num = 1
        self.sort = 1
        self.note_sort = 1000  # default to last
        self.errors = {}

    def add_description_note(self, note):
        """ adds a description note about a new item
        """
        # first make sure the has-note predicate exists
        self.create_note_entity()
        note = str(note)
        if len(note) > 1:
            # save the note as a string
            str_man = StringManagement()
            str_man.project_uuid = self.project_uuid
            str_man.source_id = self.source_id
            object_uuid = str_man.get_make_string(str(note))
            # now make the assertion
            new_ass = Assertion()
            new_ass.uuid = self.uuid
            new_ass.subject_type = self.item_type
            new_ass.project_uuid = self.project_uuid
            new_ass.source_id = self.source_id
            if self.obs_node is False:
                new_ass.obs_node = '#obs-' + str(self.obs_num)
            else:
                new_ass.obs_node = self.obs_node
            new_ass.obs_num = self.obs_num
            new_ass.sort = self.note_sort
            new_ass.visibility = 1
            new_ass.predicate_uuid = Assertion.PREDICATES_NOTE
            new_ass.object_type = 'xsd:string'
            new_ass.object_uuid = object_uuid
            new_ass.save()

    def create_note_entity(self):
        """ creates a note predicate entity if it does not yet
            exist
        """
        leg = LinkEntityGeneration()
        leg.check_add_note_pred()
