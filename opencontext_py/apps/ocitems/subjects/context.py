import hashlib
from django.db import IntegrityError
from django.db import models
from django.db.models import Avg, Max, Min
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.ocitem.models import OCitem as OCitem
from opencontext_py.apps.ocitems.manifest.models import Manifest as Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion, Containment
from opencontext_py.apps.entities.entity.models import Entity


# Some functions for processing subject items
class SubjectGeneration():
    error_uuids = dict()

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

    def generate_context_path(self, uuid, include_self=True):
        """
        generates a context path for a subject with a given uuid
        """
        delim = Subject.HIEARCHY_DELIM
        path = False
        act_contain = Containment()
        act_contain.contexts = []
        r_contexts = act_contain.get_parents_by_child_uuid(uuid)
        # now reverse the list of contexts, so top most context is first, followed by children contexts
        contexts = r_contexts[::-1]
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


class Context():
    """ Class for managing subject contexts, especially for lookups """
    def __init__(self):
        self.entity = False

    def context_dereference(self, context):
        """ looks up a context, described as a '/' seperated list of labels """
        ent = Entity()
        output = False
        try:
            subject = Subject.objects.filter(context=context)[:1]
        except Subject.DoesNotExist:
            subject = False
        if subject is not False:
            if len(subject) == 1:
                output = ent.dereference(subject[0].uuid)
                self.entity = ent
        return output
