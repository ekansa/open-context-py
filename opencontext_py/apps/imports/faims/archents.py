import os
import codecs
import uuid as GenUUID
import re
import datetime
from dateutil.parser import parse
from lxml import etree
from django.db import models
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.imports.fields.datatypeclass import DescriptionDataType


class ArchEntsImport():
    """ Loads GeoJSON files for import

from opencontext_py.apps.imports.faims.archents import ArchEntsImport
faims_ents = ArchEntsImport()
faims_ents.get_entity_types('PAZC2015', 'archents.xml')
tree = faims_ents.load_xml_file('PAZC2015', 'archents.xml')

from opencontext_py.apps.imports.faims.archents import ArchEntsImport
faims_ents = ArchEntsImport()
faims_ents.process_archents('faims-test-geo', 'archents.xml')

Note: in the element <freetext> a user enters an annotation
on an observation.

<formattedIdentifierformattedIdentifier> is best to use for a label,
but the faims-uuid for the entity is the locally unique id 


    """

    def __init__(self):
        self.root_import_dir = settings.STATIC_IMPORTS_ROOT
        self.tree = None
        self.project_uuid = False
        self.source_id = False
        self.import_persons = {}
        self.load_into_importer = False
        self.attributes = {}

    def process_archents(self, act_dir, filename):
        """ processes the archents file """
        self.tree = self.load_xml_file(act_dir, filename)
        if self.tree is not False:
            self.classify_tree_attributes()

    def get_entity_types(self, act_dir, filename):
        """ gets a list of different entity types in the
            FAIMS xml
        """
        tree = self.load_xml_file(act_dir, filename)
        if tree is not False:
            ent_types = tree.xpath('/archents/aenttype')
            for ent_type in ent_types:
                ents = ent_type.xpath('archentity')
                print(ent_type.get('aentTypeName') + ': ' + ent_type.get('aentTypeID'))
                print('Number of entities: ' + str(len(ents)))
                for entity in ents:
                    self.process_entity(entity)

    def classify_tree_attributes(self):
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
                            self.attributes[prop_id] = dt_class_obj
    
    
    def review_attribute_data_types(self):
        """ review data types for attributes """
        for prop_id, dt_class_obj in self.attributes.items():
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

    def set_check_directory(self, act_dir):
        """ Prepares a directory to find import GeoJSON files """
        output = False
        full_dir = self.root_import_dir + act_dir + '/'
        if not os.path.exists(full_dir):
            os.makedirs(full_dir)
        if os.path.exists(full_dir):
            output = full_dir
        return output

    def load_xml_file(self, act_dir, filename):
        """ Loads a file and parse it into a
            json object
        """
        tree = False
        dir_file = self.set_check_directory(act_dir) + filename
        if os.path.exists(dir_file):
            self.source_id = filename
            tree = etree.parse(dir_file)
        return tree

    
        
        