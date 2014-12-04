import uuid as GenUUID
from django.conf import settings
from django.db import models
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.predicates.management import PredicateManagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fields.templating import ImportProfile
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.process import ProcessCells
from opencontext_py.apps.imports.fieldannotations.subjects import CandidateSubject
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral
from opencontext_py.apps.imports.sources.unimport import UnImport


# Processes to generate non-descriptive predicates. These are
# predicates that link subjects, media, persons, documents, and projects entities
# together.
class ProcessLinks():

    # This list has predicates not processed as 'linking' relations
    DEFAULT_EXCLUSION_PREDS = [Assertion.PREDICATES_CONTAINS,
                               ImportFieldAnnotation.PRED_CONTAINED_IN,
                               ImportFieldAnnotation.PRED_DESCRIBES]

    def __init__(self, source_id):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        self.start_row = 1
        self.batch_size = 250
        self.end_row = self.batch_size
        self.example_size = 5
        self.link_rels = False
        self.count_active_fields = 0

    def clear_source(self):
        """ Clears a prior import if the start_row is 1.
            This makes sure new entities and assertions are made for
            this source_id, and we don't duplicate things
        """
        if self.start_row <= 1:
            # will clear an import of descriptions
            unimport = UnImport(self.source_id,
                                self.project_uuid)
            unimport.delete_links_assertions()
            unimport.delete_predicate_links(False)
        return True

    def get_link_examples(self):
        """ Gets example entities with linking relations
        """
        example_entities = []
        self.get_link_annotations()
        if self.link_rels is not False:
            for subj_field_num, rels in self.link_rels.items():
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
                            entity_label = rels['sub_field_obj'].value_prefix + entity_label
                            entity['label'] = entity_label
                            entity['id'] = str(subj_field_num) + '-' + str(row_key)
                            entity['links'] = []
                            example_rows = []
                            example_rows.append(dist_rec['rows'][0])
                            in_rows = [dist_rec['rows'][0]]
                            for pred_obj in rels['pred_objs']:
                                act_preds = []
                                if pred_obj['predicate_uuid'] is not False:
                                    pred_item = LastUpdatedOrderedDict()
                                    pred_item['id'] = pred_obj['predicate_uuid']
                                    ent = Entity()
                                    found = ent.dereference(pred_obj['predicate_uuid'])
                                    if found:
                                        pred_item['label'] = ent.label
                                    else:
                                        pred_item['label'] = '[Missing predicate!]'
                                    act_preds.append(pred_item)
                                elif pred_obj['pred_field_obj'] is not False:
                                    # linking predicate is in a field
                                    pc = ProcessCells(self.source_id,
                                                      self.start_row)
                                    pred_recs = pc.get_field_records(pred_obj['pred_field_obj'].field_num,
                                                                     in_rows)
                                    for pred_rec in pred_recs:
                                        pred_item = LastUpdatedOrderedDict()
                                        pred_item['id'] = str(pred_obj['pred_field_obj'].field_num)
                                        pred_item['id'] += '-' + str(pred_rec['rows'][0])
                                        pred_item['label'] = pred_rec['imp_cell_obj'].record
                                        if len(pred_item['label']) < 1:
                                            pred_item['label'] = '[BLANK]'
                                        if len(act_precs) < self.example_size:
                                            act_preds.append(pred_item)
                                for pred_item in act_preds:
                                    link_item = LastUpdatedOrderedDict()
                                    link_item['predicate'] = pred_item
                                    # values are in a list, to keep consistent with descriptions
                                    link_item['object'] = False
                                    obj_field_obj = pred_obj['obj_field_obj']
                                    # now get a value for the object from the imported cells
                                    pc = ProcessCells(self.source_id,
                                                      self.start_row)
                                    obj_recs = pc.get_field_records(obj_field_obj.field_num,
                                                                    in_rows)
                                    pg = ProcessGeneral(self.source_id)
                                    obj_rec = pg.get_first_distinct_record(obj_recs)
                                    if obj_rec is not False:
                                        object_val = LastUpdatedOrderedDict()
                                        object_label = obj_field_obj.value_prefix
                                        if len(obj_rec['imp_cell_obj'].record) > 1:
                                            object_label += obj_rec['imp_cell_obj'].record
                                        else:
                                            object_label += '[BLANK]'
                                        object_val['label'] = object_label
                                        object_val['id'] = str(obj_rec['imp_cell_obj'].field_num)
                                        object_val['id'] += '-' + str(obj_rec['rows'][0])
                                        link_item['object'] = object_val
                                        if len(entity['links']) < self.example_size:
                                            entity['links'].append(link_item)
                            example_entities.append(entity)
        return example_entities

    def process_link_batch(self):
        """ processes fields describing linking relations
            between subjects, media, documents, persons, projects entities.
            If start_row is 1, then previous imports of this source are cleared
        """
        self.clear_source()  # clear prior import for this source
        self.end_row = self.start_row + self.batch_size
        self.get_link_annotations()
        if self.link_rels is not False:
            for subj_field_num, rels in self.link_rels.items():
                # get some example records
                sub_field_obj = rels['sub_field_obj']
                pc = ProcessCells(self.source_id,
                                  self.start_row)
                distinct_records = pc.get_field_records(subj_field_num,
                                                        False)
                if distinct_records is not False:
                    # sort the list in row_order from the import table
                    pg = ProcessGeneral(self.source_id)
                    distinct_records = pg.order_distinct_records(distinct_records)
                    for row_key, dist_rec in distinct_records.items():
                        subject_uuid = dist_rec['imp_cell_obj'].fl_uuid
                        subject_type = sub_field_obj.field_type
                        subject_ok = dist_rec['imp_cell_obj'].cell_ok
                        sort = 0
                        in_rows = dist_rec['rows']
                        for pred_obj in rels['pred_objs']:
                            act_preds = {}
                            obs_num = 1  # default observation number
                            if pred_obj['predicate_uuid'] is not False:
                                act_preds[pred_obj['predicate_uuid']] = in_rows
                            elif pred_obj['pred_field_obj'] is not False:
                                # linking predicate is in a field
                                if pred_obj['pred_field_obj'].obs_num > 0:
                                    obs_num = pred_obj['pred_field_obj'].obs_num
                                sort = pred_obj['pred_field_obj'].field_num
                                pc = ProcessCells(self.source_id,
                                                  self.start_row)
                                pred_recs = pc.get_field_records(pred_obj['pred_field_obj'].field_num,
                                                                 in_rows)
                                for pred_rec in pred_recs:
                                    clp = CandidateLinkPredicate()
                                    clp.source_id = self.source_id
                                    clp.project_uuid = self.project_uuid
                                    clp.make_reconcile_link_pred(pred_rec['imp_cell_obj'].record)
                                    if clp.uuid is not False:
                                        act_preds[clp.uuid] = pred_rec['rows']
                            obs_node = '#obs-' + str(obs_num)
                            for predicate_uuid, act_in_rows in act_preds.items():
                                obj_field_obj = pred_obj['obj_field_obj']
                                # now get a value for the object from the imported cells
                                pc = ProcessCells(self.source_id,
                                                  self.start_row)
                                obj_recs = pc.get_field_records(obj_field_obj.field_num,
                                                                act_in_rows)
                                if sort < 1:
                                    sort = obj_field_obj.field_num
                                for obj_rec in obj_recs:
                                    object_uuid = obj_rec['imp_cell_obj'].fl_uuid
                                    object_type = obj_rec.field_type
                                    object_ok = obj_rec['imp_cell_obj'].cell_ok
                                    cla = CandidateLinkAssersion()
                                    cla.project_uuid = self.project_uuid
                                    cla.source_id = self.source_id
                                    cla.subject_uuid = subject_uuid
                                    cla.subject_type = subject_type
                                    cla.obs_node = obs_node
                                    cla.obs_num = obs_num
                                    cla.sort = sort
                                    cla.predicate_uuid = predicate_uuid
                                    cla.object_uuid = object_uuid
                                    cla.object_type = object_type
                                    if subject_ok and object_ok and predicte_uuid is not False:
                                        cla.create_link()

    def get_link_annotations(self):
        """ Gets descriptive annotations, and a 
            or a list of fields that are not in containment relationships
        """
        link_annotations = ImportFieldAnnotation.objects\
                                                .filter(source_id=self.source_id)\
                                                .exclude(predicate__in=self.DEFAULT_EXCLUSION_PREDS)\
                                                .order_by('field_num', 'object_field_num')
        if len(link_annotations) > 0:
            self.count_active_fields = len(link_annotations)
            self.link_rels = LastUpdatedOrderedDict()
            for link_anno in link_annotations:
                pg = ProcessGeneral(self.source_id)
                subj_field = pg.get_field_obj(link_anno.field_num)
                obj_field = pg.get_field_obj(link_anno.object_field_num)
                if subj_field is not False and obj_field is not False:
                    # print('Found subject, object')
                    if subj_field.field_type in ImportProfile.DEFAULT_SUBJECT_TYPE_FIELDS \
                       and obj_field.field_type in ImportProfile.DEFAULT_SUBJECT_TYPE_FIELDS:
                        # print('Valid subject, object')
                        if link_anno.field_num not in self.link_rels:
                            rels = {'sub_field_obj': subj_field,
                                    'pred_objs': []}
                        else:
                            rels = self.link_rels[link_anno.field_num]
                        pred_obj = {'predicate_uuid': False,
                                    'pred_field_obj': False,
                                    'obj_field_obj': obj_field}
                        if link_anno.predicate_field_num > 0:
                            pred_obj['pred_field_obj'] = pg.get_field_obj(link_anno.predicate_field_num)
                        else:
                            pred_obj['predicate_uuid'] = link_anno.predicate
                        rels['pred_objs'].append(pred_obj)
                        self.link_rels[link_anno.field_num] = rels


