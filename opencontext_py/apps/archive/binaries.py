import os
import shutil
from time import sleep

from django.db.models import OuterRef, Subquery

from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict

from opencontext_py.apps.archive import utilities as zen_utilities
from opencontext_py.apps.archive import metadata as zen_metadata
from opencontext_py.apps.archive.zenodo import ArchiveZenodo

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllAssertion,
    AllManifest,
    AllResource,
    AllIdentifier,
)

from opencontext_py.apps.all_items.editorial.archive import file_utilities as fu

from opencontext_py.apps.all_items.representations import item


"""
# Running this:
import importlib
from opencontext_py.apps.archive import binaries as zen_binaries

importlib.reload(zen_binaries)
zen_binaries.assemble_depositions_dirs_for_project('a52bd40a-9ac8-4160-a9b0-bd2795079203')

zen_binaries.archive_project_binary_dir(
    project_uuid='a52bd40a-9ac8-4160-a9b0-bd2795079203',
    act_path='/home/ekansa/github/open-context-py/static/exports/files-1-by---a52bd40a-9ac8-4160-a9b0-bd2795079203',
    do_testing=True,
)
zen_binaries.add_project_archive_dir_metadata(
    project_uuid='a52bd40a-9ac8-4160-a9b0-bd2795079203',
    act_path='/home/ekansa/github/open-context-py/static/exports/files-1-by---a52bd40a-9ac8-4160-a9b0-bd2795079203',
    deposition_id='17832',
    do_testing=True,
)
zen_binaries.archive_all_project_binary_dirs(
    project_uuid='a52bd40a-9ac8-4160-a9b0-bd2795079203',
    do_testing=False,
)
zen_binaries.assemble_depositions_dirs_for_project(
    'a2d7b2d2-b5de-4433-8d69-2eaf9456349e',
    forced_act_partition_number=0,
)
zen_binaries.archive_all_project_binary_dirs(
    project_uuid='a2d7b2d2-b5de-4433-8d69-2eaf9456349e',
    do_testing=True,
)


zen_binaries.reset_zendodo_metadata_for_files(
    act_path='/home/ekansa/github/open-context-py/static/exports/files-1-by---a52bd40a-9ac8-4160-a9b0-bd2795079203',
)


"""


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
    'checksum',
]


def make_archival_filename(file_type, slug, file_uri):
    """ makes an archival file name based on the
        file type, the slug, and the file_uri
    """
    prefix = ARCHIVE_FILE_PREFIXES.get(file_type, '')
    if '.' in file_uri:
        file_ex = file_uri.split('.')
        extension = file_ex[-1].lower()
        filename = prefix + slug + '.' + extension
    else:
        filename = prefix + slug
    return filename


def get_resource_obj_from_archival_filename(filename):
    """ gets a resource object from an archival file name """
    prefix_to_resource_type = {v:k for k, v in ARCHIVE_FILE_PREFIXES.items()}
    act_file_type = None
    slug_part = None
    for prefix, file_type in prefix_to_resource_type.items():
        if filename.startswith(prefix):
            act_file_type = file_type
            slug_part = filename[len(prefix):]
            break
    if not act_file_type or not slug_part:
        return None
    if '.' in slug_part:
        id_ex = slug_part.split('.')
        slug_part = id_ex[0]
    res_obj = AllResource.objects.filter(
        item__slug=slug_part,
        resourcetype__item_key=act_file_type,
    ).first()
    return res_obj


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
        filename = make_archival_filename(
            res_obj.resourcetype.item_key,
            man_obj.slug,
            file_uri
        )
        if not filename in files_dict:
            act_dict = {
                'short_term_url': f'https://{file_uri}',
                'filename': filename,
                'dc-terms:isPartOf': f'https://{man_obj.uri}',
                'type': [],
            }
            files_dict[filename] = act_dict
        files_dict[filename]['type'].append(res_obj.resourcetype.item_key)
    return files_dict


def record_associated_categories(dir_dict, rep_dict):
    """ gets citation information for the specific media item
    """
    path_objs = rep_dict.get('oc-gen:has-linked-contexts', [])
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


def record_citation_people(dir_dict, rep_dict):
    """ gets citation information for the specific media item
    """
    cite_preds = [
        'dc-terms:creator',
        'dc-terms:contributor',
    ]
    for cite_pred in cite_preds:
        if not rep_dict.get(cite_pred):
            continue
        if not dir_dict.get(cite_pred):
            # just in case we don't have this citation predicate
            # in the directory dict
            dir_dict[cite_pred] = []
        for cite_obj in rep_dict.get(cite_pred, []):
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


