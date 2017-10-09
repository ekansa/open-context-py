from django.db import models
from django.conf import settings
from django.db import models
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate


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
            self.children = lr.child_entities
        return self.children

    def get_described_children(self, identifier):
        """ Gets SKOS or OWL children for an entity
        """
        ent = Entity()
        found = ent.dereference(identifier)
        if found:
            self.children = []
            lr = LinkRecursion()
            lr.get_entity_children(identifier)
            self.children = lr.child_entities
            described_children = self.add_child_entity(identifier,
                                                       self.children)
        return [described_children]

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

    def get_description_tree(self,
                             entity_obj,
                             depth=1,
                             first_time=True,
                             item_type=False,
                             class_uri=False):
        """ gets a hierarchy for descriptive
            predicates and types
        """
        lr = LinkRecursion()
        if entity_obj.item_type == 'projects':
            tree = self.make_containment_item(entity_obj)
            if item_type is not False and class_uri is False:
                # returns the classes associated with an item_type for a project
                tree['label'] = tree['label'] + ', ' + item_type
                tree['children'] = self.get_proj_type_classes_items(entity_obj.uuid, 
                                                                    item_type)
            elif item_type is not False and class_uri is not False:
                # returns the predicates associated with an item_type and class_uri
                tree['children'] = self.get_proj_type_class_preds(entity_obj.uuid,
                                                                  item_type,
                                                                  class_uri,
                                                                  True)
            else:
                # project root, returns the item_types for the project
                tree['children'] = self.get_proj_types(entity_obj.uuid)
            if first_time:
                output = []
                output.append(tree)
            else:
                output = tree
        elif entity_obj.item_type == 'predicates':
            tree = self.make_containment_item(entity_obj)
            tree['children'] = []
            child_list = lr.get_entity_children(entity_obj.uuid, False)
            if len(child_list) > 0:
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
            elif entity_obj.data_type == 'id':
                top_types = lr.get_pred_top_rank_types(entity_obj.uuid)
                for top_type in top_types:
                    uri = top_type['id']
                    uuid = URImanagement.get_uuid_from_oc_uri(uri)
                    item = False
                    if depth > 1:
                        child_ent = Entity()
                        found = child_ent.dereference(uuid)
                        if found:
                            item = self.get_description_tree(child_ent,
                                                             depth - 1,
                                                             False)
                    else:
                        item = LastUpdatedOrderedDict()
                        item['id'] = uuid
                        item['label'] = top_type['label']
                        item['class_uri'] = 'type'
                        item['class_label'] = 'type'
                    tree['children'].append(item)
                tree['children'] = self.sort_children_by_label(tree['children'])
            else:
                pass
            if first_time:
                output = []
                output.append(tree)
            else:
                output = tree
        elif entity_obj.item_type == 'types':
            tree = self.make_containment_item(entity_obj)
            tree['children'] = []
            act_children = lr.get_entity_children(entity_obj.uuid, False)
            for child_uuid in act_children:
                if child_uuid != entity_obj.uuid:
                    child_ent = Entity()
                    found = child_ent.dereference(child_uuid)
                    if found:
                        if depth > 1:
                            child = self.get_description_tree(child_ent,
                                                              depth - 1,
                                                              False)
                        else:
                            child = self.make_containment_item(child_ent)
                        child['class_uri'] = 'type'
                        child['class_label'] = 'type'
                        tree['children'].append(child)
            if len(tree['children']) == 0:
                tree.pop('children', None)
            else:
                tree['children'] = self.sort_children_by_label(tree['children'])
            if first_time:
                output = []
                output.append(tree)
            else:
                output = tree
        else:
            output = []
        return output

    def get_proj_types(self, project_uuid):
        """ get predicates used for different types """
        skip_types = ['types',
                      'predicates']
        output = []
        man_dist = Manifest.objects\
                           .filter(project_uuid=project_uuid)\
                           .values('item_type')\
                           .distinct('item_type')
        for man_type in man_dist:
            item_type = man_type['item_type']
            if item_type not in skip_types:
                item = LastUpdatedOrderedDict()
                item['id'] = project_uuid + '/' + item_type
                item['label'] = 'Descriptions for ' + item_type
                item['class_uri'] = ''
                item['class_label'] = ''
                item['children'] = self.get_proj_type_classes(project_uuid,
                                                              item_type)
                output.append(item)
        complex_preds = self.get_proj_complex_description_preds(project_uuid)
        if len(complex_preds) > 0:
            item = LastUpdatedOrderedDict()
            item['id'] = project_uuid + '/complex-descriptions'
            item['label'] = 'Descriptions used in Complex Descriptions'
            item['class_uri'] = ''
            item['class_label'] = ''
            item['children'] =  ['']
            output.append(item)
        return output

    def get_proj_type_classes_items(self,
                                    project_uuid,
                                    item_type,
                                    do_children=True):
        """ gets a list of classes for a project_uuid
            and a given item_type formated as
            items for easy API use
        """
        output = []
        if item_type != 'complex-descriptions':
            classes = self.get_proj_type_classes(project_uuid, item_type)
            for class_uri in classes:
                class_ent = self.get_cache_entity(class_uri)
                if class_ent is not False:
                    class_label = class_ent.label
                else:
                    class_label = item_type
                if len(class_label) < 1:
                    class_label = item_type
                item = LastUpdatedOrderedDict()
                item['id'] = project_uuid + '/' + item_type + '/' + class_uri
                item['label'] = 'Properties used with ' + class_label
                item['class_uri'] = ''
                item['class_label'] = ''
                item['children'] = self.get_proj_type_class_preds(project_uuid,
                                                                  item_type,
                                                                  class_uri,
                                                                  False)
                output.append(item)
        else:
            output = self.get_proj_complex_description_preds(project_uuid)
        return output

    def get_proj_type_classes(self, project_uuid, item_type):
        """ get list of classes for a project_uuid
            and a given item_type
        """
        output = []
        man_classes = Manifest.objects\
                              .filter(project_uuid=project_uuid,
                                      item_type=item_type)\
                              .order_by('class_uri')\
                              .distinct('class_uri')
        for man_class in man_classes:
            output.append(man_class.class_uri)
        return output

    def get_proj_type_predicates(self, project_uuid, item_type):
        """ get predicates used for different types, organized by class """
        output = []
        classes = self.get_proj_type_classes(project_uuid, item_type)
        for class_uri in classes:
            preds = self.get_proj_type_class_preds(project_uuid,
                                                   item_type,
                                                   class_uri)
            for pred in preds:
                output.append(pred)
        return output

    def get_proj_type_class_preds(self,
                                  project_uuid,
                                  item_type,
                                  class_uri,
                                  do_children=True):
        """ get items for a project, an item_type
            and a class_uri
        """
        output = []
        ignore_preds = ['oc-gen:has-note',
                        'oc-gen:contains',
                        'oc-gen:has-complex-description',
                        'oc-3']
        l_tab_p = 'oc_manifest'
        filter_classes = 'oc_assertions.uuid = oc_manifest.uuid \
                          AND oc_manifest.class_uri = \'' + class_uri + '\' '
        ass_types = Assertion.objects\
                             .filter(subject_type=item_type,
                                     project_uuid=project_uuid)\
                             .exclude(predicate_uuid__in=ignore_preds)\
                             .extra(tables=[l_tab_p],
                                    where=[filter_classes])\
                             .order_by('predicate_uuid')\
                             .distinct('predicate_uuid')
        for ass_type in ass_types:
            ent = Entity()
            found = ent.dereference(ass_type.predicate_uuid)
            if found:
                item = LastUpdatedOrderedDict()
                item['id'] = ass_type.predicate_uuid
                item['label'] = ent.label
                item['class_uri'] = ent.data_type
                if ent.data_type in Predicate.DATA_TYPES_HUMAN:
                    item['class_label'] = Predicate.DATA_TYPES_HUMAN[ent.data_type]
                else:
                    item['class_label'] = ent.data_type
                if do_children and ent.data_type == 'id':
                    # get the children for this predicate
                    item['more'] = True
                output.append(item)
        if len(output) > 1:
            output = self.sort_children_by_label(output)
        return output
    
    def get_proj_complex_description_preds(self,
                                           project_uuid,
                                           do_children=True):
        """ get predicate items for complex descriptions in a
            project
        """
        output = []
        ignore_preds = ['oc-gen:has-note',
                        'oc-gen:contains',
                        'oc-gen:has-complex-description',
                        'oc-3']
        ass_types = Assertion.objects\
                             .filter(subject_type='complex-description',
                                     project_uuid=project_uuid)\
                             .exclude(predicate_uuid__in=ignore_preds)\
                             .order_by('predicate_uuid')\
                             .distinct('predicate_uuid')
        for ass_type in ass_types:
            ent = Entity()
            found = ent.dereference(ass_type.predicate_uuid)
            if found:
                item = LastUpdatedOrderedDict()
                item['id'] = ass_type.predicate_uuid
                item['label'] = ent.label
                item['class_uri'] = ent.data_type
                if ent.data_type in Predicate.DATA_TYPES_HUMAN:
                    item['class_label'] = Predicate.DATA_TYPES_HUMAN[ent.data_type]
                else:
                    item['class_label'] = ent.data_type
                if do_children and ent.data_type == 'id':
                    # get the children for this predicate
                    item['more'] = True
                output.append(item)
        if len(output) > 1:
            output = self.sort_children_by_label(output)
        return output

