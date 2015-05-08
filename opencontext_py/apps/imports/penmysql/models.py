import json
import requests
from django.db import connection
from django.db.models import Q
from django.db.models import Avg, Max, Min
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation as LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity as LinkEntity
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest as Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile as Mediafile
from opencontext_py.apps.ocitems.persons.models import Person as Person
from opencontext_py.apps.ocitems.projects.models import Project as Project
from opencontext_py.apps.ocitems.documents.models import OCdocument as OCdocument
from opencontext_py.apps.ocitems.strings.models import OCstring as OCstring
from opencontext_py.apps.ocitems.octypes.models import OCtype as OCtype
from opencontext_py.apps.ocitems.predicates.models import Predicate as Predicate
from opencontext_py.apps.ocitems.projects.models import Project as Project
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata


# PenMysql requests JSON-data from the Penelope MySQL datastore.
# This is useful for synching the postgres and mysql databases as a temporary measure
class PenMysql():
    DEFAULT_EARLY = '1970-01-01'
    UNIQUE_FIELDS = {'link_annotations': ['subject', 'predicate_uri', 'object_uri'],
                     'link_entities': ['uri'],
                     'oc_assertions': ['uuid',
                                       'obs_num',
                                       'predicate_uuid',
                                       'object_uuid',
                                       'data_num',
                                       'data_date'],
                     'oc_documents': ['uuid'],
                     'oc_events': ['uuid',
                                   'meta_type',
                                   'when_type'],
                     'oc_geospace': ['uuid',
                                     'meta_type'],
                     'oc_identifiers': ['uuid',
                                        'stable_type'],
                     'oc_manifest': ['uuid'],
                     'oc_mediafiles': ['uuid',
                                       'file_type'],
                     'oc_obsmetadata': ['source_id',
                                        'obs_num'],
                     'oc_persons': ['uuid'],
                     'oc_predicates': ['uuid'],
                     'oc_projects': ['uuid'],
                     'oc_strings': ['uuid'],
                     'oc_subjects': ['uuid'],
                     'oc_types': ['uuid']}
    REQUEST_TABLES = LastUpdatedOrderedDict({'oc_documents': {'sub': [False]},
                                             'oc_mediafiles': {'sub': [False]},
                                             'oc_persons': {'sub': [False]},
                                             'oc_subjects': {'sub': [False]},
                                             'oc_geospace': {'sub': [False]},
                                             'oc_events': {'sub': [False]},
                                             'oc_types': {'sub': [False]},
                                             'oc_strings': {'sub': [False]},
                                             'oc_predicates': {'sub': ['variable',
                                                                       'link']},
                                             'oc_assertions': {'sub': ['contain',
                                                                       'property',
                                                                       'links-subjects',
                                                                       'links-media',
                                                                       'links-documents',
                                                                       'links-persons'
                                                                       ]},
                                             'link_entities': {'sub': [False]},
                                             'link_annotations': {'sub': [False]}})

    def __init__(self):
        self.json_r = False
        self.force_insert = True  # if false overwrite a record if it already exists
        self.update_keep_old = False  # if true, use old data to 'fill in the blanks' of fields
        self.table_records_base_url = False  # base URL for getting JSON data to import
        self.record_batch_size = 200
        self.start_table = False
        self.start_sub = False
        self.start_batch = 0
        self.after = '2001-01-01'
        self.uuids = False
        self.item_types = False
        self.item_type = False

    def get_project_records(self, project_uuid):
        """ Gets all the data belonging to a project """
        for act_table, sub_dict in self.REQUEST_TABLES.items():
            self.get_project_tab_records(project_uuid, act_table)

    def get_project_tab_records(self, project_uuid, act_table, sub_table=False):
        """ Gets all the data belonging to a project for a particular table """
        if act_table in self.REQUEST_TABLES:
            if sub_table is False:
                sub_dict = self.REQUEST_TABLES[act_table]
                for sub_table in sub_dict['sub']:
                    if self.start_table is False:
                        print('Working on: ' + act_table + ' (' + str(sub_table) + ')')
                        self.process_request_table(act_table,
                                                   sub_table,
                                                   self.after,
                                                   project_uuid)
                    else:
                        if self.start_table == act_table and sub_table == self.start_sub:
                            # So we can start at some point in the process, useful to recover from interrupts
                            print('Process starts on: ' + act_table + ' (' + str(sub_table) + ')')
                            self.process_request_table(act_table,
                                                       sub_table,
                                                       self.after,
                                                       project_uuid)
                            self.start_table = False
                            self.start_sub = False
                        else:
                            print('Skipping : ' + act_table + ' (' + str(sub_table) + ')')
            else:
                print('Process working on: ' + act_table + ' (' + str(sub_table) + ')')
                if sub_table != 'links-uuids':
                    self.process_request_table(act_table,
                                               sub_table,
                                               self.after,
                                               project_uuid)
                else:
                    self.process_links_uuids(self.after,
                                             project_uuid)

    def process_links_uuids(self, after, project_uuid):
        """ iterates through a specific type of
            content to get linking relations
        """
        self.after = after
        if self.item_types is not False:
            if not isinstance(self.item_types, list):
                self.item_types = [self.item_types]
            for item_type in self.item_types:
                self.item_type = item_type
                print('Getting ' + item_type + ' uuids')
                man_list = Manifest.objects\
                                   .filter(item_type=item_type,
                                           project_uuid=project_uuid)
                self.uuids = []
                continue_tab = True
                count = 0
                for man_obj in man_list:
                    count += 1
                    self.uuids.append(man_obj.uuid)
                    if len(self.uuids) >= 25:
                        print('Fetching ' + item_type + ' uuids (' + str(count) + ')')
                        json_ok = self.get_table_records('oc_assertions',
                                                         'links-uuids',
                                                         self.after,
                                                         0,
                                                         1000,
                                                         project_uuid)
                        if json_ok is not None:
                            self.uuids = []
                            continue_tab = self.store_tab_records()
                if len(self.uuids) > 0:
                    # now do the remaining
                    print('LAST fetch for ' + item_type + ' uuids (' + str(count) + ')')
                    json_ok = self.get_table_records('oc_assertions',
                                                     'links-uuids',
                                                     self.after,
                                                     0,
                                                     1000,
                                                     project_uuid)
                    if json_ok is not None:
                        self.uuids = []
                        continue_tab = self.store_tab_records()

    def process_inferred_subject_uuids(self, after, project_uuid):
        """ iterates through a specific type of
            content to get linking relations
            for items not connected to subjects
        """
        self.after = after
        if self.item_types is not False:
            if not isinstance(self.item_types, list):
                self.item_types = [self.item_types]
            continue_tab = True
            count = 0
            for item_type in self.item_types:
                self.item_type = item_type
                print('Getting ' + item_type + ' uuids')
                man_list = Manifest.objects\
                                   .filter(item_type=item_type,
                                           project_uuid=project_uuid)
                for man_obj in man_list:
                    # check no subjects associated
                    self.uuids = False
                    uuid = man_obj.uuid
                    sub_ass = Assertion.objects\
                                       .filter(Q(subject_type='subjects',
                                                 object_uuid=uuid)
                                               | Q(uuid=uuid,
                                                   predicate_uuid='oc-3',
                                                   object_type='subjects'))[:1]
                    if len(sub_ass) < 1:
                        # no linking to a subject yet, so lets make one
                        count += 1
                        output = '[' + str(count) + '] Get inferred subjects for: '
                        output += uuid + ' ' + item_type
                        print(output)
                        self.uuids = [uuid]
                        json_ok = self.get_table_records('oc_assertions',
                                                         'links-subjects-inf',
                                                         self.after,
                                                         0,
                                                         1000,
                                                         project_uuid)
                        continue_tab = self.store_tab_records()
                        if json_ok is not None:
                            self.uuids = False
                            continue_tab = self.store_tab_records()
                    if continue_tab is False:
                        break

    def process_request_table(self, act_table,
                              sub_table,
                              after,
                              project_uuids=False):
        """ iterates through a table until there are
        no more records to save
        """
        continue_tab = True
        if self.start_batch > 0\
           and self.start_table == act_table\
           and self.start_sub == sub_table:
            start = self.start_batch
            self.start_batch = 0
        else:
            start = 0
        recs = self.record_batch_size
        while continue_tab:
            json_ok = self.get_table_records(act_table,
                                             sub_table,
                                             after,
                                             start,
                                             recs,
                                             project_uuids)
            if json_ok is not None:
                continue_tab = self.store_tab_records()
            else:
                print('Bad JSON in: ' + act_table + '(' + str(sub_table) + ')')
                continue_tab = False
            start = start + recs

    def get_missing_media(self, project_uuids):
        """ gets oc_annotations for items missing descriptions """
        if ',' in project_uuids:
            p_list = project_uuids.split(',')
        else:
            p_list = [project_uuids]
        for project_uuid in p_list:
            sql = ' SELECT ass.hash_id, ass.object_uuid AS muuid \
                    FROM oc_assertions AS ass \
                    WHERE ass.project_uuid = \
                    \'' + project_uuid + '\' \
                    AND ass.object_type = \'media\' \
                    AND ass.object_uuid NOT IN ( \
                    SELECT man.uuid \
                    FROM oc_manifest AS man \
                    WHERE man.project_uuid = \
                    \'' + project_uuid + '\' \
                    AND (man.item_type = \'media\')\
                    );'
            no_media = Assertion.objects.raw(sql)
            uuids = []
            for missing in no_media:
                uuid = missing.muuid
                if uuid not in uuids:
                    uuids.append(uuid)
                    json_ok = self.get_table_records('oc_mediafiles',
                                                     False,
                                                     self.after,
                                                     0,
                                                     200,
                                                     project_uuid,
                                                     uuid)
                    if json_ok is not None:
                        continue_tab = self.store_tab_records()

    def get_missing_strings(self, project_uuids):
        """ gets oc_annotations for items missing descriptions """
        if ',' in project_uuids:
            p_list = project_uuids.split(',')
        else:
            p_list = [project_uuids]
        for project_uuid in p_list:
            sql = 'SELECT oc_assertions.hash_id, oc_assertions.object_uuid AS string_uuid \
                   FROM oc_assertions \
                   LEFT JOIN oc_strings ON oc_assertions.object_uuid = oc_strings.uuid \
                   WHERE oc_assertions.project_uuid = \
                   \'' + project_uuid + '\' \
                   AND oc_assertions.object_type = \'xsd:string\' \
                   AND oc_strings.uuid IS NULL; '
            no_strings = Assertion.objects.raw(sql)
            for obj_missing in no_strings:
                json_ok = self.get_table_records('oc_strings',
                                                 False,
                                                 self.after,
                                                 0,
                                                 200,
                                                 project_uuid,
                                                 obj_missing.string_uuid)
                if json_ok is not None:
                    continue_tab = self.store_tab_records()
            sql = 'SELECT oc_types.uuid, oc_types.content_uuid AS string_uuid \
                   FROM oc_types \
                   LEFT JOIN oc_strings ON oc_types.content_uuid = oc_strings.uuid \
                   WHERE oc_types.project_uuid = \
                   \'' + project_uuid + '\' \
                   AND oc_strings.uuid IS NULL; '
            no_strings = OCtype.objects.raw(sql)
            for obj_missing in no_strings:
                json_ok = self.get_table_records('oc_strings',
                                                 False,
                                                 self.after,
                                                 0,
                                                 200,
                                                 project_uuid,
                                                 obj_missing.string_uuid)
                if json_ok is not None:
                    continue_tab = self.store_tab_records()

    def get_missing_link_entities(self, project_uuids):
        """ gets oc_annotations for items missing descriptions """
        if ',' in project_uuids:
            p_list = project_uuids.split(',')
        else:
            p_list = [project_uuids]
        for project_uuid in p_list:
            q = 'http://opencontext.org%'
            sql = 'SELECT link_annotations.hash_id, link_annotations.object_uri AS object_uri \
                   FROM link_annotations \
                   LEFT JOIN link_entities ON link_annotations.object_uri = link_entities.uri \
                   WHERE link_annotations.project_uuid = \
                   \'' + project_uuid + '\' \
                   AND link_annotations.object_uri NOT LIKE %(my_like)s \
                   AND link_entities.uri IS NULL; '
            # print(str(sql))
            no_objects = LinkAnnotation.objects.raw(sql, {'my_like': q})
            for obj_missing in no_objects:
                json_ok = self.get_table_records('link_entities',
                                                 False,
                                                 self.after,
                                                 0,
                                                 200,
                                                 project_uuid,
                                                 False,
                                                 obj_missing.object_uri)
                if json_ok is not None:
                    continue_tab = self.store_tab_records()

    def get_missing_descriptions(self, project_uuids):
        """ gets oc_annotations for items missing descriptions """
        if ',' in project_uuids:
            p_list = project_uuids.split(',')
        else:
            p_list = [project_uuids]
        for project_uuid in p_list:
            sql = 'SELECT oc_manifest.uuid AS uuid \
                   FROM oc_manifest \
                   LEFT JOIN oc_assertions ON \
                   (oc_manifest.uuid = oc_assertions.uuid \
                   AND oc_assertions.predicate_uuid != \'' \
                + Assertion.PREDICATES_CONTAINS + '\') \
                   WHERE oc_manifest.project_uuid = \
                   \'' + project_uuid + '\' \
                   AND oc_assertions.uuid IS NULL; '
            non_descript = Manifest.objects.raw(sql)
            for dull_man in non_descript:
                json_ok = self.get_table_records('oc_assertions',
                                                 'property',
                                                 self.after,
                                                 0,
                                                 200,
                                                 project_uuid,
                                                 dull_man.uuid)
                if json_ok is not None:
                    continue_tab = self.store_tab_records()

    def get_table_records(self, act_table,
                          sub_table,
                          after,
                          start,
                          recs,
                          project_uuids=False,
                          uuid=False,
                          uri=False):
        """
        gets json data for records of a mysql datatable after a certain time
        """
        payload = {'tab': act_table,
                   'after': after,
                   'start': start,
                   'recs': recs}
        if sub_table is not False:
            payload['sub'] = sub_table
        if project_uuids is not False:
            payload['project_uuids'] = project_uuids
        if uuid is not False:
            payload['uuid'] = uuid
        if isinstance(self.uuids, list):
            payload['uuids'] = ','.join(self.uuids)
        if self.item_type is not False:
            payload['item_type'] = self.item_type
        if uri is not False:
            payload['uri'] = uri
        r = requests.get(self.table_records_base_url, params=payload, timeout=1440)
        print('Getting data: ' + r.url)
        r.raise_for_status()
        json_r = r.json()
        self.json_r = json_r
        return json_r

    def get_json_data(self, json_url):
        """
        gets json data from a specific URL
        """
        r = requests.get(json_url)
        json_r = r.json()
        self.json_r = json_r
        return json_r

    def store_tab_records(self):
        """
        iterates through tabs in the JSON data to save list of records for each tab
        """
        has_records = False  # the JSON data actually has records
        if('tabs' in self.json_r):
            tabs = self.json_r['tabs']
            for act_table in tabs:
                if(act_table in self.json_r):
                    recs = self.json_r[act_table]
                    if len(recs) > 0:
                        has_records = True
                        print("\n Active table: " + act_table + " (Recs: " + str(len(recs)) + ")")
                        self.store_records(act_table, recs)
        else:
            print("Where's the data?")
        return has_records

    def check_allow_write(self, act_table, record):
        """
        checks to see if a record is OK to add
        """
        if(self.force_insert is False):
            allow_write = True # create new record or save over old
        else:
            allow_write = False
            if(act_table in self.UNIQUE_FIELDS):
                sql = 'SELECT * FROM ' + act_table + ' WHERE '
                f_terms = []
                for act_field in self.UNIQUE_FIELDS[act_table]:
                    if act_field in record:
                        f_term = act_field + ' = \'' + str(record[act_field]) + '\' '
                        f_terms.append(f_term)
                sql = sql + ' AND '.join(f_terms)
                sql = sql + ' LIMIT 1; '
                cursor = connection.cursor()
                cursor.execute(sql)
                results = cursor.fetchall()
                if(len(results) < 1):
                    allow_write = True
        return allow_write

    def dictfetchall(self, cursor):
        "Returns all rows from a cursor as a dict"
        desc = cursor.description
        return [
            dict(zip([col[0] for col in desc], row))
            for row in cursor.fetchall()
        ]

    def prep_update_keep_old(self, act_table, record):
        """
        checks to see if a record is OK to add
        """
        if(self.update_keep_old is False):
            new_record = record  # do not change the new record with old values
        else:
            new_record = False  # default to false, a failure
            if(act_table in self.UNIQUE_FIELDS):
                sql = 'SELECT * FROM ' + act_table + ' WHERE '
                f_terms = []
                for act_field in self.UNIQUE_FIELDS[act_table]:
                    if act_field in record:
                        f_term = act_field + ' = \'' + record[act_field] + '\' '
                        f_terms.append(f_term)
                sql = sql + ' AND '.join(f_terms)
                sql = sql + ' LIMIT 1; '
                cursor = connection.cursor()
                cursor.execute(sql)
                results = self.dictfetchall(cursor)
                if(len(results) == 1):
                    new_record = {}
                    for field_key, value in results[0].items():
                        if field_key in record:
                            new_record[field_key] = record[field_key]  # use new data provided
                        else:
                            new_record[field_key] = value  # use old value for data
        return new_record

    def store_records(self, act_table, recs):
        """
        stores records retrieved for a given table
        """
        i = 0
        for record in recs:
            i += 1
            allow_write = self.check_allow_write(act_table, record)
            record = self.prep_update_keep_old(act_table, record)
            if(allow_write is False and self.update_keep_old is False):
                print('\n Not allowed to overwite record.' + str(i))
            else:
                # print('\n Adding record:' + str(record))
                newr = False
                if(act_table == 'link_annotations'):
                    newr = LinkAnnotation(**record)
                elif(act_table == 'link_entities'):
                    newr = LinkEntity(**record)
                elif(act_table == 'oc_assertions'):
                    newr = Assertion(**record)
                elif(act_table == 'oc_manifest'):
                    newr = Manifest(**record)
                elif(act_table == 'oc_subjects'):
                    newr = Subject(**record)
                elif(act_table == 'oc_mediafiles'):
                    newr = Mediafile(**record)
                elif(act_table == 'oc_documents'):
                    newr = OCdocument(**record)
                elif(act_table == 'oc_persons'):
                    newr = Person(**record)
                elif(act_table == 'oc_projects'):
                    newr = Project(**record)
                elif(act_table == 'oc_strings'):
                    newr = OCstring(**record)
                elif(act_table == 'oc_types'):
                    newr = OCtype(**record)
                elif(act_table == 'oc_geospace'):
                    newr = Geospace(**record)
                elif(act_table == 'oc_events'):
                    newr = Event(**record)
                elif(act_table == 'oc_predicates'):
                    newr = Predicate(**record)
                elif(act_table == 'oc_identifiers'):
                    newr = StableIdentifer(**record)
                elif(act_table == 'oc_obsmetadata'):
                    newr = ObsMetadata(**record)
                if(newr is not False):
                    try:
                        newr.save(force_insert=self.force_insert,
                                  force_update=self.update_keep_old)
                    except Exception as error:
                        print('Something slipped past in ' + act_table + '...' + str(error))
