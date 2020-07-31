import os, sys, shutil
import codecs
import requests
from io import BytesIO
from time import sleep
from internetarchive import get_session, get_item
from django.conf import settings
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile, ManageMediafiles
from opencontext_py.apps.ocitems.manifest.models import Manifest


class BinaryFiles():
    """
    This class has useful methods for managing binary
    media files. It is mainly for copying and moving such files form the file system,
    the localhost, or a remote host over HTTP.
    
    For archiving purposes, it is often needed to stage such files locally.
    """
    
    def __init__(self):
        self.root_export_dir = settings.STATIC_EXPORTS_ROOT
        self.cache_file_dir = 'binary-cache'
        self.full_path_cache_dir = None
        self.do_http_request_for_cache = True  # use an HTTP request to get a file for local caching and saving with a new filename
        self.delay_before_request = .5  # delay a request by .5 seconds so as not to overwhelm a remote server
        self.remote_uri_sub = None  # substitution for a remote uri
        self.local_uri_sub = None  # local substitution uri prefix, so no retrieval from remote
        self.local_filesystem_uri_sub = None  # substitution to get a path to the local file in the file system
        self.pref_tiff_archive = False # Prefer to archive a TIFF archive file
        self.errors = []
    
    def get_cache_full_file(self, json_ld, man_obj):
        """ gets and caches the fill file, saving temporarily to a local directory """
        file_name = None
        slug = man_obj.slug
        file_uri = self.get_archive_fileuri(json_ld)
        if not file_uri:
            import pdb; pdb.set_trace()
            print('Cannot find a file_uri in {} [{}]'.format(man_obj.label, man_obj.uuid))
            return None
        # We found a file uri.
        if isinstance(self.local_uri_sub, str) and isinstance(self.remote_uri_sub, str):
            # get a local copy of the file, not a remote copy
            file_uri = file_uri.replace(self.remote_uri_sub, self.local_uri_sub)
            if 'https://' in self.remote_uri_sub:
                # so we also replace the https or http version of the remote with a local
                alt_remote_sub = self.remote_uri_sub.replace('https://', 'http://')
                file_uri = file_uri.replace(alt_remote_sub, self.local_uri_sub)
        if '.' in file_uri:
            file_ex = file_uri.split('.')
            file_name = slug + '.' + file_ex[-1]
        else:
            file_name = slug
        file_ok = self.get_cache_remote_file_content(file_name, file_uri)
        if not file_ok:
            file_name = False
            error_msg = 'UUID: ' + man_obj.uuid + ' file_uri: ' + file_uri
            error_msg += ' file caching error.'
            self.errors.append(error_msg)
        return file_name
            
    def get_full_fileuri(self, json_ld):
        """ gets the full file uri """
        if not 'oc-gen:has-files' in json_ld:
            return None
        for f_obj in json_ld['oc-gen:has-files']:
            if f_obj['type'] == 'oc-gen:fullfile':
                return f_obj['id']
        return None
    
    def get_archive_fileuri(self, json_ld):
        """ gets the full file uri """
        if not 'oc-gen:has-files' in json_ld:
            return None
        if self.pref_tiff_archive:
            for f_obj in json_ld['oc-gen:has-files']:
                if f_obj['type'] == 'oc-gen:archive':
                    return f_obj['id']
        # no TIFF archive file found, so use the full-file
        return self.get_full_fileuri(json_ld)
                
    def get_cache_remote_file_content(self, file_name, file_uri, act_dir=None):
        """ either uses an HTTP request to get a remote file
            or looks for the file in the file system and copies it within
            the file system
        """
        if not act_dir:
            act_dir = self.cache_file_dir
        if self.do_http_request_for_cache:
            ok = self.get_cache_remote_file_content_http(file_name,
                                                         file_uri,
                                                         act_dir)
        else:
            ok = self.get_cache_remote_file_content_filesystem(file_name,
                                                               file_uri,
                                                               act_dir)
        return ok

    def get_cache_remote_file_content_filesystem(self, file_name, file_uri, act_dir=None):
        """ use the file system to get the file for caching
            and saving with a new filename
        """
        ok = False
        dir_file = self.join_dir_filename(file_name, act_dir)
        if os.path.exists(dir_file):
            # the file already exists, no need to download it again
            print('Already cached: ' + dir_file)
            ok = True
        else:
            print('Cannot find: ' + dir_file)
            print('Need to copy with file-system: ' + file_uri)
            if isinstance(self.remote_uri_sub, str) and isinstance(self.local_filesystem_uri_sub, str):
                original_path = file_uri.replace(self.remote_uri_sub,
                                                 self.local_filesystem_uri_sub)
                if os.path.exists(original_path):
                    try:
                        shutil.copy2(original_path, dir_file)
                        ok = True
                    except:
                        print('Problem copying to: ' + dir_file)
                        ok = False
                else:
                    print('CANNOT FIND ORIGINAL AT: ' + original_path)
        return ok
    
    def get_cache_remote_file_content_http(self, file_name, file_uri, act_dir=None):
        """ uses HTTP requests to get the content of a remote file,
            saves it to cache with the filename 'file_name'
        """
        ok = False
        dir_file = self.join_dir_filename(file_name, act_dir)
        if os.path.exists(dir_file):
            # the file already exists, no need to download it again
            print('Already cached: ' + dir_file)
            ok = True
        else:
            print('Cannot find: ' + dir_file)
            print('Need to download: ' + file_uri)
            if not isinstance(self.local_uri_sub, str):
                # only delay if we're not looking locally for the file
                sleep(self.delay_before_request)
            r = requests.get(file_uri, stream=True)
            if r.status_code == 200:
                with open(dir_file, 'wb') as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
                f.close()
                ok = True
            else:
                # try with different capitalization
                if '.JPG' in file_uri:
                    new_file_uri = file_uri.replace('.JPG', '.jpg')
                elif '.jpg' in file_uri:
                    new_file_uri = file_uri.replace('.jpg', '.JPG')
                else:
                    new_file_uri = None
                if new_file_uri is not None:
                    print('Now trying with different capitalization: ' + new_file_uri)
                    if not isinstance(self.local_uri_sub, str):
                        # only delay if we're not looking locally for the file
                        sleep(self.delay_before_request)
                    r = requests.get(new_file_uri, stream=True)
                    if r.status_code == 200:
                        with open(dir_file, 'wb') as f:
                            for chunk in r.iter_content(1024):
                                f.write(chunk)
                        f.close()
                        ok = True
        return ok
 
    def join_dir_filename(self, file_name, act_dir):
        """ outputs a full path WITH filename """
        if isinstance(act_dir, str):
            path = self.set_check_directory(act_dir)
        elif isinstance(self.full_path_cache_dir, str):
            path = self.full_path_cache_dir
        else:
            path = self.root_export_dir
        dir_file = os.path.join(path, file_name)
        return dir_file

    def check_exists(self, file_name, act_dir):
        """ checks to see if a file exists """
        dir_file = self.join_dir_filename(file_name, act_dir)
        if os.path.exists(dir_file):
            output = True
        else:
            output = False
        return output

    def set_check_directory(self, act_dir):
        """ Prepares a directory to find import GeoJSON files """
        output = False
        if isinstance(self.full_path_cache_dir, str):
            full_dir = self.full_path_cache_dir
            if not os.path.exists(full_dir):
                os.makedirs(full_dir)
        else:
            full_dir = self.root_export_dir
            if isinstance(act_dir, str):
                if len(act_dir) > 0:
                    full_dir = self.root_export_dir + '/' + act_dir
                    full_dir = full_dir.replace('//', '/')
                    if not os.path.exists(full_dir):
                        os.makedirs(full_dir)
        if os.path.exists(full_dir):
            output = full_dir
        return output
    
    def get_directory_files(self, act_dir):
        """ Gets a list of files from a directory """
        files = False
        path = self.set_check_directory(act_dir)
        if os.path.exists(path):
            for dirpath, dirnames, filenames in os.walk(path):
                files = sorted(filenames)
        else:
            print('Cannot find: ' + path)
        return files