def get_make_save_dir_dict(
    part_num,
    license_uri,
    project_uuid,
    dir_content_file_json=zen_utilities.PROJECT_DIR_FILE_MANIFEST_JSON_FILENAME
):
    """Makes a dictionary object with metadata about a directory of files"""
    act_path = zen_utilities.make_project_part_license_dir_path(
        part_num,
        license_uri,
        project_uuid,
    )
    dir_dict = zen_utilities.load_serialized_json(
        path=act_path,
        filename=dir_content_file_json,
    )
    if dir_dict:
        return dir_dict, act_path
    # We didn't have an existing dir dict, so make one.
    dir_dict = {
        'dc-terms:isPartOf': f'https://opencontext.org/projects/{project_uuid}',
        'dc-terms:license': f'https://{AllManifest().clean_uri(license_uri)}',
        'partition-number': part_num,
        'label': zen_utilities.make_project_part_license_dir_name(
            part_num,
            license_uri,
            project_uuid,
        ),
        'size': 0,
        'dc-terms:creator': [],
        'dc-terms:contributor': [],
        'category': [],
        'files': [],
    }
    # Save the directory dictionary to a json file
    zen_utilities.save_serialized_json(
        path=act_path,
        filename=dir_content_file_json,
        dict_obj=dir_dict,
    )
    return dir_dict, act_path


def get_manifest_grouped_by_license(project_uuid):
    """ gets a dict keyed by license uri with a list of media objects
    for a given project.
    """
    # The default copyright license, if none is given
    project_license_uri = AllManifest().clean_uri(
        configs.CC_DEFAULT_LICENSE_CC_BY_URI
    )
    project_license = AllAssertion.objects.filter(
        subject_id=project_uuid,
        predicate_id=configs.PREDICATE_DCTERMS_LICENSE_UUID,
    ).first()
    if project_license:
        # The project has it's own license
        project_license_uri = project_license.object.uri

    media_license_qs = AllAssertion.objects.filter(
        subject_id=OuterRef('uuid'),
        predicate_id=configs.PREDICATE_DCTERMS_LICENSE_UUID,
    ).values('object__uri')[:1]

    file_zenodo_qs = AllResource.objects.filter(
        item_id=OuterRef('uuid'),
        meta_json__has_key='zenodo',
    ).values('meta_json')[:1]

    media_qs = AllManifest.objects.filter(
        project__uuid=project_uuid,
        item_type='media',
    ).annotate(
        # Add the license uri to each media object
        media_license_uri=Subquery(media_license_qs)
    ).annotate(
        # Add the zenodo metadata to each media object,
        # if it exists.
        file_zenodo_meta_json=Subquery(file_zenodo_qs),
    ).order_by(
        'media_license_uri',
        'sort',
    )
    proj_license_dict = {}
    for media_obj in media_qs:
        license_uri = media_obj.media_license_uri
        if not license_uri:
            license_uri = project_license_uri
        if not license_uri in proj_license_dict:
            proj_license_dict[license_uri] = []
        proj_license_dict[license_uri].append(media_obj)
    return proj_license_dict


