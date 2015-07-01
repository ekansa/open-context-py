import hashlib
from django.db import IntegrityError
from django.db import models
from django.db.models import Avg, Max, Min
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.ocitem.models import OCitem as OCitem
from opencontext_py.apps.ocitems.manifest.models import Manifest as Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.assertions.containment import Containment
from opencontext_py.apps.entities.entity.models import Entity


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
                    # get the contents recusivelhy
                    contents = act_contain.get_children_by_parent_uuid(uuid, True)
                    if isinstance(child_list, dict):
                        for tree_node, children in self.contents.items():
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
