import uuid as GenUUID
from django.conf import settings
from django.db import models
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.fields.templating import ImportProfile
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.process import ProcessCells
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral
from opencontext_py.apps.imports.sources.unimport import UnImport
from opencontext_py.apps.ocitems.complexdescriptions.models import ComplexDescription
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.strings.manage import StringManagement


# Processes to generate complex descriptions for other manifest recorded entities
class ProcessComplexDescriptions():

    FRAG_ID_PREFIX = '#cplxdes-'  # fragment id prefix for a complex description
    
    def __init__(self, source_id):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        self.complex_des_fields = []
        self.start_row = 1
        self.batch_size = settings.IMPORT_BATCH_SIZE
        self.end_row = self.batch_size
        self.count_active_fields = 0
        self.count_new_assertions = 0
        self.obs_num_complex_description_assertions = 1

    def clear_source(self):
        """ Clears a prior import if the start_row is 1.
            This makes sure new entities and assertions are made for
            this source_id, and we don't duplicate things
        """
        if self.start_row <= 1:
            # get rid of "documents" related assertions made from this source
            unimport = UnImport(self.source_id,
                                self.project_uuid)
            unimport.delete_complex_description_assertions()

    def process_complex_batch(self):
        """ processes fields for documents
            entities starting with a given row number.
            This iterates over all containment fields, starting
            with the root subjhect field
        """
        self.clear_source()  # clear prior import for this source
        self.end_row = self.start_row + self.batch_size
        self.get_complex_description_fields()
        label_str_uuids = {}
        if len(self.complex_des_fields) > 0:
            print('Number of Complex Description Fields: ' + str(len(self.complex_des_fields)))
            cp_id_number = 0
            for cp_field in self.complex_des_fields:
                cp_id_number += 1
                pc = ProcessCells(self.source_id,
                                  self.start_row)
                distinct_records = pc.get_field_records_by_fl_uuid(cp_field.describes_field.field_num,
                                                                   False)
                if distinct_records is not False:
                    # sort the list in row_order from the import table
                    pg = ProcessGeneral(self.source_id)
                    distinct_records = pg.order_distinct_records(distinct_records)
                    for row_key, dist_rec in distinct_records.items():
                        if cp_field.obs_num < 1:
                            obs_num = 1
                        else:
                            obs_num = cp_field.obs_num
                        obs_node = '#obs-' + str(obs_num)
                        subject_uuid = dist_rec['imp_cell_obj'].fl_uuid
                        subject_type = cp_field.describes_field.field_type
                        subject_ok = dist_rec['imp_cell_obj'].cell_ok
                        subject_record = dist_rec['imp_cell_obj'].record
                        if subject_uuid is False or\
                           len(subject_record) < 1:
                            subject_ok = False
                        if subject_uuid == 'False':
                            subject_ok = False
                        sort = 0
                        in_rows = dist_rec['rows']
                        print('Look for complex description labels in rows: ' + str(in_rows))
                        if subject_ok is not False:
                            # OK! we have the subjects of complex descriptions
                            # with uuids, so now we can make an fl_uuid for each
                            # of the complex description fields.
                            complex_uuid = subject_uuid + self.FRAG_ID_PREFIX + str(cp_id_number)
                            complex_recs = ImportCell.objects\
                                                     .filter(source_id=self.source_id,
                                                             field_num=cp_field.field_num,
                                                             row_num__in=in_rows)\
                                                     .exclude(record='')
                            if len(complex_recs) > 0:
                                # we have records in the complex description field that are not blank
                                # and are associated with the subject of the complex description.
                                # so now, let's record this association.
                                save_ok = False
                                new_ass = Assertion()
                                new_ass.uuid = subject_uuid
                                new_ass.subject_type = subject_type
                                new_ass.project_uuid = self.project_uuid
                                new_ass.source_id = self.source_id + ProcessGeneral.COMPLEX_DESCRIPTION_SOURCE_SUFFIX
                                new_ass.obs_node = obs_node
                                new_ass.obs_num = obs_num
                                new_ass.sort = 100 + cp_id_number
                                new_ass.visibility = 1
                                new_ass.predicate_uuid = ComplexDescription.PREDICATE_COMPLEX_DES
                                new_ass.object_type = 'complex-description'
                                new_ass.object_uuid = complex_uuid
                                new_ass.save()
                                try:
                                    print('Saved complex-description: ' + complex_uuid)
                                    new_ass.save()
                                    save_ok = True
                                except:
                                    save_ok = False
                                if save_ok:
                                    self.count_new_assertions += 1
                                # now look through the complex description records and make labels
                                for comp_rec in complex_recs:
                                    # first save the fl_uuid for the complex description
                                    comp_rec.fl_uuid = complex_uuid
                                    comp_rec.save()
                                    if isinstance(cp_field.value_prefix, str):
                                        cp_label = cp_field.value_prefix + comp_rec.record
                                    else:
                                        cp_label = comp_rec.record
                                    if cp_label not in label_str_uuids:
                                        # make a uuid for the record value
                                        # adding a source_id suffix keeps this from being deleted as descriptions get processed
                                        sm = StringManagement()
                                        sm.project_uuid = self.project_uuid
                                        sm.source_id = self.source_id + ProcessGeneral.COMPLEX_DESCRIPTION_SOURCE_SUFFIX
                                        oc_string = sm.get_make_string(cp_label)
                                        content_uuid = oc_string.uuid
                                        label_str_uuids[cp_label] = content_uuid
                                    content_uuid = label_str_uuids[cp_label]
                                    save_ok = False
                                    new_ass = Assertion()
                                    new_ass.uuid = complex_uuid
                                    new_ass.subject_type = 'complex-description'
                                    new_ass.project_uuid = self.project_uuid
                                    # adding a source_id suffix keeps this from being deleted as descriptions get processed
                                    new_ass.source_id = self.source_id + ProcessGeneral.COMPLEX_DESCRIPTION_SOURCE_SUFFIX
                                    new_ass.obs_node = '#obs-' + str(self.obs_num_complex_description_assertions)
                                    new_ass.obs_num = self.obs_num_complex_description_assertions
                                    new_ass.sort = 1
                                    new_ass.visibility = 1
                                    new_ass.predicate_uuid = ComplexDescription.PREDICATE_COMPLEX_DES_LABEL
                                    new_ass.object_type = 'xsd:string'
                                    new_ass.object_uuid = content_uuid
                                    try:
                                        new_ass.save()
                                        save_ok = True
                                    except:
                                        save_ok = False
                                    if save_ok:
                                        self.count_new_assertions += 1
                                

    def get_complex_description_fields(self):
        """ Makes a list of document fields
        """
        complex_des_fields = []
        raw_cp_fields = ImportField.objects\
                                   .filter(source_id=self.source_id,
                                           field_type='complex-description')
        for cp_field in raw_cp_fields:
            desribes_fields = ImportFieldAnnotation.objects\
                                                   .filter(source_id=self.source_id,
                                                           field_num=cp_field.field_num,
                                                           predicate=ImportFieldAnnotation.PRED_COMPLEX_DES)[:1]
            if len(desribes_fields) > 0:
                desc_field_objs = ImportField.objects\
                                             .filter(source_id=self.source_id,
                                                     field_num=desribes_fields[0].object_field_num,
                                                     field_type__in=ImportProfile.DEFAULT_SUBJECT_TYPE_FIELDS)[:1]
                if len(desc_field_objs) > 0:
                    # OK! the complex property field describes a field with the correct field type (ImportProfile.DEFAULT_SUBJECT_TYPE_FIELDS)
                    # it is OK then to use to make complex descriptions
                    cp_field.describes_field = desc_field_objs[0]
                    complex_des_fields.append(cp_field)
        self.complex_des_fields = complex_des_fields
        self.count_active_fields = len(self.complex_des_fields)
        return self.complex_des_fields
