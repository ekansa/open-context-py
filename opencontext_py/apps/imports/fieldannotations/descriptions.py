import uuid as GenUUID
import re
import datetime
from dateutil.parser import parse
from django.conf import settings
from django.db import models
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.assertions.predicatetype import PredicateTypeAssertions
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.predicates.manage import PredicateManagement
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.octypes.manage import TypeManagement
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.strings.manage import StringManagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fields.templating import ImportProfile
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.process import ProcessCells
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral
from opencontext_py.apps.imports.sources.unimport import UnImport


# Processes to generate descriptions
class ProcessDescriptions():

    def __init__(self, source_id):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        self.description_annotations = False
        self.des_rels = False
        self.start_row = 1
        self.batch_size = settings.IMPORT_BATCH_SIZE
        self.end_row = self.batch_size
        self.example_size = 5
        self.reconciled_predicates = {}
        self.reconciled_types = {}
        self.field_valueofs = {}
        self.subject_predicate_counts = {}
        self.count_active_fields = 0
        self.count_new_assertions = 0
        self.label_preds = {}

    def clear_source(self):
        """ Clears a prior import if the start_row is 1.
            This makes sure new entities and assertions are made for
            this source_id, and we don't duplicate things
        """
        if self.start_row <= 1:
            # will clear an import of descriptions
            print('Clearing old description assertions...')
            unimport = UnImport(self.source_id,
                                self.project_uuid)
            unimport.COMPLEX_DESCRIPTION_SOURCE_SUFFIX = ProcessGeneral.COMPLEX_DESCRIPTION_SOURCE_SUFFIX
            ok = unimport.delete_describe_assertions()
            if ok:
                print('Assertions deleted...')
            else:
                print('Something horrible happened!')
            unimport.delete_predicate_vars()
            unimport.delete_types_entities()
            unimport.delete_strings()
        return True

    def get_description_examples(self):
        """ Gets example entities described by other fields
        """
        example_entities = []
        self.get_description_annotations()
        if self.des_rels is not False:
            for subj_field_num, ent_obj in self.des_rels.items():
                # get some example records 
                pc = ProcessCells(self.source_id,
                                  self.start_row)
                distinct_records = pc.get_field_records(subj_field_num,
                                                        False)
                if distinct_records is not False:
                    entity_example_count = 0
                    # sort the list in row_order from the import table
                    pg = ProcessGeneral(self.source_id)
                    distinct_records = pg.order_distinct_records(distinct_records)
                    for row_key, dist_rec in distinct_records.items():
                        if entity_example_count < self.example_size:
                            # if we're less than the example size, make
                            # an example object
                            entity_example_count += 1
                            entity = LastUpdatedOrderedDict()
                            entity_label = dist_rec['imp_cell_obj'].record
                            if len(entity_label) < 1:
                                entity_label = '[BLANK]'
                            entity_label = ent_obj['field'].value_prefix + entity_label
                            entity['label'] = entity_label
                            entity['id'] = str(subj_field_num) + '-' + str(row_key)
                            entity['descriptions'] = []
                            example_rows = []
                            example_rows.append(dist_rec['rows'][0])
                            for des_field_obj in ent_obj['des_by_fields']:
                                des_item = LastUpdatedOrderedDict()
                                des_item['predicate'] = LastUpdatedOrderedDict()
                                # values are in a list, in case there are more than 1 (variable-value)
                                des_item['objects'] = []
                                des_item['predicate']['type'] = des_field_obj.field_type
                                if des_field_obj.field_type == 'description':
                                    # set the predicate for this description
                                    des_item['predicate']['label'] = des_field_obj.label
                                    des_item['predicate']['id'] = des_field_obj.field_num
                                    # now get a value for this description from the imported cells
                                    pc = ProcessCells(self.source_id,
                                                      self.start_row)
                                    val_recs = pc.get_field_records(des_field_obj.field_num,
                                                                    example_rows)
                                    pg = ProcessGeneral(self.source_id)
                                    val_rec = pg.get_first_distinct_record(val_recs)
                                    if val_rec is not False:
                                        object_val = LastUpdatedOrderedDict()
                                        object_val['record'] = val_rec['imp_cell_obj'].record
                                        object_val['id'] = val_rec['rows'][0]
                                        des_item['objects'].append(object_val)
                                    entity['descriptions'].append(des_item)
                                elif des_field_obj.field_type == 'variable':
                                    # need to get the predicate from the imported cells
                                    pc = ProcessCells(self.source_id,
                                                      self.start_row)
                                    var_recs = pc.get_field_records(des_field_obj.field_num,
                                                                    example_rows)
                                    pg = ProcessGeneral(self.source_id)
                                    val_rec = pg.get_first_distinct_record(var_recs)
                                    if var_recs is not False:
                                        for key, var_rec in var_recs.items():
                                            des_item['predicate']['label'] = var_rec['imp_cell_obj'].record
                                            if len(des_item['predicate']['label']) > 0:
                                                # only add the description item the variable exists
                                                add_des_item = True
                                            else:
                                                add_des_item = False
                                            pid = str(des_field_obj.field_num) + '-' + str(var_rec['rows'][0])
                                            des_item['predicate']['id'] = pid
                                            # now need to get fields that have object values for the predicate
                                            valueof_fields = self.get_variable_valueof(des_field_obj)
                                            for val_field_obj in valueof_fields:
                                                pc = ProcessCells(self.source_id,
                                                                  self.start_row)
                                                val_recs = pc.get_field_records(val_field_obj.field_num,
                                                                                example_rows)
                                                pg = ProcessGeneral(self.source_id)
                                                val_rec = pg.get_first_distinct_record(val_recs)
                                                if val_rec is not False:
                                                    object_val = LastUpdatedOrderedDict()
                                                    object_val['record'] = val_rec['imp_cell_obj'].record
                                                    oid = str(val_field_obj.field_num) + '-' + str(val_rec['rows'][0])
                                                    object_val['id'] = oid
                                                    des_item['objects'].append(object_val)
                                            if add_des_item:
                                                entity['descriptions'].append(des_item)
                            example_entities.append(entity)
        return example_entities

    def process_description_batch(self):
        """ processes fields describing a subject (subjects, media, documents, persons, projects)
            entity field.
            if start_row is 1, then previous imports of this source are cleared
        """
        self.clear_source()  # clear prior import for this source
        self.end_row = self.start_row + self.batch_size
        self.get_description_annotations()
        if self.des_rels is not False:
            for subj_field_num, ent_obj in self.des_rels.items():
                # loop through the fields that describe the subj_field_num
                self.reconcile_descriptive_predicates(ent_obj['des_by_fields'])
            # --------
            # reconciles types and strings by looping through reconciled predicate fields
            self.reconcile_types_strings()
            # --------
            for subj_field_num, ent_obj in self.des_rels.items():
                subj_field_type = ent_obj['field'].field_type
                obs_num_field_num = ent_obj['obs_num_field_num']
                # get records for the subject of the description
                pc = ProcessCells(self.source_id,
                                  self.start_row)
                distinct_records = pc.get_field_records_by_fl_uuid(subj_field_num,
                                                                   False)
                if distinct_records is not False:
                    pg = ProcessGeneral(self.source_id)
                    distinct_records = pg.order_distinct_records(distinct_records)
                    # print(str(distinct_records))
                    for row_key, dist_rec in distinct_records.items():
                        if dist_rec['imp_cell_obj'].cell_ok:
                            subject_uuid = dist_rec['imp_cell_obj'].fl_uuid
                            # the subject record is OK to use for creating
                            # description records
                            # print('subject_uuid: ' + subject_uuid)
                            for des_field_obj in ent_obj['des_by_fields']:
                                des_field_num = des_field_obj.field_num
                                # get the 'value-of' import cell objects for the current
                                # 'descriptive' or 'variable' field_num
                                # 'variable' field_nums may make multiple 'value-of' import_cell_objs
                                object_imp_cell_objs = self.get_assertion_object_values(des_field_num,
                                                                                        dist_rec['rows'])
                                if des_field_obj.field_type == 'variable':
                                    # print('Num var-vals: ' + str(len(object_imp_cell_objs)))
                                    pass
                                for imp_cell_obj in object_imp_cell_objs:
                                    row_num = imp_cell_obj.row_num
                                    # get the observation num and node
                                    obs_num = self.get_records_obs_num(des_field_obj,
                                                                       row_num,
                                                                       obs_num_field_num)
                                    obs_node = '#obs-' + str(obs_num)
                                    predicate = self.look_up_predicate(des_field_num,
                                                                       row_num)
                                    if predicate is not False:
                                        if predicate.sort != 0:
                                            pred_sort = predicate.sort
                                        else:
                                            pred_sort = des_field_num
                                        val_sort = self.get_multivalue_sort_val(subject_uuid,
                                                                                str(predicate.uuid))
                                        cd = CandidateDescription()
                                        cd.source_id = self.source_id
                                        cd.project_uuid = self.project_uuid
                                        cd.subject_uuid = subject_uuid
                                        cd.subject_type = subj_field_type
                                        cd.obs_num = obs_num
                                        cd.obs_node = obs_node
                                        cd.sort = float(pred_sort) + float(val_sort)
                                        cd.predicate_uuid = str(predicate.uuid)
                                        cd.data_type = predicate.data_type
                                        cd.record = str(imp_cell_obj.record)
                                        cd.fl_uuid = imp_cell_obj.fl_uuid
                                        cd.l_uuid = imp_cell_obj.l_uuid
                                        cd.create_description()
                                        if cd.is_valid:
                                            self.count_new_assertions += 1

    def get_multivalue_sort_val(self, subject_uuid, predicate_uuid):
        """ gets a value to add to the sort based on if the
            subject_uuid and predicate_uuid have been added before
        """
        s_val = 0
        key_s_p = subject_uuid + '-' + predicate_uuid
        if key_s_p in self.subject_predicate_counts:
            self.subject_predicate_counts[key_s_p] += 1.0
            s_val = float(self.subject_predicate_counts[key_s_p]) * .01
        else:
            self.subject_predicate_counts[key_s_p] = 1.0
        return s_val

    def get_description_annotations(self):
        """ Gets descriptive annotations, and a 
            or a list of fields that are not in containment relationships
        """
        self.description_annotations = ImportFieldAnnotation.objects\
                                                            .filter(source_id=self.source_id,
                                                                    predicate=ImportFieldAnnotation.PRED_DESCRIBES)\
                                                            .order_by('field_num')
        if len(self.description_annotations) > 0:
            self.count_active_fields = len(self.description_annotations)
            self.des_rels = LastUpdatedOrderedDict()
            for des_anno in self.description_annotations:
                add_descriptor_field = False
                if des_anno.object_field_num not in self.des_rels:
                    # entities being described are in the field identified by object_field_num
                    pg = ProcessGeneral(self.source_id)
                    field_obj = pg.get_field_obj(des_anno.object_field_num)
                    if field_obj is not False:
                        if field_obj.field_type in ImportProfile.DEFAULT_SUBJECT_TYPE_FIELDS:
                            obs_num_field_num = self.get_obs_num_field_num(field_obj)
                            self.des_rels[des_anno.object_field_num] = LastUpdatedOrderedDict()
                            self.des_rels[des_anno.object_field_num]['field'] = field_obj
                            self.des_rels[des_anno.object_field_num]['obs_num_field_num'] = obs_num_field_num
                            self.des_rels[des_anno.object_field_num]['des_by_fields'] = []
                            add_descriptor_field = True
                else:
                    add_descriptor_field = True
                if add_descriptor_field:
                    # the descriptive field is identified by the field_num
                    pg = ProcessGeneral(self.source_id)
                    des_field_obj = pg.get_field_obj(des_anno.field_num)
                    if des_field_obj is not False:
                        self.des_rels[des_anno.object_field_num]['des_by_fields'].append(des_field_obj)

    def get_variable_valueof(self, des_field_obj):
        """ Checks to see if the des_by_field is a variable that has designated values """
        valueof_fields = []
        if des_field_obj.field_type == 'variable':
            if des_field_obj.field_num in self.field_valueofs:
                valueof_fields = self.field_valueofs[des_field_obj.field_num]
            else:
                # get list of field_nums that have the des_by_field as their object
                valueof_fields = self.get_field_valueofs(des_field_obj.field_num)
        return valueof_fields
    
    def get_obs_num_field_num(self, field_obj):
        """ Gets the observation number field for descriptive fields if they exist."""
        obs_num_field_num = False
        obs_fields = ImportFieldAnnotation.objects\
                                          .filter(source_id=self.source_id,
                                                  predicate=ImportFieldAnnotation.PRED_OBS_NUM,
                                                  object_field_num=field_obj.field_num)[:1]
        if len(obs_fields) > 0:
            pg = ProcessGeneral(self.source_id)
            obs_num_obj = pg.get_field_obj(obs_fields[0].field_num)
            if obs_num_obj:
                if obs_num_obj.field_type == 'obs-num':
                    obs_num_field_num = obs_num_obj.field_num
        return obs_num_field_num
    
    def get_records_obs_num(self, des_field_obj, row_num, obs_num_field_num=False):
        """ Gets the observation number for the current row. Either from the
            default of 1, defined for the whole field, or from a look up on a field
            that has obs numbers, or by the default for the
            current field.
        """
        if des_field_obj.obs_num < 1:
            obs_num = 1
        else:
            obs_num = des_field_obj.obs_num
        if obs_num_field_num:
            # we have a field defined that has observation numbers.
            obs_recs = ImportCell.objects.filter(source_id=self.source_id,
                                                 field_num=obs_num_field_num,
                                                 row_num=row_num)[:1]
            if len(obs_recs):
                obs_rec = CandidateDescription().validate_integer(obs_recs[0].record)
                if obs_rec:
                    # a valid integer to use for the observation number.
                    obs_num = obs_rec
        return obs_num
        
    
    def get_field_valueofs(self, variable_field_num):
        """ gets the field_valueofs for a variable field_num """
        valueof_fields = []
        val_annos = ImportFieldAnnotation.objects\
                                         .filter(source_id=self.source_id,
                                                 predicate=ImportFieldAnnotation.PRED_VALUE_OF,
                                                 object_field_num=variable_field_num)\
                                         .order_by('field_num')
        if len(val_annos) > 0:
            for val_anno in val_annos:
                pg = ProcessGeneral(self.source_id)
                val_obj = pg.get_field_obj(val_anno.field_num)
                if val_obj is not False:
                    if val_obj.field_type == 'value':
                        valueof_fields.append(val_obj)
        self.field_valueofs[variable_field_num] = valueof_fields
        return valueof_fields

    def reconcile_descriptive_predicates(self, des_by_fields):
        """ reconciles descriptive predicate fields """
        for des_field_obj in des_by_fields:
            field_num = des_field_obj.field_num
            if field_num not in self.reconciled_predicates:
                recon_predicate = {'predicate': False,
                                   'field_obj': des_field_obj,
                                   'valueof_fields': [],
                                   'rows': False}
                if des_field_obj.field_type == 'description':
                    # straight forward. Predicate label from the Import Field label
                    cdp = CandidateDescriptivePredicate()
                    cdp.reconcile_predicate_var(des_field_obj)
                    self.field_valueofs[field_num] = [field_num] # store information about where to get values
                    recon_predicate['predicate'] = cdp.predicate
                elif des_field_obj.field_type == 'variable':
                    # Predicate label in Records of Import cells
                    pc = ProcessCells(self.source_id,
                                      self.start_row)
                    distinct_records = pc.get_field_records(des_field_obj.field_num,
                                                            False)
                    for row_key, dist_rec in distinct_records.items():
                        pred_rows = {}
                        # checks to see if we need to use even a blank label
                        # beccause of dependencies with value-of fields
                        cdp = CandidateDescriptivePredicate()
                        cdp.label = self.make_var_label_evenif_blank(des_field_obj,
                                                                     dist_rec)
                        cdp.des_import_cell = dist_rec['imp_cell_obj']
                        cdp.data_type = des_field_obj.field_data_type
                        cdp.reconcile_predicate_var(des_field_obj)
                        # print('Check: ' + cdp.label)
                        for imp_cell_row in dist_rec['rows']:
                            pred_rows[imp_cell_row] = cdp.predicate
                        recon_predicate['rows'] = pred_rows
                self.reconciled_predicates[des_field_obj.field_num] = recon_predicate

    def make_var_label_evenif_blank(self, des_field_obj, dist_rec):
        """ Checks to see if a descriptive field of type "variable"
           needs to be created even in cases of Import Cell records,
           that are used for labeling predicate-variables are blank.
           We need a "blank" predicate-variable when 
        """
        # print('Check var-label-even-blank: ' + str(dist_rec['rows']))
        label = dist_rec['imp_cell_obj'].record
        if len(label) < 1:
            valueof_fields = self.get_variable_valueof(des_field_obj)
            for valueof_field in valueof_fields:
                pc = ProcessCells(self.source_id,
                                  self.start_row)
                distinct_records = pc.get_field_records(valueof_field.field_num,
                                                        dist_rec['rows'])
                for row_key, val_dist_rec in distinct_records.items():
                    if len(val_dist_rec['imp_cell_obj'].record) > 0:
                        label = CandidateDescriptivePredicate.DEFAULT_BLANK
                        label += '[Field: ' + str(des_field_obj.field_num) + ']'
                        break
                if len(label) > 0:
                    break
        return label

    def look_up_predicate(self, field_num, row_num):
        """ Looks up the appropriate predicate_uuid based on
            a field_num and a row_num
        """
        predicate = False
        if field_num in self.reconciled_predicates:
            act_field = self.reconciled_predicates[field_num]
            predicate = act_field['predicate']
            if predicate is False:
                if row_num in act_field['rows']:
                    predicate = act_field['rows'][row_num]
                else:
                    # look up the predicate the hard way
                    # we don't have a predicate for this row, so
                    # look it up through reconciliation
                    des_field_obj = act_field['field_obj']
                    pc = ProcessCells(self.source_id,
                                      row_num)
                    distinct_records = pc.get_field_records(field_num,
                                                            [row_num])
                    for row_key, var_dist_rec in distinct_records.items():
                        if len(var_dist_rec['imp_cell_obj'].record) > 0:
                            cdp = CandidateDescriptivePredicate()
                            cdp.label = var_dist_rec['imp_cell_obj'].record
                            cdp.des_import_cell = var_dist_rec['imp_cell_obj']
                            cdp.data_type = des_field_obj.field_data_type
                            cdp.reconcile_predicate_var(des_field_obj)
                            predicate = cdp.predicate
        return predicate

    def reconcile_types_strings(self):
        """ Reconciles type items by looping through reconciled
            predicate fields. Also reconciles strings
        """
        for field_num, recon_predicate in self.reconciled_predicates.items():
            data_type = recon_predicate['field_obj'].field_data_type
            if data_type == 'id' or data_type == 'xsd:string':
                # we have a field with an id data_type, which becomes a types entity
                if recon_predicate['rows'] is not False:
                    valueof_fields = []
                    valueof_fields_objs = self.get_variable_valueof(recon_predicate['field_obj'])
                    for valueof_field in valueof_fields_objs:
                        if isinstance(valueof_field, ImportField):
                            valueof_fields.append(valueof_field.field_num)
                        elif isinstance(valueof_field, int):
                            valueof_fields.append(valueof_field)
                elif recon_predicate['predicate'] is not False:
                    valueof_fields = [field_num]
                else:
                    valueof_fields = []
                for valueof_field in valueof_fields:
                    pc = ProcessCells(self.source_id,
                                      self.start_row)
                    # print('Check value of field: ' + str(valueof_field))
                    distinct_records = pc.get_field_records(valueof_field,
                                                            False)
                    if distinct_records is not False:
                        for row_key, val_dist_rec in distinct_records.items():
                            if len(val_dist_rec['imp_cell_obj'].record) > 0:
                                # found a non-blank type item
                                cs = CandidateString()
                                cs.source_id = self.source_id
                                cs.project_uuid = self.project_uuid
                                cs.reconcile_string_cell(val_dist_rec['imp_cell_obj'])
                                content_uuid = cs.uuid  # string content uuid
                                if data_type == 'id':
                                    if recon_predicate['rows'] is not False:
                                        # need to create types row by row, because the predicate
                                        # comes from import cell records, not the import field
                                        for row_num in val_dist_rec['rows']:
                                            predicate = self.look_up_predicate(field_num,
                                                                               row_num)
                                            if predicate is not False:
                                                ct = CandidateType()
                                                ct.reconcile_type_cell(predicate.uuid,
                                                                       content_uuid,
                                                                       val_dist_rec['imp_cell_obj'],
                                                                       row_num)
                                    elif recon_predicate['predicate'] is not False:
                                        # predicate comes from the import field
                                        # no need to worry about individual rows
                                        predicate = recon_predicate['predicate']
                                        ct = CandidateType()
                                        ct.source_id = self.source_id
                                        ct.project_uuid = self.project_uuid
                                        ct.reconcile_type_cell(predicate.uuid,
                                                               content_uuid,
                                                               val_dist_rec['imp_cell_obj'],
                                                               False)

    def get_assertion_object_values(self, field_num, in_rows):
        """ Gets the import_cell_objects for a given field and row constraint """
        object_imp_cell_objs = []
        if field_num not in self.field_valueofs:
            # for some reason we don't have the value of fields yet
            self.get_field_valueofs(field_num)
        if field_num in self.field_valueofs:
            valueof_fields = self.field_valueofs[field_num]
            for valueof_field in valueof_fields:
                if isinstance(valueof_field, ImportField):
                    # it is not an integer, but an ImportField object
                    valueof_field = valueof_field.field_num
                print('Value of field: ' + str(valueof_field))
                pc = ProcessCells(self.source_id,
                                  self.start_row)
                cells = pc.get_field_row_records(valueof_field,
                                                 in_rows)
                for cell in cells:
                    object_imp_cell_objs.append(cell)
        else:
            print('cannot find field_valueofs for ' + str(field_num))
            pass
        return object_imp_cell_objs


