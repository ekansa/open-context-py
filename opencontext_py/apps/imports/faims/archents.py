import os
import codecs
import uuid as GenUUID
import re
import datetime
import json
from dateutil.parser import parse
from lxml import etree
from django.db import models
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.fields.datatypeclass import DescriptionDataType
from opencontext_py.apps.imports.faims.files import FileManage


class ArchEntsImport():
    """ Loads ArchEnts.xml files for import

from opencontext_py.apps.imports.faims.archents import ArchEntsImport
faims_ents = ArchEntsImport()
faims_ents.gen_config('faims-survey')

Note: in the element <freetext> a user enters an annotation
on an observation.

<formattedIdentifierformattedIdentifier> is best to use for a label,
but the faims-uuid for the entity is the locally unique id 


    """

    def __init__(self):
        self.tree = None
        self.project_uuid = False
        self.source_id = False
        self.import_persons = {}
        self.load_into_importer = False
        self.dt_attribute_objs = LastUpdatedOrderedDict()
        self.attributes = LastUpdatedOrderedDict()
        self.entity_types = LastUpdatedOrderedDict()
        self.relation_types = LastUpdatedOrderedDict()
        self.oc_config_relation_types = 'oc-relation-types'
        self.oc_config_entity_types = 'oc-entity-types'
        self.oc_config_attributes = 'oc-attributes'
        self.fm = FileManage()

    def gen_config(self, act_dir, filename='archents.xml'):
        """ processes the archents file """
        self.tree = self.fm.load_xml_file(act_dir, filename)
        if self.tree is not False:
            self.load_or_classify_attributes(act_dir)
            self.load_or_get_entity_types(act_dir)
            self.check_update_relations_types(act_dir)

    def load_or_get_entity_types(self, act_dir):
        """ loads or classifies attributes in a tree """
        key = self.oc_config_entity_types
        json_obj = self.fm.get_dict_from_file(key, act_dir)
        if json_obj is None:
            # need to read the XML and get entity types
            self.get_xml_entity_types()
            self.fm.save_serialized_json(key,
                                         act_dir,
                                         self.entity_types)
        else:
            self.entity_types = json_obj

    def get_xml_entity_types(self):
        """ gets a list of different entity types in the
            FAIMS xml
        """
        if self.tree is not False:
            ent_types = self.tree.xpath('/archents/aenttype')
            for ent_type in ent_types:
                faims_id = ent_type.get('aentTypeID')
                ent_type_obj = LastUpdatedOrderedDict()
                ent_type_obj['id'] = faims_id
                ent_type_obj['label'] = ent_type.get('aentTypeName')
                ent_type_obj['item_type'] = None
                ent_type_obj['class_uri'] = None
                # add the type label as an attribute
                ent_type_obj['add_type_as_attribute'] = True
                ent_type_obj['space_context_rank'] = 0
                self.entity_types[faims_id] = ent_type_obj

    def load_or_classify_attributes(self, act_dir):
        """ loads or classifies attributes in a tree """
        key = self.oc_config_attributes
        json_obj = self.fm.get_dict_from_file(key, act_dir)
        if json_obj is None:
            # need to read the XML and make the classifications from scratch
            self.classify_xml_tree_attributes()
            # now make dictionary objects to save as JSON
            self.attributes = LastUpdatedOrderedDict()
            for prop_id, dt_class_obj in self.dt_attribute_objs.items():
                attrib_dict = dt_class_obj.make_dict_obj()
                attrib_dict['predicate_type'] = 'variable'
                attrib_dict['predicate_type'] = 'variable'  # default type
                attrib_dict['oc-equiv'] = None  # default to no equivalence
                attrib_dict = self.check_attribute_as_identifier(attrib_dict,
                                                                 ImportFieldAnnotation.PRED_CONTAINED_IN)
                if prop_id not in self.attributes:
                    self.attributes[prop_id] = attrib_dict
            self.fm.save_serialized_json(key,
                                         act_dir,
                                         self.attributes)
        else:
            # we have JSON with dictionary objects to read into the classes
            self.attributes = json_obj
            for prop_id, attrib_dict in self.attributes.items():
                dt_class_obj = DescriptionDataType()
                ok = dt_class_obj.read_dict_obj(attrib_dict)
                if ok:
                    self.dt_attribute_objs[prop_id] = dt_class_obj
            # now update if new attributes where found
            save_update = False
            for prop_id, dt_class_obj in self.dt_attribute_objs.items():
                attrib_dict = dt_class_obj.make_dict_obj()
                attrib_dict['predicate_type'] = 'variable'  # default type
                attrib_dict['oc-equiv'] = None  # default to no equivalence
                attrib_dict = self.check_attribute_as_identifier(attrib_dict,
                                                                 ImportFieldAnnotation.PRED_CONTAINED_IN)
                if prop_id not in self.attributes:
                    save_update = True
                    self.attributes[prop_id] = attrib_dict
            if save_update:
                self.fm.save_serialized_json(key,
                                             act_dir,
                                             self.attributes)

    def check_update_relations_types(self, act_dir):
        """ checks to see if different relation types are used in
            identifiers, updates accordingly
        """
        key = self.oc_config_relation_types
        json_obj = self.fm.get_dict_from_file(key, act_dir)
        if json_obj is not None:
            self.relation_types = json_obj
            for faims_id_pred, rel_dict in json_obj.items():
                rel_dict = self.check_attribute_as_identifier(rel_dict,
                                                              Assertion.PREDICATES_CONTAINS)
                self.relation_types[faims_id_pred] = rel_dict
            self.fm.save_serialized_json(key,
                                         act_dir,
                                         self.relation_types) 

    def check_attribute_as_identifier(self, attrib_dict, oc_equiv):
        """ checks to see if the attribute is used as an identifier
            if so, then it is likely part of a spatial context
        """
        if self.tree is not False:
            idents = self.tree.xpath('//identifiers/identifier')
            for ident in idents:
                if not isinstance(attrib_dict['oc-equiv'], str):
                    # check to see if we've got a matching attribute label
                    ident_names = ident.xpath('attributename')
                    for ident_name in ident_names:
                        if ident_name.text == attrib_dict['label']:
                            attrib_dict['oc-equiv'] = ImportFieldAnnotation.PRED_CONTAINED_IN
                            break
                else:
                    # we've got an equivalent so no need to loop
                    break
        return attrib_dict

    def classify_xml_tree_attributes(self):
        """ classifies attributes in a tree """
        if self.tree is not False:
            ent_types = self.tree.xpath('/archents/aenttype')
            for ent_type in ent_types:
                ents = ent_type.xpath('archentity')
                for entity in ents:
                    props = entity.xpath('properties/property')
                    for prop in props:
                        prop_name = prop.xpath('attributename')[0].text
                        prop_id = prop.xpath('attributeid')[0].text
                        if prop_id not in self.attributes:
                            dt_class_obj = DescriptionDataType()
                            dt_class_obj.id = prop_id
                            dt_class_obj.label = prop_name
                        else:
                            dt_class_obj = self.attributes[prop_id]
                        record = self.get_property_record(prop)
                        if record is not None:
                            dt_class_obj.check_record_datatype(record)
                            dt_class_obj.data_type = dt_class_obj.classify_data_type()
                            self.dt_attribute_objs[prop_id] = dt_class_obj
    
    def review_attribute_data_types(self):
        """ review data types for attributes """
        for prop_id, dt_class_obj in self.dt_attribute_objs.items():
            print('-------------------------')
            print('Prop: ' + dt_class_obj.label)
            print('Data-type: ' + str(dt_class_obj.data_type))
            print('TOTAL: ' + str(dt_class_obj.total_count))
            print('Boolean: ' + str(dt_class_obj.boolean_count))
            print('Int: ' + str(dt_class_obj.int_count))
            print('Float: ' + str(dt_class_obj.float_count))
            print('Datetime: ' + str(dt_class_obj.datetime_count))
            print('Uniques: ' + str(len(dt_class_obj.uniqe_str_hashes)))
            print(' ')
                        
    def process_entity(self, entity):
        """processes each entity """
        faims_uuid = entity.xpath('uuid')[0].text
        uuid = GenUUID.uuid4()
        uuid = str(uuid)
        print('FAIMS-UUID: ' + faims_uuid)
        print('UUID: ' + uuid)
        created_by = entity.xpath('createdBy')[0].text
        modified_by = entity.xpath('modifiedBy')[0].text
        created_by_uuid = self.get_make_person_uuid(created_by)
        modified_by_uuid = self.get_make_person_uuid(modified_by)
        print('Creator: ' + created_by + '(' + created_by_uuid + ')')
        print('Modified: ' + modified_by + '(' + modified_by_uuid + ')')
        print('-----------------------------------------')
    
    def get_property_record(self, prop):
        record = None
        vocabs = prop.xpath('vocabname')
        for vocab in vocabs:
            record = vocab.text
        if record is None:
            measures = prop.xpath('measure')
            for measure in measures:
                record = measure.text
        return record

    def get_make_person_uuid(self, person_name):
        """ gets or makes uuid for a person """
        if person_name in self.import_persons:
            uuid = self.import_persons[person_name]
        else:
            uuid = GenUUID.uuid4()
            uuid = str(uuid)
            self.import_persons[person_name] = uuid
        return uuid
