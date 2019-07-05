import json
import os, sys, shutil
import codecs
import requests
from io import BytesIO
from time import sleep
from django.db import models
from django.conf import settings
from collections import OrderedDict
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.binaryfiles import BinaryFiles
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.ocitem.generation import OCitem
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ldata.linkannotations.licensing import Licensing
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile, ManageMediafiles


class ArchiveFiles():
    """
    saves JSON and media files for deposit into external repositories
    
    
    """
    
    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.working_dir = 'archives'
        self.proj_manifest_objs = {}
        self.saved_uuids = []
        self.error_uuids = []
        self.do_http_request_for_cache = True  # use an HTTP request to get a file for local caching and saving with a new filename
        self.remote_uri_sub = None  # substitution for a remote uri
        self.local_uri_sub = None  # local substitution uri prefix, so no retrieval from remote
        self.local_filesystem_uri_sub = None  # substitution to get a path to the local file in the file system
        self.bin_file_obj = BinaryFiles()
    
    def save_project_data(self, project_uuid):
        """ saves data associated with a project """
        man_objs = Manifest.objects\
                           .filter(project_uuid=project_uuid)\
                           .exclude(item_type='tables')\
                           .order_by('sort')[:30]
        for man_obj in man_objs:
            # archive the files
            self.save_item_and_rels(man_obj.uuid,
                                    project_uuid,
                                    True)

    def save_item_and_rels(self, uuid, archive_proj_uuid, do_rels=True):
        """ saves an item based on its uuid,
            and optionally ALSO saves related items
            
            archive_proj_uuid is the uuid for the project we're
            archiving now. An item in that archive may actuall come
            from another project, but is included in this archive
            because of a dependency through referencing (context, people)
            
        """
        if uuid in self.saved_uuids:
            # we have a memory of this already saved
            item_saved = True
        else:
            item_saved = False
            archive_proj = self.get_proj_manifest_obj(archive_proj_uuid)
            oc_item = OCitem(True)  # use cannonical URIs
            exists = oc_item.check_exists(uuid)
            if exists and archive_proj is not None:
                act_dirs = []
                act_dirs.append(archive_proj.slug)  # the archive project slug is the directory
                item_type = oc_item.manifest.item_type
                if item_type != 'projects':
                    act_dirs.append(item_type)  # put items of different types into different directories
                file_name = oc_item.manifest.uuid + '.json'
                file_exists = self.check_exists(act_dirs, file_name)
                if file_exists:
                    # we already saved it
                    item_saved = True
                else:
                    # we have not made the file, so make it now
                    oc_item.generate_json_ld()
                    self.save_serialized_json(act_dirs,
                                              file_name,
                                              oc_item.json_ld)
                    new_file_exists = self.check_exists(act_dirs, file_name)
                    if new_file_exists:
                        # we saved the new file!
                        item_saved = True
                        self.saved_uuids.append(oc_item.manifest.uuid)
                    else:
                        # we have a problem with this file
                        item_saved = False
                        print('ERROR! Did not save: ' + oc_item.manifest.uuid)
                        self.error_uuids.append(oc_item.manifest.uuid)
                    if do_rels:
                        rel_uuids = self.get_related_uuids(oc_item.json_ld)
                        for rel_uuid in rel_uuids:
                            rel_saved = self.save_item_and_rels(rel_uuid,
                                                                archive_proj_uuid,
                                                                False)
        return item_saved   
    
    def get_related_uuids(self, item_dict):
        """ gets uuids for the contexts,
            and people associated with an item
            this insures that the data dump will include
            JSON-LD files for all relevant contexts,
            and people even from another project
        """
        pred_keys = [
            'oc-gen:has-path-items',
            'oc-gen:has-linked-context-path',
            'dc-terms:contributor',
            'dc-terms:creator',
            'dc-terms:isPartOf'
        ]
        uuids = self.get_predicate_uuids(pred_keys,
                                         item_dict)
        return uuids
    
    def get_predicate_uuids(self, pred_keys, item_dict):
        """ gets uuids for open context items
            for a given LIST of predicate keys for an item dict
        """
        uuids = []
        if not isinstance(pred_keys, list):
            pred_keys = [pred_keys]
        if isinstance(item_dict, dict):
            for pred_key in pred_keys:
                items = item_dict.get(pred_key, [])
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict) or not 'id' in item:
                        continue
                    uuid = URImanagement.get_uuid_from_oc_uri(item['id'])
                    if not uuid or uuid in uuids:
                        continue
                    uuids.append(uuid)
        return uuids
    
    def get_proj_manifest_obj(self, project_uuid):
        """ gets the manifest object for a given project """
        if project_uuid not in self.proj_manifest_objs:
            try:
                man_obj = Manifest.objects.get(uuid=project_uuid)
            except Manifest.DoesNotExist:
                man_obj = None
            self.proj_manifest_objs[project_uuid] = man_obj
        else:
            man_obj = self.proj_manifest_objs[project_uuid]
        return man_obj
    
    def prep_bin_file_obj(self):
        """ prepares a binary file class object to manage the
            retrieval and caching of binary files
        """
        if self.bin_file_obj is None:
            self.bin_file_obj = BinaryFiles()
            self.bin_file_obj.cache_file_dir = self.cache_file_dir
            self.bin_file_obj.do_http_request_for_cache = self.do_http_request_for_cache
            self.bin_file_obj.remote_uri_sub = self.remote_uri_sub
            self.bin_file_obj.local_uri_sub = self.local_uri_sub
            self.bin_file_obj.local_filesystem_uri_sub = self.local_filesystem_uri_sub

    def check_exists(self, act_dirs, file_name):
        """ checks to see if a file exists """
        dir_file = self.make_full_path_filename(act_dirs, file_name)
        if os.path.exists(dir_file):
            output = True
        else:
            output = False
        return output
    
    def make_full_path_filename(self, act_dirs, file_name):
        """ makes a full filepath and file name string """
        path = self.prep_directory(act_dirs, False)
        dir_file = os.path.join(path, file_name)
        return dir_file
    
    def save_serialized_json(self, act_dirs, file_name, dict_obj):
        """ saves a data in the appropriate path + file """
        path = self.prep_directory(act_dirs)
        dir_file = os.path.join(path, file_name)
        json_output = json.dumps(dict_obj,
                                 indent=4,
                                 ensure_ascii=False)
        file = codecs.open(dir_file, 'w', 'utf-8')
        file.write(json_output)
        file.close()
    
    def get_dict_from_file(self, act_dirs, file_name):
        """ gets the file string
            if the file exists,
        """
        json_obj = None
        path = self.prep_directory(act_dirs, False)
        dir_file = os.path.join(path, file_name)
        if os.path.exists(dir_file):
            try:
                json_obj = json.load(codecs.open(dir_file,
                                                 'r',
                                                 'utf-8-sig'),
                                     object_pairs_hook=OrderedDict)
            except:
                print('Cannot parse as JSON: ' + dir_file)
                json_obj = False
        return json_obj
    
    def get_directory_size(self, act_dirs):
        """ returns a list of directories contained in a list
            of act_dirs
        """
        src_dir = self.prep_directory(act_dirs, False)
        total_size = self.get_directory_size_path(src_dir)
        return total_size
    
    def get_directory_size_path(self, path):
        """ gets directory size recusively, but from a path
            not from a list of act_dirs
        """
        if isinstance(path, str):
            total_size = os.path.getsize(path)
            for item in os.listdir(path):
                itempath = os.path.join(path, item)
                if os.path.isfile(itempath):
                    total_size += os.path.getsize(itempath)
                elif os.path.isdir(itempath):
                    total_size += self.get_directory_size_path(itempath)
        else:
            total_size = None
        return total_size

    def get_sub_directories(self, act_dirs):
        """ returns a list of directories contained in a list
            of act_dirs
        """
        src_dir = self.prep_directory(act_dirs, False)
        output = []
        for dirpath, dirnames, filenames in os.walk(src_dir):
            output = dirnames
            break
        return output

    def prep_directory(self, act_dirs, make_dir=True):
        """ Prepares a directory to receive export files """
        output = False
        if not isinstance(act_dirs, list):
            act_dirs = [act_dirs]
        act_dirs = [self.working_dir] + act_dirs
        full_path = self.root_export_dir
        for act_dir in act_dirs:
            full_path = full_path + '/' + act_dir
            full_path = full_path.replace('//', '/')
            if not os.path.exists(full_path) and make_dir:
                print('Prepared directory: ' + str(full_path))
                os.makedirs(full_path)
        if os.path.exists(full_path):
            output = full_path
        return output