class CandidateDescription():

    def __init__(self):
        self.project_uuid = False
        self.source_id = False
        self.subject_uuid = False
        self.subject_type = False
        self.obs_node = False
        self.obs_num = 0
        self.sort = 0
        self.predicate_uuid = False
        self.object_uuid = False
        self.object_type = False
        self.data_type = False
        self.data_num = None
        self.data_date = None
        self.record = False
        self.fl_uuid = False
        self.l_uuid = False
        self.is_valid = False

    def create_description(self):
        """ Creates a new descriptive assertion if data is valid """
        self.is_valid = self.validate_creation()
        if self.is_valid:
            new_ass = Assertion()
            new_ass.uuid = self.subject_uuid
            new_ass.subject_type = self.subject_type
            new_ass.project_uuid = self.project_uuid
            new_ass.source_id = self.source_id
            new_ass.obs_node = self.obs_node
            new_ass.obs_num = self.obs_num
            new_ass.sort = self.sort
            new_ass.visibility = 1
            new_ass.predicate_uuid = self.predicate_uuid
            new_ass.object_type = self.object_type
            if self.object_uuid is not False:
                new_ass.object_uuid = self.object_uuid
            if self.data_num is not None:
                new_ass.data_num = self.data_num
            if self.data_date is not None:
                new_ass.data_date = self.data_date
            new_ass.save()

    def validate_creation(self):
        """Validates to see if it's OK to create a new descriptive assertion
        """
        is_valid = False
        if self.subject_uuid is not False \
           and self.predicate_uuid is not False \
           and len(self.record) > 0:
            if self.data_type == 'id':
                self.object_type = 'types'
                # use the field-literal combination uuid
                self.object_uuid = self.fl_uuid
            else:
                self.object_type = self.data_type
                if self.data_type == 'xsd:string':
                    # use the literal uuid
                    self.object_uuid = self.l_uuid
                elif self.data_type == 'xsd:boolean':
                    boolean_literal = self.validate_convert_boolean(self.record)
                    if boolean_literal is not None:
                        self.data_num = boolean_literal
                    else:
                        # record of the data_type. Need to make a related
                        # predicate to save this as a string
                        self.make_datatype_wrong_assertion(self.predicate_uuid,
                                                           self.record)
                elif self.data_type == 'xsd:integer':
                    int_literal = self.validate_integer(self.record)
                    if int_literal is not None:
                        self.data_num = int_literal
                    else:
                        # record of the data_type. Need to make a related
                        # predicate to save this as a string
                        self.make_datatype_wrong_assertion(self.predicate_uuid,
                                                           self.record)
                elif self.data_type == 'xsd:double':
                    d_literal = self.validate_numeric(self.record)
                    if d_literal is not None:
                        self.data_num = d_literal
                    else:
                        # record of the data_type. Need to make a related
                        # predicate to save this as a string
                        self.make_datatype_wrong_assertion(self.predicate_uuid,
                                                           self.record)
                elif self.data_type == 'xsd:date':
                    try:
                        date_obj = parse(self.record)
                        self.data_date = date_obj
                    except:
                        # no date could be derived from the record
                        self.make_datatype_wrong_assertion(self.predicate_uuid,
                                                           self.record)
            is_new = self.check_description_new(self.subject_uuid,
                                                self.obs_num,
                                                self.predicate_uuid,
                                                self.object_uuid,
                                                self.data_num,
                                                self.data_date)
            # print('Is new?: ' + str(is_new))
            if is_new:
                is_valid = True
            else:
                is_valid = False
        return is_valid

    def validate_integer(self, record):
        """ validates a string to be an integer
            returns None if not
        """
        output = None
        float_record = self.validate_numeric(record)
        if float_record is not None:
            try:
                output = int(float_record)
            except ValueError:
                output = None
        return output

    def validate_numeric(self, record):
        """ validates a string to be a number
            returns None if not
        """
        try:
            output = float(record)
        except ValueError:
            output = None
        return output

    def check_description_new(self,
                              subject_uuid,
                              obs_num,
                              predicate_uuid,
                              object_uuid,
                              data_num,
                              data_date):
        """Checks to see if it's OK to create a new descriptive assertion
           with an identifier as the object
        """
        is_new = True
        if object_uuid is not False:
            old_ass = Assertion.objects\
                               .filter(uuid=subject_uuid,
                                       obs_num=obs_num,
                                       predicate_uuid=predicate_uuid,
                                       object_uuid=object_uuid)[:1]
            if len(old_ass) > 0:
                is_new = False
        elif data_num is not None:
            old_ass = Assertion.objects\
                               .filter(uuid=subject_uuid,
                                       obs_num=obs_num,
                                       predicate_uuid=predicate_uuid,
                                       data_num=data_num)[:1]
            if len(old_ass) > 0:
                is_new = False
        elif data_date is not None:
            try:
                old_ass = Assertion.objects\
                                   .filter(uuid=subject_uuid,
                                           obs_num=obs_num,
                                           predicate_uuid=predicate_uuid,
                                           data_date=data_date)[:1]
            except:
                old_ass = False
            if old_ass is False:
                is_new = False
            else:
                if len(old_ass) > 0:
                    is_new = False
        else:
            is_new = None
        return is_new

    def validate_convert_boolean(self, record):
        """ Validates boolean values for a record
            returns a boolean 0 or 1 if
        """
        output = None
        record = record.lower()
        booleans = {'n': 0,
                    'no': 0,
                    'none': 0,
                    'absent': 0,
                    'false': 0,
                    'f': 0,
                    '0': 0,
                    '0.0': 0,
                    'y': 1,
                    'yes': 1,
                    'present': 1,
                    'true': 1,
                    't': 1,
                    '1': 1,
                    '1.0': 1}
        if record in booleans:
            output = booleans[record]
        return output

    def make_datatype_wrong_assertion(self, predicate_uuid, content):
        """ Makes an assertion for records that don't fit the
            expected data_type / object_type
        """
        pm = PredicateManagement()
        pm.project_uuid = self.project_uuid
        pm.source_id = self.source_id
        pm.sort = self.sort
        new_note_predicate = pm.get_make_related_note_predicate(predicate_uuid, ' (Note)')
        if new_note_predicate is not False:
            note_pred_uuid = new_note_predicate.uuid
            # save a skos:related assertion linking the old and new predicates
            ptm = PredicateTypeAssertions()
            ptm.skos_relate_old_new_predicates(self.project_uuid,
                                               self.source_id,
                                               predicate_uuid,
                                               note_pred_uuid)
            sm = StringManagement()
            sm.project_uuid = self.project_uuid
            sm.source_id = self.source_id
            oc_string = sm.get_make_string(content)
            object_uuid = oc_string.uuid
            if self.check_description_new(self.subject_uuid,
                                          self.obs_num,
                                          note_pred_uuid,
                                          object_uuid,
                                          None,
                                          None):
                # this asertion does not exist yet, OK to make it
                new_ass = Assertion()
                new_ass.uuid = self.subject_uuid
                new_ass.subject_type = self.subject_type
                new_ass.project_uuid = self.project_uuid
                new_ass.source_id = self.source_id
                new_ass.obs_node = self.obs_node
                new_ass.obs_num = self.obs_num
                new_ass.sort = self.sort + .1
                new_ass.visibility = 1
                new_ass.predicate_uuid = note_pred_uuid
                new_ass.object_uuid = object_uuid
                new_ass.object_type = 'xsd:string'
                new_ass.save()