def assemble_depositions_dirs_for_project(
    project_uuid,
    check_binary_files_present=False,
    dir_content_file_json=zen_utilities.PROJECT_DIR_FILE_MANIFEST_JSON_FILENAME,
    allow_zip_contents=True,
    forced_act_partition_number=None,
):
    """Assembles deposition directories for a given project"""
    project_dirs = zen_utilities.get_project_binaries_dirs(project_uuid)
    files_present = zen_utilities.gather_project_dir_filename_list(
        project_uuid=project_uuid,
        check_binary_files_present=check_binary_files_present,
    )
    act_partition_number = 0
    if project_dirs:
        act_partition_number = zen_utilities.get_maximum_dir_partition_number_for_project(
            project_uuid
        )
    if forced_act_partition_number is not None:
        act_partition_number = forced_act_partition_number
    proj_license_dict = get_manifest_grouped_by_license(project_uuid)
    if allow_zip_contents:
        zip_dir_contents = zen_utilities.recommend_zip_archive(proj_license_dict)
    else:
        zip_dir_contents = False
    for license_uri, man_objs in proj_license_dict.items():
        act_partition_number += 1
        dir_dict, act_path = get_make_save_dir_dict(
            part_num=act_partition_number,
            license_uri=license_uri,
            project_uuid=project_uuid,
            dir_content_file_json=dir_content_file_json,
        )
        for man_obj in man_objs:
            dir_full = zen_utilities.check_if_dir_is_full(
                act_path,
                zip_dir_contents=zip_dir_contents,
            )
            if (dir_full
               or
               (not zip_dir_contents and len(dir_dict.get('files', [])) >= zen_utilities.MAX_DEPOSITION_FILE_COUNT)
            ):
                # Prepare a new directory for the next set of files
                print(f'{act_partition_number} appears full. Preparing a new directory for {act_path}')
                act_partition_number = zen_utilities.get_maximum_dir_partition_number_for_project(
                    project_uuid
                )
                act_partition_number += 1
                dir_dict, act_path = get_make_save_dir_dict(
                    part_num=act_partition_number,
                    license_uri=license_uri,
                    project_uuid=project_uuid,
                    dir_content_file_json=dir_content_file_json,
                )
            if zip_dir_contents:
                dir_dict['files_in_zip_archive'] = zen_utilities.PROJECT_ZIP_FILENAME
            rep_dict = None
            files_dict = get_item_media_files(man_obj)
            dir_updated = False
            for filename, file_dict in files_dict.items():
                if filename in files_present:
                    # We already have this file, so skip it
                    continue
                files_present.append(filename)
                if not rep_dict:
                    _, rep_dict = item.make_representation_dict(
                        subject_id=str(man_obj.uuid),
                        for_solr=False,
                    )
                    dir_dict = record_associated_categories(dir_dict, rep_dict)
                    dir_dict = record_citation_people(dir_dict, rep_dict)
                if not rep_dict:
                    # Something went wrong with the representation dict!
                    continue
                # Actually download and saving the file locally
                cache_file_path = fu.get_cache_file(
                    file_uri=file_dict.get('short_term_url'),
                    cache_filename=file_dict.get('filename'),
                    cache_dir=act_path,
                    local_file_dir=None,
                    remote_to_local_path_split=None,
                )
                if not cache_file_path:
                    # We couldn't cache the file locally, so skip it
                    continue
                dir_updated = True
                dir_dict['files'].append(file_dict)
            if dir_updated:
                # Save the updated directory dictionary to a json file
                zen_utilities.save_serialized_json(
                    path=act_path,
                    filename=dir_content_file_json,
                    dict_obj=dir_dict,
                )


def add_project_archive_dir_metadata(
    project_uuid,
    act_path,
    deposition_id,
    proj_dict=None,
    dir_dict=None,
    dir_content_file_json=zen_utilities.PROJECT_DIR_FILE_MANIFEST_JSON_FILENAME,
    do_testing=False,
):
    """ adds metadata about a project to Zenodo deposition by deposition_id """
    if not dir_dict:
        dir_dict = zen_utilities.load_serialized_json(
            path=act_path,
            filename=dir_content_file_json,
        )
    if not dir_dict:
        raise ValueError(f'Cannot read an archive contents file in: {act_path}')
    if not proj_dict:
        _, proj_dict = item.make_representation_dict(
            subject_id=project_uuid,
            for_solr=False,
        )
    if not proj_dict:
        raise ValueError(f'No project dict found for: {project_uuid}')

    meta = zen_metadata.make_zenodo_proj_media_files_metadata(
        proj_dict=proj_dict,
        dir_dict=dir_dict,
        dir_content_file_json=dir_content_file_json,
    )
    az = ArchiveZenodo(do_testing=do_testing)
    output = az.update_metadata(deposition_id, meta)
    if not output:
        return False
    print(f'Added {proj_dict.get("label")} metadata for: {act_path} to deposition: {deposition_id}')
    return True


def reset_zendodo_metadata_for_files(
    act_path,
    dir_content_file_json=zen_utilities.PROJECT_DIR_FILE_MANIFEST_JSON_FILENAME,
):
    """ resets the zenodo metadata for the files manifest in a given directory
    """
    dir_dict = zen_utilities.load_serialized_json(
        path=act_path,
        filename=dir_content_file_json,
    )
    for file_dict in dir_dict.get('files', []):
        filename = file_dict.get('filename')
        if not filename:
            continue
        for key in ZENODO_FILE_KEYS:
            if file_dict.get(key):
                file_dict.pop(key)
            zen_utilities.save_serialized_json(
                path=act_path,
                filename=dir_content_file_json,
                dict_obj=dir_dict,
            )
    print(
        f'Reset file metadata in {act_path} to remove Zenodo specific keys, values'
    )


