import os
import codecs
import uuid as GenUUID
from lxml import etree
from django.db import models
from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event


class ArchEntsImport():
    """ Loads GeoJSON files for import

from opencontext_py.apps.imports.faims.archents import ArchEntsImport
faims_ents = ArchEntsImport()
faims_ents.get_entity_types('PAZC2015', 'archents.xml')
tree = faims_ents.load_xml_file('PAZC2015', 'archents.xml')
    """

    def __init__(self):
        self.root_import_dir = settings.STATIC_IMPORTS_ROOT
        self.project_uuid = False
        self.source_id = False
        self.import_persons = {}
        self.load_into_importer = False

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
