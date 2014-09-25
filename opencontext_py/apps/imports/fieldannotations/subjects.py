import uuid as GenUUID
from django.conf import settings
from django.db import models
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell


# Processes to generate subjects items for an import
class ProcessSubjects():

    def __init__(self, source_id):
        self.source_id = False
        self.subjects_fields = False
        self.contain_ordered_subjects = {}
        self.non_contain_subjects = []
        self.root_subject_field = False  # field_num for the root subject field
        self.field_parent_entites = {}  # Parent entities named for a given field
        self.start_row = 1
        self.batch_size = 250
        self.end_row = self.batch_size

    def process_contained_batch(self):
        self.end_row = self.start_row + self.batch_size
        self.get_subject_fields()
        if root_subject_field is not False:
            pass

    def get_distinct_field_subjects(self, field_num, in_rows=False):
        if in_rows is False:
            field_cells = ImportCell.objects\
                                    .order_by()\
                                    .filter(source_id=self.source_id,
                                            field_num=field_num,
                                            row_num_gte=self.start_row,
                                            row_num_lt=self.end_row)\
                                    .distinct('rec_hash')
        else:
            field_cells = ImportCell.objects\
                                    .order_by()\
                                    .filter(source_id=self.source_id,
                                            field_num=field_num,
                                            row_num__in=in_rows)\
                                    .distinct('rec_hash')
        if len(field_cells) > 0:
            pass

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
                                                           predicate_rel=Assertion.PREDICATES_CONTAINS)[:1]
                child_anno = ImportFieldAnnotation.objects\
                                                  .filter(source_id=self.source_id,
                                                          field_num=sub_field.field_num,
                                                          predicate_rel=Assertion.PREDICATES_CONTAINS)[:1]
                if len(child_anno) > 0:
                    self.contain_ordered_subjects[sub_field.field_num] = child_anno[0].object_field_num
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
        self.field_parent_entites[field_num] = False
        parent_anno = ImportFieldAnnotation.objects\
                                           .filter(source_id=self.source_id,
                                                   field_num=field_num,
                                                   predicate_rel=ImportFieldAnnotation.PRED_CONTAINED_IN)[:1]
        if len(parent_anno) > 0:
            ent = Entity()
            found = ent.dereference(parent_anno[0].object_uuid)
            if found:
                self.field_parent_entites[field_num] = ent

    def get_subject_fields(self):
        sub_fields = ImportField.objects\
                                .filter(source_id=self.source_id,
                                        field_type='subjects')


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
        self.allow_blank = False  # Allow item to be bank
        self.allow_new = False  # only allow new if item is imported in a hierachy, otherwise match with manifest
        self.import_rows = False  # if a list, then changes to uuids are saved for all rows in this list

    def reconcile_item(self, imp_cell_obj):
        """ Checks to see if the item exists in the subjects table """
        self.imp_cell_obj = imp_cell_obj
        if len(imp_cell_obj.record) > 0:
            self.label = self.label_prefix + imp_cell_obj.record
        else:
            if self.allow_blank:
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
                pass

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