class CandidateDescriptivePredicate():
    """ Class for reconciling and generating a descriptive predicate """

    DEFAULT_BLANK = '[Blank]'

    def __init__(self):
        self.label = False
        self.project_uuid = False
        self.source_id = False
        self.uuid = False
        self.data_type = False
        self.sort = 0
        self.des_import_cell = False
        self.predicate = False
        self.candidate_uuid = False

    def setup_field(self, des_field_obj):
        """ sets up, with slightly different patterns for
            description field or a variable field
        """
        if des_field_obj.field_type == 'description':
            self.candidate_uuid = des_field_obj.f_uuid
            if self.label is False:
                self.label = des_field_obj.label
        elif des_field_obj.field_type == 'variable':
            # print('Variable Datatype: ' + str(self.data_type))
            if self.des_import_cell is not False:
                self.candidate_uuid = self.des_import_cell.fl_uuid
                if self.label is False:
                    self.label = self.des_import_cell.record
            # print('Variable Label: ' + self.label)
        if self.project_uuid is False:
            self.project_uuid = des_field_obj.project_uuid
        if self.source_id is False:
            self.source_id = des_field_obj.source_id
        if self.data_type is False:
            self.data_type = des_field_obj.field_data_type
        if self.sort < 1:
            self.sort = des_field_obj.field_num

    def reconcile_predicate_var(self, des_field_obj):
        """ reconciles a predicate variable from the Import Field
        """
        output = False
        self.setup_field(des_field_obj)
        if len(self.label) > 0:
            output = True
            pm = PredicateManagement()
            pm.project_uuid = self.project_uuid
            pm.source_id = self.source_id
            pm.sort = self.sort
            predicate = pm.get_make_predicate(self.label,
                                              'variable',
                                              self.data_type)
            self.uuid = predicate.uuid
            self.predicate = predicate
            self.sort = predicate.sort
            if predicate.uuid != self.candidate_uuid:
                if self.des_import_cell is False:
                    # update the reconcilted UUID with for the import field object
                    des_field_obj.f_uuid = self.uuid
                    des_field_obj.save()
                else:
                    # update the reconcilted UUID for import cells with same rec_hash
                    up_cells = ImportCell.objects\
                                         .filter(source_id=self.source_id,
                                                 field_num=self.des_import_cell.field_num,
                                                 rec_hash=self.des_import_cell.rec_hash)
                    for up_cell in up_cells:
                        # save each cell with the correct UUID
                        up_cell.fl_uuid = self.uuid
                        up_cell.uuids_save()
        return output


