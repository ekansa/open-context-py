import csv
import os
import json
import requests
from time import sleep
from collections import OrderedDict
from django.db import models
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.exports.expfields.models import ExpField
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.exptables.models import ExpTable
from opencontext_py.apps.exports.exprecords.create import Create


class ExpMigrate():
    """ Migrates old tables into new tables

from opencontext_py.apps.exports.migrate.migrate import ExpMigrate
exm = ExpMigrate()
exm.migrate_old_tables()

from opencontext_py.apps.exports.migrate.migrate import ExpMigrate
exm = ExpMigrate()
exm.document_missing_old_oc_uuids()


from opencontext_py.apps.exports.exprecords.dump import CSVdump
dump = CSVdump()
dump.dump('2edc4d5eeffe18944c973b242c555cbe', 'test.csv')

    """

    LEGACY_TAB_BASE_URI = 'http://opencontext.org/exports/'
    OLDER_TAB_BASE_URI = 'http://opencontext.org/tables/'
    SLEEP_TIME = .5

    def __init__(self):
        self.root_import_dir = settings.STATIC_IMPORTS_ROOT
        self.table_id_list = []
        self.table_dir = 'oc-tabs'  # CSV files from more recent open context downloads
        self.old_oc_table_dir = 'old-oc-tabs'  # JSON files for older open context downloads
        self.table_manifest_csv = 'tab-manifest.csv'
        self.delay_before_request = self.SLEEP_TIME
        self.label = False
        self.created = False
        self.note = ''
        self.act_table_obj = False
        self.abs_path = 'C:\\GitHub\\open-context-py\\static\\imports\\'

    def migrate_old_tables(self):
        """ migrates all the old JSON table data
            into the table export models
        """
        self.get_migrate_old_oc_table_ids()
        for old_table_id in self.table_id_list:
            if isinstance(old_table_id, str):
                try:
                    exp_tab = ExpTable.objects.get(table_id=old_table_id)
                except ExpTable.DoesNotExist:
                    exp_tab = False
                if exp_tab is not False:
                    print('Skipping already imported: ' + old_table_id)
                else:
                    self.migrate_old_oc_table(old_table_id)

    def convert_all_old_oc_to_old_csv(self):
        """ converts all the old-oc JSON to CSV
            this represents an old version
            of the original CSV data
        """
        self.get_migrate_old_oc_table_ids()
        for old_table_id in self.table_id_list:
            if isinstance(old_table_id, str):
                self.convert_old_oc_json_to_csv(old_table_id)

    def document_missing_old_oc_uuids(self):
        """ checks to see that uuids
            are missing, documents them in a JSON file
        """
        missing = LastUpdatedOrderedDict()
        missing['total-missing'] = 0
        self.get_migrate_old_oc_table_ids()
        for old_table_id in self.table_id_list:
            act_tab = LastUpdatedOrderedDict()
            act_tab['label'] = self.label
            act_tab['records'] = LastUpdatedOrderedDict()
            if isinstance(old_table_id, str):
                uuids = self.get_old_oc_record_uuids(old_table_id,
                                                     True)
                for uuid in uuids:
                    u_ok = ExpCell.objects\
                                  .filter(table_id=old_table_id,
                                          uuid=uuid)[:1]
                    if len(u_ok) < 1:
                        missing['total-missing'] += 1
                        print(str(missing['total-missing']) + ' uuid: ' + uuid)
                        if self.act_table_obj is not False:
                            if 'records' in self.act_table_obj:
                                if uuid in self.act_table_obj['records']:
                                    act_tab['records'][uuid] = self.act_table_obj['records'][uuid]
            missing[old_table_id] = act_tab
        missing_json = json.dumps(missing,
                                  ensure_ascii=False, indent=4)
        dir_file = self.set_check_directory(self.old_oc_table_dir) + 'missing-uuids.json'
        f = open(dir_file, 'w', encoding='utf-8')
        f.write(missing_json)
        f.close()

    def get_migrate_old_oc_table_ids(self):
        """ gets old table ids from the
            directory contents for the old format
        """
        act_dir = self.root_import_dir + self.old_oc_table_dir
        abs_dir = self.abs_path + 'old-oc-tabs'
        for filename in os.listdir(abs_dir):
            if '.json' in filename:
                old_table_id = filename.replace('.json', '')
                self.table_id_list.append(old_table_id)
        return self.table_id_list

    def migrate_old_oc_table(self, old_table_id):
        """ migrates data from an old open context table, identified by an ID
            into the new table exporter models
        """
        uuids = self.get_old_oc_record_uuids(old_table_id)
        if len(uuids) > 0:
            ctab = Create()
            ctab.table_id = old_table_id
            ctab.include_ld_source_values = False  # do NOT include values assocated with linked data
            ctab.include_original_fields = True  # include fields from source data
            ctab.source_field_label_suffix = ''  # blank suffix for source data field names
            ctab.prep_default_fields()
            ctab.uuidlist = uuids
            ctab.process_uuid_list(uuids)
            ctab.get_predicate_uuids()  # now prepare to do item descriptions
            ctab.get_predicate_link_annotations()  # even if not showing linked data
            ctab.process_ld_predicates_values()  # only if exporting linked data
            ctab.save_ld_fields()  # only if exporting linked data
            ctab.save_source_fields()  # save source data, possibly limited by observations
            ctab.update_table_metadata()  # save a record of the table metadata
            self.save_table_metadata(old_table_id)

    def save_table_metadata(self, old_table_id):
        """ saves table metadata from the source JSON """
        if self.label is not False and self.created is not False:
            try:
                exp_tab = ExpTable.objects.get(table_id=old_table_id)
            except ExpTable.DoesNotExist:
                exp_tab = False
            if exp_tab is not False:
                exp_tab.label = self.label
                exp_tab.created = self.created
                exp_tab.abstract = self.note
                exp_tab.save()

    def get_old_oc_record_uuids(self, old_table_id, cache_obj=False):
        """ gets a list of uuids from an old
            open context JSON format file
        """
        uuids = []
        print('Dir ' + str(self.old_oc_table_dir) + ' id: ' + old_table_id)
        dir_file = self.set_check_directory(self.old_oc_table_dir) + old_table_id + '.json'
        if os.path.exists(dir_file):
            fp = open(dir_file, 'r')
            try:
                # keep keys in the same order as the original file
                json_obj = json.load(fp, object_pairs_hook=OrderedDict)
            except:
                print('CRAP! File not valid JSON' + dir_file)
                json_obj = False
            if cache_obj:
                self.act_table_obj = json_obj
            if json_obj is not False:
                if 'meta' in json_obj:
                    note_list = []
                    if 'table_name' in json_obj['meta']:
                        self.label = json_obj['meta']['table_name']
                        if len(self.label) < 1:
                            if 'projects' in json_obj['meta']:
                                self.label = ', '.join(json_obj['meta']['projects'])
                                self.label = 'Table for: ' + self.note
                    if 'table_description' in json_obj['meta']:
                        if len(json_obj['meta']['table_description']) > 0:
                            note_list.append(json_obj['meta']['table_description'])
                    if 'tagstring' in json_obj['meta']:
                        if len(json_obj['meta']['tagstring']) > 0:
                            note_list.append(json_obj['meta']['tagstring'])
                    if len(note_list) == 0:
                        self.note = 'No note'
                    else:
                        self.note = ' '.join(note_list)
                    if 'TabCreated' in json_obj['meta']:
                        self.created = json_obj['meta']['TabCreated']
                if 'records' in json_obj:
                    for uuid, rec in json_obj['records'].items():
                        uuids.append(uuid)
        return uuids

    def convert_old_oc_json_to_csv(self, old_table_id):
        """ gets a list of uuids from an old
            open context JSON format file
        """
        field_mappings = {
            'proj': 'Project',
            'person': 'Linked Persons',
            'def_context_0': 'Context (1)',
            'def_context_1': 'Context (2)',
            'def_context_2': 'Context (3)',
            'def_context_3': 'Context (4)',
            'def_context_4': 'Context (5)',
            'def_context_5': 'Context (6)',
            'pub_date': 'Publication Date',
            'update': 'Last Updated',
            'category': 'Category',
            'label': 'Item name'
        }
        ok = False
        print('Dir ' + str(self.old_oc_table_dir) + ' id: ' + old_table_id)
        dir_file = self.set_check_directory(self.old_oc_table_dir) + old_table_id + '.json'
        csv_file = self.set_check_directory(self.old_oc_table_dir) + old_table_id + '.csv'
        if os.path.exists(dir_file):
            fp = open(dir_file, 'r')
            try:
                # keep keys in the same order as the original file
                json_obj = json.load(fp, object_pairs_hook=OrderedDict)
            except:
                print('CRAP! File not valid JSON' + dir_file)
                json_obj = False
            if json_obj is not False:
                if 'records' in json_obj:
                    i = 0
                    rows = []
                    fields = []
                    for uuid, rec in json_obj['records'].items():
                        row = []
                        if i == 0:
                            # first row is for column headings
                            row.append('Open Context URL')
                            for field, val in rec.items():
                                fields.append(field)
                                if field in field_mappings:
                                    # change name to the field mappings
                                    field = field_mappings[field]
                                row.append(field)
                        else:
                            uri = 'http://opencontext.org/subjects/' + uuid
                            row.append(uri)
                            for field in fields:
                                if field in rec:
                                    if rec[field] is None:
                                        value = ''
                                    else:
                                        value = str(rec[field])
                                else:
                                    value = ''
                                row.append(value)
                        rows.append(row)
                        i += 1
                    if len(rows) > 0:
                        f = open(csv_file, 'w', newline='', encoding='utf-8')
                        writer = csv.writer(f)
                        for row in rows:
                            writer.writerow(row)
                        f.closed
                        ok = True
        return ok

    def check_table_files_exist(self):
        """ checks to see if table files exist """
        self.get_table_id_list()
        for table_id in self.table_id_list:
            dir_file = self.set_check_directory(self.table_dir) + table_id + '.csv'
            if os.path.exists(dir_file):
                print('OK: ' + table_id)
            else:
                print('----------------------------')
                print('** MISSING !!! ' + table_id)
                print('----------------------------')

    def get_tables_from_oc(self):
        """ downloads legacy data for tables """
        self.get_table_id_list()
        for table_id in self.table_id_list:
            self.get_save_legacy_csv(table_id)

    def get_table_id_list(self):
        """ gets a list of tables from the tab-manifest.csv directory """
        tab_obj = self.load_csv_file(self.table_dir, self.table_manifest_csv)
        if tab_obj is not False:
            fields = self.get_table_fields(tab_obj)
            # first field is the tableID
            i = 0
            for row in tab_obj:
                if i > 0:
                    table_id = row[0]  # first cell has the table ID field
                    self.table_id_list.append(table_id)
                i += 1
        return self.table_id_list

    def get_table_fields(self, tab_obj):
        """ gets list of table fields from the first row """
        fields = []
        if tab_obj is not False:
            fields = tab_obj[0]
        return fields

    def get_save_legacy_csv(self, table_id):
        """ gets and saves the legacy csv files
            from open context
        """
        sleep(self.delay_before_request)
        dir_file = self.set_check_directory(self.table_dir) + table_id + '.csv'
        url = self.LEGACY_TAB_BASE_URI + table_id + '.csv'
        print('Working on :' + url)
        try:
            gapi = GeneralAPI()
            r = requests.get(url,
                             timeout=480,
                             headers=gapi.client_headers)
            r.raise_for_status()
            text = r.text
        except:
            text = False
        if text is not False:
            f = open(dir_file, 'w', encoding='utf-8')
            f.write(text)
            f.close()

    def set_check_directory(self, act_dir):
        """ Prepares a directory to find import GeoJSON files """
        output = False
        full_dir = self.root_import_dir + act_dir + '/'
        if os.path.exists(full_dir):
            output = full_dir
        if output is False:
            output = self.abs_path + act_dir + '\\'
        return output

    def load_csv_file(self, act_dir, filename):
        """ Loads a file and parse a csv
            file
        """
        tab_obj = False
        dir_file = self.set_check_directory(act_dir) + filename
        if os.path.exists(dir_file):
            with open(dir_file, encoding='utf-8') as csvfile:
                dialect = csv.Sniffer().sniff(csvfile.read(1024))
                csvfile.seek(0)
                csv_obj = csv.reader(csvfile, dialect)
                tab_obj = []
                for row in csv_obj:
                    row_list = []
                    for cell in row:
                        row_list.append(cell)
                    tab_obj.append(row_list)
        return tab_obj
