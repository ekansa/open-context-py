import os
import requests
from time import sleep
from internetarchive import get_session, get_item
from django.conf import settings

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import models_utils

from opencontext_py.apps.all_items.editorial.archive import file_utilities as fu
from opencontext_py.apps.all_items.editorial.archive import internet_archive as ia

from opencontext_py.apps.etl.general import image_media as imm
from opencontext_py.apps.etl.kobo import media

"""
test

import importlib
from opencontext_py.apps.all_items.models import (
    AllManifest
)
from opencontext_py.apps.all_items.editorial.archive import internet_archive_thumbnails as ia_thumbs
importlib.reload(ia_thumbs)

ia_thumbs.make_preview_thumb_versions_of_ia_full_qs()


"""

ARCHIVE_LOCAL_ROOT_PATH = settings.STATIC_EXPORTS_ROOT
MERRITT_ROOT_URL = 'merritt.cdlib.org'
THUMBNAIL_DIR = 'ia-thumbnails'
PREVIEW_DIR = 'ia-previews'
FULL_DIR = 'ia-full-temp'

CLOUD_URL_PREFIX = 'https://storage.googleapis.com/opencontext-media/internet-archive/'
UPDATE_PROD_DATABASE = False
UPDATE_LOCAL_DATABASE = False
GET_FULLFILE_FROM_IA = True


def ia_service_update():
    r_qs = AllResource.objects.filter(uri__startswith='iiif.archivelab.org')
    for r_obj in r_qs:
        r_obj.meta_json['iiif_orig_uri'] = r_obj.uri
        r_obj.uri = r_obj.uri.replace('iiif.archivelab.org/', 'iiif.archive.org/')
        r_obj.save(using='prod')
        r_obj.save(using='default')
        print(f'Saved {r_obj.item.label} [{r_obj.item.uuid}]: https://{r_obj.uri}')



def make_full_path_filename(path, filename):
    """ makes a full filepath and file name string """
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, filename)


def make_file_uri_from_cache_path(cache_path, check_exists=True):
    if not cache_path:
        return None
    file_uri = None
    for act_dir in [THUMBNAIL_DIR, PREVIEW_DIR, FULL_DIR,]:
        if not act_dir in cache_path:
            continue
        if check_exists and not os.path.exists(cache_path):
            # We decided to check if the file exists, and it doesn't
            continue
        filename = os.path.basename(cache_path)
        file_uri = AllManifest().clean_uri(f'{CLOUD_URL_PREFIX}{act_dir}/{filename}')
    return file_uri


def get_ia_full_file_qs():
    """Gets a queryset of resourc objects for Internet archive full or archive files"""
    file_qs = AllResource.objects.filter(
        uri__startswith=ia.IA_ITEM_BASE_URI,
        resourcetype_id__in=[
            configs.OC_RESOURCE_IA_FULLFILE_UUID,
            configs.OC_RESOURCE_ARCHIVE_UUID,
            configs.OC_RESOURCE_FULLFILE_UUID,
        ],
    ).exclude(
        uri__endswith='.pdf',
    ).exclude(
        uri__endswith='.PDF',
    ).exclude(
        uri__endswith='.zip',
    ).exclude(
        uri__endswith='.ZIP',
    )
    return file_qs


def download_or_get_cached_thumb_preview_paths(file_obj):
    """Downloads or gets the cached paths for a file object"""
    filename = file_obj.uri.split('/')[-1]
    thumb_path = os.path.join(ARCHIVE_LOCAL_ROOT_PATH, THUMBNAIL_DIR)
    thumb_filepath = make_full_path_filename(thumb_path, filename)
    preview_path = os.path.join(ARCHIVE_LOCAL_ROOT_PATH, PREVIEW_DIR)
    preview_filepath = make_full_path_filename(preview_path, filename)
    thumb_variants = [
        thumb_filepath,
        media.replace_extension(thumb_filepath, new_extension='jpg'),
        media.replace_extension(thumb_filepath, new_extension='png'),
    ]
    preview_variants = [
        preview_filepath,
        media.replace_extension(preview_filepath, new_extension='jpg'),
        media.replace_extension(preview_filepath, new_extension='png'),
    ]
    thumb_actual = None
    for thumb_variant in thumb_variants:
        if os.path.exists(thumb_variant):
            thumb_actual = thumb_variant
            break
    preview_actual = None
    for preview_variant in preview_variants:
        if os.path.exists(thumb_variant):
            preview_actual = preview_variant
            break
    if thumb_actual and preview_actual:
        return thumb_actual, preview_actual
    full_path = os.path.join(ARCHIVE_LOCAL_ROOT_PATH, FULL_DIR)
    os.makedirs(full_path, exist_ok=True)
    if not GET_FULLFILE_FROM_IA:
        # Skipping download
        print(f'Skipping download of {file_obj.uri}')
        return None, None
    cache_file_path = fu.get_cache_file(
        file_uri=f'https://{file_obj.uri}',
        cache_filename=filename,
        cache_dir=full_path,
        local_file_dir=None,
        remote_to_local_path_split=None,
    )
    if not cache_file_path:
        # We couldn't get the file, so return None, None
        return None, None
    preview_actual = media.make_new_size_file(
        src_file=cache_file_path,
        new_file=preview_filepath,
        new_width=imm.MAX_PREVIEW_WIDTH,
    )
    print(f'Made preview {preview_actual}')
    thumb_actual = media.make_new_size_file(
        src_file=cache_file_path,
        new_file=thumb_filepath,
        new_width=imm.MAX_THUMBNAIL_WIDTH,
    )
    print(f'Made thumb {thumb_actual}')
    if thumb_actual and preview_actual:
        # Delete the cached full file
        os.remove(cache_file_path)
    return thumb_actual, preview_actual


