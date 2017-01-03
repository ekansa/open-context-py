import os
import codecs
import re
import json
from collections import OrderedDict
from lxml import etree
from django.conf import settings


class FileManage():
    """ Loads and saves XML and JSON Files """

    def __init__(self):
        self.root_import_dir = settings.STATIC_IMPORTS_ROOT

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
    
    def get_dict_from_file(self, key, act_dir):
        """ gets the file string
            if the file exists,
        """
        if '.json' not in key:
            file_name = key + '.json'
        json_obj = None
        dir_file = self.set_check_directory(act_dir) + file_name
        try:
            json_obj = json.load(codecs.open(dir_file,
                                             'r',
                                             'utf-8-sig'),
                                 object_pairs_hook=OrderedDict)
        except:
            # print('Cannot parse as JSON: ' + dir_file)
            json_obj = None
        return json_obj
    
    def save_serialized_json(self, key, act_dir, dict_obj):
        """ saves a data in the appropriate path + file """
        if '.json' not in key:
            file_name = key + '.json'
        else:
            file_name = key
        dir_file = self.set_check_directory(act_dir) + file_name
        print('save to path: ' + dir_file)
        json_output = json.dumps(dict_obj,
                                 indent=4,
                                 ensure_ascii=False)
        file = codecs.open(dir_file, 'w', 'utf-8')
        file.write(json_output)
        file.close()