class CandidateLinkAssersion():

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

    def create_link(self):
        """ Creates a new link assertion if data is valid """
        is_valid = self.validate_creation()
        if is_valid:
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
            new_ass.object_uuid = self.object_uuid
            new_ass.save()

    def validate_creation(self):
        """Validates to see if it's OK to create a new descriptive assertion
        """
        is_valid = False
        if self.subject_uuid is not False \
           and self.predicate_uuid is not False \
           and self.object_uuid is not False > 0:
            is_new = self.check_link_new(self.subject_uuid,
                                         self.obs_num,
                                         self.predicate_uuid,
                                         self.object_uuid)
            print('Is new?: ' + str(is_new))
            if is_new:
                is_valid = True
            else:
                is_valid = False
        return is_valid

    def check_link_new(self,
                       subject_uuid,
                       obs_num,
                       predicate_uuid,
                       object_uuid):
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
            old_ass = Assertion.objects\
                               .filter(uuid=subject_uuid,
                                       obs_num=obs_num,
                                       predicate_uuid=predicate_uuid,
                                       data_date=data_date)[:1]
            if len(old_ass) > 0:
                is_new = False
        else:
            is_new = None
        return is_new


class CandidateLinkPredicate():
    """ Class for reconciling and generating a descriptive predicate """

    DEFAULT_BLANK = '[Blank]'

    def __init__(self):
        self.label = False
        self.project_uuid = False
        self.source_id = False
        self.uuid = False
        self.class_uri = 'link'  # defualt for linking predicates
        self.data_type = 'id'  # default for linking enitities
        self.sort = 0
        self.des_import_cell = False
        self.predicate = False

    def make_reconcile_link_pred(self, label):
        """ Makes a linking predicate from a given predicate label """
        self.label = label
        pm = PredicateManagement()
        pm.project_uuid = self.project_uuid
        pm.source_id = self.source_id
        pm.data_type = self.data_type
        pm.sort = self.sort
        pm.get_make_predicate(label,
                              self.class_uri,
                              self.data_type)
        self.uuid = pm.predicate.uuid
