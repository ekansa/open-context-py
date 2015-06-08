import hashlib
from django.conf import settings
from django.db import models
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.entities.entity.models import Entity


class Containment():

    def __init__(self):
        self.contents = {}
        self.contexts = {}
        self.contexts_list = []
        self.recurse_count = 0
        self.related_subjects = False # subject items related to an item

    def get_project_top_level_contexts(self, project_uuid, visible_only=True):
        """
        Gets a list the top level contexts in a project hierarchy,
        Assumes a project is hierarchy is contained in a more general
        containment hierarchy owned by other projects
        """
        if project_uuid != '0':
            a_tab = 'oc_assertions'
            m_tab = '"oc_manifest" AS "m_b"'
            filters = 'oc_assertions.object_uuid=oc_manifest.uuid \
                      AND oc_assertions.predicate_uuid = \''\
                      + Assertion.PREDICATES_CONTAINS + '\' \
                      AND oc_assertions.uuid=m_b.uuid \
                      AND m_b.project_uuid != \''\
                      + project_uuid + '\' '
            top = Manifest.objects\
                          .filter(project_uuid=project_uuid,
                                  item_type='subjects')\
                          .extra(tables=[a_tab, m_tab], where=[filters])\
                          .values_list('uuid', flat=True)\
                          .distinct()
        else:
            top = []
            a_tab = 'oc_assertions'
            filter_a = 'oc_assertions.uuid=oc_manifest.uuid \
                        AND oc_assertions.predicate_uuid = \''\
                        + Assertion.PREDICATES_CONTAINS + '\' '
            cnt = Manifest.objects\
                          .filter(project_uuid=project_uuid,
                                  item_type='subjects')\
                          .extra(tables=[a_tab], where=[filter_a])\
                          .values_list('uuid', flat=True)\
                          .distinct()
            for uuid in cnt:
                contained = Assertion.objects\
                                     .filter(object_uuid=uuid,
                                             predicate_uuid=Assertion.PREDICATES_CONTAINS)[:1]
                if len(contained) < 1:
                    top.append(uuid)
        return top

    def get_parents_by_child_uuid(self, child_uuid, recursive=True, visibile_only=True):
        """
        creates a list of parent uuids from the containment predicate, is defaults to a recursive function
        to get all parent uuids
        """
        parent_uuid = False
        try:
            parents = Assertion.objects.filter(object_uuid=child_uuid,
                                               obs_num=1,
                                               predicate_uuid=Assertion.PREDICATES_CONTAINS)
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
            children = Assertion.objects\
                                .filter(uuid=parent_uuid,
                                        predicate_uuid=Assertion.PREDICATES_CONTAINS)
            for child in children:
                if(child.obs_node not in self.contents):
                    self.contents[child.obs_node] = []
            for child in children:
                child_uuid = child.object_uuid
                self.contents[child.obs_node].append(child_uuid)
                if recursive and (self.recurse_count < 20):
                    self.contents = self.get_children_by_parent_uuid(child_uuid,
                                                                     recursive,
                                                                     visibile_only)
            self.recurse_count += 1
        except Assertion.DoesNotExist:
            child_uuid = False
        return self.contents

    def get_related_subjects(self, uuid, reverse_links_ok=True):
        """
        makes a list of related subjects uuids from a given uuid. if none present,
        defaults to look at reverse link assertions
        """
        if not isinstance(self.related_subjects, list):
            rel_sub_uuid_list = []
            rel_subjects = Assertion.objects.filter(uuid=uuid, object_type='subjects')
            for sub in rel_subjects:
                rel_sub_uuid_list.append(sub.object_uuid)
            if len(rel_sub_uuid_list) < 1 and reverse_links_ok:
                rel_subjects = Assertion.objects.filter(object_uuid=uuid,
                                                        subject_type='subjects',
                                                        predicate_uuid=Assertion.PREDICATES_LINK)
                for sub in rel_subjects:
                    rel_sub_uuid_list.append(sub.uuid)
            self.related_subjects = rel_sub_uuid_list
        else:
            rel_sub_uuid_list = self.related_subjects
        return rel_sub_uuid_list

    def get_related_context(self, uuid, reverse_links_ok=True):
        """
        gets context for media, and document items by looking for related subjects
        """
        self.contexts = {}
        self.contexts_list = []
        parents = False
        rel_sub_uuid_list = self.get_related_subjects(uuid, reverse_links_ok)
        if len(rel_sub_uuid_list) > 0:
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
                    metadata_items = Geospace.objects.filter(uuid=search_uuid)
                    if len(metadata_items) >= 1:
                        break
                    else:
                        metadata_items = False
                elif metadata_type == 'temporal':
                    # get temporal metadata
                    lequiv = LinkEquivalence()
                    subjects = lequiv.get_identifier_list_variants(search_uuid)
                    predicates = lequiv.get_identifier_list_variants('dc-terms:temporal')
                    metadata_items = LinkAnnotation.objects\
                                                   .filter(subject__in=subjects,
                                                           predicate_uri__in=predicates)
                    if len(metadata_items) >= 1:
                        break
                    else:
                        metadata_items = False
                else:
                    metadata_items = Event.objects.filter(uuid=search_uuid)
                    if len(metadata_items) >= 1:
                        break
                    else:
                        # can't find any vent, build a list of parent uuids to search
                        metadata_items = False
                if isinstance(metadata_items, list):
                    if len(metadata_items) < 1:
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

    def get_temporal_from_project(self, project_uuid):
        """ gets temporal metadata by association with a project """
        lequiv = LinkEquivalence()
        subjects = lequiv.get_identifier_list_variants(project_uuid)
        predicates = lequiv.get_identifier_list_variants('dc-terms:temporal')
        metadata_items = LinkAnnotation.objects\
                                       .filter(subject__in=subjects,
                                               predicate_uri__in=predicates)
        if len(metadata_items) < 1:
            metadata_items = False
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

    def get_parent_slug_by_slug(self, child_slug):
        """ gets the slug for a parent item
            from a child item's slug
        """
        self.recurse_count = 0
        self.contexts_list = []
        self.contexts = {}
        output = False
        ent = Entity()
        found = ent.dereference(child_slug)
        if found:
            self.get_parents_by_child_uuid(ent.uuid, False)
            if len(self.contexts_list) > 0:
                parent_uuid = self.contexts_list[0]
                # clear class so we can use this again
                self.contexts_list = []
                self.contexts = {}
                self.recurse_count = 0
                ent_p = Entity()
                found_p = ent_p.dereference(parent_uuid)
                if found_p:
                    output = ent_p.slug
                else:
                    print('Cannot dereference parent_uuid: ' + parent_uuid)
            else:
                # print('No parent item found. (Root Context)')
                pass
        else:
            print('Cannot find the item for slug: ' + child_slug)
        return output
    
    def get_list_context_depth(self,
                               children_uuids=[],
                               prev_context_depth=0):
        """ checks to see how many context fields are needed
        """
        parents = Assertion.objects\
                           .filter(predicate_uuid=Assertion.PREDICATES_CONTAINS,
                                   object_uuid__in=children_uuids)\
                           .values_list('uuid', flat=True)\
                           .distinct('uuid')
        if len(parents) > 0:
            self.recurse_count += 1
            if self.recurse_count < 20:
                output = self.get_list_context_depth(parents,
                                                     prev_context_depth + 1)
            else:
                output = False
        else:
            output = prev_context_depth
        return output
