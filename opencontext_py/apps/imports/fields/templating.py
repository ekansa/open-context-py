from django.db import models
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
from opencontext_py.apps.imports.fieldannotations.general import ProcessGeneral


# Stores data about fields from imported tables
class ImportProfile():

    DEFAULT_SUBJECT_TYPE_FIELDS = ['subjects',
                                   'media',
                                   'documents',
                                   'persons',
                                   'projects',
                                   'complex-description']

    DEFAULT_DESCRIBE_TYPE_FIELDS = ['description',
                                    'variable',
                                    'value',
                                    'lat',
                                    'lon',
                                    'geojson',
                                    'early',
                                    'late',
                                    'metadata',
                                    'complex-description',
                                    'obs-num']

    DEFAULT_DESCRIBE_OBJECT_TYPES = ['types',
                                     'xsd:boolean',
                                     'xsd:date',
                                     'xsd:integer',
                                     'xsd:double']

    def __init__(self, source_id):
        self.source_id = source_id
        pg = ProcessGeneral(source_id)
        pg.get_source()
        self.project_uuid = pg.project_uuid
        self.fields = []
        self.has_doc_field = False
        self.raw_field_annotations = []
        self.label = False
        self.has_subjects = False
        self.get_examples = False
        self.field_annotations = False
        self.PREDICATE_CONTAINS = Assertion.PREDICATES_CONTAINS
        self.PREDICATE_LINK = Assertion.PREDICATES_LINK
        self.PREDICATE_CONTAINED_IN = ImportFieldAnnotation.PRED_CONTAINED_IN
        self.PRED_DESCRIBES = ImportFieldAnnotation.PRED_DESCRIBES
        self.PRED_VALUE_OF = ImportFieldAnnotation.PRED_VALUE_OF
        self.PRED_MEDIA_PART_OF = ImportFieldAnnotation.PRED_MEDIA_PART_OF
        self.PRED_DOC_Text = ImportFieldAnnotation.PRED_DOC_Text
        self.PRED_GEO_LOCATION = ImportFieldAnnotation.PRED_GEO_LOCATION
        self.PRED_DATE_EVENT = ImportFieldAnnotation.PRED_DATE_EVENT
        self.PRED_OBS_NUM = ImportFieldAnnotation.PRED_OBS_NUM
        self.PRED_METADATA = ImportFieldAnnotation.PRED_METADATA
        self.PRED_DRAFT_CONTAINS = ImportFieldAnnotation.PRED_DRAFT_CONTAINS
        self.PRED_COMPLEX_DES = ImportFieldAnnotation.PRED_COMPLEX_DES
        self.PRED_COMPLEX_LABEL = ImportFieldAnnotation.PRED_COMPLEX_LABEL
        self.nav = False
        self.has_media_field = False
        self.has_doc_field = False
        self.has_complex_des_field = False

    def get_fields(self, field_num_list=False):
        """ Gets a list of field objects, limited by a list of field_num if not false """
        if field_num_list is not False:
            imp_fields = ImportField.objects\
                                    .filter(source_id=self.source_id,
                                            field_num__in=field_num_list)
        else:
            imp_fields = ImportField.objects\
                                    .filter(source_id=self.source_id)
        self.fields = imp_fields

    def get_subject_type_fields(self, field_num_list=False):
        """ Gets a list of subject-type field objects,
            limited by a list of field_num if not false
        """
        self.get_examples = True
        if field_num_list is not False:
            imp_fields = ImportField.objects\
                                    .filter(source_id=self.source_id,
                                            field_type__in=self.DEFAULT_SUBJECT_TYPE_FIELDS,
                                            field_num__in=field_num_list)
        else:
            imp_fields = ImportField.objects\
                                    .filter(source_id=self.source_id,
                                            field_type__in=self.DEFAULT_SUBJECT_TYPE_FIELDS)
        for field_obj in imp_fields:
            if field_obj.field_type == 'media':
                self.has_media_field = True
            if field_obj.field_type == 'documents':
                self.has_doc_field = True
            if field_obj.field_type == 'complex-description':
                self.has_complex_des_field = True
            field_obj.examples = self.get_example_entities(field_obj.field_num,
                                                           field_obj.value_prefix)
            field_obj.ex_csv = ', '.join(field_obj.examples)
            if len(field_obj.field_value_cat) > 0:
                ent = Entity()
                ent.get_icon = True
                found = ent.dereference(field_obj.field_value_cat)
                if found:
                    field_obj.field_value_cat_label = ent.label
                    field_obj.field_value_cat_icon = ent.icon
            else:
                field_obj.field_value_cat_icon = False
                field_obj.field_value_cat_label = ''
            self.fields.append(field_obj)

    def get_example_entities(self, field_num, value_prefix):
        """ Gets some examples of named entites, appending the value prefix
        """
        examples = []
        example_cells = ImportCell.objects\
                                  .order_by()\
                                  .filter(source_id=self.source_id,
                                          field_num=field_num)\
                                  .distinct('rec_hash')[:5]
        if len(example_cells) > 0:
            for cell in example_cells:
                if len(str(cell.record)) > 0:
                    examples.append(value_prefix + str(cell.record))
        return examples

    def get_field_annotations(self):
        """ get list of annotations on fields """
        anno_list = ImportFieldAnnotation.objects\
                                         .filter(source_id=self.source_id)
        self.raw_field_annotations = anno_list
        return self.raw_field_annotations

    def get_annotations_by_subject_field(self, field_num):
        output = []
        if len(self.raw_field_annotations) < 1:
            self.get_field_annotations()
        for anno_obj in self.raw_field_annotations:
            if anno_obj.field_num == field_num:
                anno_dict = self.make_dict_from_anno_obj(anno_obj)
                output.append(anno_dict)
        return output

    def get_field_object(self, field_num):
        """ gets the field object for a specific field_num """
        output = False
        self.get_fields()
        for field_obj in self.fields:
            if field_obj.field_num == field_num:
                output = field_obj
                break
        return output

    def jsonify_field_annotations(self):
        """ makes a list of field annotations with field metadata
           for annotated fields used for a source_id
        """
        self.field_annotations = []
        for anno_obj in self.raw_field_annotations:
            anno_dict = self.make_dict_from_anno_obj(anno_obj)
            self.field_annotations.append(anno_dict)
        return self.field_annotations

    def check_subject_entity_fields(self):
        """ checks to see it there is at least one field that gets
            described (subjects, media, documents, projects,
            persons)
        """
        for field_obj in self.fields:
            if field_obj.field_type in self.DEFAULT_SUBJECT_TYPE_FIELDS:
                self.has_subjects = True
                break
        return self.has_subjects

    def make_dict_from_anno_obj(self, anno_obj):
        """ returns an ordered dict for an import field annotation object """
        anno_dict = LastUpdatedOrderedDict()
        anno_dict['id'] = anno_obj.id
        sub_field_obj = self.get_field_object(anno_obj.field_num)
        if sub_field_obj is not False:
            anno_dict['subject'] = self.make_dict_from_field_obj(sub_field_obj)
            anno_dict['subject']['id'] = anno_obj.field_num
        else:
            anno_dict['subject'] = False
        if anno_obj.predicate_field_num > 0:
            pred_field_obj = self.get_field_object(anno_obj.predicate_field_num)
            anno_dict['predicate'] = self.make_dict_from_field_obj(pred_field_obj)
            anno_dict['predicate']['id'] = anno_obj.predicate_field_num
            anno_dict['predicate']['type'] = 'import-field'
        else:
            anno_dict['predicate'] = LastUpdatedOrderedDict()
            anno_dict['predicate']['id'] = anno_obj.predicate
            ent = Entity()
            found = ent.dereference(anno_obj.predicate)
            if found:
                anno_dict['predicate']['label'] = ent.label
                anno_dict['predicate']['type'] = ent.item_type
            elif anno_obj.predicate == ImportFieldAnnotation.PRED_CONTAINED_IN:
                anno_dict['predicate']['label'] = 'Contained in'
            elif anno_obj.predicate == ImportFieldAnnotation.PRED_DESCRIBES:
                anno_dict['predicate']['label'] = 'Describes'
            elif anno_obj.predicate == ImportFieldAnnotation.PRED_VALUE_OF:
                anno_dict['predicate']['label'] = 'Value of'
            elif anno_obj.predicate == ImportFieldAnnotation.PRED_MEDIA_PART_OF:
                anno_dict['predicate']['label'] = 'Media part of'
            elif anno_obj.predicate == ImportFieldAnnotation.PRED_DOC_Text:
                anno_dict['predicate']['label'] = 'Has document text'
            elif anno_obj.predicate == ImportFieldAnnotation.PRED_DRAFT_CONTAINS:
                anno_dict['predicate']['label'] = 'Contains (part. hierarchy)'
            elif anno_obj.predicate == ImportFieldAnnotation.PRED_COMPLEX_DES:
                anno_dict['predicate']['label'] = 'Has Complex Description'
            elif anno_obj.predicate == ImportFieldAnnotation.PRED_OBS_NUM:
                anno_dict['predicate']['label'] = 'Is Observation Number Of'
            else:
                anno_dict['predicate']['label'] = False
                anno_dict['predicate']['type'] = False
        if anno_obj.object_field_num > 0:
            obj_field_obj = self.get_field_object(anno_obj.object_field_num)
            anno_dict['object'] = self.make_dict_from_field_obj(obj_field_obj)
            anno_dict['object']['id'] = anno_obj.object_field_num
            anno_dict['object']['type'] = 'import-field'
        else:
            anno_dict['object'] = LastUpdatedOrderedDict()
            anno_dict['object']['id'] = anno_obj.object_uuid
            ent = Entity()
            found = ent.dereference(anno_obj.object_uuid)
            if found:
                anno_dict['object']['label'] = ent.label
                anno_dict['object']['type'] = ent.item_type
            else:
                anno_dict['object']['label'] = False
                anno_dict['object']['type'] = False
        return anno_dict

    def make_dict_from_field_obj(self, field_obj):
        """ returns an ordered dict for a field_obj """
        field_dict = LastUpdatedOrderedDict()
        field_dict['field_num'] = field_obj.field_num
        field_dict['label'] = field_obj.label
        field_dict['ref_name'] = field_obj.ref_name
        field_dict['field_type'] = field_obj.field_type
        field_dict['field_data_type'] = field_obj.field_data_type
        field_dict['field_value_cat'] = field_obj.field_value_cat
        field_dict['obs_num'] = field_obj.obs_num
        field_dict['value_prefix'] = field_obj.value_prefix
        field_dict['unique_count'] = field_obj.unique_count
        field_dict['f_uuid'] = field_obj.f_uuid
        if self.get_examples:
            field_dict['examples'] = self.get_example_entities(field_obj.field_num,
                                                               field_obj.value_prefix)
            field_dict['ex_csv'] = ', '.join(field_dict['examples'])
            if len(field_obj.field_value_cat) > 0:
                ent = Entity()
                ent.get_icon = True
                found = ent.dereference(field_obj.field_value_cat)
                if found:
                    field_dict['field_value_cat_label'] = ent.label
                    field_dict['field_value_cat_icon'] = ent.icon
        return field_dict

    def jsonify_fields(self):
        """ Returns the list of field objects as a json-friendly object """
        output = []
        for field_obj in self.fields:
            field_dict = self.make_dict_from_field_obj(field_obj)
            field_dict['annotations'] = self.get_annotations_by_subject_field(field_obj.field_num)
            output.append(field_dict)
        return output