class CandidateString():
    """ Class for reconciling and generating strings """

    def __init__(self):
        self.content = False
        self.project_uuid = False
        self.source_id = False
        self.uuid = False
        self.oc_string = False

    def reconcile_string_cell(self, imp_cell):
        """ reconciles a predicate variable from the Import Field
        """
        output = False
        if len(imp_cell.record) > 0:
            output = True
            sm = StringManagement()
            sm.project_uuid = imp_cell.project_uuid
            sm.source_id = imp_cell.source_id
            self.oc_string = sm.get_make_string(imp_cell.record)
            self.uuid = self.oc_string.uuid
            self.content = self.oc_string.content
            # self.source_id = self.oc_string.source_id
            if self.uuid != imp_cell.l_uuid:
                # update the reconcilted UUID for import cells with same rec_hash
                up_cells = ImportCell.objects\
                                     .filter(source_id=self.source_id,
                                             field_num=imp_cell.field_num,
                                             rec_hash=imp_cell.rec_hash)
                for up_cell in up_cells:
                    # save each cell with the correct UUID
                    up_cell.l_uuid = str(self.uuid)
                    up_cell.uuids_save()
        return output


class CandidateType():
    """ Class for reconciling and generating strings """

    def __init__(self):
        self.project_uuid = False
        self.source_id = False
        self.oc_type = False
        self.uuid = False

    def reconcile_type_cell(self,
                            predicate_uuid,
                            content_uuid,
                            imp_cell,
                            row_num=False):
        """ reconciles a distinct type,
            with consideration for how the 
        """
        output = False
        if len(imp_cell.record) > 0 \
           and predicate_uuid is not False \
           and content_uuid is not False:
            output = True
            tm = TypeManagement()
            tm.project_uuid = imp_cell.project_uuid
            tm.source_id = imp_cell.source_id
            self.oc_type = tm.get_make_type_pred_uuid_content_uuid(predicate_uuid,
                                                                   content_uuid)
            # self.source_id = self.oc_type.source_id
            if self.oc_type.uuid != imp_cell.fl_uuid \
               or self.oc_type.content_uuid != imp_cell.l_uuid:    # update the reconcilted UUID for import cells with same rec_hash
                if row_num is False:
                    up_cells = ImportCell.objects\
                                         .filter(source_id=self.source_id,
                                                 field_num=imp_cell.field_num,
                                                 rec_hash=imp_cell.rec_hash)
                else:
                    up_cells = ImportCell.objects\
                                         .filter(source_id=self.source_id,
                                                 field_num=imp_cell.field_num,
                                                 row_num=row_num)
                for up_cell in up_cells:
                    # save each cell with the correct UUID
                    up_cell.fl_uuid = self.oc_type.uuid
                    up_cell.l_uuid = self.oc_type.content_uuid
                    up_cell.uuids_save()
        return output
