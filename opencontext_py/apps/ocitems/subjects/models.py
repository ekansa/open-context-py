import hashlib
from django.db import IntegrityError
from django.db import models
from django.db.models import Avg, Max, Min
from opencontext_py.apps.ocitems.ocitem.models import OCitem as OCitem
from opencontext_py.apps.ocitems.manifest.models import Manifest as Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion, Containment


# A subject is a generic item that is the subbject of observations
# A subject is the main type of record in open context for analytic data
# The main dependency for this app is for OCitems, which are used to generate
# Every type of item in Open Context, including subjects
class Subject(models.Model):
    uuid = models.CharField(max_length=50, primary_key=True)
    hash_id = models.CharField(max_length=50, unique=True)
    project_uuid = models.CharField(max_length=50)
    source_id = models.CharField(max_length=50)
    context = models.CharField(max_length=400)
    updated = models.DateTimeField(auto_now=True)

    def make_hash_id(self):
        """
        creates a hash-id to insure unique combinations of project_uuids and contexts
        """
        hash_obj = hashlib.sha1()
        concat_string = self.project_uuid + " " + self.context
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def save(self):
        """
        creates the hash-id on saving to insure a unique subject
        """
        self.hash_id = self.make_hash_id()
        super(Subject, self).save()

    def get_item(self):
        actItem = OCitem()
        self.ocitem = actItem.get_item(self.uuid)
        self.label = self.ocitem.label
        self.item_type = self.ocitem.item_type
        return self.ocitem

    class Meta:
        db_table = 'oc_subjects'


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

    def generate_context_path(self, uuid, include_self=True, delim='/'):
        """
        generates a context path for a subject with a given uuid
        """
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
