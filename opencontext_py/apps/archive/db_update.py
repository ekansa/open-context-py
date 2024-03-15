import os
import shutil
from time import sleep

from django.db.models import OuterRef, Subquery

from django.conf import settings

from opencontext_py.apps.archive import binaries as zen_binaries
from opencontext_py.apps.archive import metadata as zen_metadata
from opencontext_py.apps.archive import utilities as zen_utilities

from opencontext_py.apps.archive.zenodo import ArchiveZenodo, OC_COMMUNITY_UUID

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllAssertion,
    AllManifest,
    AllResource,
    AllIdentifier,
)


"""
# Running this:
import importlib
from opencontext_py.apps.archive import db_update as zen_db

importlib.reload(zen_db)

zen_db.record_all_project_zenodo_deposits()
"""

def get_deposition_doi_url(deposition):
    if not deposition:
        return None
    doi_url = deposition.get('doi_url')
    if doi_url:
        return doi_url
    metadata = deposition.get('metadata', {})
    doi = deposition.get('doi')
    if not doi:
        doi = metadata.get('doi')
    if not doi:
        doi = metadata.get('prereserve_doi', {}).get('doi')
    if not doi:
        return None
    doi_url = f'https://doi.org/{doi}'
    return doi_url


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
    res_obj = zen_binaries.get_resource_obj_from_archival_filename(filename)
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
    if params is None:
        params = {
            'communities': OC_COMMUNITY_UUID,
        }
    az = ArchiveZenodo()
    depositions = az.get_all_depositions_list(params=params)
    if not depositions:
        print('No depositions found')
        return None
    for deposition in depositions:
        deposition_id = deposition.get('id')
        doi_url = get_deposition_doi_url(deposition)
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


def validate_man_obj_deposition_relation(man_obj, deposition):
    """Verifies that a project manifest object relates to a Zenodo deposition object"""
    if not man_obj or not deposition:
        return False
    rel_found = False
    legacy_id = man_obj.meta_json.get('legacy_id')
    for rel_obj in deposition.get('metadata', {}).get('related_identifiers', []):
        rel_id = rel_obj.get('identifier')
        if not rel_id:
            continue
        if not rel_obj.get('relation') in ['isPartOf', 'compiles',]:
            continue
        if AllManifest().clean_uri(rel_id) == man_obj.uri:
            rel_found = True
            break
        if legacy_id and rel_id.endswith(f'/{man_obj.item_type}/{legacy_id}'):
            print(f'Legacy ID match: {rel_id} has {legacy_id}')
            rel_found = True
            break
    return rel_found


def get_or_create_zenodo_deposition_man_obj(
    dep_title,
    dep_uri,
    source_id,
    publisher_id,
    project_id,
    deposition_type=None,
):
    """Gets or creates a manifest object for a Zenodo deposition"""
    dep_uri = AllManifest().clean_uri(dep_uri)
    dep_obj = AllManifest.objects.filter(
        uri=dep_uri
    ).first()
    if dep_obj and deposition_type:
        # Make sure we have the deposition type recorded
        dep_obj.meta_json['deposition_type'] = deposition_type
        dep_obj.save()
        return dep_obj
    # OK. Now make it.
    dep_man_dict = {
        'publisher_id': publisher_id,
        'project_id': project_id,
        'item_class_id': configs.DEFAULT_CLASS_UUID,
        'source_id': source_id,
        'item_type': 'uri',
        'data_type': 'id',
        'label': dep_title,
        'uri': dep_uri,
        'context_id': configs.ZENODO_VOCAB_UUID,
        'meta_json': {
            'deposition_type': deposition_type,
        },
    }
    dep_obj, _ = AllManifest.objects.get_or_create(
        uri=dep_uri,
        defaults=dep_man_dict,
    )
    return dep_obj


def get_or_create_zenodo_deposition_relation_assertion(
    subject_id,
    object_id,
    publisher_id,
    project_id,
    source_id,
    predicate_id=configs.PREDICATE_DCTERMS_HAS_PART_UUID,
):
    # Now record the assertion linking the project object to the
    # record of the Zenodo deposition
    assert_dict = {
        'project_id': project_id,
        'publisher_id': publisher_id,
        'source_id': source_id,
        'subject_id': subject_id,
        'predicate_id': predicate_id,
        'object_id': object_id, # This is the zenodo deposition object
    }
    ass_obj, _ = AllAssertion.objects.get_or_create(
        uuid=AllAssertion().primary_key_create(
            subject_id=assert_dict['subject_id'],
            predicate_id=assert_dict['predicate_id'],
            object_id=assert_dict['object_id'],
        ),
        defaults=assert_dict
    )
    print(
        f'Assertion {ass_obj.uuid}: '
        f'is {ass_obj.subject.label} [{ass_obj.subject.uuid}]'
        f'-> {ass_obj.predicate.label} [{ass_obj.predicate.uuid}]'
        f'-> {ass_obj.object.label} [{ass_obj.object.uuid}]'
    )
    return ass_obj


