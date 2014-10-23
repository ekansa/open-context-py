import uuid as GenUUID
from django.conf import settings
from django.db import models
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.process import ProcessCells
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral


# Processes to generate subjects items for an import
class ProcessSubjects():

    def __init__(self, source_id):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        self.subjects_fields = False
        self.contain_ordered_subjects = {}
        self.non_contain_subjects = []
        self.root_subject_field = False  # field_num for the root subject field
        self.field_parent_entities = {}  # Parent entities named for a given field
        self.start_row = 1
        self.batch_size = 250
        self.end_row = self.batch_size
        self.example_size = 5

    def get_contained_examples(self):
        example_containment = []
        self.get_subject_fields()
        if self.root_subject_field is not False:
            example_containment = self.get_contained_field_exp(self.root_subject_field,
                                                               False,
                                                               True)
        return example_containment

    def get_contained_field_exp(self,
                                field_num,
                                in_rows=False,
                                check_parent_entity=False):
        """ get examples of entities in containment fields, does recursive lookups
            to get a whole tree, limited to a maximum of a few examples
        """
        contain_nodes = False
        add_field_examples = True
        if field_num == self.root_subject_field and check_parent_entity:
            # Check to see if the root is contained in a named entity
            if self.field_parent_entities[field_num] is not False:
                # Root is in a named entity, so add it.
                contain_nodes = []
                add_field_examples = False
                parent_uuid = self.field_parent_entities[field_num].uuid
                parent_context = self.field_parent_entities[field_num].context
                contain_node = LastUpdatedOrderedDict()
                contain_node['label'] = parent_context
                contain_node['type'] = 'subjects'
                contain_node['field_label'] = 'Parent of field: ' + self.subjects_fields[field_num].label
                contain_node['field_num'] = 0
                contain_node['id'] = parent_uuid
                # now look for children of the root entity.
                contain_node['children'] = self.get_contained_field_exp(field_num)
                contain_nodes.append(contain_node)
        if add_field_examples:
            pc = ProcessCells(self.source_id,
                              self.start_row)
            distinct_records = pc.get_field_records(field_num,
                                                    in_rows)
            if distinct_records is not False:
                contain_nodes = []
                unique_labels = []
                field_obj = self.subjects_fields[field_num]
                for rec_hash, dist_rec in distinct_records.items():
                    if len(contain_nodes) <= self.example_size:
                        # only add examples if we're less or equal to the the total example size
                        contain_node = LastUpdatedOrderedDict()
                        entity_label = dist_rec['imp_cell_obj'].record
                        if len(entity_label) < 1:
                            entity_label = '[BLANK]'
                        entity_label = field_obj.value_prefix + entity_label
                        contain_node['label'] = entity_label
                        contain_node['type'] = 'import-record'
                        contain_node['field_label'] = field_obj.label
                        contain_node['field_num'] = field_num
                        contain_node['id'] = dist_rec['rows'][0]
                        contain_node['children'] = False
                        if field_num in self.contain_ordered_subjects:
                            if self.contain_ordered_subjects[field_num] is not False:
                                unique_child_labels = []
                                for child_field in self.contain_ordered_subjects[field_num]:
                                    act_children = self.get_contained_field_exp(child_field,
                                                                                dist_rec['rows'])
                                    if act_children is not False:
                                        if contain_node['children'] is False:
                                            contain_node['children'] = []
                                        for act_child in act_children:
                                            if act_child['label'] not in unique_child_labels:
                                                # so we only list the same entity once
                                                contain_node['children'].append(act_child)
                                                unique_child_labels.append(act_child['label'])
                        if entity_label not in unique_labels:
                            # so we only list the same entity once
                            contain_nodes.append(contain_node)
                            unique_labels.append(entity_label)
        return contain_nodes

    def process_contained_batch(self):
        """ processes containment fields for subject
            entities starting with a given row number.
            This iterates over all containment fields, starting
            with the root subjhect field
        """
        self.end_row = self.start_row + self.batch_size
        self.get_subject_fields()
        if root_subject_field is not False:
            self.process_field_hierarchy(root_subject_field)

    def process_field_hierarchy(self,
                                field_num,
                                parent_uuid=False,
                                parent_context='',
                                in_rows=False):
        """ processes subject entitites from a given field. takes arguments
            about:
            1. field_num (the field to find candidate subject entities)
            2. parent_uuid (the uuid for the parent / containing subject entity)
            3. parent_context (the context path of the parent entitiy)
            4. in_rows (a list of row numbers to search within. this insures
               that entities are reconciled within contexts so that a
               Bone 1 in a Locus 1 is noted as different from a Bone 1 in
               Locus 2)

            Note: this function is recursive and calls itself if the
            the field_num has child fields.
        """
        pc = ProcessCells(self.source_id,
                          self.start_row)
        distinct_records = pc.get_field_records(field_num,
                                                in_rows)
        if distinct_records is not False:
            field_obj = self.subjects_fields[field_num]
            if field_num == self.root_subject_field and parent_uuid is False:
                if field_num in self.field_parent_entites:
                    if self.field_parent_entities[field_num] is not False:
                        parent_uuid = self.field_parent_entities[field_num].uuid
                        parent_context = self.field_parent_entities[field_num].context
            for rec_hash, dist_rec in distinct_records.items():
                cs = CandidateSubject()
                cs.project_uuid = self.project_uuid
                cs.source_id = self.source_id
                cs.obs_node = 'obs-' + str(field_obj.obs_num)
                cs.obs_num = field_obj.obs_num
                cs.parent_context = parent_context
                cs.patent_uuid = parent_uuid
                cs.label_prefix = field_obj.value_prefix
                cs.allow_new = True  # allow new because it is a hierarchic field
                cs.class_uri = field_obj.class_uri
                cs.import_rows = dist_rec['rows']
                cs.reconcile_item(dist_rec['imp_cell_obj'])
                if cs.uuid is not False:
                    if field_num in self.contain_ordered_subjects:
                        if self.contain_ordered_subjects[field_num] is not False:
                            # subject entity successfully reconciled or created
                            # now process next level down in hierarchy, if it exists
                            self.process_field_hierarchy(self.contain_ordered_subjects[field_num],
                                                         cs.uuid,
                                                         cs.context,
                                                         dist_rec['rows'])

    def get_subject_fields(self):
        """ Gets subject fields, puts them into a containment hierarchy
            or a list of fields that are not in containment relationships
        """
        sub_fields = ImportField.objects\
                                .filter(source_id=self.source_id,
                                        field_type='subjects')
        if len(sub_fields) > 0:
            self.subjects_fields = {}
            # Assertion.PREDICATES_CONTAINS
            for sub_field in sub_fields:
                self.subjects_fields[sub_field.field_num] = sub_field
                parent_anno = ImportFieldAnnotation.objects\
                                                   .filter(source_id=self.source_id,
                                                           object_field_num=sub_field.field_num,
                                                           predicate=Assertion.PREDICATES_CONTAINS)[:1]
                child_anno = ImportFieldAnnotation.objects\
                                                  .filter(source_id=self.source_id,
                                                          field_num=sub_field.field_num,
                                                          predicate=Assertion.PREDICATES_CONTAINS)
                if len(child_anno) > 0:
                    self.contain_ordered_subjects[sub_field.field_num] = []
                    for child in child_anno:
                        self.contain_ordered_subjects[sub_field.field_num].append(child.object_field_num)
                    if len(parent_anno) < 1:
                        # field has children, but no parent it's at the root level
                        self.root_subject_field = sub_field.field_num
                        # check to see if the root field has a parent entity
                        self.get_field_parent_entity(sub_field.field_num)
                else:
                    if len(parent_anno) > 0:
                        # field has no child fields.
                        self.contain_ordered_subjects[sub_field.field_num] = False
                    else:
                        # field has no containment relations
                        self.non_contain_subjects.append(sub_field.field_num)
                        # check to see if the uncontained field has a parent entity
                        self.get_field_parent_entity(sub_field.field_num)

    def get_field_parent_entity(self, field_num):
        """ Get's a parent entity named for a given field """
        self.field_parent_entities[field_num] = False
        parent_anno = ImportFieldAnnotation.objects\
                                           .filter(source_id=self.source_id,
                                                   field_num=field_num,
                                                   predicate=ImportFieldAnnotation.PRED_CONTAINED_IN)[:1]
        if len(parent_anno) > 0:
            ent = Entity()
            ent.get_context = True
            found = ent.dereference(parent_anno[0].object_uuid)
            if found:
                self.field_parent_entities[field_num] = ent

    def get_field_subjects(self):
        distinct_records = False
        if self.in_rows is False:
            field_cells = ImportCell.objects\
                                    .filter(source_id=self.source_id,
                                            field_num=self.field_num,
                                            row_num_gte=self.start_row,
                                            row_num_lt=self.end_row)
        else:
            field_cells = ImportCell.objects\
                                    .order_by()\
                                    .filter(source_id=self.source_id,
                                            field_num=self.field_num,
                                            row_num__in=self.in_rows)
        if len(field_cells) > 0:
            distinct_records = {}
            for cell in field_cells:
                # iterate through cells to get list of row_nums for each distinct value
                if cell.rec_hash not in distinct_records:
                    distinct_records[cell.rec_hash]['rows'] = []
                    distinct_records[cell.rec_hash]['imp_cell_obj'] = cell
                distinct_records[cell.rec_hash]['rows'].append(cell.row_num)
        return distinct_records