def zenodo_archive_in_zip_file(
    act_path,
    dir_dict,
    az,
    bucket_url,
    deposition_id,
    dir_content_file_json=zen_utilities.PROJECT_DIR_FILE_MANIFEST_JSON_FILENAME,
):
    """ Archives individual files for a dir_dict to Zenodo """
    if not dir_dict.get('files_in_zip_archive'):
        raise ValueError('A zip archive should NOT be made for these files')
    file_paths = []
    for file_dict in dir_dict.get('files', []):
        filename = file_dict.get('filename')
        if not filename:
            continue
        done = False
        for key in ZENODO_FILE_KEYS:
            if file_dict.get(key):
                done = True
        if done:
            # This file is already uploaded
            continue
        file_path = os.path.join(act_path, filename)
        if not os.path.exists(file_path):
            raise ValueError(f'Cannot find: {file_path}')
        file_paths.append(file_path)
    if not file_paths:
        return None
    zip_path, zip_name = zen_utilities.zip_files(path=act_path, file_paths=file_paths)
    zenodo_resp = az.upload_file_by_put(
        bucket_url=bucket_url,
        full_path_file=zip_path,
        filename=zip_name,
    )
    if not zenodo_resp:
        raise ValueError(f'Cannot upload zip file to bucket: {zip_path}')
    print(
        f'Archived {zip_name} (zipped media files) to deposition {deposition_id}'
    )
    # Record zipfile metadata returned from Zenodo in the dir_dict
    for key in ZENODO_FILE_KEYS:
        if not zenodo_resp.get(key):
            continue
        dir_dict_key = f'zip_archive_{key}'
        dir_dict[dir_dict_key] = zenodo_resp[key]
    # Save the update with the zenodo file specific key values
    zen_utilities.save_serialized_json(
        path=act_path,
        filename=dir_content_file_json,
        dict_obj=dir_dict,
    )


def zenodo_archive_individual_files(
    act_path,
    dir_dict,
    az,
    bucket_url,
    deposition_id,
    dir_content_file_json=zen_utilities.PROJECT_DIR_FILE_MANIFEST_JSON_FILENAME,
):
    """ Archives individual files for a dir_dict to Zenodo """
    if dir_dict.get('files_in_zip_archive'):
        raise ValueError('These files should be put into a zip archive')
    i = 0
    len_files = len(dir_dict.get('files', []))
    for file_dict in dir_dict.get('files', []):
        filename = file_dict.get('filename')
        if not filename:
            continue
        done = False
        for key in ZENODO_FILE_KEYS:
            if file_dict.get(key):
                done = True
        if done:
            # This file is already uploaded
            continue
        file_path = os.path.join(act_path, filename)
        if not os.path.exists(file_path):
            raise ValueError(f'Cannot find: {file_path}')
        zenodo_resp = az.upload_file_by_put(
            bucket_url=bucket_url,
            full_path_file=file_path,
            filename=filename,
        )
        if not zenodo_resp:
            raise ValueError(f'Cannot upload file to bucket: {file_path}')
        i += 1
        for key in ZENODO_FILE_KEYS:
            if not zenodo_resp.get(key):
                continue
            file_dict[key] = zenodo_resp[key]
        print(
            f'[{i} of {len_files}] Archived {filename} of {dir_dict.get("label")} to deposition {deposition_id}'
        )
        # Save the update with the zenodo file specific key values
        zen_utilities.save_serialized_json(
            path=act_path,
            filename=dir_content_file_json,
            dict_obj=dir_dict,
        )


