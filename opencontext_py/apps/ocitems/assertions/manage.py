import hashlib
from django.conf import settings
from django.db import models
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.edit.moddata import DeleteMerge
from opencontext_py.apps.ocitems.assertions.containment import Containment


class ManageAssertions():
    """
    This class has useful functions for creating and updating assertion data
    """
    def __init__(self):
        self.source_id = 'manual'
        self.visibility = 1
        self.contain_obs_node = '#contents-1'
        self.contain_obs_num = 1
        self.contain_sort = 1

    def change_predicate_object_uuid(self, predicate_uuid, old_object_uuid,
                                     new_object_uuid, new_object_type):
        """ Changes an object of a given predicate. Useful if an object_uuid has changed """
        old_assertions = Assertion.objects.filter(predicate_uuid=predicate_uuid,
                                                  object_uuid=old_object_uuid)
        for act_ass in old_assertions:
            act_ass.object_uuid = new_object_uuid
            act_ass.object_type = new_object_type
            act_ass.save()
        return len(old_assertions)

    def add_containment_assertion(self, parent_uuid, child_uuid):
        """ adds a new spatial containment assertion """
        con_exists = Assertion.objects\
                              .filter(predicate_uuid=Assertion.PREDICATES_CONTAINS,
                                      object_uuid=child_uuid)[:1]
        if len(con_exists) < 1:
            # child is not contained by something else, so make a containment rel
            try:
                parent = Manifest.objects.get(uuid=parent_uuid)
            except Manifest.DoesNotExist:
                parent = False
            try:
                child = Manifest.objects.get(uuid=child_uuid)
            except Manifest.DoesNotExist:
                child = False
            if parent is not False and child is not False:
                if parent.item_type == 'subjects'\
                   and child.item_type == 'subjects':
                    con_ass = Assertion()
                    con_ass.uuid = parent.uuid
                    con_ass.subject_type = parent.item_type
                    con_ass.project_uuid = child.project_uuid
                    con_ass.source_id = self.source_id
                    con_ass.obs_node = self.contain_obs_node
                    con_ass.obs_num = self.contain_obs_num
                    con_ass.sort = self.contain_sort
                    con_ass.visibility = self.visibility
                    con_ass.predicate_uuid = Assertion.PREDICATES_CONTAINS
                    con_ass.object_uuid = child.uuid
                    con_ass.object_type = child.item_type
                    con_ass.save()
                    cont = Containment()
                    child_children = cont.get_children_by_parent_uuid(child.uuid,
                                                                      True)
                    dm = DeleteMerge()
                    dm.update_children_subjects(child_children)
        else:
            print('Item already containted in: ' + con_exists[0].uuid)
