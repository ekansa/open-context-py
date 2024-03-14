import copy
import os
import shutil
import requests
from time import sleep

from django.conf import settings


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllResource,
)

from opencontext_py.libs.generalapi import GeneralAPI

"""
test

import importlib
from opencontext_py.apps.all_items.models import (
    AllManifest
)
from opencontext_py.apps.all_items.editorial.archive import file_utilities as fu
importlib.reload(fu)


cache_dir = '/home/ekansa/ia-files/'
file_uri = 'https://artiraq.org/static/opencontext/kahramanmaras-survey/full/km-136.pdf'
local_file_dir = '/home/ekansa/github/open-context-py/static/imports/kahramanmaras-survey'
remote_to_local_path_split = 'kahramanmaras-survey'
ia_1 = fu.get_cache_file(
    file_uri,
    'test-km-136.pdf',
    local_file_dir,
    remote_to_local_path_split,
)

"""


DELAY_BEFORE_REQUEST = 0.5



def check_make_directory(full_dir_path):
    """Checks and if missing creates a directory for files"""
    if not os.path.exists(full_dir_path):
        os.makedirs(full_dir_path)
    if os.path.exists(full_dir_path):
        return full_dir_path
    return None


def get_full_file_uri(rep_dict):
    """Gets the full file uri from a rep_dict

    :param dict rep_dict: A JSON-LD representation dict for a
        media item.

    returns str (file_uri)
    """
    if not rep_dict.get('oc-gen:has-files'):
        return None
    for f_obj in rep_dict.get('oc-gen:has-files'):
        if f_obj.get('type') == 'oc-gen:fullfile':
            return f_obj.get('id')
    return None


def get_best_archive_file_uri(rep_dict):
    """Gets the best file uri for archiving

    :param dict rep_dict: A JSON-LD representation dict for a
        media item.

    returns str (file_uri)
    """
    if not rep_dict.get('oc-gen:has-files'):
        return None
    for f_obj in rep_dict.get('oc-gen:has-files'):
        if f_obj.get('type') == 'oc-gen:archive':
            return f_obj.get('id')
    # No Archive file found, so use the full-file
    return get_full_file_uri(rep_dict)


def get_cache_file(
    file_uri,
    cache_filename,
    cache_dir,
    local_file_dir=None,
    remote_to_local_path_split=None,
    redirect_ok=True
):
    """Locally caches a file to a cache directory

    :param str file_uri: The file uri (with http:// or https://) for the remote file.
    :param str cache_filename: The name of the file when cached locally
    :param str cache_dir: The path for the local file cache directory
    :param str local_file_dir: The directory path if the remote file is already stored locally
        in a directory structure that mimics a path structure in the remote file_uri
    :param str remote_to_local_path_split: A string used to split the file_uri at a point
        where the remote file_uri path maps to the current file in the local_file_dir
    """
    cache_dir = check_make_directory(cache_dir)
    if not cache_dir:
        raise ValueError(f'No cache directory {cache_dir}')
    cache_file_path = os.path.join(cache_dir, cache_filename)
    if os.path.exists(cache_file_path):
        # We have already cached this file!
        return cache_file_path
    local_file_path = None
    if local_file_dir and remote_to_local_path_split:
        if remote_to_local_path_split in file_uri:
            uri_ex = file_uri.split(remote_to_local_path_split)
            local_file_path = os.path.join(local_file_dir, uri_ex[-1])
    if local_file_path:
        if not os.path.exists(local_file_path):
            print(f'No file at local_file_path: {local_file_path}')
            local_file_path = None
    if local_file_path:
        local_ok = None
        try:
            shutil.copy2(local_file_path, cache_file_path)
            local_ok = True
        except:
            print(f'Problem copying  {local_file_path} to {cache_file_path}')
            local_ok = False
        if local_ok:
            # We succeeded in copying the local file to the cache_file_path
            print(f'Successfully copied locally from {local_file_path}')
            return cache_file_path
    if '127.0.0.1' not in file_uri:
        # Delay if we're not requesting from the local host
        sleep(DELAY_BEFORE_REQUEST)
    gapi = GeneralAPI()
    r = requests.get(file_uri, stream=True, headers=gapi.client_headers)
    if (
        (r.status_code == requests.codes.ok)
        or
        (redirect_ok and r.status_code >= 300 and r.status_code <= 310)
    ):
        with open(cache_file_path, 'wb') as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
        f.close()
        print(f'Successfully copied from remote {file_uri}')
        return cache_file_path
    print(f'Failure to retrieve {file_uri}')
    return None