def archive_project_binary_dir(
    project_uuid,
    act_path,
    proj_dict=None,
    deposition_id=None,
    dir_content_file_json=zen_utilities.PROJECT_DIR_FILE_MANIFEST_JSON_FILENAME,
    do_testing=False,
):
    """ archives a project binary directory to Zenodo """
    dir_dict = zen_utilities.load_serialized_json(
        path=act_path,
        filename=dir_content_file_json,
    )
    valid, errors = zen_utilities.validate_archive_dir_binaries(act_path, dir_dict=dir_dict)
    if not valid:
        for error in errors:
            print(error)
        raise ValueError(f'Cannot archive an invalid directory: {act_path}')
    az = ArchiveZenodo(do_testing=do_testing)
    bucket_url = None
    if not deposition_id:
        deposition_dict = az.create_empty_deposition()
        if not deposition_dict:
            raise ValueError(f'Cannot create an empty deposition for: {act_path}')
        deposition_id = az.get_deposition_id_from_metadata(deposition_dict)
        bucket_url = az.get_bucket_url_from_metadata(deposition_dict)
    if not bucket_url and deposition_id:
        bucket_url = az.get_remote_deposition_bucket_url(deposition_id)
    if not bucket_url:
        raise ValueError(f'Cannot get bucket url for: {act_path}')
    if not deposition_id:
        raise ValueError(f'Cannot get deposition id for: {act_path}')
    len_files = len(dir_dict.get('files', []))
    if dir_dict.get('files_in_zip_archive'):
        # Upload and archive the files consolidated within a single zip file
        zenodo_archive_in_zip_file(
            act_path=act_path,
            dir_dict=dir_dict,
            az=az,
            bucket_url=bucket_url,
            deposition_id=deposition_id,
            dir_content_file_json=dir_content_file_json,
        )
    else:
        # Upload and archive the files individually
        zenodo_archive_individual_files(
            act_path=act_path,
            dir_dict=dir_dict,
            az=az,
            bucket_url=bucket_url,
            deposition_id=deposition_id,
            dir_content_file_json=dir_content_file_json,
        )
    # Now upload the Zenodo file manifest JSON
    manifest_path = os.path.join(act_path, dir_content_file_json)
    zenodo_resp = az.upload_file_by_put(
        bucket_url=bucket_url,
        full_path_file=manifest_path,
        filename=dir_content_file_json,
    )
    if not zenodo_resp:
        raise ValueError(f'Cannot upload file to bucket: {manifest_path}')
    # Now make metadata for the deposition.
    if not proj_dict:
        _, proj_dict = item.make_representation_dict(
            subject_id=project_uuid,
            for_solr=False,
        )
    if not proj_dict:
        raise ValueError(f'No project dict found for: {project_uuid}')
    dep_meta_dict = zen_metadata.make_zenodo_proj_media_files_metadata(
        proj_dict=proj_dict,
        dir_dict=dir_dict,
        dir_content_file_json=dir_content_file_json,
    )
    az.update_metadata(deposition_id, dep_meta_dict)
    print(
        f'Archived {len_files} files to deposition {deposition_id}; {dep_meta_dict.get("title")}'
    )


def archive_all_project_binary_dirs(
    project_uuid,
    proj_dict=None,
    do_testing=False,
):
    """ archives all project binary directories to Zenodo """
    project_dirs = zen_utilities.get_project_binaries_dirs(project_uuid)
    for act_path in project_dirs:
        if not act_path.startswith(zen_utilities.ARCHIVE_LOCAL_ROOT_PATH):
            act_path = os.path.join(zen_utilities.ARCHIVE_LOCAL_ROOT_PATH, act_path)
        archive_project_binary_dir(
            project_uuid=project_uuid,
            act_path=act_path,
            proj_dict=proj_dict,
            do_testing=do_testing,
        )


def update_resource_obj_zenodo_file_deposit(
    deposition_id,
    doi_url,
    zenodo_file_dict,
):
    """Updates the zenodo archive metadata for a resource object"""
    if not deposition_id or not doi_url or not zenodo_file_dict:
        return None
    filename = zenodo_file_dict.get('filename')
    if not filename:
        return None
    res_obj = get_resource_obj_from_archival_filename(filename)
    if not res_obj:
        return None
    if res_obj.meta_json.get('zenodo'):
        # We already have a record of this resource record
        # being deposited in Zenodo
        return res_obj
    oc_dict = {
        'deposition_id': deposition_id,
        'doi_url': AllManifest().clean_uri(doi_url),
        'filename': filename,
        'filesize': zenodo_file_dict.get('filesize'),
        'checksum': zenodo_file_dict.get('checksum'),
        'zenodo_file_id': zenodo_file_dict.get('id'),
    }
    res_obj.meta_json['zenodo'] = oc_dict
    res_obj.save()
    return res_obj


def record_all_zenodo_depositions(params=None):
    """Records Zenodo depositions for resource instances
    based on file lists returned from Zenodo API
    """
    az = ArchiveZenodo()
    depositions = az.get_all_depositions_list(params=params)
    for deposition in depositions:
        deposition_id = deposition.get('id')
        doi_url = deposition.get('doi_url')
        title = deposition.get('title')
        if not deposition_id or not doi_url:
            continue
        files = deposition.get('files', [])
        print(f'Processing deposition {title} [id: {deposition_id}] with {len(files)} files')
        res_count = 0
        for zenodo_file_dict in files:
            res_obj = update_resource_obj_zenodo_file_deposit(
                deposition_id,
                doi_url,
                zenodo_file_dict,
            )
            if not res_obj:
                continue
            res_count += 1
        print(f'Processed {res_count} resources for deposition {title} [id: {deposition_id}]')
