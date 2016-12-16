import uuid as GenUUID
from django.db import models
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.strings.manage import StringManagement
from opencontext_py.apps.ocitems.predicates.manage import PredicateManagement
from opencontext_py.apps.imports.fields.datatypeclass import DescriptionDataType


class FaimsDescription():
    """ Processes the import of an attribute
        that describes a given FAIMS entity
    """

    def __init__(self):
        self.project_uuid = False
        self.source_id = False
        self.attrib_dict = False
        self.subject_uuid = None
        self.subject_type = None
        self.predicate_uuid = None
        self.object_uuid = None
        self.obs_num = 1
        self.sort_num = 10
        self.faims_record = None
        self.faims_record_id = None
        self.reconcile_key = 'faims_id'

    def add_description(self):
        """ validates the value's data type
            if the data type differs from the
            predicate data type,
            add it as a note
        """
        # validate the faims record against its expected data type
        # the validated_record will be None if not valid
        if isinstance(self.subject_uuid, str) \
           and isinstance(self.subject_type, str):
            # we have subject information
            ok_to_add = False
            data_type = self.attrib_dict['data_type']
            if isinstance(self.predicate_uuid, str):
                predicate_uuid = self.predicate_uuid
            elif 'predicate_uuid' in self.attrib_dict:
                predicate_uuid = self.attrib_dict['predicate_uuid']
            object_date = None
            object_uuid = None
            object_num = None
            object_type = data_type
            if data_type == 'id':
                # we're processing a controlled vocab (oc-type) object
                if isinstance(self.faims_record_id, str):
                    if self.faims_record_id in self.attrib_dict['objects']:
                        # we found the object for this item
                        obj_dict = self.attrib_dict['objects'][self.faims_record_id]
                        object_uuid = obj_dict['type_uuid']
                        object_type = 'types'
                        ok_to_add = True
            elif self.faims_record is not None:
                # we're processing a literal value
                ddt = DescriptionDataType()
                validated_record = ddt.validate_literal_by_data_type(data_type,
                                                                     self.faims_record)
                if validated_record is not None:
                    # the record is valid for the data_type
                    ok_to_add = True
                    if data_type == 'xsd:date':
                        object_date = validated_record
                    elif data_type == 'xsd:string':
                        # we have a string, so add it to the database and get its uuid
                        str_man = StringManagement()
                        str_man.project_uuid = self.project_uuid
                        str_man.source_id = self.source_id
                        str_obj = str_man.get_make_string(validated_record)
                        object_uuid = str(str_obj.uuid)
                    else:
                        # we have numeric data, so add to numeric data
                        object_num = validated_record
                else:
                    # the record is not valid for the data_type, so treat it as a string
                    # so first we need to make a predicate for it, that is for
                    # string values of this associated with this attribute
                    object_type = 'xsd:string'
                    sup_dict = LastUpdatedOrderedDict()
                    sup_dict[self.reconcile_key] = self.attrib_dict['id']  # the faims attribute id
                    pm = PredicateManagement()
                    pm.project_uuid = self.project_uuid
                    pm.source_id = self.source_id
                    pm.sup_dict = sup_dict
                    pm.sup_reconcile_key = self.reconcile_key
                    pm.sup_reconcile_value = self.attrib_dict['id']  # the faims attribute id
                    pred_obj = pm.get_make_predicate(self.attrib_dict['label'] + ' [Note]',
                                                     self.attrib_dict['predicate_type'],
                                                     object_type)
                    if pred_obj is not False:
                        # we have a new predicate
                        predicate_uuid = pred_obj.uuid
                        # now make an object_uuid for the original faims record
                        str_man = StringManagement()
                        str_man.project_uuid = self.project_uuid
                        str_man.source_id = self.source_id
                        str_obj = str_man.get_make_string(self.faims_record)
                        object_uuid = str(str_obj.uuid)
                        ok_to_add = True
            else:
                # not valid data, don't add
                ok_to_add = False
            if ok_to_add:
                # now we're OK to add the descrpitive assertion
                new_ass = Assertion()
                new_ass.uuid = self.subject_uuid
                new_ass.subject_type = self.subject_type
                new_ass.project_uuid = self.project_uuid
                new_ass.source_id = self.source_id
                new_ass.obs_node = '#obs-' + str(self.obs_num)
                new_ass.obs_num = self.obs_num
                new_ass.sort = self.sort_num
                new_ass.visibility = 1
                new_ass.predicate_uuid = predicate_uuid
                new_ass.object_type = object_type
                if object_num is not None:
                    new_ass.data_num = object_num
                if object_date is not None:
                    new_ass.data_date = object_date
                if object_uuid is not None:
                    new_ass.object_uuid = object_uuid
                try:
                    new_ass.save()
                except:
                    # probably already imported
                    pass
        
    def add_type_description(self, predicate_uuid, object_uuid, object_type='types'):
        """ adds a description with a controlled vocabulary, where
            both predicate_uuid and object_uuid are known
        """
        if isinstance(self.subject_uuid, str) \
           and isinstance(self.subject_type, str):
            new_ass = Assertion()
            new_ass.uuid = self.subject_uuid
            new_ass.subject_type = self.subject_type
            new_ass.project_uuid = self.project_uuid
            new_ass.source_id = self.source_id
            new_ass.obs_node = '#obs-' + str(self.obs_num)
            new_ass.obs_num = self.obs_num
            new_ass.sort = self.sort_num
            new_ass.visibility = 1
            new_ass.predicate_uuid = predicate_uuid
            new_ass.object_type = object_type
            new_ass.object_uuid = object_uuid
            try:
                new_ass.save()
            except:
                # probably already imported
                pass