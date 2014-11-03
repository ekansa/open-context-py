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
from opencontext_py.apps.imports.fields.templating import ImportProfile
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.process import ProcessCells
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral


# Processes to generate subjects items for an import
class ProcessDescriptions():

    def __init__(self, source_id):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        self.description_annotations = False
        self.des_rels = False
        self.start_row = 1
        self.batch_size = 250
        self.end_row = self.batch_size
        self.example_size = 5

    def clear_source(self):
        """ Clears a prior import if the start_row is 1.
            This makes sure new entities and assertions are made for
            this source_id, and we don't duplicate things
        """
        if self.start_row <= 1:
            # will clear an import of descriptions
            pass
        return True

    def get_description_examples(self):
        """ Gets example entities described by other fields
        """
        self.get_description_annotations()

    def get_description_annotations(self):
        """ Gets descriptive annotations, and a 
            or a list of fields that are not in containment relationships
        """
        self.description_annotations = ImportFieldAnnotation.objects\
                                                            .filter(source_id=self.source_id,
                                                                    predicate=ImportFieldAnnotation.PRED_DESCRIBES)\
                                                            .order_by(field_num)
        if len(self.description_annotations) > 0:
            self.des_rels = LastUpdatedOrderedDict()
            for des_anno in self.des_rels:
                add_descriptor_field = False
                if des_anno.object_field_num not in self.des_rels:
                    # entities being described are in the field identified by object_field_num
                    field_obj = self.get_field_obj(des_anno.object_field_num)
                    if field_obj is not False:
                        if field_obj.field_type in ImportProfile.DEFAULT_SUBJECT_TYPE_FIELDS:
                            self.des_rels[des_anno.object_field_num] = LastUpdatedOrderedDict()
                            self.des_rels[des_anno.object_field_num]['field'] = field_obj
                            self.des_rels[des_anno.object_field_num]['des_by_fields'] = []
                            add_descriptor_field = True
                else:
                    add_descriptor_field = True
                if add_descriptor_field:
                    # the descriptive field is identified by the field_num
                    des_field_obj = self.get_field_obj(des_anno.field_num)
                    if des_field_obj is not False:
                        self.self.des_rels[des_anno.object_field_num]['des_by_fields'].append(des_field_obj)

    def get_variable_valueof(self, des_field_obj):
        """ Checks to see if the des_by_field is a variable that has designated values """
        valueof_fields = False
        if des_field_obj.field_type == 'variable':
            # get list of field_nums that have the des_by_field as their object
            val_annos = ImportFieldAnnotation.objects\
                                             .filter(source_id=self.source_id,
                                                     predicate=ImportFieldAnnotation.PRED_VALUE_OF,
                                                     object_field_num=des_field_obj.field_num)\
                                             .order_by(field_num)
            if len(val_annos) > 1:
                valueof_fields = []
                for val_anno in val_annos:
                    val_obj = self.get_field_obj(val_anno.field_num)
                    if val_obj is not False:
                        if val_obj.field_type == 'value':
                            valueof_fields.append(val_obj)
        return valueof_fields

    def get_field_obj(self, field_num):
        """ Gets a field object based on a field_num """
        output = False
        f_objs = ImportField.objects\
                            .filter(source_id=self.source_id,
                                    field_num=field_num)[:1]
        if len(f_objs) > 0:
            output = f_objs[0]
        return output


class CandidateDescription():

    DEFAULT_BLANK = '[Blank]'

    def __init__(self):
        self.project_uuid = False
        self.source_id = False

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
        new_man.item_type = 'subjects'
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
        hash_id = Subject().make_hash_id(self.project_uuid, context)
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
