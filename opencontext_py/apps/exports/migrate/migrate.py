import csv
import os
import json
import requests
from django.utils.encoding import smart_text
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
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ocitems.assertions.manage import ManageAssertions
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer



class ExpMigrate():
    """ Migrates old tables into new tables



from opencontext_py.apps.exports.exprecords.dump import CSVdump
dump = CSVdump()
dump.dump('2edc4d5eeffe18944c973b242c555cbe', 'test.csv')

from opencontext_py.apps.exports.migrate.migrate import ExpMigrate
exm = ExpMigrate()
exm.get_table_dois()




    """

    LEGACY_TAB_BASE_URI = 'http://opencontext.org/exports/'
    OLDER_TAB_BASE_URI = 'http://opencontext.org/tables/'
    SLEEP_TIME = .5

    MIGRATION_SETTINGS = {
        'default': {
            'include_equiv_ld': True,
            'include_ld_source_values': False,
            'include_original_fields': True,
            'include_equiv_ld_literals': False,
        },
        'f07bce4fb08cfe926505c9e534d89a09': {
            # eol main
            'include_equiv_ld': True,
            'include_ld_source_values': True,
            'include_original_fields': False,
            'include_equiv_ld_literals': False,
        },
        '314adedf882421055fc215a56ba7a79b': {
            # eol main v2
            'include_equiv_ld': True,
            'include_ld_source_values': True,
            'include_original_fields': False,
            'include_equiv_ld_literals': False,
        },
        '05f2db65ff4faee1290192bd9a1868ed': {
            # eol metrics
            'include_equiv_ld': True,
            'include_ld_source_values': True,
            'include_original_fields': False,
            'include_equiv_ld_literals': True,
        },
        '85624441bf9215018c73ecdce82b3ceb': {
            # eol metrics
            'include_equiv_ld': True,
            'include_ld_source_values': True,
            'include_original_fields': False,
            'include_equiv_ld_literals': True,
        },
        'def8fb9c9d7fdc1993db45b7350ca955': {
            # eol metrics v2
            'include_equiv_ld': True,
            'include_ld_source_values': True,
            'include_original_fields': False,
            'include_equiv_ld_literals': True,
        }
    }

    def __init__(self):
        self.root_import_dir = settings.STATIC_IMPORTS_ROOT
        self.delete_existing = False
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
        self.tab_metadata = []

    def get_table_dois(self):
        """ gets a list of tables from the tab-manifest.csv directory """
        tab_obj = self.load_csv_file(self.table_dir, self.table_manifest_csv)
        if tab_obj is not False:
            fields = self.get_table_fields(tab_obj)
            # first field is the tableID
            i = 0
            for row in tab_obj:
                if i > 0:
                    meta = {}
                    meta['table_id'] = row[0]  # first cell has the table ID field
                    meta['label'] = row[3]
                    meta['created'] = row[4]
                    row_len = len(row)
                    ids = {'doi': None,
                           'ark': None}
                    f_i = 12
                    last_f_i = row_len - 1
                    while f_i <= last_f_i:
                        json_part = row[f_i].replace('\\', '')
                        if '"doi":' in json_part and \
                           '"doi":"http://' not in json_part:
                            doi = json_part.replace('"doi":', '')
                            doi = doi.replace('"', '')
                            ids['doi'] = doi
                            print('DOI: ' + doi)
                        if '"ark":' in json_part and \
                           '"ark":"http://' not in json_part:
                            ark = json_part.replace('"ark":', '')
                            ark = ark.replace('"', '')
                            ids['ark'] = ark
                            print('ark: ' + ark)
                        f_i += 1
                    for stable_type, ident in ids.items():
                        if ident is not None:
                            id_obj = StableIdentifer()
                            id_obj.stable_id = ident
                            id_obj.stable_type = stable_type
                            id_obj.uuid = meta['table_id']
                            id_obj.project_uuid = '0'
                            id_obj.item_type = 'tables'
                            id_obj.save()
                i += 1
        return self.tab_metadata

    def add_subjects_from_table(self, source_id, old_table):
        """ adds subjects from a table """
        proj_mappings = {
            'Petra Great Temple Excavations': 'A5DDBEA2-B3C8-43F9-8151-33343CBDC857',
            'Hazor: Zooarchaeology': 'HazorZooPRJ0000000010',
            'San Diego Archaeological Center': '3FAAA477-5572-4B05-8DC1-CA264FE1FC10'
        }
        class_mappings = {
            'Small Find': 'oc-gen:cat-object',
            'Arch. Element': 'oc-gen:cat-arch-element',
            'Locus': 'oc-gen:cat-locus',
            'Non Diag. Bone': 'oc-gen:cat-non-diag-bone'
        }
        filename = old_table + '.csv'
        tab_obj = self.load_csv_file(self.table_dir, filename)
        missing_parents = {}
        if tab_obj is not False:
            i = -1
            context_cells_indexes = []
            label_index = False
            category_index = False
            for row in tab_obj:
                i += 1
                if i == 0:
                    cc = 0
                    for cell in row:
                        if 'Context (' in cell:
                            context_cells_indexes.append(cc)
                        if 'Item name' == cell:
                            label_index = cc
                        if 'Category' == cell:
                            category_index = cc
                        cc += 1
                elif i > 0 and label_index is not False \
                    and category_index is not False:
                    # OK to generate a new item
                    uuid = row[0]
                    label = row[label_index]
                    tab_source = row[1]
                    if row[3] in proj_mappings \
                       and row[category_index] in class_mappings:
                        class_uri = class_mappings[row[category_index]]
                        project_uuid = proj_mappings[row[3]]
                        parent_contexts = []
                        for context_cell_index in context_cells_indexes:
                            parent_contexts.append(row[context_cell_index])
                        parent_context = '/'.join(parent_contexts)
                        par_sub = Subject.objects\
                                         .filter(project_uuid=project_uuid,
                                                 context=parent_context)[:1]
                        if len(par_sub) < 1:
                            print('Cannot find parent: ' + parent_context)
                        else:
                            print('Found parent: ' + parent_context)
                            parent_uuid = par_sub[0].uuid
                            try:
                                parent_ok = Manifest.objects.get(uuid=parent_uuid)
                            except Manifest.DoesNotExist:
                                parent_ok = False
                            if parent_ok is not False:
                                # we have a parent, so make the bone
                                man = Manifest()
                                m_ass = ManageAssertions()
                                m_ass.source_id = source_id
                                su_gen = SubjectGeneration()
                                man.uuid = uuid
                                man.label = label
                                man.source_id = source_id
                                man.item_type = 'subjects'
                                man.class_uri = class_uri
                                man.project_uuid = project_uuid
                                man.save()
                                m_ass.add_containment_assertion(parent_uuid, man.uuid)
                                su_gen.generate_save_context_path_from_manifest_obj(man)
                                print('Added: ' + uuid + ' from ' + tab_source)
                            else:
                                missing_parents[parent_uuid] = {'label': parent_label, 'tab': tab_source}
                else:
                    if i > 0:
                        print('Strange problems...')
                        raise('Check: ' + str(row))
            print('Missing parents: ' + str(missing_parents))

    def get_uuid_from_uri(self, uri):
        """ gets a uuid from a uri, assumes this is an open context URI"""
        uri_ex = uri.split('/')
        return uri_ex[-1]

    def check_csv_by_manifest(self, old_table):
        """ checks for missing CSV data in an old table, saves list of missing data """
        missing_tab = False
        uuids = self.get_csv_uuid_first_fields(old_table)
        if isinstance(uuids, list):
            missing_tab = []
            i = 0
            for row in uuids:
                if i == 0:
                    # field headings
                    missing_tab.append(row)
                else:
                    uuid = row[0]
                    try:
                        ok_man = Manifest.objects.get(uuid=uuid)
                    except Manifest.DoesNotExist:
                        ok_man = False
                    if ok_man is False:
                        print('Missing!! ' + str(uuid))
                        missing_tab.append(row)
                    else:
                        #print('OK: ' + uuid)
                        pass
                i += 1
            if len(missing_tab) > 1:
                # has missing uuid
                missing_file = self.set_check_directory(self.table_dir) + 'missing-' + old_table + '.csv'
                f = open(missing_file, 'w', newline='', encoding='utf-8')
                writer = csv.writer(f)
                for missing_row in missing_tab:
                    writer.writerow(missing_row)  # write the field labels in first row
                f.closed
            return missing_tab

    def clear_csv_tables(self):
        """ clears, deletes prior migration of the
            csv table imports
        """
        tab_list = self.get_table_id_list()
        for meta in tab_list:
            table_id = meta['table_id']
            print('Deleting: ' + table_id)
            ExpCell.objects\
                   .filter(table_id=table_id)\
                   .delete()
            ExpField.objects\
                    .filter(table_id=table_id)\
                    .delete()
            ExpTable.objects\
                    .filter(table_id=table_id)\
                    .delete()

    def migrate_csv_tables(self):
        """ migrates data from csv tables """
        tab_list = self.get_table_id_list()
        for meta in tab_list:
            try:
                exp_tab = ExpTable.objects.get(table_id=meta['table_id'])
            except ExpTable.DoesNotExist:
                exp_tab = False
            if exp_tab is not False:
                if self.delete_existing:
                    print('Delete previous import of: ' + meta['table_id'])
                    ExpCell.objects\
                           .filter(table_id=meta['table_id'])\
                           .delete()
                    ExpField.objects\
                            .filter(table_id=meta['table_id'])\
                            .delete()
                    ExpTable.objects\
                            .filter(table_id=meta['table_id'])\
                            .delete()
                    print('Re-loading: ' + meta['table_id'])
                    self.migrate_csv_table_data(meta)
                else:
                    print('Skipping already imported: ' + meta['table_id'])
            else:
                print('Checking: ' + meta['table_id'])
                self.migrate_csv_table_data(meta)

    def migrate_csv_table_data(self, meta):
        """ migrates data from an old csv table
            to the new export table models
        """
        uuids = self.get_csv_uuid_list(meta['table_id'])
        if len(uuids) > 0:
            print('Adding: ' + meta['table_id'] + ', ' + str(len(uuids)) + ' uuids')
            if meta['table_id'] in self.MIGRATION_SETTINGS:
                mset = self.MIGRATION_SETTINGS[meta['table_id']]
            else:
                mset = self.MIGRATION_SETTINGS['default']
            ctab = Create()
            ctab.table_id = meta['table_id']
            ctab.include_equiv_ld = mset['include_equiv_ld']
            ctab.include_ld_source_values = mset['include_ld_source_values']
            ctab.include_original_fields = mset['include_original_fields']
            ctab.include_equiv_ld_literals = mset['include_equiv_ld_literals']
            ctab.boolean_multiple_ld_fields = False  # single field for LD fields
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
            self.save_csv_table_metadata(meta)

    def save_csv_table_metadata(self, meta):
        """ saves csv table metadata """
        try:
            exp_tab = ExpTable.objects.get(table_id=meta['table_id'])
        except ExpTable.DoesNotExist:
            exp_tab = False
        if exp_tab is not False:
            exp_tab.label = meta['label']
            exp_tab.created = meta['created']
            exp_tab.save()

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
            mset = self.MIGRATION_SETTINGS['default']
            ctab = Create()
            ctab.table_id = old_table_id
            ctab.include_equiv_ld = mset['include_equiv_ld']
            ctab.include_ld_source_values = mset['include_ld_source_values']
            ctab.include_original_fields = mset['include_original_fields']
            ctab.include_equiv_ld_literals = mset['include_equiv_ld_literals']
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

    def get_csv_uuid_list(self, table_id):
        """ gets a uuid list for the more recent version
            of open context data tables. the first
            column is a field with uris
        """
        uuids = []
        filename = table_id + '.csv'
        tab_obj = self.load_csv_file(self.table_dir, filename)
        if tab_obj is not False:
            i = 0
            for row in tab_obj:
                if i > 0:
                    uri = row[0]  # the 1st column is the uri
                    uuid = uri.replace('http://opencontext.org/subjects/', '')
                    uuids.append(uuid)
                i += 1
        return uuids

    def get_csv_uuid_first_fields(self, table_id):
        """ gets a uuid list for the more recent version
            of open context data tables. the first
            column is a field with uris
        """
        uuids = []
        filename = table_id + '.csv'
        tab_obj = self.load_csv_file(self.table_dir, filename)
        if tab_obj is not False:
            i = 0
            for row in tab_obj:
                if i == 0:
                    first_row = ['uuid', 'source-table']
                    first_row += row
                    uuids.append(first_row)
                else:
                    uri = row[0]  # the 1st column is the uri
                    uuid = uri.replace('http://opencontext.org/subjects/', '')
                    new_row = [uuid, table_id]
                    new_row += row
                    uuids.append(new_row)
                i += 1
        return uuids

    def get_table_id_list(self):
        """ gets a list of tables from the tab-manifest.csv directory """
        tab_obj = self.load_csv_file(self.table_dir, self.table_manifest_csv)
        if tab_obj is not False:
            fields = self.get_table_fields(tab_obj)
            # first field is the tableID
            i = 0
            for row in tab_obj:
                if i > 0:
                    meta = {}
                    meta['table_id'] = row[0]  # first cell has the table ID field
                    meta['label'] = row[3]
                    meta['created'] = row[4]
                    self.tab_metadata.append(meta)
                i += 1
        return self.tab_metadata

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
            with open(dir_file, encoding='utf-8', errors='replace') as csvfile:
                # dialect = csv.Sniffer().sniff(csvfile.read(1024))
                # csvfile.seek(0)
                csv_obj = csv.reader(csvfile)
                tab_obj = []
                for row in csv_obj:
                    row_list = []
                    for cell in row:
                        row_list.append(cell)
                    tab_obj.append(row_list)
        else:
            print('Cannot find: ' + dir_file)
        return tab_obj
