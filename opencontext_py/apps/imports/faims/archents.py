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
from opencontext_py.apps.ocitems.predicates.manage import PredicateManagement
from opencontext_py.apps.ocitems.octypes.manage import TypeManagement
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.sources.models import ImportSource
from opencontext_py.apps.imports.fields.datatypeclass import DescriptionDataType
from opencontext_py.apps.imports.faims.description import FaimsDescription
from opencontext_py.apps.imports.faims.files import FileManage


class ArchEntsImport():
    """ Loads ArchEnts.xml files for import

from opencontext_py.apps.imports.faims.archents import ArchEntsImport
faims_ents = ArchEntsImport()
faims_ents.gen_config('faims-survey')

from opencontext_py.apps.imports.faims.archents import ArchEntsImport
faims_ents = ArchEntsImport()
faims_ents.db_initial_subjects_creation('faims-test')

Note: in the element <freetext> a user enters an annotation
on an observation.

<formattedIdentifierformattedIdentifier> is best to use for a label,
but the faims-uuid for the entity is the locally unique id 


    """

    FAIMS_ENTITY_TYPE_PREDICATE_LABEL = 'Entity Record Type'
    
    def __init__(self):
        self.tree = None
        self.project_uuid = False
        self.source_id = False
        self.import_persons = {}
        self.root_subject_label = False
        self.root_subject_uuid = False
        self.root_subject_context = False
        self.root_subject_class = 'oc-gen:cat-site'
        self.root_subject_sup_id = 'auto-root'
        self.load_into_importer = False
        self.dt_attribute_objs = LastUpdatedOrderedDict()
        self.attributes = LastUpdatedOrderedDict()
        self.entity_types = LastUpdatedOrderedDict()
        self.relation_types = LastUpdatedOrderedDict()
        self.entities = LastUpdatedOrderedDict()
        self.oc_config_relation_types = 'oc-relation-types'
        self.oc_config_entity_types = 'oc-entity-types'
        self.oc_config_attributes = 'oc-attributes'
        self.oc_config_entities = 'oc-entities'
        self.reconcile_key = 'faims_id'
        self.ent_type_pred_sup_id = 'auto-entity-type'
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
                ent_type_obj['predicate_uuid'] = None
                ent_type_obj['type_uuid'] = None
                # counts ranking
                xml_entities = ent_type.xpath('archentity')
                ent_type_obj['count'] = len(xml_entities)
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
    
    def db_initial_subjects_creation(self, act_dir, filename='archents.xml'):
        """ inital creation of subjects """
        self.tree = self.fm.load_xml_file(act_dir, filename)
        self.entities = self.fm.get_dict_from_file(self.oc_config_entities,
                                                   act_dir)
        if self.entities is None:
            self.entities = LastUpdatedOrderedDict()
        self.entity_types = self.fm.get_dict_from_file(self.oc_config_entity_types,
                                                       act_dir)
        if self.tree is not False and self.entity_types is not None:
            # we loaded the needed data, now to create the subject entities
            # first we make a temporary root item for the import,
            # this puts everything into an intial context tree
            self.db_create_temporary_root_subject()
            # now we get the entity types to check which ones are subjects to import
            ent_types = self.tree.xpath('/archents/aenttype')
            for ent_type in ent_types:
                faims_id = ent_type.get('aentTypeID')
                faims_id = str(faims_id)
                if faims_id in self.entity_types:
                    ent_dict = self.entity_types[faims_id]
                    if isinstance(ent_dict['class_uri'], str) \
                       and ent_dict['item_type'] == 'subjects':
                        # we have an entity type OK to make subjects with
                        # so we can now get the entity XML and make
                        print('OK to make subjects for: ' + ent_dict['label'])
                        xml_entities = ent_type.xpath('archentity')
                        for xml_ent in xml_entities:
                            faims_item_id = xml_ent.xpath('uuid')[0].text
                            item_label = xml_ent.xpath('identifiers/formattedIdentifier')[0].text
                            item_label = item_label.replace('{', '')
                            item_label = item_label.replace('}', '')
                            item_label = item_label.strip()
                            print('Import FAIMS-ID: ' + faims_item_id + ' label: ' + item_label)
                            self.db_create_initial_subject_item(act_dir,
                                                                ent_dict,
                                                                faims_item_id,
                                                                item_label) 
    
    def db_create_initial_subject_item(self,
                                       act_dir,
                                       ent_dict,
                                       faims_item_id,
                                       item_label):
        """ reconciles or makes a new subject item (manifest, subject,
            initial containment assertion)
        """
        if faims_item_id not in self.entities:
            # a new item, not seen before
            man_obj = self.check_get_faims_manifest_object(faims_item_id,
                                                           item_label,
                                                           ent_dict['item_type'],
                                                           ent_dict['class_uri'])
            if man_obj is False:
                # we did not find it, so make a new one
                # first, make the supplemental dict object to help associate the faims_item_id
                # with the manifest object. This makes reconcilation precise.
                sup_dict = {}
                sup_dict[self.reconcile_key] = faims_item_id
                sup_dict['faims_label'] = item_label
                # now, make sure the item label is unique
                item_label = self.check_make_manifest_label_unique(item_label,
                                                                   ent_dict['item_type'],
                                                                   ent_dict['class_uri'])
                # make the intial context, based on the root context's path
                context = self.root_subject_context + '/' + item_label
                uuid = GenUUID.uuid4()
                uuid = str(uuid)
                new_sub = Subject()
                new_sub.uuid = uuid
                new_sub.project_uuid = self.project_uuid
                new_sub.source_id = self.source_id
                new_sub.context = context
                new_sub.save()
                man_obj = Manifest()
                man_obj.uuid = uuid
                man_obj.project_uuid = self.project_uuid
                man_obj.source_id = self.source_id
                man_obj.item_type = 'subjects'
                man_obj.repo = ''
                man_obj.class_uri = ent_dict['class_uri']
                man_obj.label = item_label
                man_obj.des_predicate_uuid = ''
                man_obj.views = 0
                man_obj.sup_json = sup_dict
                man_obj.save()
                # now add the initial containment relationship
                self.add_change_containment_assertion(self.root_subject_uuid,
                                                      man_obj.uuid)
            # now save the open context uuid for the entity in the entities dict
            self.entities[faims_item_id] = LastUpdatedOrderedDict()
            self.entities[faims_item_id]['uuid'] = man_obj.uuid
            self.entities[faims_item_id]['item_type'] = man_obj.item_type
            self.fm.save_serialized_json(self.oc_config_entities,
                                         act_dir,
                                         self.entities)
    
    def check_make_manifest_label_unique(self,
                                         item_label,
                                         item_type,
                                         class_uri,
                                         label_suffix_num=1):
        """ checks to make sure a given label for a given item type
            is really unique in the manifest, if not add a suffix
        """
        original_label = item_label
        if label_suffix_num > 1:
            item_label += ' [' + str(label_suffix_num) + ']'
        man_objs = Manifest.objects\
                           .filter(label=item_label,
                                   item_type=item_type,
                                   class_uri=class_uri,
                                   project_uuid=self.project_uuid)[:1]
        if len(man_objs) > 0 and label_suffix_num < 10000:
            label_suffix_num += 1
            item_label = self.check_make_manifest_label_unique(original_label,
                                                               item_type,
                                                               class_uri,
                                                               label_suffix_num)
        return item_label
    
    def check_get_faims_manifest_object(self,
                                        faims_item_id,
                                        item_label,
                                        item_type,
                                        class_uri):
        """ checks to see if a faims entity has a manifest object, by
            matching label (including possible suffixes), item_type,
            class_uri, project AND faims_item_id
        """
        man_obj = False
        man_objs = Manifest.objects\
                           .filter(label__contains=item_label,
                                   item_type=item_type,
                                   class_uri=class_uri,
                                   project_uuid=self.project_uuid)
        if len(man_objs) > 0:
            for act_man_obj in man_objs:
                match_ok = act_man_obj.check_sup_json_key_value(self.reconcile_key,
                                                                faims_item_id)
                if match_ok:
                    # the faims_item_id matches the suplemental JSON dict key-value
                    # for this item, so we have a genuine matching manifest record
                    man_obj = act_man_obj
                    break
        return man_obj
    
    def add_change_containment_assertion(self, parent_uuid, child_uuid):
        """ adds or changes a containment assertion """
        contain_pred = Assertion.PREDICATES_CONTAINS
        del_old = Assertion.objects\
                           .filter(predicate_uuid=contain_pred,
                                   object_uuid=child_uuid)\
                           .delete()
        new_ass = Assertion()
        new_ass.uuid = parent_uuid
        new_ass.subject_type = 'subjects'
        new_ass.project_uuid = self.project_uuid
        new_ass.source_id = self.source_id
        new_ass.obs_node = '#contents-' + str(1)
        new_ass.obs_num = 1
        new_ass.sort = 1
        new_ass.visibility = 1
        new_ass.predicate_uuid = contain_pred
        new_ass.object_type = 'subjects'
        new_ass.object_uuid = child_uuid
        new_ass.save()
    
    def db_create_temporary_root_subject(self):
        """ makes a temporary root subject for the whole import
            makes it easier to move subjects into hiearchies later
        """
        if not isinstance(self.root_subject_label, str):
            self.root_subject_label = self.source_id + '-root'
        if not isinstance(self.root_subject_context, str):
            self.root_subject_context = self.root_subject_label
        if not isinstance(self.root_subject_uuid, str):
            man_objs = Manifest.objects\
                               .filter(label=self.root_subject_label,
                                       class_uri=self.root_subject_class,
                                       project_uuid=self.project_uuid)[:1]
            if len(man_objs) > 0:
                self.root_subject_uuid = man_objs[0].uuid
            else:
                # did not find a root subject, so make one
                sup_dict = {}
                sup_dict[self.reconcile_key] = self.root_subject_sup_id
                root_uuid = GenUUID.uuid4()
                root_uuid = str(root_uuid)
                self.root_subject_uuid = root_uuid
                new_sub = Subject()
                new_sub.uuid = self.root_subject_uuid
                new_sub.project_uuid = self.project_uuid
                new_sub.source_id = self.source_id
                new_sub.context = self.root_subject_context
                new_sub.save()
                new_man = Manifest()
                new_man.uuid = self.root_subject_uuid
                new_man.project_uuid = self.project_uuid
                new_man.source_id = self.source_id
                new_man.item_type = 'subjects'
                new_man.repo = ''
                new_man.class_uri = self.root_subject_class
                new_man.label = self.root_subject_label
                new_man.des_predicate_uuid = ''
                new_man.views = 0
                new_man.sup_json = sup_dict
                new_man.save()
    
    def db_save_reconcile_entity_predicates_types(self, act_dir):
        """ saves predicates and type items to the
            Open Context database, and / or reconciles these
            items with previously saved items from the same project
        """
        key = self.oc_config_entity_types
        json_obj = self.fm.get_dict_from_file(key, act_dir)
        if json_obj is None:
            print('Need to 1st generate an attributes file from the ArchEnts!')
            ok = False
        else:
            # we have JSON with dictionary for the entity_types
            self.entity_types = json_obj
            make_entity_types_assertions = False
            for faims_ent_type_id, ent_dict in json_obj.items():
                if isinstance(ent_dict['item_type'], str) \
                   and ent_dict['add_type_as_attribute']:
                    # OK we have some items that need entity types made as
                    # a descriptive attribute
                    make_entity_types_assertions = True
                    break
            if make_entity_types_assertions:
                # we have entity_types that need to have a descriptive
                # predicate, so create a new predicate in Open Context
                # to describe entity_types for this project
                sup_dict = LastUpdatedOrderedDict()
                sup_dict[self.reconcile_key] = self.ent_type_pred_sup_id
                pm = PredicateManagement()
                pm.project_uuid = self.project_uuid
                pm.source_id = self.source_id
                pm.sup_dict = sup_dict
                pm.sup_reconcile_key = self.reconcile_key
                pm.sup_reconcile_value = self.ent_type_pred_sup_id
                pred_obj = pm.get_make_predicate(self.FAIMS_ENTITY_TYPE_PREDICATE_LABEL,
                                                 'variable',
                                                 'id')
                if pred_obj is not False:
                    # we reconciled or created the predicate!
                    # now we mint oc_types for all the entity_types
                    predicate_uuid = str(pred_obj.uuid)
                    for faims_ent_type_id, ent_dict in json_obj.items():
                        if isinstance(ent_dict['item_type'], str) \
                           and ent_dict['add_type_as_attribute']:
                            # OK, we have an item entity type to be used as a description
                            sup_dict = LastUpdatedOrderedDict()
                            sup_dict[self.reconcile_key] = faims_ent_type_id
                            tm = TypeManagement()
                            tm.project_uuid = self.project_uuid
                            tm.source_id = self.source_id
                            tm.sup_dict = sup_dict
                            tm.sup_reconcile_key = self.reconcile_key
                            tm.sup_reconcile_value = faims_ent_type_id
                            type_obj = tm.get_make_type_within_pred_uuid(predicate_uuid,
                                                                         ent_dict['label'])
                            if type_obj is not False:
                                # we have reconciled the type!
                                ent_dict['type_uuid'] = str(type_obj.uuid)
                                ent_dict['predicate_uuid'] = predicate_uuid
                                self.entity_types[faims_ent_type_id] = ent_dict
                # now save the results
                self.fm.save_serialized_json(key,
                                             act_dir,
                                             self.entity_types)
        
    def db_save_entity_attributes(self, act_dir, filename='archents.xml'):
        """ saves descriptive attributes for an entity """
        if self.tree is None:
            # we have not imported the XML yet
            self.tree = self.fm.load_xml_file(act_dir, filename)
        if len(self.entities) < 1:
            self.entities = self.fm.get_dict_from_file(self.oc_config_entities,
                                                       act_dir)
        if len(self.entity_types) < 1:
            self.entity_types = self.fm.get_dict_from_file(self.oc_config_entity_types,
                                                           act_dir)
        if len(self.attributes) < 1:
            self.attributes = self.fm.get_dict_from_file(self.oc_config_attributes,
                                                         act_dir)
        if self.tree is not False \
           and self.entities is not None \
           and self.entity_types is not None \
           and self.attributes is not None:
            # we've loaded the data we need!
            print('Have all data needed to make entity descriptions....')
            ent_types = self.tree.xpath('/archents/aenttype')
            for ent_type in ent_types:
                faims_ent_type_id = ent_type.get('aentTypeID')
                faims_ent_type_id = str(faims_ent_type_id)
                if faims_ent_type_id in self.entity_types:
                    # we found the entity type in our configuration
                    ent_type_dict = self.entity_types[faims_ent_type_id]
                    # check if we should make entity type assertions?
                    record_entity_type = self.check_make_entity_type_assertion(ent_type_dict) 
                    xml_entities = ent_type.xpath('archentity')
                    for xml_ent in xml_entities:
                        faims_item_id = xml_ent.xpath('uuid')[0].text
                        if faims_item_id in self.entities:
                            # we found the entity in our saved, reconciled entities
                            subject_uuid = self.entities[faims_item_id]['uuid']
                            subject_type = self.entities[faims_item_id]['item_type']
                            sort_num = 10
                            if record_entity_type: 
                                # make assertion about the entity type
                                fd = FaimsDescription()
                                fd.project_uuid = self.project_uuid
                                fd.soure_id = self.source_id
                                fd.subject_uuid = subject_uuid
                                fd.subject_type = subject_type
                                fd.sort_num = sort_num
                                fd.add_type_description(ent_type_dict['predicate_uuid'],
                                                        ent_type_dict['type_uuid'])
                            props = xml_ent.xpath('properties/property')
                            for prop in props:
                                sort_num += 1
                                prop_id = prop.xpath('attributeid')[0].text
                                if prop_id in self.attributes:
                                    # we found the property attribute
                                    fd = FaimsDescription()
                                    fd.project_uuid = self.project_uuid
                                    fd.soure_id = self.source_id
                                    fd.subject_uuid = subject_uuid
                                    fd.subject_type = subject_type
                                    fd.sort_num = sort_num
                                    fd.attrib_dict = self.attributes[prop_id]
                                    fd.faims_record = self.get_property_record(prop)
                                    vocab_ids = prop.xpath('vocabid')
                                    for vocab_id in vocab_ids:
                                       fd.faims_record_id = vocab_id.text
                                    fd.add_description()
                       
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
        rvocabs = prop.xpath('resolvedvocabname')
        for rvocab in rvocabs:
            record = rvocab.text
        if record is None:
            vocabs = prop.xpath('vocabname')
            for vocab in vocabs:
                record = vocab.text
        if record is None:
            measures = prop.xpath('measure')
            for measure in measures:
                record = measure.text
        return record

    def check_make_entity_type_assertion(self, ent_type_dict):
        """ make an entity type assertion ? """
        make_assertion = False
        if ent_type_dict['add_type_as_attribute']:
            if 'predicate_uuid' in ent_type_dict \
                and 'type_uuid' in ent_type_dict:
                if isinstance(ent_type_dict['predicate_uuid'], str) \
                    and isinstance(ent_type_dict['type_uuid'], str):
                    # we have data we need to make the assertion
                    make_assertion = True
        return make_assertion
