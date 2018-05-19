import json
import os
import codecs
from collections import OrderedDict
from django.db import models
from django.conf import settings


class FileCacheJSON():
    """
    saves JSON for rapid retrieval, because other file caches
    often get evictions
    """
    
    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.act_export_dir = False
        self.working_dir = 'search'
    
    def get_dict_from_file(self, key):
        """ gets the file string
            if the file exists,
        """
        file_name = key + '.json'
        json_obj = None
        ok = self.check_exists(file_name)
        if ok:
            path = self.prep_directory(self.working_dir)
            dir_file = path + file_name
            try:
                json_obj = json.load(codecs.open(dir_file,
                                                 'r',
                                                 'utf-8-sig'),
                                     object_pairs_hook=OrderedDict)
            except:
                print('Cannot parse as JSON: ' + dir_file)
                json_obj = False
        return json_obj
    
    def check_exists(self, file_name):
        """ checks to see if a file exists """
        path = self.prep_directory(self.working_dir)
        dir_file = path + file_name
        if os.path.exists(dir_file):
            output = True
        else:
            print('Cannot find: ' + path)
            output = False
        return output
    
    def save_serialized_json(self, key, dict_obj):
        """ saves a data in the appropriate path + file """
        file_name = key + '.json'
        path = self.prep_directory(self.working_dir)
        dir_file = path + file_name
        print('save to path: ' + dir_file)
        json_output = json.dumps(dict_obj,
                                 indent=4,
                                 ensure_ascii=False)
        file = codecs.open(dir_file, 'w', 'utf-8')
        file.write(json_output)
        file.close()

    def prep_directory(self, act_dir):
        """ Prepares a directory to receive export files """
        output = False
        full_dir = self.root_export_dir + act_dir + '/'
        if self.act_export_dir is not False:
            full_dir = self.act_export_dir + '/' + act_dir
        full_dir.replace('//', '/')
        if not os.path.exists(full_dir):
            print('Prepared directory: ' + str(full_dir))
            os.makedirs(full_dir)
        if os.path.exists(full_dir):
            output = full_dir
        if output[-1] != '/':
            output += '/'
        return output
