import json
import requests
from django.db import connection
from django.db.models import Avg, Max, Min
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation as LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity as LinkEntity
from opencontext_py.apps.ocitems.manifest.models import Manifest as Manifest
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
                                       'predicate_uuid'],
                     'oc_documents': ['uuid'],
                     'oc_events': ['uuid',
                                   'meta_type',
                                   'when_type'],
                     'oc_geospace': ['uuid',
                                     'meta_type'],
                     'oc_identifiers': ['uuid',
                                        'stable_type'],
                     'oc_manifest': ['uuid'],
                     'oc_mediafiles': ['uuid'
                                       'file_type'],
                     'oc_obsmetadata': ['source_id',
                                        'obs_num'],
                     'oc_persons': ['uuid'],
                     'oc_predicates': ['uuid'],
                     'oc_projects': ['uuid'],
                     'oc_strings': ['uuid'],
                     'oc_subjects': ['uuid'],
                     'oc_types': ['uuid']}

    def __init__(self):
        self.json_r = False
        self.force_insert = True  # if false overwrite a record if it already exists
        self.update_keep_old = False  # if true, use old data to 'fill in the blanks' of fields

    def get_table_records(self, act_table, after, start):
        """
        gets json data for records of a mysql datatable after a certain time
        """
        payload = {'table': act_table, 'after': after, 'start': start}
        r = requests.get(self.TABLE_RECORDS_URL, params=payload, timeout=240)
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
        if('tabs' in self.json_r):
            tabs = self.json_r['tabs']
            for act_table in tabs:
                if(act_table in self.json_r):
                    recs = self.json_r[act_table]
                    print("\n Active table: " + act_table + " (Recs: " + str(len(recs)) + ")")
                    self.store_records(act_table, recs)

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
                    f_term = act_field + ' = \'' + record[act_field] + '\' '
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
                print('\n Not allowed to overwite record.')
            else:
                newr = False
                if(act_table == 'link_annotations'):
                    newr = LinkAnnotation(**record)
                elif(act_table == 'link_entities'):
                    newr = LinkEntity(**record)
                elif(act_table == 'oc_manifest'):
                    newr = Manifest(**record)
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
                elif(act_table == 'oc_events'):
                    newr = Event(**record)
                elif(act_table == 'oc_predicates'):
                    newr = Predicate(**record)
                elif(act_table == 'oc_identifiers'):
                    newr = StableIdentifer(**record)
                elif(act_table == 'oc_obsmetadata'):
                    newr = ObsMetadata(**record)
                if(newr is not False):
                    newr.save(force_insert=self.force_insert,
                              force_update=self.update_keep_old)