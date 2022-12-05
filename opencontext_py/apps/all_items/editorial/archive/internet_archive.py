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
from opencontext_py.apps.all_items.representations import item
from opencontext_py.apps.all_items.representations import citation

from opencontext_py.apps.all_items.editorial.archive import file_utilities as fu


"""
test

import importlib
from opencontext_py.apps.all_items.models import (
    AllManifest
)
from opencontext_py.apps.all_items.editorial.archive import internet_archive as ia
importlib.reload(ia)

uuid = 'ee1ad885-6e18-436b-bab0-8a0f91e722c3'
meta = ia.make_ia_metadata_dict(uuid)


"""

IA_FILE_TYPE = 'oc-gen:ia-fullfile'
IIIF_FILE_TYPE = 'oc-gen:iiif'
UPLOAD_SLEEP_TIME = 0.66

IA_COLLECTION = 'opencontext'
IA_ID_PREFIX = 'opencontext'

IA_ITEM_BASE_URI = 'archive.org/download'
IA_IIIF_BASE_URI = 'iiif.archivelab.org/iiif'

SOURCE_ID = 'ia-archive-script'


def start_ia_session():
    """Starts an internet archive session """
    config = dict(
        s3=dict(
            acccess=settings.INTERNET_ARCHIVE_ACCESS_KEY,
            secret=settings.INTERNET_ARCHIVE_SECRET_KEY
        )
    )
    s = get_session(config=config, debug=True)
    s.access_key = settings.INTERNET_ARCHIVE_ACCESS_KEY
    s.secret_key = settings.INTERNET_ARCHIVE_SECRET_KEY
    return s


def make_ia_metadata_dict_from_objs(man_obj, rep_dict, no_index=None):
    """Makes an Internet Archive metadata dict for an item

    :param AllManifest man_obj: An AllManifest object instance
    :param dict rep_dict: A JSON-LD representation dict for the man_obj item
    :param bool no_index: An optional flag to not index the item in the Internet Archive

    returns dict
    """
    citation_dict = citation.make_citation_dict(rep_dict)
    licence_list = rep_dict.get('dc-terms:license', [{}])
    license_uri = licence_list[0].get('id')
    id_list = []
    for id_type, id_val in citation_dict.get('ids').items():
        id_list.append(f'{id_type}: {id_val}')
    id_str = '; '.join(id_list)
    ia_metadata = {
        'collection': IA_COLLECTION,
        'uri': rep_dict.get('id', f'https://{man_obj.uri}'),
        'title': citation_dict.get('title'),
        'partof': citation_dict.get('part_of_uri', f'https://{settings.CANONICAL_BASE_URL}'),
        'publisher': f'{configs.OPEN_CONTEXT_PROJ_LABEL} (https://{settings.CANONICAL_BASE_URL})',
        'description': (
            f'<div>Media Resource: "{man_obj.label}", '
            f'published by {configs.OPEN_CONTEXT_PROJ_LABEL} at: <a href="https://{man_obj.uri}">https://{man_obj.uri}</a>; '
            f'as part of the <a href="https://{man_obj.project.uri}">{man_obj.project.label}</a> '
            f'data publication. Identified by: {id_str}</div>'
        ),
        'licenseurl': license_uri,
    }
    for id_type, id_val in citation_dict.get('ids').items():
        id_type = id_type.lower()
        ia_metadata[id_type] = id_val
    if str(man_obj.item_class.uuid) == configs.CLASS_OC_IMAGE_MEDIA:
        ia_metadata['mediatype'] = 'image'
    if no_index:
        # add a noindex key so it does not show up in the Internet Archive index
        ia_metadata['noindex'] = True
    return ia_metadata


def make_ia_metadata_dict(uuid=None, man_obj=None, no_index=None):
    """Makes an Internet Archive metadata dict for an item

    :param AllManifest man_obj: An AllManifest object instance
    :param str(UUID) uuid: A UUID for an AllManifest Object instance
    :param bool no_index: An optional flag to not index the item in the Internet Archive

    returns dict
    """
    if man_obj and not uuid:
        uuid = man_obj.uuid
    if not uuid:
        raise ValueError(f'Need an AllManifest object uuid')
    man_obj, rep_dict = item.make_representation_dict(
        subject_id=uuid,
        for_solr_or_html=True,
    )
    if not man_obj:
        raise ValueError(f'Bad uuid: {uuid}, no associated AllManifest instance')
    return make_ia_metadata_dict_from_objs(man_obj, rep_dict, no_index=no_index)


