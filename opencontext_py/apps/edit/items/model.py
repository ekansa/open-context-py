from django.db import models
from django.db.models import Q
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.projects.permissions import ProjectPermissions


# Help organize the code, with a class to make editing items easier
class ItemEdit():
    """ This class contains methods to make editing items happen """

    def __init__(self,
                 uuid,
                 request=False):
        self.uuid = uuid
        self.request = request
        try:
            self.manifest = Manifest.objects.get(uuid=uuid)
        except Manifest.DoesNotExist:
            self.manifest = False
        if request is not False and self.manifest is not False:
            # check to make sure edit permissions OK
            pp = ProjectPermissions(self.manifest.project_uuid)
            self.edit_permitted = pp.edit_allowed(request)
        else:
            # default to no editting permissions
            self.edit_permitted = False

    def update_label(self, label):
        """ Updates an item's label. Generally straightforward
            except for subjects
        """
        old_label = self.manifest.label
        output = {'action': 'update-label',
                  'change': {'prop': 'label',
                             'new': label,
                             'old': old_label}}
        return output

    def update_class_uri(self, class_uri):
        """ Updates an item's label. Generally straightforward
            except for subjects
        """
        old_class_uri = self.manifest.class_uri
        output = {'action': 'update-class-uri',
                  'change': {'prop': 'class_uri',
                             'new': class_uri,
                             'old': old_class_uri}}
        return output

    def change_child_order(self, child_uuid, lower_sort):
        """ Updates the sort order of containment
            assertions. If lower_sort = true, then then child_uuid
            becomes goes 1 step earlier in the sort order. If lower_sort = false,
            the child_uuid goes 1 step later in the sort order.
        """
        pass