class CandidateSubject():

    DEFAULT_BLANK = '[Blank]'

    def __init__(self):
        self.project_uuid = False
        self.source_id = False
        self.parent_uuid = False
        self.obs_node = False
        self.obs_num = 0
        self.parent_context = ''
        self.label_prefix = ''
        self.context = ''
        self.label = False
        self.class_uri = ''
        self.uuid = False  # final, uuid for the item
        self.imp_cell_obj = False  # ImportCell object
        self.evenif_blank = False  # Mint a new item even if the record is blank
        self.allow_new = False  # only allow new if item is imported in a hierachy, otherwise match with manifest
        self.import_rows = False  # if a list, then changes to uuids are saved for all rows in this list

    def reconcile_item(self, imp_cell_obj):
        """ Checks to see if the item exists in the subjects table """
        self.imp_cell_obj = imp_cell_obj
        if len(imp_cell_obj.record) > 0:
            self.label = self.label_prefix + imp_cell_obj.record
        else:
            pg = ProcessGeneral(self.source_id)
            self.evenif_blank = pg.check_blank_required(imp_cell_obj.field_num,
                                                        imp_cell_obj.row_num)
            if self.evenif_blank:
                self.label = self.label_prefix + self.DEFAULT_BLANK
        if self.allow_new and self.label is not False:
            # Only create a new item if it is allowed and if the label is not false
            if len(self.parent_context) > 0:
                self.context = self.parent_context + Subject.HIEARCHY_DELIM + self.label
            else:
                self.context = self.label
            match_found = self.match_against_subjects(self.context)
            if match_found is False:
                # create new subject, manifest objects. Need new UUID, since we can't assume
                # the fl_uuid for the ImportCell reflects unique entities in a field, since
                # uniqueness depends on context (values in other cells)
                self.uuid = GenUUID.uuid4()
                self.create_subject_item()
        else:
            if self.label is not False:
                # only allow matches on non-blank items when not creating a record
                match_found = self.match_against_mainfest(self.label,
                                                          self.class_uri)
        self.update_import_cell_uuid()
        self.add_contain_assertion()

    def add_contain_assertion(self):
        """ Adds a containment assertion for the new subject item """
        if self.allow_new\
           and self.parent_uuid is not False\
           and self.uuid is not False:
            new_ass = Assertion()
            new_ass.uuid = self.parent_uuid
            new_ass.subject_type = 'subjects'
            new_ass.project_uuid = self.project_uuid
            new_ass.source_id = self.source_id
            new_ass.obs_node = self.obs_node
            new_ass.obs_num = self.obs_num
            new_ass.sort = 1
            new_ass.visibility = 1
            new_ass.predicate_uuid = Assertion.PREDICATES_CONTAINS
            new_ass.object_uuid = self.uuid
            new_ass.object_type = 'subjects'
            new_ass.save()

    def create_subject_item(self):
        """ Create and save a new subject object"""
        new_sub = Subject()
        new_sub.uuid = self.uuid  # use the previously assigned temporary UUID
        new_sub.project_uuid = self.project_uuid
        new_sub.source_id = self.source_id
        new_sub.context = self.context
        new_sub.save()
        new_man = Manifest()
        new_man.uuid = self.uuid
        new_man.project_uuid = self.project_uuid
        new_man.source_id = self.source_id
        new_man.repo = ''
        new_man.class_uri = self.class_uri
        new_man.label = self.label
        new_man.des_predicate_uuid = ''
        new_man.views = 0
        new_man.save()

    def update_import_cell_uuid(self):
        """ Saves the uuid to the import cell record """
        if self.uuid is not False:
            if self.import_rows is False:
                # only update the current import cell object
                self.imp_cell_obj.fl_uuid = self.uuid
                self.imp_cell_obj.save()
            else:
                # update all the import cells in the list of rows
                # to have the relevant uuid
                self.imp_cell_obj.fl_uuid = self.uuid
                self.imp_cell_obj.save()
                up_cells = ImportCell.objects\
                                     .filter(source_id=self.source_id,
                                             field_num=self.imp_cell_obj.field_num,
                                             row_num__in=self.import_rows)
                for up_cell in up_cells:
                    # save each cell with the correct UUID
                    up_cell.fl_uuid = self.uuid
                    up_cell.save()

    def match_against_subjects(self, context):
        """ Checks to see if the item exists in the subjects table """
        match_found = False
        hash_id = Subject.make_hash_id(self.project_uuid, context)
        try:
            subject_match = Subject.objects\
                                   .get(hash_id=hash_id)
        except Subject.DoesNotExist:
            subject_match = False
        if subject_match is not False:
            match_found = True
            self.uuid = subject_match.uuid
        return match_found

    def match_against_manifest(self, label, class_uri):
        """ Checks to see if the item exists in the manifest """
        match_found = False
        manifest_match = Manifest.objects\
                                 .filter(project_uuid=self.project_uuid,
                                         label=label,
                                         class_uri=class_uri)[:1]
        if len(manifest_match) > 0:
            match_found = True
            self.uuid = manifest_match[0].uuid
        else:
            # can't match the item in the manifest
            if self.allow_new is False:
                # mark the cell to be ignored. It can't be associated with any entities
                self.imp_cell_obj.cell_ok = False
                self.imp_cell_obj.save()
        return match_found