def make_ia_filename(slug, file_uri):
    """Makes a filename for the file to be locally cached then uploaded to the Internet Archive

    :param str slug: The slug identifier for a manifest object item
    :param str file_uri: The file_uri for the item that will be uploaded

    returns str ia_filename
    """
    if not '.' in file_uri:
        return slug
    # Use the extension present in the file_uri
    file_ex = file_uri.split('.')
    ext = file_ex[-1].lower()
    return f'{slug}.{ext}'


def make_ia_metadata_and_ia_cache_file(
    uuid=None,
    man_obj=None,
    no_index=None,
    cache_dir=None,
    local_file_dir=None,
    remote_to_local_path_split=None,
    skip_if_ia_archived=True,
):
    """Creates ia_metadata and caches a file in prep for upload to the Internet Archive

    :param AllManifest man_obj: An AllManifest object instance
    :param str(UUID) uuid: A UUID for an AllManifest Object instance
    :param bool no_index: An optional flag to not index the item in the Internet Archive
    :param str cache_dir: The path for the local file cache directory
    :param str local_file_dir: The directory path if the remote file is already stored locally
        in a directory structure that mimics a path structure in the remote file_uri
    :param str remote_to_local_path_split: A string used to split the file_uri at a point
        where the remote file_uri path maps to the current file in the local_file_dir
    :param bool skip_if_ia_archived: Skip out if the item is already in the Internet Archive.

    returns 4 element tuple (man_obj, ia_metadata, ia_filename, cache_file_path)
    """
    if not cache_dir:
        raise ValueError('Must have a cache dir defined')
    if man_obj and not uuid:
        uuid = man_obj.uuid
    if not uuid:
        raise ValueError(f'Need an AllManifest object uuid')
    ia_res = None
    if skip_if_ia_archived:
        # check to see if this item is already archived.
        ia_res = AllResource.objects.filter(
            item_id=uuid,
            uri__startswith=IA_ITEM_BASE_URI,
        ).first()
    if ia_res:
        # The item is already archived.
       return None, None, None, None, None
    man_obj, rep_dict = item.make_representation_dict(
        subject_id=uuid,
        for_solr_or_html=True,
    )
    if not man_obj:
        raise ValueError(f'Bad uuid: {uuid}, no associated AllManifest instance')
    file_uri = fu.get_best_archive_file_uri(rep_dict)
    if not file_uri:
        # No file to archive for this item.
        return None, None, None, None, None
    ia_metadata = make_ia_metadata_dict_from_objs(man_obj, rep_dict, no_index=no_index)
    ia_filename = make_ia_filename(man_obj.slug, file_uri)
    cache_file_path = fu.get_cache_file(
        file_uri=file_uri,
        cache_filename=ia_filename,
        cache_dir=cache_dir,
        local_file_dir=local_file_dir,
        remote_to_local_path_split=remote_to_local_path_split,
    )
    return man_obj, file_uri, ia_metadata, ia_filename, cache_file_path


