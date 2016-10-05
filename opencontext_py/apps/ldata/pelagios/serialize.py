import os
import codecs
from django.db import models
from django.conf import settings
from rdflib import Graph

class SerizializeRDF():
    """
    saves RDF in different file formats for rapid retrieval
    """
    
    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.act_export_dir = False
        self.pelagios_dir = 'pelagios'
    
    def get_graph_from_file(self, key, use_format='turtle'):
        """ gets the file string
            if the file exists,
        """
        file_name = key + '.ttl'
        g = None
        ok = self.check_exists(file_name)
        if ok:
            path = self.prep_directory(self.pelagios_dir)
            dir_file = path + file_name
            g = Graph()
            str_data = codecs.open(dir_file,
                                   'r',
                                   'utf-8-sig')
            g.parse(str_data, format=use_format)
        return g
    
    def check_exists(self, file_name):
        """ checks to see if a file exists """
        path = self.prep_directory(self.pelagios_dir)
        dir_file = path + file_name
        if os.path.exists(dir_file):
            output = True
        else:
            output = False
        return output
    
    def save_serialized_graph(self, key, g, use_format='turtle'):
        """ saves a data in the appropriate path + file """
        file_name = key + '.ttl'
        path = self.prep_directory(self.pelagios_dir)
        dir_file = path + file_name
        print('save to path: ' + dir_file)
        g.serialize(destination=dir_file, format=use_format)

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
