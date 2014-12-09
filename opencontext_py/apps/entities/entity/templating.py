from django.db import models
from django.conf import settings
from django.db import models
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion


# Prepares entity data for returning JSON
class EntityTemplate():

    def __init__(self):
        self.entity_obj = False
        self.parents = False
        self.children = False

    def get_parents(self, identifier):
        """ Gets parents for an entity """
        parents = LinkRecursion().get_jsonldish_entity_parents(identifier)

    def get_children(self, identifier):
        """ Gets children for an entity
        """
        ent = Entity()
        found = ent.dereference(identifier)
        if found:
            self.children = []
            lr = LinkRecursion()
            lr.get_entity_children(identifier)
            item_children = self.add_child_entity(identifier,
                                                  lr.child_entities)
            if item_children is not False:
                self.children.append(item_children)
        return self.children

    def add_child_entity(self, child_id, children_dict):
        """ creates a child entity dictionary object if found
           in the dictionary object of children and
           if the child entity can be dereferenced
        """
        active_child = False
        if child_id in children_dict:
            active_child = LastUpdatedOrderedDict()
            ent = Entity()
            ent.get_icon = True
            found = ent.dereference(child_id)
            if found:
                active_child['label'] = ent.label
                active_child['id'] = child_id
                active_child['icon'] = ent.icon
                if children_dict[child_id] is not False:
                    active_child['children'] = []
                    for child_child_id in children_dict[child_id]:
                        child_child = self.add_child_entity(child_child_id,
                                                            children_dict)
                        if child_child is not False:
                            active_child['children'].append(child_child)
                    active_child['children'] = self.sort_children_by_label(active_child['children'])
        return active_child

    def sort_children_by_label(self, children):
        """ Sorts list of children by entity label """
        sorted_children = []
        labels_dict = {}
        labels_list = []
        i = 0
        for child in children:
            # add to list of the labels
            labels_list.append(child['label'])
            # get association between label and old list index
            labels_dict[child['label']] = i
            i += 1
        # sort labels alphabetically
        labels_list.sort()
        for s_label in labels_list:
            #the old_index is the old index for the child
            old_index = labels_dict[s_label]
            s_child = children[old_index]
            sorted_children.append(s_child)
        return sorted_children