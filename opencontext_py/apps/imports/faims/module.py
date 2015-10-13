import os
import json
import codecs
import datetime
from dateutil.parser import parse
import uuid as GenUUID
from dateutil.parser import parse
from collections import OrderedDict
from django.db import models
from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event


class ModuleImport():
    """ Loads project metadata from the module.settings
        file, which is a JSON encoded-file that describes
        a FAIMS project

from opencontext_py.apps.imports.faims.module import ModuleImport
faims_m = ModuleImport()

    """

    def __init__(self):
        self.root_import_dir = settings.STATIC_IMPORTS_ROOT
        self.project_uuid = False
        self.source_id = False
        self.attributes = {'version': {'label': 'Version',
                                       'data_type': 'xsd:string'},
                           'season': {'label': 'Season',
                                      'data_type': 'xsd:string'}}

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
        if os.path.exists(full_dir):
            output = full_dir
        return output

    def load_json_file(self, act_dir, filename):
        """ Loads a file and parse it into a
            json object
        """
        json_obj = False
        dir_file = self.set_check_directory(act_dir) + filename
        if os.path.exists(dir_file):
            self.source_id = filename
            fp = open(dir_file, 'r')
            # keep keys in the same order as the original file
            json_obj = json.load(fp, object_pairs_hook=OrderedDict)
        return json_obj
