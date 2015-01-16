import json
import requests
from django.db import connection
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

    def get_project_records(self, project_uuid):
        """ Gets all the data belonging to a project """
        after = '2001-01-01'
        for act_table, sub_dict in self.REQUEST_TABLES.items():
            self.get_project_tab_records(project_uuid, act_table)

    def get_project_tab_records(self, project_uuid, act_table):
        """ Gets all the data belonging to a project for a particular table """
        after = '2001-01-01'
        if act_table in self.REQUEST_TABLES:
            sub_dict = self.REQUEST_TABLES[act_table]
            for sub_table in sub_dict['sub']:
                if self.start_table is False:
                    print('Working on: ' + act_table + ' (' + str(sub_table) + ')')
                    self.process_request_table(act_table,
                                               sub_table,
                                               after,
                                               project_uuid)
                else:
                    if self.start_table == act_table and sub_table == self.start_sub:
                        # So we can start at some point in the process, useful to recover from interrupts
                        print('Process starts on: ' + act_table + ' (' + str(sub_table) + ')')
                        self.process_request_table(act_table,
                                                   sub_table,
                                                   after,
                                                   project_uuid)
                        self.start_table = False
                        self.start_sub = False
                    else:
                        print('Skipping : ' + act_table + ' (' + str(sub_table) + ')')

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

    def get_table_records(self, act_table,
                          sub_table,
                          after,
                          start,
                          recs,
                          project_uuids=False):
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
        for record in recs:
            allow_write = self.check_allow_write(act_table, record)
            record = self.prep_update_keep_old(act_table, record)
            if(allow_write is False and self.update_keep_old is False):
                print('\n Not allowed to overwite record.' + str(record))
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
