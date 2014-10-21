from django.db import models
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.imports.fieldannotations.links import CandidateLink

# Methods to describe import fields and their annotations
class ImportFieldDescribe():

    DEAFULT_MANUAL_SOURCE = 'manual'

    def __init__(self, source_id):
        self.source_id = source_id
        self.project_uuid = False
        self.field_num_list = []

    def update_field_type(self, field_type, field_num):
        """ Updates field_types for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        ImportField.objects\
                   .filter(field_num__in=self.field_num_list)\
                   .update(field_type=field_type)

    def update_field_data_type(self, field_data_type, field_num):
        """ Updates field_data_type for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        ImportField.objects\
                   .filter(field_num__in=self.field_num_list)\
                   .update(field_data_type=field_data_type)

    def update_field_label(self, label, field_num):
        """ Updates field_data_type for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        label = label.strip()
        ImportField.objects\
                   .filter(field_num__in=self.field_num_list)\
                   .update(label=label)

    def update_field_value_prefix(self, value_prefix, field_num):
        """ Updates field_prefix for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        value_prefix = value_prefix.lstrip()
        ImportField.objects\
                   .filter(field_num__in=self.field_num_list)\
                   .update(value_prefix=value_prefix)

    def update_field_value_cat(self, field_value_cat, field_num):
        """ Updates the field value category,
            which is a more fine-grain classification
            for entities to import
            for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        ImportField.objects\
                   .filter(field_num__in=self.field_num_list)\
                   .update(field_value_cat=field_value_cat)

    def get_field_num_list(self, field_num):
        """ Makes a list of field nums, splitting on commas as needed"""
        if ',' in field_num:
            self.field_num_list = field_num.split(',')
        else:
            self.field_num_list = [field_num]
        return self.field_num_list

    def update_field_contains(self, field_num, object_field_num):
        """ Updates a field annotation to make entities in a field_num (subject)
        contain entities in an object_ield_num
        """
        # delete cases where the object_field_num is contained by another field
        anno_objs = ImportFieldAnnotation.objects\
                                         .filter(source_id=self.source_id,
                                                 predicate=Assertion.PREDICATES_CONTAINS,
                                                 object_field_num=object_field_num)\
                                         .delete()
        ifa = ImportFieldAnnotation()
        ifa.source_id = self.source_id
        ifa.project_uuid = self.project_uuid
        ifa.field_num = field_num
        ifa.predicate = Assertion.PREDICATES_CONTAINS
        ifa.predicate_field_num = 0
        ifa.object_field_num = object_field_num
        ifa.object_uuid = ''
        ifa.save()

    def update_field_containedin_entity(self, field_num, object_uuid):
        """ Updates a field annotation to make it contained a subject entity (object_uuid)
            after first deleting other containment annotations
        """
        # delete cases where the another field contains the current field
        anno_objs = ImportFieldAnnotation.objects\
                                         .filter(source_id=self.source_id,
                                                 predicate=Assertion.PREDICATES_CONTAINS,
                                                 object_field_num=field_num)\
                                         .delete()
        # delete cases where the current field is contained in an entity
        anno_subjs = ImportFieldAnnotation.objects\
                                          .filter(source_id=self.source_id,
                                                  predicate=ImportFieldAnnotation.PRED_CONTAINED_IN,
                                                  field_num=field_num)\
                                          .delete()
        ifa = ImportFieldAnnotation()
        ifa.source_id = self.source_id
        ifa.project_uuid = self.project_uuid
        ifa.field_num = field_num
        ifa.predicate = ImportFieldAnnotation.PRED_CONTAINED_IN
        ifa.predicate_field_num = 0
        ifa.object_field_num = 0
        ifa.object_uuid = object_uuid
        ifa.save()

    def make_or_reconcile_link_predicate(self, label, project_uuid):
        """ gets or makes a linking relationship predicate
            based on a label
        """
        output = False
        label = label.strip()
        if len(label) > 1:
            if project_uuid == '0':
                # request to make this associated with OC
                # project '0'
                self.source_id = self.DEAFULT_MANUAL_SOURCE
            else:
                # make sure project uuid is the one associated
                # with the source_id
                project_uuid = self.project_uuid
            cl = CandidateLink()
            cl.project_uuid = project_uuid
            cl.source_id = self.source_id
            cl.make_reconcile_link_pred(label)
            output = cl.uuid
        return output

    def delete_field_annotation(self, annotation_id):
        """ Deletes an annotation by its id """
        annos = ImportFieldAnnotation.objects\
                                     .filter(source_id=self.source_id,
                                             id=annotation_id)\
                                     .delete()


