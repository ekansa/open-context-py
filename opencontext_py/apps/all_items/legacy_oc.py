
import hashlib
import uuid as GenUUID

from django.db.models import Q

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllString,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities

from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation

from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.manifest.models import Manifest as OldManiftest

"""
from opencontext_py.apps.all_items.legacy_oc import *
migrate_legacy_projects()

"""



SOURCE_ID = 'legacy-oc-migrate'

SALT = (
    'a53b5bc896b2ace7a812d33ec895279d2c4dcd3f932ce2d9c7811690aabd7e92bbf9'
    '3d5440f7b51a6b1171bcc57c94a0e6860b7b26b64fa7b5e39748de22e291652bdac2'
    '3382fe9d8b4ec405d4e79bc886ea36b7cf366098ca4deaaf86dd57b0181cbd8432ee'
    '5a7c1c259f0da8af327f0b4363fb7fc337d16d41ad666a02367c80f7ed9b1ac3035e'
    '32f666e2026d198068a6ba26c9f7ceca18e8c8d19a8fe2fd2b53a715e8d682a803f6'
    '2eb51ca594d00700b37f3fdc2707d197c0efae0574a86a09500b31ce75b8ab8c13b0'
    'aff9cd2b9d68b6acdadb5317efa542739827a0492418ceca0e9b995eafb92181a4cd'
)

MANIFEST_COPY_ATTRIBUTES = [
    'label',
    'slug',
    'views',
    'indexed',
    'vcontrol',
    'archived',
    'published',
    'revised',
]

def is_valid_uuid(val):
    try:
        return GenUUID.UUID(str(val))
    except ValueError:
        return None


def update_old_id(old_id):
    """Updates an old ID deterministically so as to be repeatable"""
    if is_valid_uuid(old_id):
        # The old ID is fine and needs no updating.
        return old_id, old_id.lower()
    hash_obj = hashlib.sha1()
    # The salt added to our hash adds some randomness so that we're less
    # likely to make an ID that collides with something else out there in the wild.
    hash_this = f'{SALT}-{old_id}'
    hash_obj.update(hash_this.encode('utf-8'))
    hash_val = hash_obj.hexdigest()
    new_uuid = str(
        GenUUID.UUID(hex=hash_val[:32])
    )
    return old_id, new_uuid


def copy_attributes(old_man_obj, new_dict={}, attributes=MANIFEST_COPY_ATTRIBUTES):
    """Copies attributes from the old_man_obj to a new_man dict"""
    if not old_man_obj:
        return new_dict
    old_dict = old_man_obj.__dict__
    for attribute in attributes:
        new_dict[attribute] = old_dict.get(attribute)
    return new_dict


def save_legacy_id_object(new_man_obj, old_id, id_scheme='oc-old'):
    """Saves a legacy identifier record if needed"""
    if str(new_man_obj.uuid) == str(old_id):
        # IDs are the same. No need to save an identifier record
        return None
    uuid = AllIdentifier().primary_key_create(
        item_id=new_man_obj.uuid,
        scheme=id_scheme,
    )
    id_obj, c = AllIdentifier.objects.get_or_create(
        uuid=uuid,
        defaults={
            'item': new_man_obj,
            'scheme': id_scheme,
            'id': old_id
        }
    )
    print(
        f'ID obj {id_obj.uuid}: '
        f'{id_obj.item.label} ({id_obj.item.uuid}) -> '
        f'{id_obj.id} ({id_obj.scheme}) created {str(c)}'
    )
    return id_obj


def migrate_old_project(old_proj):
    """Migrates an old project item to the new manifest"""
    if old_proj.uuid == '0':
        return None
    old_proj_id, new_proj_uuid = update_old_id(old_proj.uuid)
    old_parent_id, new_parent_uuid = update_old_id(old_proj.project_uuid)
    if old_parent_id != '0' and new_parent_uuid != new_proj_uuid:
        # The parent project is not the same as the old project,
        # so migrate the parent project first.
        old_parent_proj = Project.objects.get(uuid=old_parent_id)
        new_parent_proj = migrate_old_project(old_parent_proj)
    else:
        # The new parent project for "root-level" projects is the Open Context project.
        new_parent_proj = AllManifest.objects.get(uuid=configs.OPEN_CONTEXT_PROJ_UUID)

    old_proj_man_obj = OldManiftest.objects.get(uuid=old_proj_id)
    
    # Compose the meta_json object for this new project
    new_meta_json = {
        'short_id': old_proj.short_id,
        'edit_status': old_proj.edit_status,
        'view_group_id': old_proj.view_group_id,
        'edit_group_id': old_proj.edit_group_id,
        'legacy_id': old_proj_id,
    }
    old_dicts = [
        ('legacy_m_local', old_proj_man_obj.localized_json),
        ('legacy_m_sup', old_proj_man_obj.sup_json),
        ('legacy_p_sm', old_proj.sm_localized_json),
        ('legacy_p_lg', old_proj.lg_localized_json),
        ('legacy_p_meta', old_proj.meta_json),
    ]
    for d_type, old_dict in old_dicts:
        if not old_dict:
            continue
        for key, val in old_dict.items():
            if key not in new_meta_json:
                new_key = key
            else:
                new_key = f'{d_type}_{key}'
            new_meta_json[new_key] = val

    man_dict = {
        'publisher': new_parent_proj.publisher,
        'project': new_parent_proj.project,
        'source_id': SOURCE_ID,
        'item_type': 'projects',
        'data_type': 'id',
        'context': new_parent_proj,
        'meta_json': new_meta_json,
    }
    man_dict = copy_attributes(old_man_obj=old_proj_man_obj, new_dict=man_dict)
    new_man_obj, _ = AllManifest.objects.get_or_create(
        uuid=new_proj_uuid,
        defaults=man_dict
    )
    print(
        f'Migrated {new_man_obj.label} ({new_man_obj.uuid}) with: '
        f'{str(new_man_obj.meta_json)}'
    )
    save_legacy_id_object(new_man_obj, old_proj_id)

    # Add the short description for the project.
    utilities.add_string_assertion_simple(
        subject_obj=new_man_obj,
        predicate_id=configs.PREDICATE_DCTERMS_DESCRIPTION_UUID, 
        str_content=old_proj.short_des,
        publisher_id=new_man_obj.publisher.uuid,
        project_id=new_man_obj.uuid,
        source_id=SOURCE_ID,
    )
     # Add the project abstract.
    utilities.add_string_assertion_simple(
        subject_obj=new_man_obj,
        predicate_id=configs.PREDICATE_DCTERMS_ABSTRACT_UUID,
        str_content=old_proj.content,
        publisher_id=new_man_obj.publisher.uuid,
        project_id=new_man_obj.uuid,
        source_id=SOURCE_ID,
    )
    return new_man_obj


def migrate_legacy_projects():
    """Migrates project entities to the new schema"""
    for old_proj in Project.objects.all().exclude(uuid='0'):
        new_proj = migrate_old_project(old_proj)
        
