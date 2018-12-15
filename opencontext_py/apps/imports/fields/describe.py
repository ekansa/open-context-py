from titlecase import titlecase
from django.db import models
from django.db.models import Q
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fields.templating import ImportProfile
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.imports.fieldannotations.links import CandidateLinkPredicate
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.manifest.models import Manifest


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

    def match_all_unclassified(self):
        """ matches all unclassified fields against already imported predicates """
        imp_fields = ImportField.objects\
                                .filter(source_id=self.source_id)
        for imp_field in imp_fields:
            labels_list = [imp_field.label]
            # print('See: ' + str(labels_list) + ' ft:' + str(imp_field.field_type))
            if imp_field.field_type is None \
               or imp_field.field_type == '' \
               or imp_field.field_type == ImportField.DEFAULT_FIELD_TYPE:
                # print('Checking: ' + str(labels_list))
                man_pred = Manifest.objects\
                                   .filter(project_uuid=self.project_uuid,
                                           item_type='predicates',
                                           label__in=labels_list)[:1]
                if len(man_pred) > 0:
                    imp_field.field_type = 'description'
                    imp_field.label = man_pred[0].label
                    try:
                        pred = Predicate.objects.get(uuid=man_pred[0].uuid)
                    except Predicate.DoesNotExist:
                        pred = False
                    if pred is not False \
                       and (imp_field.field_data_type is None \
                            or imp_field.field_data_type == '' \
                            or imp_field.field_data_type == ImportField.DEFAULT_DATA_TYPE):
                        imp_field.field_data_type = pred.data_type
                    self.field_num_list.append(imp_field.field_num)
                    imp_field.save()
                # now check to blank out empty fields and set as ignore
                non_blank_cells = ImportCell.objects\
                                            .filter(source_id=self.source_id,
                                                    field_num=imp_field.field_num)\
                                            .exclude(record='')
                if len(non_blank_cells) < 1:
                    imp_field.field_type = 'ignore'
                    imp_field.field_data_type == ImportField.DEFAULT_DATA_TYPE
                    self.field_num_list.append(imp_field.field_num)
                    imp_field.save()

    def update_field_label(self, label, field_num):
        """ Updates field_data_type for a comma-seperated list of field_nums """
        self.get_field_num_list(field_num)
        label = label.strip()
        ImportField.objects\
                   .filter(source_id=self.source_id,
                           field_num__in=self.field_num_list)\
                   .update(label=label)
    
    def update_field_label_titlecase(self, field_num):
        """ Puts a field lable into Title Case """
        self.get_field_num_list(field_num)
        act_fields = ImportField.objects\
                                .filter(source_id=self.source_id,
                                        field_num__in=self.field_num_list)
        for act_field in act_fields:
            tc_label = titlecase(act_field.label.replace('_', ' '))
            act_field.label = tc_label
            act_field.save()

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

    def update_field_contains(self, field_num, object_field_num, pred_contains=None):
        """ Updates a field annotation to make entities in a field_num (subject)
        contain entities in an object_ield_num
        """
        if pred_contains is None:
            pred_contains = Assertion.PREDICATES_CONTAINS
        # delete cases where the object_field_num is contained by another field
        del_preds = [Assertion.PREDICATES_CONTAINS, ImportFieldAnnotation.PRED_DRAFT_CONTAINS]
        anno_objs = ImportFieldAnnotation.objects\
                                         .filter(source_id=self.source_id,
                                                 predicate__in=del_preds,
                                                 object_field_num=object_field_num)\
                                         .delete()
        ifa = ImportFieldAnnotation()
        ifa.source_id = self.source_id
        ifa.project_uuid = self.project_uuid
        ifa.field_num = field_num
        ifa.predicate = pred_contains
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
                                                 field_num=field_num,
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

    def update_description(self, field_num, object_field_num):
        """ Updates a field annotation so that a list of field_num
        are assigned to describe an object_field_num entity
        """
        self.get_field_num_list(field_num)
        # delete cases where the field_num is already used
        del_preds = [ImportFieldAnnotation.PRED_DESCRIBES,
                     ImportFieldAnnotation.PRED_GEO_LOCATION,
                     ImportFieldAnnotation.PRED_DATE_EVENT,
                     ImportFieldAnnotation.PRED_METADATA,
                     ImportFieldAnnotation.PRED_COMPLEX_DES]            
        anno_objs = ImportFieldAnnotation.objects\
                                         .filter(source_id=self.source_id,
                                                 predicate__in=del_preds,
                                                 field_num__in=self.field_num_list)\
                                         .delete()
        entity_ok = self.check_field_type(object_field_num, ImportProfile.DEFAULT_SUBJECT_TYPE_FIELDS)
        # now check to see if this is OK for making a geolocation
        geo_date_object_ok = self.check_field_type(object_field_num, ['subjects'])
        for field_num in self.field_num_list:
            des_ok = self.check_field_type(field_num, ['description',
                                                       'variable'])
            geo_ok = self.check_field_type(field_num, ['lat',
                                                       'lon',
                                                       'geojson'])
            date_ok = self.check_field_type(field_num, ['early',
                                                        'late'])
            meta_ok =  self.check_field_type(field_num, ['metadata'])
            complex_des_ok = self.check_field_type(field_num, ['complex-description'])
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
            elif geo_ok and geo_date_object_ok:
                # we have a geospatial annotations
                ifa = ImportFieldAnnotation()
                ifa.source_id = self.source_id
                ifa.project_uuid = self.project_uuid
                ifa.field_num = field_num
                ifa.predicate = ImportFieldAnnotation.PRED_GEO_LOCATION
                ifa.predicate_field_num = 0
                ifa.object_field_num = object_field_num
                ifa.object_uuid = ''
                ifa.save()
            elif date_ok and geo_date_object_ok:
                # we have a date annotations
                ifa = ImportFieldAnnotation()
                ifa.source_id = self.source_id
                ifa.project_uuid = self.project_uuid
                ifa.field_num = field_num
                ifa.predicate = ImportFieldAnnotation.PRED_DATE_EVENT
                ifa.predicate_field_num = 0
                ifa.object_field_num = object_field_num
                ifa.object_uuid = ''
                ifa.save()
            elif complex_des_ok:
                # we have complex description annotations
                ifa = ImportFieldAnnotation()
                ifa.source_id = self.source_id
                ifa.project_uuid = self.project_uuid
                ifa.field_num = field_num
                ifa.predicate = ImportFieldAnnotation.PRED_COMPLEX_DES
                ifa.predicate_field_num = 0
                ifa.object_field_num = object_field_num
                ifa.object_uuid = ''
                ifa.save()
            elif meta_ok:
                # we have metadata annotations
                ifa = ImportFieldAnnotation()
                ifa.source_id = self.source_id
                ifa.project_uuid = self.project_uuid
                ifa.field_num = field_num
                ifa.predicate = ImportFieldAnnotation.PRED_METADATA
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
    
    def update_obs_num(self, field_num, object_field_num):
        """ Updates a field annotation to make entities in a field_num (subject)
        contain entities in an object_ield_num
        """
        # delete cases where the field_num is an OBS NUM of another field
        anno_objs = ImportFieldAnnotation.objects\
                                         .filter(source_id=self.source_id,
                                                 predicate=ImportFieldAnnotation.PRED_OBS_NUM,
                                                 field_num=field_num)\
                                         .delete()
        ifa = ImportFieldAnnotation()
        ifa.source_id = self.source_id
        ifa.project_uuid = self.project_uuid
        ifa.field_num = field_num
        ifa.predicate = ImportFieldAnnotation.PRED_OBS_NUM
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
    
    def update_field_document_text_entity(self, field_num, object_field_num):
        """ Updates a field annotation to make document entities in a field_num (subject)
        have document text in an object_ield_num
        """
        # delete cases where the (subject) field_num is a media part of another field
        anno_objs = ImportFieldAnnotation.objects\
                                         .filter(source_id=self.source_id,
                                                 predicate=ImportFieldAnnotation.PRED_DOC_Text,
                                                 field_num=field_num)\
                                         .delete()
        ifa = ImportFieldAnnotation()
        ifa.source_id = self.source_id
        ifa.project_uuid = self.project_uuid
        ifa.field_num = field_num
        ifa.predicate = ImportFieldAnnotation.PRED_DOC_Text
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
    
    def update_field_predicate_infield(self,
                                       field_num,
                                       object_field_num,
                                       predicate_field_num):
        """ Updates a field annotation to make entities in a field_num (subject)
        have custom relationships defined by the values in a predicate_field_num
        to entities in the object_field_num
        """
        try:
            # in case we try to pass somthing that's not an integer
            anno_subjs = ImportFieldAnnotation.objects\
                                              .filter(source_id=self.source_id,
                                                      field_num=field_num,
                                                      object_field_num=object_field_num,
                                                      predicate_field_num=predicate_field_num)\
                                              .delete()
        except:
            pass
        anno_subjs = ImportFieldAnnotation.objects\
                                          .filter(source_id=self.source_id,
                                                  field_num=field_num,
                                                  object_field_num=object_field_num,
                                                  predicate='',
                                                  predicate_field_num=predicate_field_num)\
                                          .delete()
        ifa = ImportFieldAnnotation()
        ifa.source_id = self.source_id
        ifa.project_uuid = self.project_uuid
        ifa.field_num = field_num
        ifa.predicate = ''
        ifa.predicate_field_num = predicate_field_num
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