def record_zenodo_deposition_for_item(
    man_obj,
    deposition=None,
    rep_dict=None,
    deposition_id=None,
    deposition_type=None,
    dep_title=None,
):
    """Records a project manifest object relationship to a Zenodo deposition object"""
    dep_uri = None
    keywords = []
    if man_obj and deposition:
        # Case where we got a deposition object from the Zenodo API list
        # request.
        relation_valid = validate_man_obj_deposition_relation(man_obj, deposition)
        if not relation_valid:
            return None, None
        if not dep_title:
            dep_title = deposition.get('metadata', {}).get('title')
        dep_uri = get_deposition_doi_url(deposition)
        keywords = deposition.get('metadata', {}).get('keywords', [])
        source_id = 'zenodo-api-list'
    if man_obj and rep_dict and deposition_id:
        # Case where we just made a new deposition and want to record it.
        if not dep_title and deposition_type == 'structured_data':
            dep_title = zen_metadata.make_zenodo_structured_data_deposition_title(
                rep_dict.get('dc-terms:title', man_obj.label),
            )
        dep_uri = zen_metadata.make_zenodo_doi_url(deposition_id)
        source_id = 'zenodo-api-create'
        print(f'New {deposition_type} deposition URI: {dep_uri}')
    # We're missing some critical information needing to record a Zenodo
    # deposition as a Manifest object.
    if not dep_title or not dep_uri:
        return None, None
    # Get the type of deposition from the keywords
    if not deposition_type and 'Structured Data' in keywords:
        deposition_type = 'structured_data'
    if not deposition_type and 'Media Files' in keywords:
        deposition_type = 'media'
    # Get the appropriate project ID for different item_types
    if man_obj.item_type == 'projects':
        project_id = man_obj.uuid
    else:
        project_id = man_obj.project.uuid
    # Create the deposition object if it doesn't exist in the database
    dep_obj = get_or_create_zenodo_deposition_man_obj(
        dep_title=dep_title,
        dep_uri=dep_uri,
        source_id=source_id,
        publisher_id=man_obj.publisher.uuid,
        project_id=project_id,
        deposition_type=deposition_type,
    )
    if not dep_obj:
        # We failed to get or create a new deposition object
        return None, None
    # Now record the assertion linking the project object to the
    # record of the Zenodo deposition
    ass_obj = get_or_create_zenodo_deposition_relation_assertion(
        subject_id=man_obj.uuid,
        object_id=dep_obj.uuid,
        publisher_id=man_obj.publisher.uuid,
        project_id=project_id,
        source_id=source_id,
    )
    return dep_obj, ass_obj


def record_proj_obj_zenodo_depositions(proj_obj, params=None):
    """Records Zenodo depositions for resource instances
    based on file lists returned from Zenodo API
    """
    az = ArchiveZenodo()
    if params is None:
        params = {
            'size': 50,
            'communities': OC_COMMUNITY_UUID,
        }
    # Search, using Lucence syntax for depositions
    # params['q'] = f'*opencontext*{str(proj_obj.uuid)}'
    params['q'] = str(proj_obj.uuid)
    depositions = az.get_all_depositions_list(params=params)
    if not depositions:
        depositions = []
    legacy_id = proj_obj.meta_json.get('legacy_id')
    if legacy_id:
        # This project has a legacy ID, so we should check for older depositions
        if len(legacy_id) > 5:
            params['q'] = legacy_id
        else:
            params['q'] = f'*opencontext*{legacy_id}'
        print(f'Search Zenodo using the legacy_id: {legacy_id}')
        leg_depositions = az.get_all_depositions_list(params=params)
        if isinstance(leg_depositions, list):
            depositions += leg_depositions
    print(f'Search found {len(depositions)} deposits likely related to {proj_obj.label} [{proj_obj.uuid}]')
    related_deposits = []
    for deposition in depositions:
        dep_obj, ass_obj = record_zenodo_deposition_for_item(
            man_obj=proj_obj,
            deposition=deposition,
            rep_dict=None,
            deposition_id=None
        )
        if not dep_obj or not ass_obj:
            continue
        related_deposits.append(dep_obj)
    print(f'Saved {len(related_deposits)} deposits related to {proj_obj.label} [{proj_obj.uuid}]')


def record_all_project_zenodo_deposits(params=None, start=None):
    proj_qs = AllManifest.objects.filter(item_type='projects')
    i = 0
    if start and start > 0:
        limit_proj_qs = proj_qs[start:]
        i = start - 1
    else:
        limit_proj_qs = proj_qs
    for proj_obj in limit_proj_qs:
        i += 1
        print(f'[{i} of {proj_qs.count()}]----------------------------------------')
        record_proj_obj_zenodo_depositions(proj_obj, params=params)
        print('\n')