import os
import json
import codecs
from django.db import models
from django.conf import settings
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
imp_sj.load_data_in_directory('64-oracle-bone-test')

    """
    def __init__(self):
        self.root_import_dir = settings.STATIC_IMPORTS_ROOT
<<<<<<< HEAD
        self.files_imported = 0
        self.import_recs = 0
        self.error_recs = 0
=======
        self.json_file_count = 0
        self.imported_records = 0
>>>>>>> origin/master

    def load_data_in_directory(self, act_dir):
        """ Loads data in a directory """
        files = self.get_directory_files(act_dir)
        if isinstance(files, list):
            for filename in files:
                print('Reading: ' + filename)
                dir_file = self.root_import_dir + act_dir + '/' + filename
                json_obj = self.load_json_file(dir_file)
                if json_obj is not False:
<<<<<<< HEAD
                    self.import_serialized_json_obj(json_obj)
                    self.files_imported += 1
                    
    def import_serialized_json_obj(self, json_obj):
        """ imports a serialized json object
            to add records to the database
        """
        for obj in serializers.deserialize("json", json_obj):
            # this just saves the object, so as to
            # synch different instances of open context
            try:
                obj.save()
                saved = True
            except:
                saved = False
            if saved:
                self.import_recs += 1
            else:
                self.error_recs += 1
        
=======
                    self.json_file_count += 1
                    self.import_serialized_json_obj(json_obj)

    def import_serialized_json_obj(self, json_obj):
        """ Imports a serialized JSON object """
        for obj in serializers.deserialize("json", json_obj):
            # this just saves it, no matter what.
            obj.save()
            self.imported_records += 1
>>>>>>> origin/master

    def get_directory_files(self, act_dir):
        """ Gets a list of files from a directory """
        files = False
        full_dir = self.root_import_dir + act_dir + '/'
        if os.path.exists(full_dir):
            for dirpath, dirnames, filenames in os.walk(full_dir):
                files = sorted(filenames)
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
