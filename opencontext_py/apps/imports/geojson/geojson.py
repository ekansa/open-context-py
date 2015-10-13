import os
import json
import codecs
from collections import OrderedDict
from django.db import models
from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event


class GeoJSONimport():
    """ Loads GeoJSON files for import

from opencontext_py.apps.imports.geojson.geojson import GeoJSONimport
gimp = GeoJSONimport()
gimp.load_into_importer = True
gimp.project_uuid = '5A6DDB94-70BE-43B4-2D5D-35D983B21515'
gimp.class_uri = 'oc-gen:cat-feature'
gimp.process_features_in_file('OpenContext_GeoJSON', 'Interpreted_Architecture_KKT.geojson')
    """

    def __init__(self):
        self.root_import_dir = settings.STATIC_IMPORTS_ROOT
        self.project_uuid = False
        self.source_id = False
        self.class_uri = False
        self.load_into_importer = False
        self.properties = False
        self.props_config = [{'prop': 'FeatureNum',
                              'prefix': 'Feat. ',
                              'data_type': 'xsd:integer'}]

    def get_props_from_features(self, features):
        """ gets a list of all properties used with the features """
        self.properties = []
        for feature in features:
            if 'properties' in feature:
                props = feature['properties']
                for prop_key, val in props.items():
                    if prop_key not in self.properties:
                        self.properties.append(prop_key)

    def load_feature_into_importer(self, feature):
        """ Loads a feature into the importer with properties as different
            'fields' in the import
        """
        pass

    def add_feature_to_existing_items(self, feature):
        """ Process a feature to extract geospatial
            object. It will:
            (1) Find the appropriate item in the manifest table
            (2) Adds a record in the geospace table
        """
        if 'properties' in feature:
            props = feature['properties']
            for check_prop in self.props_config:
                if check_prop['prop'] in props:
                    prop_id = str(props[check_prop['prop']])
                    if check_prop['data_type'] == 'xsd:integer':
                        try:
                            num_id = float(prop_id)
                        except:
                            num_id = False
                        if num_id is not False:
                            try:
                                int_id = int(num_id)
                            except:
                                int_id = False
                            if int_id is not False:
                                prop_id = str(int_id)
                    prop_id = check_prop['prefix'] + prop_id
                    print('Checking to find: ' + prop_id)
                    man_objs = Manifest.objects\
                                       .filter(label=prop_id,
                                               project_uuid=self.project_uuid,
                                               class_uri=self.class_uri)[:1]
                    if len(man_objs):
                        uuid = str(man_objs[0].uuid)
                    else:
                        uuid = False
                    if uuid is not False:
                        # found a uuid for this item!
                        print('Found: ' + prop_id + ' is ' + uuid)

    def process_feature(self, feature):
        """ Process a feature to extract geospatial
            object. It will:
            (1) Find the appropriate item in the manifest table
            (2) Adds a record in the geospace table
        """
        if self.load_into_importer:
            # the features contain data that need schema mapping
            # use the importer
            self.load_feature_into_importer(feature)
        else:
            # don't create new items (in the manifest)
            # just try to match the feature to existing manifest items
            self.add_feature_to_existing_items(feature)

    def process_features_in_file(self, act_dir, filename):
        """ Processes a file to extract geojson features
            for processing each feature
        """
        json_obj = self.load_json_file(act_dir, filename)
        if json_obj is not False:
            if 'features' in json_obj:
                if self.load_into_importer:
                    self.get_props_from_features(json_obj['features'])
                for feature in json_obj['features']:
                    self.process_feature(feature)

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
