import json
import requests
from django.db import connection
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject


# Open Context had some errors (I know, I know)
# this class helps resolve some data errors
class OCerrorFix():

    def __init__(self):
        self.base_url = 'http://opencontext'
        self.done_parents = []
        self.done_context_paths = {}

    def process_orphans(self):
        """ queries for missing parents while there still are missing parents
        """
        orphans = self.get_orphans()
        print('Ophan count: ' + str(len(orphans)))
        for orphan in orphans:
            last_parent_count = len(self.done_parents)
            orphan_uuid = orphan[0]
            self.fix_ophan(orphan_uuid)
            if len(self.done_parents) > last_parent_count:
                print('New parents: ' + str(len(self.done_parents)))

    def fix_ophan(self, orphan_uuid):
        """ fixes an orphan by making requests to Open Context to get missing data
        """
        json_r = self.get_orphan_oc_context(orphan_uuid)
        if json_r is not None:
            if 'parents' in json_r:
                prev_parent = False
                subjects_path = False
                for parent in json_r['parents']:
                    manifest = False
                    if subjects_path is False:
                        subjects_path = parent['label']
                    else:
                        subjects_path += '/' + parent['label']
                    try:
                        manifest = Manifest.objects.get(uuid=parent['uuid'])
                    except Manifest.DoesNotExist:
                        manifest = False
                    if manifest is False:
                        # the parent does not yet exist!
                        print('Need to make parent: ' + parent['uuid'] + ' in: ' + str(subjects_path.encode('utf8')))
                        self.create_missing_parent(orphan_uuid,
                                                   prev_parent,
                                                   subjects_path,
                                                   parent)
                    prev_parent = parent['uuid']

    def create_missing_parent(self,
                              orphan_uuid,
                              prev_parent,
                              subjects_path,
                              parent):
        """ Makes records for a missing parent in
            manifest, oc_assertions, and oc_subjects
        """
        orphan_man = False
        try:
            orphan_man = Manifest.objects.get(uuid=orphan_uuid)
        except Manifest.DoesNotExist:
            orphan_man = False
        if orphan_man is not False:
            # first check to see we didn't create this yet
            if parent['uuid'] not in self.done_parents:
                # now save the subject
                label_path_dict = {'label': parent['label'],
                                   'context': subjects_path}
                label_path_dict = self.context_path_validate(label_path_dict)
                parent['label'] = label_path_dict['label']
                subjects_path = label_path_dict['context']
                par_sub = Subject()
                par_sub.uuid = parent['uuid']
                par_sub.project_uuid = orphan_man.project_uuid
                par_sub.source_id = 'child-xml-ref'
                par_sub.context = subjects_path
                par_sub.save()
                # first make a manifest object for this item
                parent_man = Manifest()
                parent_man.uuid = parent['uuid']
                parent_man.project_uuid = orphan_man.project_uuid
                parent_man.source_id = 'child-xml-ref'
                parent_man.item_type = 'subjects'
                parent_man.class_uri = parent['class_uri']
                parent_man.label = parent['label']
                parent_man.save()
                # now save an assertion of containment
                if prev_parent is not False:
                    par_ass = Assertion()
                    par_ass.uuid = prev_parent
                    par_ass.subject_type = 'subjects'
                    par_ass.project_uuid = orphan_man.project_uuid
                    par_ass.source_id = 'child-xml-ref'
                    par_ass.obs_node = '#contents-1'
                    par_ass.obs_num = 1
                    par_ass.sort = 1
                    par_ass.visibility = 1
                    par_ass.predicate_uuid = Assertion.PREDICATES_CONTAINS
                    par_ass.object_uuid = parent['uuid']
                    par_ass.object_type = 'subjects'
                    par_ass.save()
                # note we've made this parent, so we don't have to make it
                self.done_parents.append(parent['uuid'])
            # now check the orphan has a subject record
            orphan_sub = False
            try:
                orphan_sub = Subject.objects.get(uuid=orphan_uuid)
            except Subject.DoesNotExist:
                orphan_sub = False
            if orphan_sub is False:
                orphan_sub = Subject()
                orphan_sub.uuid = orphan_uuid
                orphan_sub.project_uuid = orphan_man.project_uuid
                orphan_sub.source_id = 'child-xml-ref'
                orphan_sub.context = subjects_path + '/' + orphan_man.label
                orphan_sub.save()

    def context_path_validate(self, label_path_dict):
        """ Validates the context path """
        if label_path_dict['context'] not in self.done_context_paths:
            path_index = 1
            subs = Subject.objects.filter(context=label_path_dict['context'])[:1]
            if len(subs) > 0:
                path_index = 2
        else:
            path_index = self.done_context_paths[label_path_dict['context']]
            path_index += 1
        self.done_context_paths[label_path_dict['context']] = path_index
        if path_index > 1:
            label_path_dict['context'] += '-' + str(path_index)
            label_path_dict['label'] += '-' + str(path_index)
            print('New path: ' + str(label_path_dict['context'].encode('utf8')))
        return label_path_dict

    def get_orphan_oc_context(self, orphan_uuid):
        """ calls open context for JSON data on the context of an orphan
            Open Context will typically have records of parent paths
        """
        url = self.base_url + '/subjects/' + orphan_uuid + '.json'
        r = requests.get(url, timeout=1440)
        print('Getting data: ' + r.url)
        r.raise_for_status()
        json_r = r.json()
        return json_r

    def get_orphans(self):
        """ executes the query to get a missing parrent list """
        cursor = connection.cursor()
        sql = 'SELECT DISTINCT ass.object_uuid AS parent_missing \
               FROM oc_assertions AS ass \
               LEFT OUTER JOIN oc_manifest AS man ON (ass.uuid = man.uuid) \
               JOIN oc_manifest AS pman ON ass.project_uuid = pman.uuid \
               WHERE man.uuid IS NULL \
               AND ass.predicate_uuid = \'' + Assertion.PREDICATES_CONTAINS + '\'; '
        cursor.execute(sql)
        return cursor.fetchall()
