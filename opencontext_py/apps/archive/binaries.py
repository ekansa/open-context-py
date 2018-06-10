import json
import os, sys, shutil
import codecs
import requests
from io import BytesIO
from time import sleep
from django.db import models
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.binaryfiles import BinaryFiles
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.archive.files import ArchiveFiles
from opencontext_py.apps.archive.metadata import ArchiveMetadata
from opencontext_py.apps.archive.zenodo import ArchiveZenodo
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.ocitem.generation import OCitem
from opencontext_py.apps.ldata.linkannotations.licensing import Licensing
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile, ManageMediafiles


class ArchiveBinaries():
    """
    saves binary media files for deposit into external repositories
    
    """
    
    ARCHIVE_FILE_TYPES = [
        'oc-gen:archive',
        'oc-gen:fullfile',
        'oc-gen:preview',
        'oc-gen:x3dom-model',
        'oc-gen:x3dom-texture',
    ]
    
    ARCHIVE_FILE_PREFIXES = {
        'oc-gen:archive': 'az---',
        'oc-gen:fullfile': 'fz---',
        'oc-gen:preview': 'pz---',
        'oc-gen:x3dom-model': 'x3m---',
        'oc-gen:x3dom-texture': 'x3t---'
    }
    
    ZENODO_FILE_KEYS = [
        'filesize',
        'checksum'
    ]
    
    def __init__(self, do_testing=False):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.working_dir = 'archives'
        self.files_prefix = 'files'
        self.temp_cache_dir = None
        self.exclude_archive_dirs = [] # list of directories to exclude from archiving
        self.max_repo_GB = 35
        self.max_repo_file_count = 1500
        self.GB_to_byte_multiplier = 1000000000
        self.sleep_first = None
        self.errors = []
        self.man_by_proj_lic = LastUpdatedOrderedDict() # dict with project UUID as key, and licences
        self.dir_contents = LastUpdatedOrderedDict()
        self.dir_content_file_json = 'zenodo-oc-files.json'
        self.arch_files_obj = ArchiveFiles()
        self.bin_file_obj = BinaryFiles()
        self.zenodo = ArchiveZenodo(do_testing)
        
    
    def archive_all_project_binaries(self, project_uuid):
        """ archives project binary files in Zenodo """
        project_dirs = self.get_project_binaries_dirs(project_uuid)
        project_dirs = self.sort_project_binaries_dirs(project_dirs)
        if isinstance(self.sleep_first, int):
            print('Pausing execution for seconds: ' + str(self.sleep_first))
            for x in range(self.sleep_first):
                print("Sleep {} of {} seconds...".format(x, self.sleep_first), end="\r")
                sleep(x * .5)
        for archive_dir in project_dirs:
            if archive_dir not in self.exclude_archive_dirs: 
                self.archive_dir_project_binaries(project_uuid, archive_dir)
            else:
                print('Skipping directory: ' + archive_dir)
    
    def archive_dir_project_binaries(self, project_uuid, archive_dir, deposition_id=None):
        """ archives files in for a project in a specific directory
            known as "act dir"
        """
        all_archived = False
        bucket_url = None
        dir_dict = self.arch_files_obj.get_dict_from_file(archive_dir,
                                                          self.dir_content_file_json)
        files_valid = self.validate_archive_dir_binaries(archive_dir,
                                                         dir_dict)
        if files_valid and deposition_id is None:
            # we could find all the files to archive, so let's start archiving!
            # first, start by making an empty deposition container in Zenodo
            deposition_dict = self.zenodo.create_empty_deposition()
            # print('Deposition dict: ' + str(deposition_dict))
            deposition_id = self.zenodo.get_deposition_id_from_metadata(deposition_dict)
            bucket_url = self.zenodo.get_bucket_url_from_metadata(deposition_dict)
            print('Made new deposition with ID: ' + str(deposition_id))
        if not isinstance(bucket_url, str) and deposition_id is not None:
            # get the bucket URL for this deposition
            bucket_url = self.zenodo.get_remote_deposition_bucket_url(deposition_id) 
        if files_valid and deposition_id is not None and isinstance(bucket_url, str):
            # we have found all the files to archive, and we have
            # a ready Zenodo deposition and bucket_url
            print('READY to archive files to ' + str(deposition_id))
            all_archived = True
            full_path_cache_dir = self.arch_files_obj.prep_directory(archive_dir)
            files_to_archive = dir_dict['files']
            i = -1
            num_files = len(files_to_archive)
            for dir_file in files_to_archive:
                i += 1
                new_to_archive = True
                for key in self.ZENODO_FILE_KEYS:
                    if key in dir_file:
                        # we already uploaded this, so skip it
                        new_to_archive = False
                if new_to_archive:
                    # we haven't yet uploaded this particular file
                    full_path_file = os.path.join(full_path_cache_dir, dir_file['filename'])
                    zenodo_resp = self.zenodo.upload_file_by_put(bucket_url,
                                                                 dir_file['filename'],
                                                                 full_path_file)
                    if isinstance(zenodo_resp, dict):
                        # successful upload!
                        show_i = i + 1
                        print('Archived ' + str(show_i) +
                              ' of ' + str(num_files) + ': ' + dir_file['filename'] +
                              ' in ' + str(deposition_id) +
                              ' from: ' + archive_dir)
                        for key in self.ZENODO_FILE_KEYS:
                            if key in zenodo_resp:
                                # this stores some information provided by zenodo about the archived file
                                dir_file[key] = zenodo_resp[key]
                        dir_dict['files'][i] = dir_file  # update the dir file information
                        # now save this, so we have an ongoing record, incase of interruption
                        self.arch_files_obj.save_serialized_json(archive_dir,
                                                                 self.dir_content_file_json,
                                                                 dir_dict)
                    else:
                        # failed to archive the file
                        all_archived = False
                        self.errors.append(dir_file)
        if all_archived:
            # now archive the whole archive contents file
            full_path_file = os.path.join(full_path_cache_dir, self.dir_content_file_json)
            zenodo_resp = self.zenodo.upload_file_by_put(bucket_url,
                                                         self.dir_content_file_json,
                                                         full_path_file)
            if isinstance(zenodo_resp, dict):
                print('Archiving complete after archiving: ' + self.dir_content_file_json + ' in ' + str(deposition_id))
            else:
                # failed to archive the file
                all_archived = False
                self.errors.append(full_path_file)
        if all_archived:
            self.add_project_archive_dir_metadata(project_uuid,
                                                  archive_dir,
                                                  deposition_id)
        return deposition_id
    
    def add_project_archive_dir_metadata(self, project_uuid, archive_dir, deposition_id):
        """ adds metadata about a project to Zenodo deposition by deposition_id """
        ok = None
        dir_dict = self.arch_files_obj.get_dict_from_file(archive_dir,
                                                          self.dir_content_file_json)
        oc_item = OCitem(True)  # use cannonical URIs
        exists = oc_item.check_exists(project_uuid)
        if exists and isinstance(dir_dict, dict):
            oc_item.generate_json_ld()
            proj_dict = oc_item.json_ld
            arch_meta = ArchiveMetadata()
            meta = arch_meta.make_zenodo_proj_media_files_metadata(proj_dict,
                                                                   dir_dict,
                                                                   self.dir_content_file_json)
            ok = self.zenodo.update_metadata(deposition_id, meta)
            if ok is not False:
                ok = True
                print('Metadata created and updated for: ' + str(deposition_id))
        return ok
        
    def validate_archive_dir_binaries(self, archive_dir, dir_dict):
        """ makes sure the all the archive dir actually has all of the files
            it says it has to archive
        """
        if not isinstance(dir_dict, dict):
            print('The archive contents file: ' + self.dir_content_file_json + ' in ' + archive_dir + ' is not parsed as a dict')
            valid = False
        else:
            valid = True
            for dir_file in dir_dict['files']:
                exists = self.arch_files_obj.check_exists(archive_dir, dir_file['filename'])
                if exists is False:
                    # can't find a file claimed to exist in the archive file
                    print('Cannot find file to archive: ' + dir_file['filename'])
                    valid = False
                    self.errors.append(dir_file)
        return valid

    def get_project_binaries_dirs(self, project_uuid):
        """ gets directories associated with a project binary file """
        project_dirs = []
        all_dirs = self.arch_files_obj.get_sub_directories([])
        for act_dir in all_dirs:
            if '---' in act_dir:
                act_ex = act_dir.split('---') 
                if self.files_prefix in act_ex[0] and project_uuid == act_ex[-1]:
                    # the first part of a the name should be like 'files-1-by'
                    # the second part, after the '---' should be the project_uuid
                    project_dirs.append(act_dir)
        return project_dirs
    
    def sort_project_binaries_dirs(self, project_dirs):
        """ sorts the list of project dirs by their number """
        sorted_dirs = None
        if isinstance(project_dirs, list):
            tuple_dirs = []
            for act_dir in project_dirs:
                act_ex = act_dir.split('---')
                first_ex = act_ex[0].split('-')
                num_part = first_ex[1]
                try:
                    dir_index= int(float(num_part))
                except:
                    dir_index = len(project_dirs) + 1
                dir_tuple = (dir_index, act_dir)
                tuple_dirs.append(dir_tuple)
            sorted_dirs = []
            for tuple_dir in sorted(tuple_dirs, key=lambda x: x[0]):
                sorted_dirs.append(tuple_dir[1])
        return sorted_dirs
                
    def save_project_binaries(self, project_uuid):
        """ saves data associated with a project """
        self.get_manifest_grouped_by_license(project_uuid)
        cached_uuids = self.get_uuids_for_cached_media_items(project_uuid)
        len_cached = len(cached_uuids)
        i = 0
        if project_uuid in self.man_by_proj_lic:
            for license_uri, manifest_list in self.man_by_proj_lic[project_uuid].items():
                len_man_list = len(manifest_list)
                for man_obj in manifest_list:
                    # archive the files
                    if man_obj.uuid not in cached_uuids:
                        i += 1
                        print('----------------------------------------')
                        print('Working on new item: ' + str(i) + ' of ' + str(len_man_list) +  ' ('+ str(len_cached) + ' previously done)')
                        ok = self.save_media_files(man_obj, license_uri)
                        print('----------------------------------------')
    
    def get_manifest_grouped_by_license(self, project_uuid):
        """ gets list of distinct licenses for a project_uuid's
            media files
        """
        lic_obj = Licensing()
        license_uris = []
        man_objs = Manifest.objects\
                           .filter(project_uuid=project_uuid,
                                   item_type='media')\
                           .order_by('sort')
        for man_obj in man_objs:
            lic_uri = lic_obj.get_license(man_obj.uuid,
                                          man_obj.project_uuid)
            if man_obj.project_uuid not in self.man_by_proj_lic:
                self.man_by_proj_lic[man_obj.project_uuid] = LastUpdatedOrderedDict()
            if lic_uri not in self.man_by_proj_lic[man_obj.project_uuid]:
                self.man_by_proj_lic[man_obj.project_uuid][lic_uri] = []
                license_uris.append(lic_uri)
            self.man_by_proj_lic[man_obj.project_uuid][lic_uri].append(man_obj)
        return license_uris

    def save_media_files(self, man_obj, license_uri):
        """ saves media files 
            
        """
        ok = False
        if isinstance(man_obj, Manifest):
            # first get metadata about the media item, especially creator + contribution informaiton
            oc_item = OCitem(True)  # use cannonical URIs
            exists = oc_item.check_exists(man_obj.uuid)
            oc_item.generate_json_ld()
            project_uuid = man_obj.project_uuid
            part_num = self.get_current_part_num(license_uri,
                                                 project_uuid)
            act_dir = self.make_act_files_dir_name(part_num,
                                                   license_uri,
                                                   project_uuid)
            dir_dict = self.dir_contents[project_uuid][act_dir]
            # now get the item media files!
            item_files_dict = self.get_item_media_files(man_obj)
            new_files = []
            files_ok = 0
            for file_uri_key, item_file_dict in item_files_dict.items():
                # print('Checking ' + file_uri_key)
                file_name = item_file_dict['filename']
                found = self.check_file_exists_in_all_project_dirs(project_uuid, file_name)
                if found:
                    files_ok += 1
                else:
                    file_name = item_file_dict['filename']
                    for dir_file in dir_dict['files']:
                        if dir_file['filename'] == file_name:
                            found = True
                            files_ok += 1
                            break
                if found is False:
                    # we have a new file to save
                    # Now set the full path to cache the file
                    self.bin_file_obj.full_path_cache_dir = self.arch_files_obj.prep_directory(act_dir)
                    # now retrieve and save the file
                    # check first if there's a file in the temp-cache directory (from previous attempts)
                    ok = self.copy_file_from_temp_cache(act_dir, file_name)
                    if ok is False:
                        ok = self.bin_file_obj.get_cache_remote_file_content(file_name,
                                                                             file_uri_key)
                    if ok:
                        files_ok += 1
                        dir_dict = self.record_associated_categories(dir_dict,
                                                                     oc_item.json_ld)
                        dir_dict = self.record_citation_people(dir_dict, oc_item.json_ld)
                        new_files.append(item_file_dict)
                    else:
                        self.errors.append(item_file_dict)
            dir_dict['size'] = self.arch_files_obj.get_directory_size(act_dir)
            print('Adding files for ' + man_obj.uuid + ' ' + str(len(new_files)))
            dir_dict['files'] += new_files
            self.arch_files_obj.save_serialized_json(act_dir,
                                                     self.dir_content_file_json,
                                                     dir_dict)
            self.dir_contents[project_uuid][act_dir] = dir_dict
            if len(item_files_dict) == files_ok:
                # we have saved the expected number of files for this item
                ok = True
        return ok
    
    def check_file_exists_in_all_project_dirs(self, project_uuid, file_name):
        """ checks if a file already exists in any of the project dirs """
        exists = False
        project_dirs = self.get_project_binaries_dirs(project_uuid)
        for archive_dir in project_dirs:
            exists = self.arch_files_obj.check_exists(archive_dir, file_name)
            if exists:
                print('Found ' + file_name + ' in ' + archive_dir)
                break
        return exists
    
    def copy_file_from_temp_cache(self, archive_dir, file_name):
        """ copies a file from a temp cache if it exists into the
            current archive dir
        """
        copied_ok = False
        if isinstance(self.temp_cache_dir, str):
            original_dir_file = self.arch_files_obj.make_full_path_filename(self.temp_cache_dir,
                                                                            file_name)
            new_dir_file = self.arch_files_obj.make_full_path_filename(archive_dir,
                                                                       file_name)
            original_exists = self.arch_files_obj.check_exists(self.temp_cache_dir,
                                                               file_name)
            if original_exists:
                try:
                    shutil.copy2(original_dir_file , new_dir_file)
                    copied_ok = True
                except:
                    print('Problem copying to: ' + new_dir_file)
                    copied_ok = False
        if copied_ok:
            print('Copied temp-cache file: ' + file_name)
        return copied_ok
    
    def get_current_part_num(self, license_uri, project_uuid):
        """ gets the current directory number based on
            the total size of the contents
        """
        part_num = 1
        if project_uuid not in self.dir_contents:
            self.dir_contents[project_uuid] = LastUpdatedOrderedDict()
            archive_dirs = self.arch_files_obj.get_sub_directories([])
            for archive_dir in archive_dirs:
                if self.files_prefix in archive_dir and \
                   ('---' +  project_uuid) in archive_dir:
                    # we found an existing file archive for this project
                    dir_dict = self.arch_files_obj.get_dict_from_file(archive_dir,
                                                                      self.dir_content_file_json)
                    if isinstance(dir_dict, dict):
                        # we succeeded in loading its existing file list dict
                        self.dir_contents[project_uuid][archive_dir] = dir_dict
        for act_dir_key, dir_dict in self.dir_contents[project_uuid].items():
            if dir_dict['partion-number'] > part_num:
                part_num = dir_dict['partion-number']
        for act_dir_key, dir_dict in self.dir_contents[project_uuid].items():
            if dir_dict['partion-number'] == part_num:
                if dir_dict['size'] >= (self.max_repo_GB * self.GB_to_byte_multiplier):
                    # the highest part_num found has a big size, so increment up to the
                    # next part number
                    part_num += 1
                elif len(dir_dict['files']) >= self.max_repo_file_count:
                    part_num += 1
        act_dir = self.make_act_files_dir_name(part_num, license_uri, project_uuid)
        if act_dir not in self.dir_contents[project_uuid]:
            # make a new dir_dict for this active directory
            self.dir_contents[project_uuid][act_dir] = self.make_dir_dict(part_num,
                                                                          license_uri,
                                                                          project_uuid)
        return part_num
    
    def get_uuids_for_cached_media_items(self, project_uuid):
        """ gets a list of uuids for media items already locally cached """
        uuids = {}
        project_dirs = self.get_project_binaries_dirs(project_uuid)
        for archive_dir in project_dirs:
            dir_dict = self.arch_files_obj.get_dict_from_file(archive_dir,
                                                              self.dir_content_file_json)
            if isinstance(dir_dict, dict):
                if 'files' in dir_dict:
                    for dir_file in dir_dict['files']:
                        if 'dc-terms:isPartOf' in dir_file:
                            uri = dir_file['dc-terms:isPartOf']
                            uri_ex = uri.split('/')
                            uuid = uri_ex[-1]
                            if uuid not in uuids:
                                uuids[uuid] = []
                            if archive_dir not in uuids[uuid]:
                                uuids[uuid].append(archive_dir)
                            if len(uuids[uuid]) > 1:
                                print('UUID: ' + uuid + ' in directories: ' + str(uuids[uuid]))
        return uuids           
        
    def make_dir_dict(self, part_num, license_uri, project_uuid):
        """ """
        act_dir = self.make_act_files_dir_name(part_num, license_uri, project_uuid)
        dir_dict = LastUpdatedOrderedDict()
        dir_dict['dc-terms:isPartOf'] = URImanagement.make_oc_uri(project_uuid,
                                                                  'projects')
        dir_dict['dc-terms:license'] = license_uri
        dir_dict['partion-number'] = part_num
        dir_dict['label'] =  act_dir
        dir_dict['size'] = 0
        dir_dict['dc-terms:creator'] = []
        dir_dict['dc-terms:contributor'] = []
        dir_dict['category'] = []
        dir_dict['files'] = []
        # save it so we can have a directory ready
        self.arch_files_obj.save_serialized_json(act_dir,
                                                 self.dir_content_file_json,
                                                 dir_dict)
        return dir_dict
        
    
    def record_citation_people(self, dir_dict, item_dict):
        """ gets citation information for the specific media item
        """
        cite_preds = [
            'dc-terms:creator',
            'dc-terms:contributor'
        ]
        for cite_pred in cite_preds:
            if cite_pred in item_dict:
                if cite_pred not in dir_dict:
                    # just in case we don't have this citation predicate
                    # in the directory dict
                    dir_dict[cite_pred] = []
                all_cites = []
                old_ids = []
                for old_cite in dir_dict[cite_pred]:
                    for cite_obj in item_dict[cite_pred]:
                        if cite_obj['id'] == old_cite['id']:
                            old_cite['count'] += 1
                            break
                    old_ids.append(old_cite['id'])
                    all_cites.append(old_cite)
                for cite_obj in item_dict[cite_pred]:
                    cite_obj['count'] = 1
                    if cite_obj['id'] not in old_ids:
                        # we have a new reference to someone
                        old_ids.append(cite_obj['id'])
                        all_cites.append(cite_obj)
                dir_dict[cite_pred] = all_cites
        return dir_dict
    
    def record_associated_categories(self, dir_dict, item_dict):
        """ gets citation information for the specific media item
        """
        if 'oc-gen:has-linked-context-path' in item_dict:
            path_obj = item_dict['oc-gen:has-linked-context-path']
            if 'oc-gen:has-path-items' in path_obj:
                if isinstance(path_obj['oc-gen:has-path-items'], list):
                    last_path_obj = path_obj['oc-gen:has-path-items'][-1]
                    if 'type' in last_path_obj:
                        act_type = last_path_obj['type']
                        if 'category' not in dir_dict:
                            # just in case we don't have this predicate
                            # in the directory dict
                            dir_dict['category'] = []
                        all_cats = []
                        old_ids = []
                        for old_cat in dir_dict['category']:
                            if act_type == old_cat['id']:
                                old_cat['count'] += 1
                            old_ids.append(old_cat['id'])
                            all_cats.append(old_cat)
                        if act_type not in old_ids:
                            # we have a new reference to someone
                            cat_obj = LastUpdatedOrderedDict()
                            cat_obj['id'] = act_type
                            cat_obj['count'] = 1
                            old_ids.append(act_type)
                            all_cats.append(cat_obj)
                        dir_dict['category'] = all_cats
        return dir_dict
    
    def get_item_media_files(self, man_obj):
        """ gets media file uris for archiving """
        files_dict = LastUpdatedOrderedDict()
        if isinstance(man_obj, Manifest):
            med_files = Mediafile.objects\
                                 .filter(uuid=man_obj.uuid,
                                         file_type__in=self.ARCHIVE_FILE_TYPES)\
                                 .order_by('-filesize')
            #  print('found files: ' + str(len(med_files)))
            for act_type in self.ARCHIVE_FILE_TYPES:
                for med_file in med_files:
                    if med_file.file_type == act_type:
                        extension = ''
                        frag = None
                        file_uri = med_file.file_uri
                        if '#' in file_uri:
                            file_ex = file_uri.split('#')
                            file_uri = file_ex[0]
                            frag = file_ex[-1]
                        if file_uri not in files_dict:
                            act_dict = LastUpdatedOrderedDict()
                            act_dict['filename'] = self.make_archival_file_name(med_file.file_type,
                                                                                man_obj.slug,
                                                                                file_uri)
                            act_dict['dc-terms:isPartOf'] = URImanagement.make_oc_uri(man_obj.uuid,
                                                                                      man_obj.item_type)
                            act_dict['type'] = []
                            files_dict[file_uri] = act_dict
                        files_dict[file_uri]['type'].append(med_file.file_type)
        return files_dict
    
    def make_archival_file_name(self, file_type, slug, file_uri):
        """ makes an archival file name based on the
            file type, the slug, and the file_uri
        """
        if file_type in self.ARCHIVE_FILE_PREFIXES:
            prefix = self.ARCHIVE_FILE_PREFIXES[file_type]
        else:
            prefix = ''
        if '.' in file_uri:
            file_ex = file_uri.split('.')
            extension = file_ex[-1].lower()
            file_name = prefix + slug + '.' + extension
        else:
            file_name = prefix + slug
        return file_name
    
    def make_act_files_dir_name(self, part_num, license_uri, project_uuid):
        """ makes a directory name for a given project, license, and directory_number """
        lic_part = license_uri.replace('http://creativecommons.org/publicdomain/', '')
        lic_part = lic_part.replace('https://creativecommons.org/publicdomain/', '')
        lic_part = lic_part.replace('http://creativecommons.org/licenses/', '')
        lic_part = lic_part.replace('https://creativecommons.org/licenses/', '')
        if '/' in lic_part:
            lic_ex = lic_part.split('/')
            lic_part = lic_ex[0]
        act_dir = self.files_prefix + '-' +  str(part_num) + '-' + lic_part + '---' + project_uuid
        return act_dir
