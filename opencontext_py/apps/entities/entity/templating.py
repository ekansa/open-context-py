from django.db import models
from django.conf import settings
from django.db import models
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ocitems.assertions.containment import Containment


# Prepares entity data for returning JSON
class EntityTemplate():

    def __init__(self):
        self.entity_obj = False
        self.parents = False
        self.children = False
        self.mem_entities = {}  # entities kept in memory to reduce database lookups

    def get_parents(self, identifier):
        """ Gets SKOS or OWL parents for an entity """
        parents = LinkRecursion().get_jsonldish_entity_parents(identifier)

    def get_children(self, identifier):
        """ Gets SKOS or OWL children for an entity
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

    def make_containment_item(self, entity_obj):
        """ make a last ordered dict for a
            entity to be used as a containment item
        """
        item = LastUpdatedOrderedDict()
        item['id'] = entity_obj.uuid
        item['label'] = entity_obj.label
        item['item_type'] = entity_obj.item_type
        item['class_uri'] = entity_obj.class_uri
        item['class_label'] = False
        if item['class_uri'] is not False:
            if len(item['class_uri']) > 0:
                class_entity = self.get_cache_entity(entity_obj.class_uri)
                if class_entity is not False:
                    item['class_label'] = class_entity.label
        return item

    def get_containment_children(self,
                                 entity_obj,
                                 depth=1,
                                 first_time=True):
        """ gets a spatial containment
            hierarchy. If the entity_obj.item_type = 'projects'
            then the get the project's root parents.
            It the entity_obj.item_type is subjects, then get
            items containtained by the uuid
        """
        cont = Containment()
        if entity_obj.item_type == 'projects':
            tree = self.make_containment_item(entity_obj)
            tree['children'] = []
            child_list = cont.get_project_top_level_contexts(entity_obj.uuid)
            for child_uuid in child_list:
                child_ent = Entity()
                found = child_ent.dereference(child_uuid)
                if found:
                    if depth > 1:
                        child = self.get_containment_children(child_ent,
                                                              depth - 1,
                                                              False)
                    else:
                        child = self.make_containment_item(child_ent)
                    tree['children'].append(child)
            if first_time:
                output = []
                output.append(tree)
            else:
                output = tree
        elif entity_obj.item_type == 'subjects':
            tree = self.make_containment_item(entity_obj)
            tree['children'] = []
            path_dict = cont.get_children_by_parent_uuid(entity_obj.uuid,
                                                         False)
            for path_key, child_list in path_dict.items():
                for child_uuid in child_list:
                    child_ent = Entity()
                    found = child_ent.dereference(child_uuid)
                    if found:
                        if depth > 1:
                            child = self.get_containment_children(child_ent,
                                                                  depth - 1,
                                                                  False)
                        else:
                            child = self.make_containment_item(child_ent)
                        tree['children'].append(child)
            if first_time:
                output = []
                output.append(tree)
            else:
                output = tree
        else:
            output = []
        return output
