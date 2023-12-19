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


def get_resource_obj_from_archival_file_name(file_name):
    """ gets a resource object from an archival file name """
    prefix_to_resource_type = {v:k for k, v in ARCHIVE_FILE_PREFIXES.items()}
    act_file_type = None
    slug_part = None
    for prefix, file_type in prefix_to_resource_type.items():
        if file_name.startswith(prefix):
            act_file_type = file_type
            slug_part = file_name[len(prefix):]
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
        'dc-terms:contributor',
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
        dir_content_file_json=zen_utilities.PROJECT_DIR_FILE_MANIFEST_JSON_FILENAME
    ):
    """Makes a dictionary object with metadata about a directory of files"""
    act_path = zen_utilities.make_project_part_license_dir_path(
        part_num,
        license_uri,
        project_uuid,
    )
    dir_dict = {
        'dc-terms:isPartOf': f'https://opencontext.org/projects/{project_uuid}',
        'dc-terms:license': license_uri,
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
        file_name=dir_content_file_json,
        dict_obj=dir_dict,
    )
    return dir_dict


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


def assemble_depositions_dirs_for_project(project_uuid, check_binary_files_present=False):
    """Assembles deposition directories for a given project"""
    project_dirs = zen_utilities.get_project_binaries_dirs(project_uuid)
    files_present = zen_utilities.gather_project_dir_file_name_list(
        project_uuid=project_uuid,
        check_binary_files_present=check_binary_files_present,
    )
    act_partition_number = 0
    if project_dirs:
        act_partition_number = zen_utilities.get_maximum_dir_partition_number_for_project(
            project_uuid
        )
    proj_license_dict = get_manifest_grouped_by_license(project_uuid)
    for license_uri, man_objs in proj_license_dict.items():
        act_partition_number += 1
    


def update_ressource_obj_zenodo_file_deposit(
    deposition_id,
    doi_url,
    zenodo_file_dict,
):
    """Updates the zenodo archive metadata for a resource object"""
    if not deposition_id or not doi_url or not zenodo_file_dict:
        return None
    file_name = zenodo_file_dict.get('filename')
    if not file_name:
        return None
    res_obj = get_resource_obj_from_archival_file_name(file_name)
    if not res_obj:
        return None
    if res_obj.meta_json.get('zenodo'):
        # We already have a record of this resource record
        # being deposited in Zenodo
        return res_obj
    oc_dict = {
        'deposition_id': deposition_id,
        'doi_url': AllManifest().clean_uri(doi_url),
        'filename': file_name,
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
            res_obj = update_ressource_obj_zenodo_file_deposit(
                deposition_id,
                doi_url,
                zenodo_file_dict,
            )
            if not res_obj:
                continue
            res_count += 1
        print(f'Processed {res_count} resources for deposition {title} [id: {deposition_id}]')
