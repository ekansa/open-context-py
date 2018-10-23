import hashlib
from django.db import IntegrityError
from django.db import models
from django.db.models import Avg, Max, Min
from unidecode import unidecode
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.ocitem.models import OCitem as OCitem
from opencontext_py.apps.ocitems.manifest.models import Manifest as Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.entities.entity.models import Entity
from django.core.cache import caches


# Some functions for processing subject items
class SubjectGeneration():

    def __init__(self):
        self.error_uuids = dict()
        self.changes = 0

    def get_most_recent_subject(self):
        """
        gets the most recently updated Subject date
        """
        try:
            subject_dates = Subject.objects.filter(updated__isnull=False).aggregate(last=Max('updated'))
            return subject_dates['last']
        except Subject.DoesNotExist:
            return False

    def get_most_recent_manifest_subjects(self):
        """
        gets the most recently revised date for subjects in the manifest table
        """
        try:
            manifest_dates = Manifest.objects.filter(item_type='subjects',
                                                     revised__isnull=False).aggregate(last=Max('revised'))
            return manifest_dates['last']
        except Manifest.DoesNotExist:
            return False

    def get_revised_manifest_subjects(self):
        """
        gets subjects from the manifest that have been revised
        """
        manifest_subjects = False
        last_subject_date = self.get_most_recent_subject()
        if(last_subject_date is not False and last_subject_date is not None):
            try:
                manifest_subjects = Manifest.objects.filter(item_type='subjects', revised__gte=last_subject_date)
            except Manifest.DoesNotExist:
                manifest_subjects = False
        else:
            try:
                manifest_subjects = Manifest.objects.filter(item_type='subjects')
            except Manifest.DoesNotExist:
                manifest_subjects = False
        return manifest_subjects

    def generate_context_path(self, uuid, include_self=True, delim='/'):
        """
        generates a context path for a subject with a given uuid
        """
        path = False
        act_contain = Containment()
        act_contain.redis_ok = False
        contexts = []
        r_contexts = act_contain.get_parents_by_child_uuid(uuid)
        for tree_node, r_parents in r_contexts.items():
            # now reverse the list of parent contexts, so top most parent context is first,
            # followed by children contexts
            contexts = r_parents[::-1]
        if(include_self):
            contexts.append(uuid)
        if(len(contexts) > 0):
            path_items = []
            for p_uuid in contexts:
                try:
                    act_p = Manifest.objects.get(uuid=p_uuid)
                    path_items.append(act_p.label)
                except Manifest.DoesNotExist:
                    return False
            path = delim.join(path_items)
        return path

    def generate_save_context_path_from_uuid(self, uuid, do_children=True):
        """ Generates and saves a context path for a subject item by uuid """
        cache = caches['redis']
        cache.clear()
        output = False
        try:
            man_obj = Manifest.objects.get(uuid=uuid,
                                           item_type='subjects')
        except Manifest.DoesNotExist:
            man_obj = False
        if man_obj is not False:
            if man_obj.item_type == 'subjects':
                output = self.generate_save_context_path_from_manifest_obj(man_obj)
                if do_children:
                    act_contain = Containment()
                    act_contain.redis_ok = False
                    # get the contents recusivelhy
                    contents = act_contain.get_children_by_parent_uuid(uuid, True)
                    if isinstance(contents, dict):
                        for tree_node, children in contents.items():
                            for child_uuid in children:
                                # do the children, but not recursively since we
                                # already have a resurive look up of contents
                                output = self.generate_save_context_path_from_uuid(child_uuid,
                                                                                   False)
        return output

    def generate_save_context_path_from_manifest_obj(self, man_obj):
        """ Generates a context path for a manifest object, then saves it to the Subjects """
        output = False
        new_context = True
        act_context = self.generate_context_path(man_obj.uuid)
        if act_context is not False:
            print('Saving Path (' + str(man_obj.uuid) + '): ' + str(unidecode(act_context)))
            try:
                sub_obj = Subject.objects.get(uuid=man_obj.uuid)
                if sub_obj.context == act_context:
                    new_context = False
            except Subject.DoesNotExist:
                sub_obj = False
            if sub_obj is False:    
                sub_obj = Subject()
                sub_obj.uuid = man_obj.uuid
                sub_obj.project_uuid = man_obj.project_uuid
                sub_obj.source_id = man_obj.source_id
            sub_obj.context = act_context
            if new_context:
                try:
                    sub_obj.save()
                    output = sub_obj
                    self.changes += 1
                except IntegrityError as e:
                    self.error_uuids[sub_obj.uuid] = {'context': act_context,
                                                      'error': e}
        else:
            self.error_uuids[man_obj.uuid] = {'context': act_context,
                                              'error': 'bad path'}
        return output

    def make_parent_the_only_parent(self, parent_uuid, pref_project_uuid=None):
        """Makes a parent the only parent of the children of that parent.
        
        This removes children from other hierarchies other than the hierarchy
        for the specified parent_uuid.
        """
        # Get the children that are supposed to be parents of the parent_uuid
        keep_p_asses = Assertion.objects.filter(uuid=parent_uuid,
                                                predicate_uuid=Assertion.PREDICATES_CONTAINS)
        for keep_p_ch in keep_p_asses:
            changed = False
            ch_uuid = keep_p_ch.object_uuid
            # Now get other assertions where the child item is contained in another item
            # that is not its preferred parent.
            bad_asses = Assertion.objects.filter(predicate_uuid=Assertion.PREDICATES_CONTAINS,
                                                 object_uuid=ch_uuid)\
                                         .exclude(uuid=parent_uuid)
            if len(bad_asses):
                print('Remove {} erroneous parents for :'.format(len(bad_asses), ch_uuid))
                bad_asses.delete()
                changed = True
            # Sometimes a child can have multiple containment relationships to the SAME
            # parent, but this still screws it up.
            good_asses = Assertion.objects.filter(uuid=parent_uuid,
                                                  predicate_uuid=Assertion.PREDICATES_CONTAINS,
                                                  object_uuid=ch_uuid)
            if len(good_asses) <= 1:
                continue
            print('Muliple ({}) parent assertions for : {} '.format(len(good_asses), ch_uuid))
            if pref_project_uuid:
                # Get a query set that excludes the preferred project_uuid
                redund_ass = Assertion.objects.filter(uuid=parent_uuid,
                                                      predicate_uuid=Assertion.PREDICATES_CONTAINS,
                                                      object_uuid=ch_uuid)\
                                               .exclude(project_uuid=pref_project_uuid)
            else:
                # Get a queryset that excludes the first item from the good query set.
                redund_ass = Assertion.objects.filter(uuid=parent_uuid,
                                                      predicate_uuid=Assertion.PREDICATES_CONTAINS,
                                                      object_uuid=ch_uuid)\
                                               .exclude(hash_id=good_asses[0].hash_id)
            if len(redund_ass) < len(good_asses):
                print('Delete {} containment assertions for child_uuid {}'.format(len(redund_ass), ch_uuid))
                redund_ass.delete()
                changed = True
            if changed:
                # Now clean up the Subjects path for the item.
                self.generate_save_context_path_from_uuid(ch_uuid)

    def fix_multiple_context_paths(self, root_uuid, level_limit=1):
        """ fixes context paths for uuids where there may be more than
            1 containment assertion
        """
        fix_uuids = self.get_fix_multiple_context_paths_uuids(root_uuid, [], level_limit)
        print('Need to fix: ' + str(len(fix_uuids)) + ' items.')
        for uuid in fix_uuids:
            self.generate_save_context_path_from_uuid(uuid, True)
        return fix_uuids
    
    def get_fix_multiple_context_paths_uuids(self,
                                             root_uuid,
                                             fix_uuids=[],
                                             level_limit=1,
                                             current_level=0):
        """ gets a list of uuids for subject items that mistakenly had multiple containment assertions
            to the same parent.
            Works recurively upto a certain depth.
        """
        if current_level < level_limit:
            new_level = current_level + 1
            del_hashes = []
            asses = Assertion.objects.filter(uuid=root_uuid, predicate_uuid='oc-gen:contains').order_by('project_uuid')
            for ass in asses:
                if ass.object_uuid not in fix_uuids and ass.hash_id not in del_hashes:
                    # get other containment asserions if we don't already have this
                    # contained object in the fix list
                    asses_b = Assertion.objects\
                                       .filter(uuid=root_uuid,
                                               predicate_uuid='oc-gen:contains',
                                               object_uuid=ass.object_uuid)\
                                       .exclude(hash_id=ass.hash_id)
                    for ass_b in asses_b:
                        del_hashes.append(ass_b.hash_id)
                        if ass_b.object_uuid not in fix_uuids:
                            fix_uuids.append(ass_b.object_uuid)
                if new_level < level_limit:
                    new_uuids = self.get_fix_multiple_context_paths_uuids(ass.object_uuid,
                                                                          fix_uuids,
                                                                          level_limit,
                                                                          new_level)
                    if len(new_uuids) > 0: 
                        if ass.object_uuid not in fix_uuids:
                            # while the current contained object is not in the fix list,
                            # some of its children need fixing, so add them to the fix list
                            for new_uuid in new_uuids:
                                if new_uuid not in fix_uuids:
                                    fix_uuids.append(new_uuid) 
            # now delete the redundant containment assertions
            for hash_id in del_hashes:
                Assertion.objects.filter(hash_id=hash_id).delete()
        return fix_uuids



    def process_manifest_for_subjects(self):
        """
        adds or updates subjects for the oc_subjects table
        """
        done_count = 0
        manifest_subjects = self.get_revised_manifest_subjects()
        if(manifest_subjects is not False):
            for sub_item in manifest_subjects:
                act_context = self.generate_context_path(sub_item.uuid)
                if(act_context is not False):
                    sub = Subject(uuid=sub_item.uuid,
                                  project_uuid=sub_item.project_uuid,
                                  source_id=sub_item.source_id,
                                  context=act_context)
                    try:
                        sub.save()
                    except IntegrityError as e:
                        self.error_uuids[sub_item.uuid] = {'context': act_context,
                                                           'error': e}
                    done_count += 1
                else:
                    self.error_uuids[sub_item.uuid] = {'context': act_context,
                                                       'error': 'bad path'}
        return done_count
