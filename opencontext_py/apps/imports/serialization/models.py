import pytz
import os
import json
import codecs
from django.db import models
from django.db import transaction
from django.conf import settings
from datetime import datetime
from django.utils import timezone
from django.core import serializers
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.entities.redirects.models import RedirectMapping
from opencontext_py.apps.exports.expfields.models import ExpField
from opencontext_py.apps.exports.exprecords.models import ExpCell
from opencontext_py.apps.exports.exptables.models import ExpTable
from opencontext_py.apps.edit.inputs.profiles.models import InputProfile
from opencontext_py.apps.edit.inputs.fieldgroups.models import InputFieldGroup
from opencontext_py.apps.edit.inputs.inputrelations.models import InputRelation
from opencontext_py.apps.edit.inputs.inputfields.models import InputField
from opencontext_py.apps.edit.inputs.rules.models import InputRule


# Reads Serialized JSON from the Exporter
class ImportSerizializedJSON():
    """

from opencontext_py.apps.imports.serialization.models import ImportSerizializedJSON
imp_sj = ImportSerizializedJSON()
imp_sj.act_import_dir = '/home/ekansa'
imp_sj.data_dirs = [
'0-hybrid-objects-and-intercultural-assemblages-in-colonia',
'38-digital-companion-to-animal-consumption-at-the-monumen',
'38-digital-companion-to-archaeological-animals-of-the-sou',
'38-digital-companion-to-dog-remains-from-the-marismas-nac',
'38-digital-companion-to-inferring-the-archaeological-cont',
'38-digital-companion-to-late-nineteenth-and-early-twentie',
'38-digital-companion-to-molluscs-as-food-in-a-prolific-co',
'38-digital-companion-to-preliminary-analysis-of-the-zooar',
'38-digital-companion-to-the-use-of-animals-by-the-pre-his',
'38-the-archaeology-of-mesoamerican-animals',
'63-hybrid-objects-and-intercultural',
'65-biometrical-database-of-european-aurochs-and-domestic-c',
'66-essays-from-the-edge-of-academia-supplements-to-sushi',
'67-northern-mesopotamian-pig-husbandry-late-neolithic-eba',
'68-zooarchaeology-and-cultural-ecology-of-puesteros-in-sou',
'69-images-documenting-looting-in-the-north-cemetery-at-aby',
'70-middle-and-late-byzantine-glazed-fine-wares',
'71-the-middle-and-late-byzantine-glazed-fine-wares'
]
imp_sj.load_data_in_directories()
imp_sj.load_data_in_directory('64-oracle-bone-test')

from opencontext_py.apps.imports.serialization.models import ImportSerizializedJSON
imp_sj = ImportSerizializedJSON()
imp_sj.load_data_in_directory('24-murlo')

from opencontext_py.apps.imports.serialization.models import ImportSerizializedJSON
imp_sj = ImportSerizializedJSON()
imp_sj.act_import_dir = '/home/ekansa'
imp_sj.load_data_in_directory('97-kp-media')

from opencontext_py.apps.imports.serialization.models import ImportSerizializedJSON
imp_sj = ImportSerizializedJSON()
imp_sj.act_import_dir = '/home/dainst_ekansa'
imp_sj.load_data_in_directory('86-oracle-bones')

    """

    def __init__(self):
        self.root_import_dir = settings.STATIC_IMPORTS_ROOT
        self.act_import_dir = False
        self.files_imported = 0
        self.import_recs = 0
        self.error_recs = 0
        self.data_dirs = []

    def load_data_in_directories(self):
        """ Loads data in a variety of directories """
        for act_dir in self.data_dirs:
            print('*********************')
            print('Working on ' + act_dir)
            print('*********************')
            self.load_data_in_directory(act_dir)

    def load_data_in_directory(self, act_dir):
        """ Loads data in a directory """
        files = self.get_directory_files(act_dir)
        if isinstance(files, list):
            for filename in files:
                print('Reading: ' + filename)
                dir_file = self.define_import_directory(act_dir, filename)
                json_obj = self.load_json_file(dir_file)
                if json_obj is not False:
                    all_ok = self.import_serialized_json_obj(json_obj)
                    if all_ok is False:
                        print('Problem: ' + dir_file)
                    self.files_imported += 1

    def import_serialized_json_obj(self, json_obj):
        """ imports a serialized json object
            to add records to the database
        """
        all_ok = True
        try:
            with transaction.atomic():
                for obj in serializers.deserialize("json", json_obj):
                    # this just saves the object, so as to
                    # synch different instances of open contex
                    if hasattr(obj, 'object'):
                        # object_dict = obj.object.__dict__
                        # print(str(object_dict))
                        if hasattr(obj.object, 'data_date'):
                            if isinstance(obj.object.data_date, datetime):
                                if timezone.is_naive(obj.object.data_date):
                                    obj.object.data_date = pytz.utc.localize(obj.object.data_date)
                        if hasattr(obj.object, 'created'):
                            if isinstance(obj.object.created, datetime):
                                if timezone.is_naive(obj.object.created):
                                    obj.object.created = pytz.utc.localize(obj.object.created)
                        if hasattr(obj.object, 'updated'):
                            if isinstance(obj.object.updated, datetime):
                                if timezone.is_naive(obj.object.updated):
                                    obj.object.updated = pytz.utc.localize(obj.object.updated)
                    obj.save()
        except Exception as e:
            print('Problem: ' + str(e))
            all_ok = False
        return all_ok

    def get_directory_files(self, act_dir):
        """ Gets a list of files from a directory """
        files = False
        full_dir = self.define_import_directory(act_dir)
        if os.path.exists(full_dir):
            for dirpath, dirnames, filenames in os.walk(full_dir):
                files = sorted(filenames)
        else:
            print('Cannot find: ' + full_dir)
        return files

    def load_json_file(self, dir_file):
        """ Loads a file and parse it into a
            json object
        """
        json_obj = False
        if os.path.exists(dir_file):
            try:
                json_obj = json.load(codecs.open(dir_file,
                                                 'r',
                                                 'utf-8-sig'))
            except:
                print('Cannot parse as JSON: ' + dir_file)
                json_obj = False
        return json_obj

    def define_import_directory(self, act_dir, filename=''):
        """ defines the import directory
            to be the default or somewhere else on the file system
        """
        if self.act_import_dir is not False:
            full_dir = self.act_import_dir + '/' + act_dir
        else:
            full_dir = self.root_import_dir + '/' + act_dir
        if len(filename) > 0:
            full_dir += '/' + filename
        full_dir.replace('//', '/')
        return full_dir
