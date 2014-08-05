import hashlib
from django.conf import settings
from django.db import models
from opencontext_py.apps.ocitems.assertions.models import Assertion


class ManageAssertions():
    """
    This class has useful functions for creating and updating assertion data
    """

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
