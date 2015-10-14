from django.db import models
from django.db.models import Q
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fields.templating import ImportProfile
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.imports.fieldannotations.links import CandidateLinkPredicate


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
                   .filter(source_id=self.source_id,
                           field_num__in=self.field_num_list)\
                   .update(field_type=field_type)

    def update_field_data_type(self, field_data_type, field_num):
        """ Updates field_data_type for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        ImportField.objects\
                   .filter(source_id=self.source_id,
                           field_num__in=self.field_num_list)\
                   .update(field_data_type=field_data_type)

    def update_field_label(self, label, field_num):
        """ Updates field_data_type for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        label = label.strip()
        ImportField.objects\
                   .filter(source_id=self.source_id,
                           field_num__in=self.field_num_list)\
                   .update(label=label)

    def update_field_value_prefix(self, value_prefix, field_num):
        """ Updates field_prefix for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        value_prefix = value_prefix.lstrip()
        ImportField.objects\
                   .filter(source_id=self.source_id,
                           field_num__in=self.field_num_list)\
                   .update(value_prefix=value_prefix)

    def update_field_value_cat(self, field_value_cat, field_num):
        """ Updates the field value category,
            which is a more fine-grain classification
            for entities to import
            for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        ImportField.objects\
                   .filter(source_id=self.source_id,
                           field_num__in=self.field_num_list)\
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

    def update_field_links(self, field_num, object_field_num):
        """ Updates a field annotation to make entities in a field_num (subject)
        contain entities in an object_ield_num
        """
        # delete cases where the object_field_num is contained by another field
        anno_objs = ImportFieldAnnotation.objects\
                                         .filter(source_id=self.source_id,
                                                 predicate=Assertion.PREDICATES_LINK,
                                                 object_field_num=object_field_num)\
                                         .delete()
        ifa = ImportFieldAnnotation()
        ifa.source_id = self.source_id
        ifa.project_uuid = self.project_uuid
        ifa.field_num = field_num
        ifa.predicate = Assertion.PREDICATES_LINK
        ifa.predicate_field_num = 0
        ifa.object_field_num = object_field_num
        ifa.object_uuid = ''
        ifa.save()

    def update_desciption(self, field_num, object_field_num):
        """ Updates a field annotation so that a list of field_num
        are assigned to describe an object_field_num entity
        """
        self.get_field_num_list(field_num)
        # delete cases where the field_num is already used
        del_preds = [ImportFieldAnnotation.PRED_DESCRIBES,
                     ImportFieldAnnotation.PRED_GEO_LOCATION]
        anno_objs = ImportFieldAnnotation.objects\
                                         .filter(source_id=self.source_id,
                                                 predicate__in=del_preds,
                                                 field_num__in=self.field_num_list)\
                                         .delete()
        entity_ok = self.check_field_type(object_field_num, ImportProfile.DEFAULT_SUBJECT_TYPE_FIELDS)
        # now check to see if this is OK for making a geolocation
        geo_object_ok = self.check_field_type(object_field_num, ['subjects'])
        for field_num in self.field_num_list:
            des_ok = self.check_field_type(field_num, ['description',
                                                       'variable'])
            geo_ok = self.check_field_type(field_num, ['lat',
                                                       'lon',
                                                       'geojson'])
            if des_ok and entity_ok:
                # only make the annotation if the subject is a value, object is a variable
                ifa = ImportFieldAnnotation()
                ifa.source_id = self.source_id
                ifa.project_uuid = self.project_uuid
                ifa.field_num = field_num
                ifa.predicate = ImportFieldAnnotation.PRED_DESCRIBES
                ifa.predicate_field_num = 0
                ifa.object_field_num = object_field_num
                ifa.object_uuid = ''
                ifa.save()
            elif geo_ok and geo_object_ok:
                # we have a geospatial annotation
                ifa = ImportFieldAnnotation()
                ifa.source_id = self.source_id
                ifa.project_uuid = self.project_uuid
                ifa.field_num = field_num
                ifa.predicate = ImportFieldAnnotation.PRED_GEO_LOCATION
                ifa.predicate_field_num = 0
                ifa.object_field_num = object_field_num
                ifa.object_uuid = ''
                ifa.save()

    def update_variable_value(self, field_num, object_field_num):
        """ Updates a field annotation to make entities in a field_num (subject)
        contain entities in an object_ield_num
        """
        # delete cases where the field_num is a value_of another field
        anno_objs = ImportFieldAnnotation.objects\
                                         .filter(source_id=self.source_id,
                                                 predicate=ImportFieldAnnotation.PRED_VALUE_OF,
                                                 field_num=field_num)\
                                         .delete()
        ifa = ImportFieldAnnotation()
        ifa.source_id = self.source_id
        ifa.project_uuid = self.project_uuid
        ifa.field_num = field_num
        ifa.predicate = ImportFieldAnnotation.PRED_VALUE_OF
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
    
    def update_field_media_part_of_entity(self, field_num, object_field_num):
        """ Updates a field annotation to make entities in a field_num (subject)
        a media part of entities in an object_ield_num
        """
        # delete cases where the (subject) field_num is a media part of another field
        anno_objs = ImportFieldAnnotation.objects\
                                         .filter(source_id=self.source_id,
                                                 predicate=ImportFieldAnnotation.PRED_MEDIA_PART_OF,
                                                 field_num=field_num)\
                                         .delete()
        ifa = ImportFieldAnnotation()
        ifa.source_id = self.source_id
        ifa.project_uuid = self.project_uuid
        ifa.field_num = field_num
        ifa.predicate = ImportFieldAnnotation.PRED_MEDIA_PART_OF
        ifa.predicate_field_num = 0
        ifa.object_field_num = object_field_num
        ifa.object_uuid = ''
        ifa.save()

    def update_field_custom_predicate(self,
                                      field_num,
                                      object_field_num,
                                      predicate_id,
                                      predicate_type):
        """ Updates a field annotation to make entities in a field_num (subject)
        have a custom relationship (predicate_id) to an object_field_num
        """
        try:
            # in case we try to pass somthing that's not an integer
            anno_subjs = ImportFieldAnnotation.objects\
                                              .filter(source_id=self.source_id,
                                                      field_num=field_num,
                                                      object_field_num=object_field_num,
                                                      predicate_field_num=predicate_id)\
                                              .delete()
        except:
            pass
        anno_subjs = ImportFieldAnnotation.objects\
                                          .filter(source_id=self.source_id,
                                                  field_num=field_num,
                                                  object_field_num=object_field_num,
                                                  predicate=predicate_id)\
                                          .delete()
        ifa = ImportFieldAnnotation()
        ifa.source_id = self.source_id
        ifa.project_uuid = self.project_uuid
        ifa.field_num = field_num
        if 'field' in predicate_type:
            # predicate linking relation in an importer field
            # means entities in this field describe different linking relations
            ifa.predicate = ''
            ifa.predicate_field_num = predicate_id
        else:
            # predicate linking relation is the predicate_id
            ifa.predicate = predicate_id
            ifa.predicate_field_num = 0
        ifa.object_field_num = object_field_num
        ifa.object_uuid = ''
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
            clp = CandidateLinkPredicate()
            clp.project_uuid = project_uuid
            clp.source_id = self.source_id
            clp.make_reconcile_link_pred(label)
            output = clp.uuid
        return output

    def delete_field_annotation(self, annotation_id):
        """ Deletes an annotation by its id """
        annos = ImportFieldAnnotation.objects\
                                     .filter(source_id=self.source_id,
                                             id=annotation_id)\
                                     .delete()

    def check_field_type(self, field_num, expected_type_list):
        """ checks to see if a given field is of the expected list """
        output = False
        ifo = ImportField.objects\
                         .filter(source_id=self.source_id,
                                 field_num=field_num,
                                 field_type__in=expected_type_list)[:1]
        if len(ifo) > 0:
            output = True
        return output
