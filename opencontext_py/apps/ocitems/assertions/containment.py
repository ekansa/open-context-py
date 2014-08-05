import hashlib
from django.conf import settings
from django.db import models
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event


class Containment():
    recurse_count = 0
    contexts = {}
    contexts_list = []
    contents = {}

    def __init__(self):
        self.contents = {}
        self.contexts = {}
        self.contexts_list = []
        recurse_count = 0

    def get_parents_by_child_uuid(self, child_uuid, recursive=True, visibile_only=True):
        """
        creates a list of parent uuids from the containment predicate, is defaults to a recursive function
        to get all parent uuids
        """
        parent_uuid = False
        try:
            parents = Assertion.objects.filter(object_uuid=child_uuid, predicate_uuid=Assertion.PREDICATES_CONTAINS)
            for parent in parents:
                if(parent.obs_node not in self.contexts):
                    self.contexts[parent.obs_node] = []
            for parent in parents:
                parent_uuid = parent.uuid
                if(parent_uuid not in self.contexts_list):
                    self.contexts_list.append(parent_uuid)
                self.contexts[parent.obs_node].append(parent_uuid)
                if(recursive and (self.recurse_count < 20)):
                    self.contexts = self.get_parents_by_child_uuid(parent_uuid, recursive, visibile_only)
            self.recurse_count += 1
        except Assertion.DoesNotExist:
            parent_uuid = False
        return self.contexts

    def get_children_by_parent_uuid(self, parent_uuid, recursive=False, visibile_only=True):
        """
        creates a list of children uuids from the containment predicate, defaults to not being recursive function
        to get all children uuids
        """
        try:
            children = Assertion.objects.filter(uuid=parent_uuid, predicate_uuid=Assertion.PREDICATES_CONTAINS)
            for child in children:
                if(child.obs_node not in self.contents):
                    self.contents[child.obs_node] = []
            for child in children:
                child_uuid = child.object_uuid
                self.contents[child.obs_node].append(child_uuid)
                if(recursive and (self.recurse_count < 20)):
                    self.contents = self.get_children_by_parent_uuid(child_uuid, recursive, visibile_only)
            self.recurse_count += 1
        except Assertion.DoesNotExist:
            child_uuid = False
        return self.contents

    def get_related_subjects(self, uuid, reverse_links_ok=True):
        """
        makes a list of related subjects uuids from a given uuid. if none present,
        defaults to look at reverse link assertions
        """
        rel_sub_uuid_list = []
        rel_subjects = Assertion.objects.filter(uuid=uuid, object_type='subjects')
        for sub in rel_subjects:
            rel_sub_uuid_list.append(sub.object_uuid)
        if(len(rel_sub_uuid_list) < 1 and reverse_links_ok):
            rel_subjects = Assertion.objects.filter(object_uuid=uuid,
                                                    subject_type='subjects',
                                                    predicate_uuid=Assertion.PREDICATES_LINK)
            for sub in rel_subjects:
                rel_sub_uuid_list.append(sub.uuid)
        return rel_sub_uuid_list

    def get_related_context(self, uuid, reverse_links_ok=True):
        """
        gets context for media, and document items by looking for related subjects
        """
        self.contexts = {}
        self.contexts_list = []
        parents = False
        rel_sub_uuid_list = self.get_related_subjects(uuid, reverse_links_ok)
        if(len(rel_sub_uuid_list) > 0):
            rel_subject_uuid = rel_sub_uuid_list[0]
            parents = self.get_parents_by_child_uuid(rel_subject_uuid)
            # add the related subject as the first item in the parent list
            if(len(parents) > 0):
                use_key = False
                for key, parent_list in parents.items():
                    use_key = key
                    break
                parents[use_key].insert(0, rel_subject_uuid)
            else:
                parents = {}
                parents['related_context'] = [rel_subject_uuid]
        return parents

    def get_geochron_from_subject_list(self, subject_list, metadata_type, do_parents=True):
        """
        gets the most specific geospatial or chronology metadata related to a list of subject items
        if not found, looks up parent items
        """
        metadata_items = False
        if(len(subject_list) < 1):
            # can't find a related subject uuid
            # print(" Sad, an empty list! \n")
            return metadata_items
        else:
            if(do_parents):
                self.contexts = {}
                self.contexts_list = []
            for search_uuid in subject_list:
                # print(" trying: " + search_uuid + "\n")
                if(metadata_type == 'geo'):
                    try:
                        metadata_items = Geospace.objects.filter(uuid=search_uuid)
                        if(len(metadata_items) >= 1):
                            break
                    except Geodata.DoesNotExist:
                        # can't find any geodata, build a list of parent uuids to search
                        metadata_items = False
                else:
                    try:
                        metadata_items = Event.objects.filter(uuid=search_uuid)
                        if(len(metadata_items) >= 1):
                            break
                    except Event.DoesNotExist:
                        # can't find any geodata, build a list of parent uuids to search
                        metadata_items = False
                if(len(metadata_items) < 1):
                    metadata_items = False
                if(do_parents and metadata_items is False):
                    self.recurse_count = 0
                    self.get_parents_by_child_uuid(search_uuid)
            if(metadata_items is False and do_parents):
                # print(" going for parents: " + str(self.contexts_list) + "\n")
                # use the list of parent uuid's from the context_list. It's in order of more
                # specific to more general
                metadata_items = self.get_geochron_from_subject_list(self.contexts_list,
                                                                     metadata_type,
                                                                     False)
        return metadata_items

    def get_related_geochron(self, uuid, item_type, metadata_type):
        """
        gets the most specific geospatial data related to an item. if not a 'subjects' type,
        looks first to find related subjects
        """
        if(item_type != 'subjects'):
            subject_list = self.get_related_subjects(uuid)
        else:
            subject_list = []
            subject_list.append(uuid)
        metadata_items = self.get_geochron_from_subject_list(subject_list, metadata_type)
        return metadata_items
