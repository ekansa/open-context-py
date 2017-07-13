import uuid as GenUUID
from django.conf import settings
from django.db import models
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.process import ProcessCells
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral
from opencontext_py.apps.imports.sources.unimport import UnImport


# Processes to generate subjects items for an import
class ProcessPersons():

    def __init__(self, source_id):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        self.persons_fields = []
        self.start_row = 1
        self.batch_size = settings.IMPORT_BATCH_SIZE
        self.end_row = self.batch_size
        self.count_active_fields = 0
        self.new_entities = []
        self.reconciled_entities = []
        self.not_reconciled_entities = []

    def clear_source(self):
        """ Clears a prior import if the start_row is 1.
            This makes sure new entities and assertions are made for
            this source_id, and we don't duplicate things
        """
        if self.start_row <= 1:
            # get rid of "subjects" related assertions made from this source
            unimport = UnImport(self.source_id,
                                self.project_uuid)
            unimport.delete_person_entities()

    def process_persons_batch(self):
        """ processes containment fields for subject
            entities starting with a given row number.
            This iterates over all containment fields, starting
            with the root subjhect field
        """
        self.clear_source()  # clear prior import for this source
        self.end_row = self.start_row + self.batch_size
        self.get_persons_fields()
        if len(self.persons_fields) > 0:
            print('Number of Person Fields: ' + str(len(self.persons_fields)))
            for field_obj in self.persons_fields:
                pc = ProcessCells(self.source_id,
                                  self.start_row)
                distinct_records = pc.get_field_records(field_obj.field_num,
                                                        False)
                if distinct_records is not False:
                    print('Distinct person recs: ' + str(len(distinct_records)))
                    for rec_hash, dist_rec in distinct_records.items():
                        cp = CandidatePerson()
                        cp.project_uuid = self.project_uuid
                        cp.source_id = self.source_id
                        cp.foaf_type = field_obj.field_value_cat
                        cp.import_rows = dist_rec['rows']  # list of rows where this record value is found
                        cp.reconcile_item(dist_rec['imp_cell_obj'])
                        if cp.uuid is not False:
                            if cp.new_entity:
                                self.new_entities.append({'id': str(cp.uuid),
                                                          'label': cp.label})
                            else:
                                self.reconciled_entities.append({'id': str(cp.uuid),
                                                                 'label': cp.label})
                        else:
                            bad_id = str(dist_rec['imp_cell_obj'].field_num)
                            bad_id += '-' + str(dist_rec['imp_cell_obj'].row_num)
                            self.not_reconciled_entities.append({'id': str(bad_id),
                                                                 'label': dist_rec['imp_cell_obj'].record})

    def get_persons_fields(self):
        """ Makes a list of persons fields
        """
        self.persons_fields = ImportField.objects\
                                         .filter(source_id=self.source_id,
                                                 field_type='persons')
        self.count_active_fields = len(self.persons_fields)
        return self.persons_fields


class CandidatePerson():

    DEFAULT_BLANK = '[BLANK PERSON/ORG]'

    def __init__(self):
        self.project_uuid = False
        self.source_id = False
        self.foaf_type = 'foaf:Person'  # default to a person
        self.combined_name = False
        self.label = False
        self.given_name = ''
        self.surname = ''
        self.mid_init = ''
        self.initials = ''
        self.uuid = False  # final, uuid for the item
        self.imp_cell_obj = False  # ImportCell object
        self.import_rows = False
        self.new_entity = False

    def reconcile_item(self, imp_cell_obj):
        """ Checks to see if the item exists """
        self.imp_cell_obj = imp_cell_obj
        if len(imp_cell_obj.record) > 0:
            self.combined_name = imp_cell_obj.record
            self.label = imp_cell_obj.record
        else:
            pg = ProcessGeneral(self.source_id)
            if self.import_rows is not False:
                check_list = self.import_rows
            else:
                check_list = [imp_cell_obj.row_num]
            self.evenif_blank = pg.check_blank_required(imp_cell_obj.field_num,
                                                        check_list)
            if self.evenif_blank:
                self.combined_name = self.DEFAULT_BLANK
                self.label = self.DEFAULT_BLANK
        if isinstance(self.label, str):
            if len(self.label) > 0:
                match_found = self.match_against_persons(self.combined_name)
                if match_found is False:
                    # create new subject, manifest objects. Need new UUID, since we can't assume
                    # the fl_uuid for the ImportCell reflects unique entities in a field, since
                    # uniqueness depends on context (values in other cells)
                    self.new_entity = True
                    self.uuid = GenUUID.uuid4()
                    self.create_person_item()
        self.update_import_cell_uuid()

    def create_person_item(self):
        """ Create and save a new subject object"""
        new_pers = Person()
        new_pers.uuid = self.uuid  # use the previously assigned temporary UUID
        new_pers.project_uuid = self.project_uuid
        new_pers.source_id = self.source_id
        new_pers.foaf_type = self.foaf_type
        new_pers.combined_name = self.combined_name
        new_pers.given_name = self.given_name
        new_pers.surname = self.surname
        new_pers.mid_init = self.mid_init
        new_pers.initials = self.initials
        new_pers.save()
        new_man = Manifest()
        new_man.uuid = self.uuid
        new_man.project_uuid = self.project_uuid
        new_man.source_id = self.source_id
        new_man.item_type = 'persons'
        new_man.repo = ''
        new_man.class_uri = self.foaf_type
        new_man.label = self.label
        new_man.des_predicate_uuid = ''
        new_man.views = 0
        new_man.save()

    def update_import_cell_uuid(self):
        """ Saves the uuid to the import cell record """
        if self.uuid is not False:
            if self.imp_cell_obj.fl_uuid != self.uuid:
                up_cells = ImportCell.objects\
                                     .filter(source_id=self.source_id,
                                             field_num=self.imp_cell_obj.field_num,
                                             rec_hash=self.imp_cell_obj.rec_hash)
                for up_cell in up_cells:
                    # save each cell with the correct UUID
                    up_cell.fl_uuid = self.uuid
                    up_cell.cell_ok = True
                    up_cell.save()

    def match_against_persons(self, combined_name):
        """ Checks to see if the item exists in the subjects table """
        match_found = False
        pers_objs = Person.objects\
                          .filter(project_uuid=self.project_uuid,
                                  combined_name=combined_name)[:1]
        if len(pers_objs) > 0:
            match_found = True
            self.uuid = pers_objs[0].uuid
        return match_found