def get_or_create_ia_resource_objs(man_obj, file_uri, ia_metadata, item_id, ia_filename):
    source_file_obj = AllResource.objects.filter(
        item=man_obj,
        uri=AllManifest().clean_uri(file_uri)
    ).first()
    if not source_file_obj:
        raise ValueError(f'Cannot find resource object {file_uri} with {man_obj.label} ({man_obj.uuid})')

    ia_file_uri = f'{IA_ITEM_BASE_URI}/{item_id}/{ia_filename}'
    ia_file_rank = AllResource.objects.filter(
        item=man_obj,
        resourcetype_id=configs.OC_RESOURCE_IA_FULLFILE_UUID,
    ).exclude(
        uri=ia_file_uri,
    ).count()
    # Make the new ia_file_res_obj.
    media_file_dict = {
        'item': man_obj,
        'project': man_obj.project,
        'resourcetype_id': configs.OC_RESOURCE_IA_FULLFILE_UUID,
        'source_id': SOURCE_ID,
        'uri': ia_file_uri,
        'filesize': source_file_obj.filesize,
        'mediatype': source_file_obj.mediatype,
        'rank': ia_file_rank,
    }
    ia_file_res_obj, _ = AllResource.objects.get_or_create(
        uuid=AllResource().primary_key_create(
            item_id=man_obj.uuid,
            resourcetype_id=configs.OC_RESOURCE_IA_FULLFILE_UUID,
            rank=ia_file_rank,
        ),
        defaults=media_file_dict,
    )
    # Now do the IIIF file, if we want one.
    if ia_metadata.get('mediatype') == 'image' and not ia_filename.endswith('.pdf'):
        ia_iiif_uri = f'{IA_IIIF_BASE_URI}/{item_id}/info.json'
    else:
        ia_iiif_uri = None
    if not ia_iiif_uri:
        # We're not making a IIIF file from this item.
        return ia_file_res_obj, None

    ia_iiif_rank = AllResource.objects.filter(
        item=man_obj,
        resourcetype_id=configs.OC_RESOURCE_IIIF_UUID,
    ).exclude(
        uri=ia_iiif_uri,
    ).count()
    # Make the new ia_file_res_obj.
    media_file_dict = {
        'item': man_obj,
        'project': man_obj.project,
        'resourcetype_id': configs.OC_RESOURCE_IA_FULLFILE_UUID,
        'source_id': SOURCE_ID,
        'uri': ia_iiif_uri,
        'filesize': 1,
        'mediatype_id': configs.MEDIA_TYPE_JSON_LD_UUID,
        'rank': ia_iiif_rank,
    }
    ia_iiif_res_obj, _ = AllResource.objects.get_or_create(
        uuid=AllResource().primary_key_create(
            item_id=man_obj.uuid,
            resourcetype_id=configs.OC_RESOURCE_IA_FULLFILE_UUID,
            rank=ia_iiif_rank,
        ),
        defaults=media_file_dict,
    )
    return ia_file_res_obj, ia_iiif_res_obj


def ia_archive_media_obj(
    uuid=None,
    man_obj=None,
    no_index=None,
    cache_dir=None,
    local_file_dir=None,
    remote_to_local_path_split=None,
    skip_if_ia_archived=True,
):
    """Archives a media item in the Internet Archive.

    :param AllManifest man_obj: An AllManifest object instance
    :param str(UUID) uuid: A UUID for an AllManifest Object instance
    :param bool no_index: An optional flag to not index the item in the Internet Archive
    :param str cache_dir: The path for the local file cache directory
    :param str local_file_dir: The directory path if the remote file is already stored locally
        in a directory structure that mimics a path structure in the remote file_uri
    :param str remote_to_local_path_split: A string used to split the file_uri at a point
        where the remote file_uri path maps to the current file in the local_file_dir
    :param bool skip_if_ia_archived: Skip out if the item is already in the Internet Archive.

    returns resource objects
    """
    man_obj, file_uri, ia_metadata, ia_filename, cache_file_path = make_ia_metadata_and_ia_cache_file(
        uuid=uuid,
        man_obj=man_obj,
        no_index=no_index,
        cache_dir=cache_dir,
        local_file_dir=local_file_dir,
        remote_to_local_path_split=remote_to_local_path_split,
        skip_if_ia_archived=skip_if_ia_archived,
    )
    if not man_obj or not ia_filename or not ia_metadata or not cache_file_path:
        return None, None
    sleep(UPLOAD_SLEEP_TIME)
    ia_session = start_ia_session()
    item_id = IA_ID_PREFIX + '-' + man_obj.slug
    ia_item = get_item(item_id, archive_session=ia_session, debug=True)
    upload_ok = None
    try:
        r = item.upload_file(
            cache_file_path,
            key=ia_filename,
            metadata=ia_metadata
        )
        if r.status_code == requests.codes.ok:
            upload_ok = True
        else:
            print(f'Bad status: {str(r.status_code)} for {cache_file_path}')
            upload_ok = False
    except:
        print(f'Problem uploading: {cache_file_path}')
        upload_ok = False
    if not upload_ok:
        return None, None
    ia_file_res_obj, ia_iiif_res_obj = get_or_create_ia_resource_objs(
        man_obj,
        file_uri,
        ia_metadata,
        item_id,
        ia_filename
    )
    return ia_file_res_obj, ia_iiif_res_obj