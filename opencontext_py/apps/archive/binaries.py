import os
import shutil
from time import sleep
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.binaryfiles import BinaryFiles

from opencontext_py.apps.archive import metadata as zen_files
from opencontext_py.apps.archive import metadata as zen_metadata
from opencontext_py.apps.archive.zenodo import ArchiveZenodo

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllAssertion,
    AllManifest,
    AllResource,
    AllIdentifier,
)

from opencontext_py.apps.all_items.representations import item


ARCHIVE_FILE_TYPES_KEYS = [
    'oc-gen:archive',
    'oc-gen:fullfile',
    'oc-gen:preview',
    'oc-gen:x3dom-model',
    'oc-gen:x3dom-texture',
    'oc-gen:nexus-3d',
    'oc-gen:hero',
]

ARCHIVE_FILE_TYPES_SLUGS = [
    'oc-gen-archive',
    'oc-gen-fullfile',
    'oc-gen-preview',
    'oc-gen-x3dom-model',
    'oc-gen-x3dom-texture',
    'oc-gen-nexus-3d',
    'oc-gen-hero',
]

ARCHIVE_FILE_PREFIXES = {
    'oc-gen:archive': 'az---',
    'oc-gen:fullfile': 'fz---',
    'oc-gen:preview': 'pz---',
    'oc-gen:x3dom-model': 'x3m---',
    'oc-gen:x3dom-texture': 'x3t---',
    'oc-gen:nexus-3d': 'nx3---',
    'oc-gen:hero': 'hz---',
}

ZENODO_FILE_KEYS = [
    'filesize',
    'checksum'
]


def make_archival_file_name(file_type, slug, file_uri):
    """ makes an archival file name based on the
        file type, the slug, and the file_uri
    """
    prefix = ARCHIVE_FILE_PREFIXES.get(file_type, '')
    if '.' in file_uri:
        file_ex = file_uri.split('.')
        extension = file_ex[-1].lower()
        file_name = prefix + slug + '.' + extension
    else:
        file_name = prefix + slug
    return file_name


def get_item_media_files(man_obj):
    """ gets media file uris for archiving """
    files_dict = {}
    if not isinstance(man_obj, AllManifest):
        return files_dict
    res_qs = AllResource.objects.filter(
        item=man_obj,
        resourcetype__slug__in=ARCHIVE_FILE_TYPES_SLUGS,
    ).select_related(
        'resourcetype'
    )
    for res_obj in res_qs:
        file_uri = res_obj.uri
        if '#' in file_uri:
            file_ex = file_uri.split('#')
            file_uri = file_ex[0]
        if not file_uri in files_dict:
            act_dict = {
                'filename': make_archival_file_name(
                    res_obj.resourcetype.item_key,
                    man_obj.slug,
                    file_uri
                ),
                'dc-terms:isPartOf': f'https://{man_obj.uri}',
                'type': [],
            }
            files_dict[file_uri] = act_dict
        files_dict[file_uri]['type'].append(res_obj.resourcetype.item_key)
    return files_dict


def make_act_files_dir_name(part_num, license_uri, project_uuid, files_prefix='files',):
    """ makes a directory name for a given project, license, and directory_number """
    lic_part = license_uri.replace('http://creativecommons.org/publicdomain/', '')
    lic_part = lic_part.replace('https://creativecommons.org/publicdomain/', '')
    lic_part = lic_part.replace('http://creativecommons.org/licenses/', '')
    lic_part = lic_part.replace('https://creativecommons.org/licenses/', '')
    if '/' in lic_part:
        lic_ex = lic_part.split('/')
        lic_part = lic_ex[0]
    act_dir = f'{files_prefix}-{str(part_num)}-{lic_part}---{project_uuid}'
    return act_dir


def record_associated_categories(dir_dict, item_dict):
    """ gets citation information for the specific media item
    """
    path_objs = item_dict.get('oc-gen:has-linked-contexts', [])
    if not len(path_objs):
        return dir_dict
    last_path_obj = path_objs[-1]
    act_type = last_path_obj.get('type')
    if not act_type:
        return dir_dict
    if not dir_dict.get('category'):
        dir_dict['category'] = []
    act_type_found = False
    for old_cat in dir_dict['category']:
        if act_type == old_cat.get('id'):
            old_cat['count'] = old_cat.get('count', 0) + 1
            act_type_found = True
    if not act_type_found:
        cat_obj = {
            'id': act_type,
            'count': 1,
        }
        dir_dict['category'].append(cat_obj)
    return dir_dict


def record_citation_people(dir_dict, item_dict):
    """ gets citation information for the specific media item
    """
    cite_preds = [
        'dc-terms:creator',
        'dc-terms:contributor'
    ]
    for cite_pred in cite_preds:
        if not item_dict.get(cite_pred):
            continue
        if not dir_dict.get(cite_pred):
            # just in case we don't have this citation predicate
            # in the directory dict
            dir_dict[cite_pred] = []
        for cite_obj in item_dict.get(cite_pred, []):
            cite_obj_found = False
            for old_cite in dir_dict.get(cite_pred, []):
                if cite_obj['id'] == old_cite['id']:
                    old_cite['count'] = old_cite.get('count', 0) + 1
                    cite_obj_found = True
                    break
            if not cite_obj_found:
                cite_obj['count'] = 1
                dir_dict[cite_pred].append(cite_obj)
    return dir_dict


def make_save_dir_dict(
        part_num,
        license_uri,
        project_uuid,
        dir_content_file_json='zenodo-oc-files.json'
    ):
    """Makes a dictionary object with metadata about a directory of files"""
    act_dir = make_act_files_dir_name(part_num, license_uri, project_uuid)
    dir_dict = {
        'dc-terms:isPartOf': f'https://opencontext.org/projects/{project_uuid}',
        'dc-terms:license': license_uri,
        'partition-number': part_num,
        'label': act_dir,
        'size': 0,
        'dc-terms:creator': [],
        'dc-terms:contributor': [],
        'category': [],
        'files': [],
    }
    # Save the directory dictionary to a json file
    zen_files.save_serialized_json(act_dir, dir_content_file_json, dir_dict)
    return dir_dict