def update_act_file_obj(
    act_file_obj,
    new_file_uri,
    processed_count=0,
    all_count=0
):
    """Updates a file object with a new file uri"""
    if not act_file_obj:
        return act_file_obj
    if act_file_obj.uri.startswith('storage.googleapis.com'):
        # We've already made this update, so skip it.
        return act_file_obj
    head_ok = None
    head_obj = models_utils.get_web_resource_head_info(uri=new_file_uri)
    if head_obj.get('filesize'):
        # Update the filesize act_file_obj.
        act_file_obj.filesize = head_obj.get('filesize')
        head_ok = True
    else:
        head_ok = False
    if isinstance(head_obj.get('mediatype'), AllManifest):
        # Update the media type of the act_file_obj.
        act_file_obj.mediatype = head_obj.get('mediatype')
    if act_file_obj.uri.startswith(ia.OLD_IA_IIIF_BASE_URI):
        # Store the IIIF uri in the meta_json
        act_file_obj.meta_json['iiif_uri'] = act_file_obj.uri
    if act_file_obj.uri.startswith(MERRITT_ROOT_URL):
        # Store the IIIF uri in the meta_json
        act_file_obj.meta_json['merritt_uri'] = act_file_obj.uri
    act_file_obj.uri = new_file_uri
    if UPDATE_PROD_DATABASE and head_ok:
        act_file_obj.save(using='prod')
    if UPDATE_LOCAL_DATABASE and head_ok:
        act_file_obj.save(using='default')
        print(f'[{processed_count} of {all_count}] Updated file uri (is uploaded: {head_ok}): {act_file_obj.uri}')
    else:
        print(f'[{processed_count} of {all_count}] Testing update of file uri (is uploaded: {head_ok}): {act_file_obj.uri}')
    return act_file_obj


def make_preview_thumb_versions_of_ia_full_obj(file_obj, processed_count=0, all_count=0):
    """Makes a preview and thumbail version of an Internet Archive full file object"""
    thumb_obj = AllResource.objects.filter(
        item=file_obj.item,
        resourcetype_id=configs.OC_RESOURCE_THUMBNAIL_UUID,
    ).exclude(
        uri__startswith=ia.OLD_IA_IIIF_BASE_URI,
    ).exclude(
        uri__startswith=MERRITT_ROOT_URL,
    ).first()
    preview_obj = AllResource.objects.filter(
        item=file_obj.item,
        resourcetype_id=configs.OC_RESOURCE_PREVIEW_UUID,
    ).exclude(
        uri__startswith=ia.OLD_IA_IIIF_BASE_URI,
    ).exclude(
        uri__startswith=MERRITT_ROOT_URL,
    ).first()
    if thumb_obj and preview_obj:
        # we already have a thumb and preview, so return them
        return thumb_obj, preview_obj
    thumb_obj = AllResource.objects.filter(
        item=file_obj.item,
        resourcetype_id=configs.OC_RESOURCE_THUMBNAIL_UUID,
        uri__startswith='storage.googleapis.com',
    ).first()
    preview_obj = AllResource.objects.filter(
        item=file_obj.item,
        resourcetype_id=configs.OC_RESOURCE_PREVIEW_UUID,
    uri__startswith='storage.googleapis.com',
    ).first()
    if thumb_obj and preview_obj:
        # we already have updated these items.
        return thumb_obj, preview_obj
    # Make sure we have local copies of the thumbnail and preview versions of this file
    thumb_filepath, preview_filepath = download_or_get_cached_thumb_preview_paths(file_obj)
    thumb_uri = make_file_uri_from_cache_path(thumb_filepath)
    preview_uri = make_file_uri_from_cache_path(preview_filepath)
    if not thumb_uri or not preview_uri:
        # We couldn't make a file uri for the thumb or preview, so return None, None
        return None, None
    thumb_obj = AllResource.objects.filter(
        item=file_obj.item,
        resourcetype_id=configs.OC_RESOURCE_THUMBNAIL_UUID,
        uri__startswith=ia.OLD_IA_IIIF_BASE_URI,
    ).first()
    if thumb_obj:
        thumb_obj = update_act_file_obj(
            act_file_obj=thumb_obj,
            new_file_uri=thumb_uri,
            processed_count=processed_count,
            all_count=all_count,
        )
    preview_obj = AllResource.objects.filter(
        item=file_obj.item,
        resourcetype_id=configs.OC_RESOURCE_PREVIEW_UUID,
        uri__startswith=ia.OLD_IA_IIIF_BASE_URI,
    ).first()
    if preview_obj:
        preview_obj = update_act_file_obj(
            act_file_obj=preview_obj,
            new_file_uri=preview_uri,
            processed_count=processed_count,
            all_count=all_count,
        )
    return thumb_obj, preview_obj


def make_preview_thumb_versions_of_ia_full_qs():
    file_qs = get_ia_full_file_qs()
    all_count = file_qs.count()
    processed_count = 0
    i = 0
    for file_obj in file_qs:
        i += 1
        print(f'[{processed_count} of {all_count}]--({i})------------------------------------------')
        thumb_obj, preview_obj = make_preview_thumb_versions_of_ia_full_obj(
            file_obj,
            processed_count=processed_count,
            all_count=all_count,
        )
        if thumb_obj and preview_obj:
            processed_count += 1
            pass
        else:
            print(f'[{processed_count} of {all_count}] Pending: {file_obj.uri}')