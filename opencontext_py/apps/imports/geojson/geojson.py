import os
import re
import json
import codecs
import datetime
from unidecode import unidecode
from dateutil.parser import parse
from collections import OrderedDict
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.template.defaultfilters import slugify
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.imports.sources.models import ImportSource
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.create import ImportRecords
from opencontext_py.apps.imports.fields.create import ImportFields
from opencontext_py.apps.imports.sources.create import ImportRefineSource


class GeoJSONimport():
    """ Loads GeoJSON files for import

from opencontext_py.apps.imports.geojson.geojson import GeoJSONimport
gimp = GeoJSONimport()
gimp.load_into_importer = True
gimp.project_uuid = '5A6DDB94-70BE-43B4-2D5D-35D983B21515'
gimp.class_uri = 'oc-gen:cat-feature'
gimp.process_features_in_file('giza-geo', 'Interpreted_Architecture_KKT.geojson')
gimp.feature_count
gimp.source_id
gimp.property_data_types
gimp.property_data_types['OBJECTID']
gimp.property_data_types['FeatureNum']
gimp.property_data_types['EntryDate']


    """

    def __init__(self):
        self.root_import_dir = settings.STATIC_IMPORTS_ROOT
        self.project_uuid = False
        self.label = False
        self.source_id = False
        self.class_uri = False
        self.load_into_importer = False
        self.round_int_properties = True  # make integer values of numeric properties that are integer values if rounded
        self.feature_count = False
        self.properties = False
        self.property_data_types = {}
        self.fields = False
        self.props_config = [{'prop': 'FeatureNum',
                              'prefix': 'Feat. ',
                              'data_type': 'xsd:integer'}]

    def get_props_from_features(self, features):
        """ gets a list of all properties used with the features """
        self.properties = []
        self.feature_count = len(features)
        for feature in features:
            if 'properties' in feature:
                props = feature['properties']
                for prop_key, val in props.items():
                    if prop_key not in self.properties:
                        self.properties.append(prop_key)

    def guess_properties_data_types(self, features):
        """ guesses the property data-types, especially
            important to round decimal values to integers
            to enable use of consident identifiers
        """
        irs = ImportRefineSource()
        property_data_types = {}
        prop_types = ['xsd:boolean',
                      'xsd:integer',
                      'xsd:double',
                      'xsd:date',
                      'other']
        property_data_types = {}
        keys = []
        for prop_key in self.properties:
            act_types = {}
            for prop_type in prop_types:
                act_types[prop_type] = 0
            i = 0
            for feature in features:
                i += 1
                if 'properties' in feature:
                    if prop_key in feature['properties']:
                        val = feature['properties'][prop_key]
                        val_data_type = irs.guess_record_data_type(val)
                        if val_data_type is not False:
                            if val_data_type in act_types:
                                act_types[val_data_type] += 1
                        else:
                            act_types['other'] += 1
            property_data_types[prop_key] = act_types
        # print(str(property_data_types))
        if self.feature_count > 0:
            main_types = {}
            for prop_key, act_prop_types in property_data_types.items():
                max_value = 0
                main_types['data_type'] = 'other'  # default data_type
                for data_type, count in act_prop_types.items():
                    if isinstance(count, int):
                        if count > max_value:
                            max_value = count
                for data_type, count in act_prop_types.items():
                    if isinstance(count, int):
                        if count == max_value and (count / self.feature_count) > .95:
                            # more than 95% of one type, so choose it
                            main_types[prop_key] = data_type
            for prop_key in self.properties:
                if prop_key in property_data_types:
                    self.property_data_types[prop_key] = property_data_types[prop_key]
                if prop_key in main_types:
                    self.property_data_types[prop_key]['data_type'] = main_types[prop_key]

    def save_feature_as_import_records(self, feature):
        """ Saves a feature into the importer with properties as different
            'fields' in the importer
        """
        pass

    def save_properties_as_import_fields(self):
        """ saves the properties as import fields
        """
        imp_f_create = ImportFields()
        imp_f_create.project_uuid = self.project_uuid
        imp_f_create.source_id = self.source_id
        col_index = 0
        new_fields = []
        self.fields = {}
        for prop_key in self.properties:
            col_index += 1
            self.fields[prop_key] = col_index
            imp_f = ImportField()
            imp_f.project_uuid = self.project_uuid
            imp_f.source_id = self.source_id
            imp_f.field_num = col_index
            imp_f.is_keycell = False
            imp_f.obs_num = 1
            imp_f.label = prop_key
            imp_f.ref_name = prop_key
            imp_f.ref_orig_name = prop_key
            imp_f.unique_count = 0
            # now add some field metadata based on other fields data in the project
            imp_f = imp_f_create.check_for_updated_field(imp_f,
                                                         prop_key,
                                                         prop_key,
                                                         True)
            # now add a field_data_type based on the guess made on this GeoJSON property
            if prop_key in self.property_data_types:
                if 'data_type' in self.property_data_types[prop_key]:
                    if self.property_data_types[prop_key]['data_type'] != 'other':
                        imp_f.field_data_type = self.property_data_types[prop_key]['data_type']
            new_fields.append(imp_f)
        # now delete any old
        ImportField.objects.filter(source_id=self.source_id).delete()
        # now save the new import fields
        for imp_f in new_fields:
            print('Saving field: ' + str(unidecode(new_imp_f.label)))
            imp_f.save()

    def save_import_source(self):
        """ saves the import source object """
        output = False
        if self.properties is not False:
            if self.feature_count > 0 \
               and len(self.properties) > 0:
                # delete a previous record if it exists
                ImportSource.objects\
                            .filter(source_id=self.source_id,
                                    project_uuid=self.project_uuid)\
                            .delete()
                irs = ImportRefineSource()
                imp_s = ImportSource()
                imp_s.source_id = self.source_id
                imp_s.project_uuid = self.project_uuid
                imp_s.label = self.label
                imp_s.field_count = len(self.properties)
                imp_s.row_count = self.feature_count
                imp_s.source_type = 'geojson'
                imp_s.is_current = True
                imp_s.imp_status = irs.DEFAULT_LOADING_STATUS
                imp_s.save()
                output = True

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
                    self.guess_properties_data_types(json_obj['features'])
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
            self.make_source_id(act_dir, filename)
            fp = open(dir_file, 'r')
            # keep keys in the same order as the original file
            json_obj = json.load(fp, object_pairs_hook=OrderedDict)
        return json_obj

    def make_source_id(self, act_dir, filename):
        """ makes a source_id by sluggifying the act_dir and filename """
        dir_file = act_dir + ' ' + filename
        dir_file = dir_file.replace('_', ' ')
        self.label = dir_file
        dir_file = dir_file.replace('.', '-')
        raw_slug = slugify(unidecode(dir_file[:40]))
        if raw_slug[0] == '-':
            raw_slug = raw_slug[1:]  # slugs don't end with dashes
        if raw_slug[-1:] == '-':
            raw_slug = raw_slug[:-1]  # slugs don't end with dashes
        raw_slug = re.sub(r'([-]){2,}', r'-', raw_slug)  # slugs can't have more than 1 dash characters
        self.source_id = 'geojson:' + raw_slug
        return self.source_id
