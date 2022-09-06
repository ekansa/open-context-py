import itertools
import json
import pytz
import hashlib

import pandas as pd

from django.core.cache import caches
from django.utils import timezone

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities
from opencontext_py.apps.all_items.legacy_all import update_old_id
from opencontext_py.apps.all_items.legacy_ld import migrate_legacy_link_annotations


from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.manifest.models import Manifest as OldManifest
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata
from opencontext_py.apps.ocitems.assertions.models import Assertion as OldAssertion
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.geospace.models import Geospace as OldGeospace
from opencontext_py.apps.ocitems.events.models import Event as OldEvent
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer as OldIdentifier


"""
from opencontext_py.apps.all_items.legacy_oc import *
migrate_legacy_projects()
migrate_root_subjects()
migrate_legacy_manifest_for_project(project_uuid='0')
migrate_legacy_spacetime_for_project(project_uuid='0')
murlo = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
migrate_legacy_manifest_for_project(project_uuid=murlo)
migrate_legacy_spacetime_for_project(project_uuid=murlo)
migrate_legacy_identifiers_for_project(project_uuid=murlo)
orig_assert_migrate_errors = migrate_legacy_assertions_for_project(murlo)
new_assert_mirgrate_errors = migrate_legacy_assertions_from_csv(
    project_uuid=murlo,
    file_path='/home/ekansa/migration-errors/very-bad-murlo-assertions.csv'
)
save_old_assertions_to_csv(
    '/home/ekansa/migration-errors/very-very-bad-murlo-assertions.csv', 
    new_assert_mirgrate_errors
)
# DT migration
new_assert_mirgrate_errors = migrate_legacy_assertions_from_csv(
    project_uuid='3',
    file_path='/home/ekansa/migration-errors/assert-m-errors-1-domuztepe-excavati.csv'
)
save_old_assertions_to_csv(
    '/home/ekansa/migration-errors/assert-m-errors-worse-1-domuztepe-excavati.csv', 
    new_assert_mirgrate_errors
)
"""

SOURCE_ID = 'legacy-oc-migrate'


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

TIME_ATTRIBUTES = [
    'indexed',
    'vcontrol',
    'archived',
    'published',
    'revised',
]

LEGACY_ROOT_SUBJECTS = [
    # List of tuples as follows:
    # old_uuid, old_context_path, new parent item.
    ('69cd6681-3550-4423-97f8-59d76a258c49', 'Afghanistan', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('feda369d-2dbc-4b16-b0ed-83524bafa620', 'Algeria', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ("a3efae9e-7826-46db-82a1-6f7c04b4af1e", 'Argentina', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('7351C966-B876-4B29-F525-5B33CBE895B7', 'Australia', configs.DEFAULT_SUBJECTS_OCEANIA_UUID),
    ('4d0191be-9aa0-4566-9b64-89c79ff23d85', 'Bahrain', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('2a9d6e29-5485-4999-9435-1a836fd57b4f', 'Belize', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('90959e36-d1e7-45b7-be4b-109c944f3f55', 'Bolivia', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('f7d43b2c-b033-4cbe-9b87-8df3f3691f9c', 'Borneo', configs.DEFAULT_SUBJECTS_ASIA_UUID),

    ('b62fc350-fc9e-4603-b936-671088f87f94', 'Bosnia and Herzegovina', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('34053a4c-44f8-4824-beab-9dadb5a66a82', 'Brazil', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('c75c197b-e532-4968-a4a0-dd11be56bef2', 'Bulgaria', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('47ed71f2-36ab-4e43-9d91-2257476a725c', 'Cambodia', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('994cbb14-e1e1-43be-b179-e3f839b87c4f', 'Cameroon', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('b582c768-0d90-4420-850c-fde4fc2d43fa', 'Canada', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('dae26993-762d-4145-8060-116665674b0e', 'Central African Republic', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('d3f31ae6-365a-4820-afc2-9eb8699a060a', 'Chile', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('e6237a65-452d-44aa-a661-dd0400e4e57d', 'China', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    # ('99e74a38-8178-41a0-83aa-13f78499f327', 'Clermont County'),
    ('239419cf-e7ea-4e41-8cbe-78d817ed3ae8', 'Colombia', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('b97e416b-9684-4fec-990f-5ca974fe657e', 'Costa Rica', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),

    ('7cf7cf91-746c-4523-99d2-983677ab9aa7', 'Croatia', configs.DEFAULT_SUBJECTS_EUROPE_UUID),

    ('67D9F00D-14E6-4A1B-3A61-EC92FC774098', 'Cyprus', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('7b8e80bf-b51f-4cf0-a13d-ce403ff15545', 'Democratic Republic of Congo', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('90d17f5c-60e9-4493-b957-95080c67384f', 'Denmark', configs.DEFAULT_SUBJECTS_EUROPE_UUID),

    ('e9ee5897-d403-4262-a2c3-c4f055755cc6', 'Ecuador', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('A2257E54-3B4F-4DA5-0E50-A428ECEB47A2', 'Egypt', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('3631ed1e-941f-4016-b169-fac4ec42c35f', 'Equatorial Guinea', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('bf7d1ef1-ae86-4516-99ba-cf1d4e282bab', 'Ethiopia', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('b86fecaf-dce0-4df4-8636-d9f724184af0', 'France', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('20404f92-9a24-4f5a-bc9b-536c563edd4a', 'Gabon', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('2_Global_Germany', 'Germany', configs.DEFAULT_SUBJECTS_EUROPE_UUID),

    ('337eef63-9258-4fb7-834a-ebe723a089eb', 'Ghana', configs.DEFAULT_SUBJECTS_AFRICA_UUID),

    ('4a5c6aab-3370-4c46-bb14-df6e591993c0', 'Guatemala', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),

    ('1e13889f-188b-408f-ac1e-133cda2c7482', 'Guinea', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('367616d7-9dd4-41ff-b072-704abf72da29', 'Guinea-Bissau', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('82916fcc-04b8-47b2-97b1-31f7019b862e', 'Greece', configs.DEFAULT_SUBJECTS_EUROPE_UUID),

    ('76a84406-1530-40e7-a81a-4fc99eecadff', 'Haiti', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),

    ('cc5a7f34-ef5e-4650-af7b-f30a74a31007', 'Iceland', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('6_global_India', 'India', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('0519B7C7-1973-4D55-17FE-6D97176B1001', 'Indian Ocean', configs.DEFAULT_SUBJECTS_OCEANIA_UUID),
    ('CD25B435-F70E-4F22-B344-85116E750814', 'Indonesia', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('9FC763F1-F606-B389-6CC285B7BCFE26A8', 'Iran', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('GHF1SPA0000077840', 'Iraq', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('3_Global_Israel', 'Israel', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('B66A08F2-5D96-4DD4-1AB1-32880C9A8D9D', 'Italy', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('0cd4d992-caa3-4b00-94ab-7eb15bba7eaf', 'Ivory Coast', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('D9AE02E5-C3F3-41D0-EB3A-39798F63GGGG', 'Jordan', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('550f3c41-7456-4ecb-aecd-e20070762261', 'Kenya', configs.DEFAULT_SUBJECTS_AFRICA_UUID),

    ('f8b1b2ac-4f10-426d-8c4c-5745f6d0403c', 'Lebanon', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('07a9c764-c101-4579-be5a-7ad3292f7eb5', 'Libya', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('2658a3bf-622b-4a22-9e65-a586976ee196', 'Liechtenstein', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('251C032B-684D-445E-156B-5710AA407B11', 'Malaysia', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('20AF0BD0-B152-4A48-E19D-3A951EEF4A58', 'Mauritius', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('ee431393-7ab1-4d7a-abec-bb05f53babda', 'Mexico', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    # Added for Cattle-People.
    ('decda957-9e07-42d6-b128-b48d1129d889', 'Mongolia', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('b3cab722-fb1f-4b8a-b7ab-2627b2eba70e', 'Morocco', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('bc2c325c-4f4a-4eb6-aea1-50b2474b8814', 'Myanmar', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('44d061ca-4aec-402e-9dec-12d0223465b3', 'Nicaragua', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('39656aad-ef90-4c98-8700-6487dd8d4d23', 'Nigeria', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('32B3883A-B007-405D-C4E0-ED129C587DFA', 'Northern Mariana Islands', configs.DEFAULT_SUBJECTS_OCEANIA_UUID),

    ('ba12f728-537e-4d9a-a1d2-2fdfe36473b2', 'Oman', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('2421c35e-7aa2-4fe0-ae90-0a995ea88136', 'Pakistan', configs.DEFAULT_SUBJECTS_ASIA_UUID),

    ('4_global_Palestine', 'Palestinian Authority', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('e6a2d6f1-c86d-454c-98a7-fdb2b1ead222', 'Peru', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('A659B68E-EC36-4477-0C79-D48B370118FC', 'Philippines', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('a2f952b7-baef-49d8-9cfb-c32a630ac64e', 'Poland', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('d9814d86-cbe1-4ba3-bdc4-b3f757443e88', 'Portugal', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('56F99175-F90F-4978-362A-5B6FE27E8B6B', 'Russia', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('c373317b-5c35-4e3e-b618-0f2a022918a9', 'Rwanda', configs.DEFAULT_SUBJECTS_AFRICA_UUID),

    ('3191c767-259c-4666-9f27-78dc6ab13d40', 'Saudi Arabia', configs.DEFAULT_SUBJECTS_ASIA_UUID),

    ('cd518ce5-801d-4e30-af66-3972c4622f7e', 'Senegal', configs.DEFAULT_SUBJECTS_AFRICA_UUID),

    ('6790ca65-964e-46e7-a8ed-2db2a3ce39cc', 'Serbia', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    # NOTE: Somaliland doesn't have international recognition for independence, see:
    # https://en.wikipedia.org/wiki/Somaliland
    ('fe9516aa-fa9c-49a5-8683-131117e87f66', 'Somaliland', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('75EE4254-7C5A-4B0F-F809-A1AFAC016C53', 'South Africa', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('A11CD813-68C7-4F02-4DDA-4C388C422231', 'South Atlantic Ocean', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('3776e3e7-91ea-4c35-9481-0b1fae3afa9a', 'Spain', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    # ('18EA072A-726B-4019-4378-305257EB3AAB', 'Special Project  84', ),
    ('2572daff-7242-474a-9b5c-f34943a684b4', 'Sudan', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('73738647-5987-40ac-ac13-12f11e58c60f', 'Sumatra', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('b8151439-71c0-41ee-87e7-1fcb155c0cf6', 'Surinam', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('2bf133ba-d0cb-411f-8e39-cd728e5bd72b', 'Sweden', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('2230cb43-fd24-4d14-bfac-dced6cbe3f23', 'Switzerland', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('d73cdb54-a47a-48a7-bc40-52a36e4ac0c8', 'Syria', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('8C2F0C28-2D8F-4DAF-DD92-D34561E753C3', 'Taiwan', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('5c73ec28-2d0b-4c93-af6d-99b5bc8ca67e', 'Tajikistan', configs.DEFAULT_SUBJECTS_ASIA_UUID),

    ('e4d3ed3d-ede0-4854-92be-4d151a0d168f', 'Tanzania', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('0194DA55-F6BE-413D-C288-EF201FC4F2D0', 'Thailand', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('1_Global_Spatial', 'Turkey', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('cf8ce7a3-868c-4311-9e4c-422e8d678244', 'Tunisia', configs.DEFAULT_SUBJECTS_AFRICA_UUID),

    ('b0054729-c5d6-40a6-89fa-6fce2fd1d2ca', 'Uganda', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('4A7C4A4A-FC66-411A-CDF4-870D153375F3', 'United Kingdom', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('2A1B75E6-8C79-49B9-873A-A2E006669691', 'United States', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('a8bd8294-91de-426a-89df-0f72352a6aaa', 'Uzbekistan', configs.DEFAULT_SUBJECTS_ASIA_UUID),

    ('a8e5898b-4f6a-4f1c-96e7-0d9da4da8a69', 'Venezuala', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),

    # This is for the Palestine Authority. Do this last, because we need to have migrated the
    # Palestinian authority first.
    ('4d42c6a0-4e19-48d5-bb1c-493fdec0dd60', 'East Jerusalem', 'bc6fd3bd-d934-0afe-60aa-51d63daf650a'),

    # This is the most weird context
    ('e1833684-f082-4708-8343-e170b4c4b221', 'International Space Station',  configs.DEFAULT_SUBJECTS_OFF_WORLD_UUID),
]

LEGACY_DATA_DATA_TYPES = {
    '3C110D75-C090-441C-BE21-BD681E1F9EE5': 'xsd:string',
}

LEGACY_MANIFEST_MAPPINGS = {
    'oc-gen:has-note': configs.PREDICATE_NOTE_UUID,
    'oc-gen:has-geo-overlay': configs.PREDICATE_GEO_OVERLAY_UUID,
}

# Data types for literal values.
LITERAL_DATA_TYPES = ['xsd:double', 'xsd:integer', 'xsd:boolean', 'xsd:date', 'xsd:string']



def legacy_to_new_item_class(legacy_class_id):
    """Looks up a new manifest object for a legacy_class_id"""
    uri = (
        'opencontext.org/vocabularies/oc-general/' 
        + legacy_class_id.split(':')[-1]
    )
    man_obj = AllManifest.objects.filter(
        uri=AllManifest().clean_uri(uri),
        context_id=configs.OC_GEN_VOCAB_UUID,
    ).first()
    return man_obj


def validate_subject_classes():
    """Validates the migration of subject classes"""
s_class_qs = OldManifest.objects.filter(
    item_type='subjects'
).order_by(
    'class_uri'
).distinct(
    'class_uri'
).values_list(
    'class_uri', 
    flat=True,
)
for old_class_id in s_class_qs:
    class_man_obj = legacy_to_new_item_class(old_class_id)
    if class_man_obj:
        continue
    print(
        f'Class_id: "{old_class_id}" missing new manifest object'
    )


def copy_attributes(
    old_man_obj, 
    new_dict={}, 
    attributes=MANIFEST_COPY_ATTRIBUTES, 
    time_attributes=TIME_ATTRIBUTES
):
    """Copies attributes from the old_man_obj to a new_man dict"""
    if not old_man_obj:
        return new_dict
    old_dict = old_man_obj.__dict__
    for attribute in attributes:
        act_val = old_dict.get(attribute)
        if act_val and attribute in time_attributes:
            if timezone.is_naive(act_val):
                act_val = pytz.utc.localize(act_val)
        new_dict[attribute] = act_val
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
        return AllManifest.objects.get(uuid=configs.OPEN_CONTEXT_PROJ_UUID)
    
    if isinstance(old_proj, OldManifest):
        # We passed an old manifest object to this function, but we need
        # a legacy project object.
        old_proj = Project.objects.get(uuid=old_proj.uuid)

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

    old_proj_man_obj = OldManifest.objects.get(uuid=old_proj_id)
    
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


def migrated_item_proj_check(old_man_obj, item_type):
    """Checks to see if an old manifest object is ok to migrate
    
    returns a tuple:

    new_manifest_object, new_manifest_project_obj
    """
    if old_man_obj.item_type != item_type:
        print(
            f'Legacy {old_man_obj.item_type}, {old_man_obj.uuid}: {old_man_obj.label} '
            f'is not the expected item_type {item_type}.'
        )
        return None, None
    old_id, new_uuid = update_old_id(old_man_obj.uuid)
    new_man_obj = AllManifest.objects.filter(
        uuid=new_uuid,
    ).first()
    if new_man_obj:
        # Congrats, we already migrated this, so skip all the rest.
        return new_man_obj, new_man_obj.project

    old_proj_id, new_proj_uuid = update_old_id(old_man_obj.project_uuid)
    project = AllManifest.objects.filter(uuid=new_proj_uuid).first()
    if not project:
        print(
            f'Legacy {old_man_obj.item_type}, {old_man_obj.uuid}: {old_man_obj.label} '
            f'missing project {old_proj_id}.'
        )
        return None, None
    return None, project


def make_new_meta_json_from_old_man_obj(old_man_obj):
    """Makes new meta_json from the old manifest object"""
    new_meta_json = {
        'legacy_id': old_man_obj.uuid,
        'legacy_source_id': old_man_obj.source_id,
    }
    old_dicts = [
        ('legacy_m_local', old_man_obj.localized_json),
        ('legacy_m_sup', old_man_obj.sup_json),
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
    return new_meta_json


def check_manage_manifest_duplicate(old_man_obj, man_dict):
    """Manages duplicate manifest entities, preserves old ids"""
    hash_id = AllManifest().make_hash_id(
        item_type=man_dict['item_type'], 
        data_type=man_dict['data_type'], 
        label=man_dict['label'],
        project_id=man_dict['project'].uuid, 
        context_id=man_dict['context'].uuid,
    )
    exist_m = AllManifest.objects.filter(hash_id=hash_id).first()
    if not exist_m:
        # Not a duplicate item.
        return None
    # Save the other old ID for this.
    exist_m_duplicate_ids = exist_m.meta_json.get('legacy_duplicate_ids', [])
    if str(old_man_obj.uuid) not in exist_m_duplicate_ids:
        exist_m_duplicate_ids.append(str(old_man_obj.uuid))
    exist_m.meta_json['legacy_duplicate_ids'] = exist_m_duplicate_ids
    exist_m.save()
    return exist_m


def migrate_legacy_predicate(old_man_obj):
    """Migrates a legacy predicate item, where old_man_obj is a predicate"""
    new_man_obj, new_project = migrated_item_proj_check(old_man_obj, 'predicates')
    if new_man_obj:
        # Congrats, we already migrated this, so skip all the rest.
        return new_man_obj
    if not new_project:
        # Skip out, can't find the related project.
        return None

    old_id, new_uuid = update_old_id(old_man_obj.uuid)
    old_pred = Predicate.objects.filter(uuid=old_id).first()
    if not old_pred:
        print(f'Legacy pred missing "{old_man_obj.uuid}" {old_man_obj.label}')
        return None

    data_type = old_pred.data_type
    if old_id in LEGACY_DATA_DATA_TYPES:
        data_type = LEGACY_DATA_DATA_TYPES[old_id]
    elif data_type != 'xsd:string':
        # Some of the very oldest dat in Open Context mixes data-types, 
        # These mixed type predicates usually have xsd:strings data-types
        # so only check for mixed types if the old_pred.data_type is
        # NOT a xsd:string. 
        p_dtypes = OldAssertion.objects.filter(
            predicate_uuid=old_id
        ).order_by(
            'object_type'
        ).distinct(
            'object_type'
        ).values_list('object_type', flat=True)
        if len(p_dtypes) > 1:
            literal_pred_dtypes = [d for d in p_dtypes if d in LITERAL_DATA_TYPES]
            ent_pred_dtypes = [d for d in p_dtypes if d not in LITERAL_DATA_TYPES]
            if len(ent_pred_dtypes) and not len(literal_pred_dtypes):
                # A happy case of all named entity data types.
                data_type = 'id'
            else:
                # We have some sort of combination of bad data types.
                print('-'*50)
                print(
                    f'Legacy pred: {old_man_obj.uuid}, {old_man_obj.label} '
                    'has too many data types: '
                )
                print(
                    f'Literal data types: {str(literal_pred_dtypes)} '
                    f'Named entity data types: {str(ent_pred_dtypes)} '
                )
                return None

    new_meta_json = make_new_meta_json_from_old_man_obj(old_man_obj)

    p_class_uuids = {
        'variable': configs.CLASS_OC_VARIABLES_UUID,
        'variables': configs.CLASS_OC_VARIABLES_UUID,
        'link': configs.CLASS_OC_LINKS_UUID,
        'links': configs.CLASS_OC_LINKS_UUID,
    }

    man_dict = {
        'publisher': new_project.publisher,
        'project': new_project,
        'item_class_id': p_class_uuids.get(
            old_man_obj.class_uri,
            configs.CLASS_OC_VARIABLES_UUID,
        ),
        'source_id': SOURCE_ID,
        'item_type': 'predicates',
        'data_type': data_type,
        'context': new_project,
        'meta_json': new_meta_json,
    }
    man_dict = copy_attributes(old_man_obj=old_man_obj, new_dict=man_dict)
    new_man_obj = check_manage_manifest_duplicate(old_man_obj, man_dict)
    if not new_man_obj:
        new_man_obj, _ = AllManifest.objects.get_or_create(
            uuid=new_uuid,
            defaults=man_dict
        )
        print(
            f'Migrated {new_man_obj.label} ({new_man_obj.uuid}) with: '
            f'{str(new_man_obj.meta_json)}'
        )
    save_legacy_id_object(new_man_obj, old_id)
    return new_man_obj


def migrate_legacy_type(old_man_obj):
    """Migrates a legacy type object """
    new_man_obj, new_project = migrated_item_proj_check(old_man_obj, 'types')
    if new_man_obj:
        # Congrats, we already migrated this, so skip all the rest.
        return new_man_obj
    if not new_project:
        # Skip out, can't find the related project.
        return None

    old_id, new_uuid = update_old_id(old_man_obj.uuid)

    old_type = OCtype.objects.filter(uuid=old_id).first()
    type_rank = 0
    old_man_pred = None
    if old_type:
        old_pred_uuid = old_type.predicate_uuid
        type_rank = old_type.rank
        old_man_pred = OldManifest.objects.filter(uuid=old_pred_uuid).first()
    if not old_man_pred:
        # Infer by use in Assertions
        old_ass = OldAssertion.objects.filter(object_uuid=old_id).first()
        if not old_ass:
            print(
                f'Old type {old_id} {old_man_obj.label} not used, no associated predicate.'
            )
            return None
        old_pred_uuid = old_ass.predicate_uuid
        old_man_pred = OldManifest.objects.filter(uuid=old_pred_uuid).first()
        print(
            f'Found legacy pred {old_pred_uuid} used with legacy subject {old_ass.uuid}.'
        )
    
    if not old_man_pred:
        print(
            f'Old predicate {old_pred_uuid} for type {old_id} {old_man_obj.label} '
            'not found.'
        )
        return None
    
    skos_note = None
    old_string = OCstring.objects.filter(uuid=old_type.content_uuid).first()
    if old_string and old_string.content != old_man_obj.label:
        skos_note = old_string.content

    # Get (or migrate) the new predicate.
    new_pred_obj = migrate_legacy_predicate(old_man_pred)
    if not new_pred_obj:
        print(
            f'New predicate migrated from {old_pred_uuid}, {old_man_pred.label} '
            f'for type {old_id} {old_man_obj.label} not found.'
        )
        return None
    # Oh my god, we finally have what we need to migrate!
    new_meta_json = make_new_meta_json_from_old_man_obj(old_man_obj)
    new_meta_json['legacy_oc_predicate_uuid'] = old_pred_uuid
    new_meta_json['legacy_oc_string_uuid'] = old_type.content_uuid

    man_dict = {
        'publisher': new_project.publisher,
        'project': new_project,
        'source_id': SOURCE_ID,
        'item_type': 'types',
        'data_type': 'id',
        'context': new_pred_obj,  # The predicate object is the context
        'meta_json': new_meta_json,
    }
    man_dict = copy_attributes(old_man_obj=old_man_obj, new_dict=man_dict)
    new_man_obj = check_manage_manifest_duplicate(old_man_obj, man_dict)
    if not new_man_obj:
        new_man_obj, _ = AllManifest.objects.get_or_create(
            uuid=new_uuid,
            defaults=man_dict
        )
        print(
            f'Migrated {new_man_obj.label} ({new_man_obj.uuid}) with: '
            f'{str(new_man_obj.meta_json)}'
        )
    save_legacy_id_object(new_man_obj, old_id)

    if not skos_note:
        # We're done. Skip out now.
        return new_man_obj

    # Add the skos-note.
    utilities.add_string_assertion_simple(
        subject_obj=new_man_obj,
        predicate_id=configs.PREDICATE_SKOS_NOTE_UUID,
        str_content=skos_note,
        publisher_id=new_man_obj.publisher.uuid,
        project_id=new_man_obj.project.uuid,
        source_id=SOURCE_ID,
    )
    return new_man_obj


def migrate_legacy_person(old_man_obj):
    """Migrates a legacy type object """
    new_man_obj, new_project = migrated_item_proj_check(old_man_obj, 'persons')
    if new_man_obj:
        # Congrats, we already migrated this, so skip all the rest.
        return new_man_obj
    if not new_project:
        # Skip out, can't find the related project.
        return None

    old_id, new_uuid = update_old_id(old_man_obj.uuid)

    old_pers = Person.objects.filter(uuid=old_id).first()
    if not old_pers:
        # Missing a critically needed record.
        print(
            f'Old person {old_id} {old_man_obj.label} missing person object.'
        )
        return None

    # We have what we need, now go forth and migrate to a new object.
    new_meta_json = make_new_meta_json_from_old_man_obj(old_man_obj)

    person_attributes = [
        'combined_name',
        'surname',
        'given_name',
        'initials',
        'mid_init',
    ]
    new_meta_json = copy_attributes(
        old_man_obj=old_pers, 
        new_dict=new_meta_json, 
        attributes=person_attributes, 
        time_attributes=[]
    )

    # Mapping of legacy foaf classes to the new class ids.
    foaf_classes = {
        '': configs.CLASS_FOAF_PERSON_UUID,
        'foaf:Person': configs.CLASS_FOAF_PERSON_UUID,
        'foaf:Organization': configs.CLASS_FOAF_ORGANIZATION_UUID,
        'foaf:Group': configs.CLASS_FOAF_GROUP_UUID,
    }

    man_dict = {
        'publisher': new_project.publisher,
        'project': new_project,
        'item_class_id': foaf_classes.get(
            old_man_obj.class_uri, 
            configs.CLASS_FOAF_PERSON_UUID
        ),
        'source_id': SOURCE_ID,
        'item_type': 'persons',
        'data_type': 'id',
        'context': new_project,
        'meta_json': new_meta_json,
    }
    man_dict = copy_attributes(old_man_obj=old_man_obj, new_dict=man_dict)
    new_man_obj = check_manage_manifest_duplicate(old_man_obj, man_dict)
    if not new_man_obj:
        new_man_obj, _ = AllManifest.objects.get_or_create(
            uuid=new_uuid,
            defaults=man_dict
        )
        print(
            f'Migrated {new_man_obj.label} ({new_man_obj.uuid}) with: '
            f'{str(new_man_obj.meta_json)}'
        )
    save_legacy_id_object(new_man_obj, old_id)
    return new_man_obj


def migrate_legacy_document(old_man_obj):
    """Migrates a legacy type object """
    new_man_obj, new_project = migrated_item_proj_check(old_man_obj, 'documents')
    if new_man_obj:
        # Congrats, we already migrated this, so skip all the rest.
        return new_man_obj
    if not new_project:
        # Skip out, can't find the related project.
        return None

    old_id, new_uuid = update_old_id(old_man_obj.uuid)

    old_doc = OCdocument.objects.filter(uuid=old_id).first()
    if not old_doc:
        # Missing a critically needed record.
        print(
            f'Old doc {old_id} {old_man_obj.label} missing document object.'
        )
        return None

    # We have what we need, now go forth and migrate to a new object.
    new_meta_json = make_new_meta_json_from_old_man_obj(old_man_obj)

    man_dict = {
        'publisher': new_project.publisher,
        'project': new_project,
        'source_id': SOURCE_ID,
        'item_type': 'documents',
        'data_type': 'id',
        'context': new_project,
        'meta_json': new_meta_json,
    }
    man_dict = copy_attributes(old_man_obj=old_man_obj, new_dict=man_dict)
    new_man_obj = check_manage_manifest_duplicate(old_man_obj, man_dict)
    if not new_man_obj:
        new_man_obj, _ = AllManifest.objects.get_or_create(
            uuid=new_uuid,
            defaults=man_dict
        )
        print(
            f'Migrated {new_man_obj.label} ({new_man_obj.uuid}) with: '
            f'{str(new_man_obj.meta_json)}'
        )
    save_legacy_id_object(new_man_obj, old_id)

    # Add the document contents.
    utilities.add_string_assertion_simple(
        subject_obj=new_man_obj,
        predicate_id=configs.PREDICATE_SCHEMA_ORG_TEXT_UUID,
        str_content=old_doc.content,
        publisher_id=new_man_obj.publisher.uuid,
        project_id=new_man_obj.project.uuid,
        source_id=SOURCE_ID,
    )
    return new_man_obj


def migrate_legacy_media_file(new_man_obj, old_mediafile_obj, skip_deference=True):
    """Gets or creates an icon from an icon_uri (also its file uri)"""
    # Get or make a manifest item for the icon itself.
    if isinstance(old_mediafile_obj.sup_json, dict):
        meta_json = old_mediafile_obj.sup_json.copy()
    else:
        meta_json = {}
    
    meta_json['legacy_file_type'] = old_mediafile_obj.file_type
    meta_json['legacy_source_id'] = old_mediafile_obj.source_id

    res_type_mappings = {
        'oc-gen:archive': (configs.OC_RESOURCE_ARCHIVE_UUID, 0),
        'oc-gen:fullfile': (configs.OC_RESOURCE_FULLFILE_UUID, 0),
        'oc-gen:hero': (configs.OC_RESOURCE_HERO_UUID, 0),
        'oc-gen:ia-archive': (configs.OC_RESOURCE_IA_FULLFILE_UUID, 0),
        'oc-gen:ia-fullfile': (configs.OC_RESOURCE_IA_FULLFILE_UUID, 0),
        'oc-gen:iiif': (configs.OC_RESOURCE_IIIF_UUID, 0),
        'oc-gen:nexus-3d': (configs.OC_RESOURCE_NEXUS_3D_UUID, 0),
        'oc-gen:preview': (configs.OC_RESOURCE_PREVIEW_UUID, 0),
        'oc-gen:preview-archived': (configs.OC_RESOURCE_PREVIEW_UUID, 100),
        'oc-gen:thumbnail':  (configs.OC_RESOURCE_THUMBNAIL_UUID, 0),
        'oc-gen:thumbnail-archived': (configs.OC_RESOURCE_THUMBNAIL_UUID, 100),
        'oc-gen:x3dom-model': (configs.OC_RESOURCE_X3DOM_MODEL_UUID, 0),
        'oc-gen:x3dom-texture': (configs.OC_RESOURCE_X3DOM_TEXTURE_UUID, 0),
    }
    extension_mappings = [
        ('.jpg', configs.MEDIA_TYPE_JPEG_UUID,),
        ('.png', configs.MEDIA_TYPE_PNG_UUID,),
        ('.tif', configs.MEDIA_TYPE_TIFF_UUID,),
        ('.tiff', configs.MEDIA_TYPE_TIFF_UUID,),
        ('.zip', configs.MEDIA_TYPE_ZIP_UUID,),
    ]

    if not res_type_mappings.get(old_mediafile_obj.file_type):
        raise ValueError(f'Cannot find resource type mapping for {old_mediafile_obj.file_type}')
        
    resourcetype_id, rank =  res_type_mappings.get(old_mediafile_obj.file_type)
    rank += old_mediafile_obj.highlight

    # Dictionary for the new media file object.
    media_file_dict = {
        'item': new_man_obj,
        'project': new_man_obj.project,
        'resourcetype_id': resourcetype_id,
        'rank': rank,
        'source_id': SOURCE_ID,
        'uri': old_mediafile_obj.file_uri,
        'meta_json': meta_json,
    }

    if resourcetype_id == configs.OC_RESOURCE_IIIF_UUID:
        media_file_dict['filesize'] = 1
        media_file_dict['mediatype_id'] = configs.MEDIA_TYPE_JSON_LD_UUID
    
    if old_mediafile_obj.filesize > 0:
        media_file_dict['filesize'] = old_mediafile_obj.filesize

    if old_mediafile_obj.mime_type_uri:
        media_type = old_mediafile_obj.mime_type_uri.replace(
            'http://purl.org/NET/mediatypes/',
            ''
        )
        new_mt = AllManifest.objects.filter(
            item_type='media-types',
            meta_json__template=media_type,
        ).first()
        if not new_mt and media_type.endswith('geo+json'):
            # There's been some churn in the geojson media type,
            # so make sure we're consistent and map to the current
            # media type.
            new_mt = AllManifest.objects.filter(
                uuid=configs.MEDIA_TYPE_GEO_JSON_UUID,
                item_type='media-types',
            ).first()
        elif not new_mt and media_type.endswith('x3d+xml'):
            new_mt = AllManifest.objects.filter(
                uuid=configs.MEDIA_TYPE_XML_UUID,
                item_type='media-types',
            ).first()
        if new_mt:
            media_file_dict['mediatype_id'] = new_mt.uuid

    if skip_deference and not media_file_dict.get('filesize'):
        # Skip derefencing, add the filesize as 1, an wrong answer
        media_file_dict['filesize'] = 1

    if skip_deference and not media_file_dict.get('mediatype_id'):
        # Attempt to figure out the media type from the extension.
        lc_uri = old_mediafile_obj.file_uri.lower()
        for ext, mediatype_id in extension_mappings:
            if not lc_uri.endswith(ext):
                continue
            media_file_dict['mediatype_id'] = mediatype_id

    res_obj, _ = AllResource.objects.get_or_create(
        uuid=AllResource().primary_key_create(
            item_id=new_man_obj.uuid,
            resourcetype_id=resourcetype_id,
            rank=rank,
        ),
        defaults=media_file_dict,
    )
    return res_obj


def migrate_legacy_project_hero_media(old_project_uuid, new_proj_man_obj):
    """Migrates legacy project hero media to a new media resource."""
    old_heros_qs = Mediafile.objects.filter(
        uuid=old_project_uuid, 
        file_type='oc-gen:hero'
    )
    for old_mediafile_obj in old_heros_qs:
        res_obj = migrate_legacy_media_file(new_proj_man_obj, old_mediafile_obj)
        print(f'Migrated project hero: {res_obj.uri} ({res_obj.uuid})')


def migrate_legacy_media(old_man_obj):
    """Migrates a legacy type object """
    type_mapping_ranks = {}
    new_man_obj, new_project = migrated_item_proj_check(old_man_obj, 'media')

    old_id, new_uuid = update_old_id(old_man_obj.uuid)
    # Get the queryset for the old manifest files associated with this old
    # media manifest object.
    old_media_files = Mediafile.objects.filter(uuid=old_id)
    if new_man_obj:
        # Congrats, we already migrated this, so skip all the rest.
        # But first we want to make sure we actually do have all the associated
        # files.
        for old_mediafile_obj in old_media_files:
            # Now migrate all the old file objects for this media item.
            if not old_mediafile_obj.file_type in type_mapping_ranks:
                type_mapping_ranks[old_mediafile_obj.file_type] = 0
            else:
                type_mapping_ranks[old_mediafile_obj.file_type] += 1
                old_mediafile_obj.highlight += type_mapping_ranks[old_mediafile_obj.file_type]
            _ = migrate_legacy_media_file(new_man_obj, old_mediafile_obj)
        return new_man_obj
    if not new_project:
        # Skip out, can't find the related project.
        return None

    if not len(old_media_files):
        # Missing a critically needed associated media files
        print(
            f'Old media {old_id} {old_man_obj.label} missing mediafile objects.'
        )
        return None

    # We have what we need, now go forth and migrate to a new object.
    new_meta_json = make_new_meta_json_from_old_man_obj(old_man_obj)

    media_class_mappings = {
        'oc-gen:3d-model': configs.CLASS_OC_3D_MEDIA,
        'oc-gen:data-table': configs.CLASS_OC_DATATABLE_MEDIA,
        'oc-gen:document-file': configs.CLASS_OC_DOCUMENT_MEDIA,
        'oc-gen:geospatial-file': configs.CLASS_OC_GIS_MEDIA,
        'oc-gen:gis-vector-file': configs.CLASS_OC_VECTOR_GIS_MEDIA,
        'oc-gen:image': configs.CLASS_OC_IMAGE_MEDIA,
        'oc-gen:video': configs.CLASS_OC_VIDEO_MEDIA,
    }

    # This helps determin media item class based on the mime-type of the
    # files associated with a media resource.
    media_class_file_tups = [
        ('oc-gen:fullfile', 'application/pdf', configs.CLASS_OC_DOCUMENT_MEDIA,),
        ('oc-gen:fullfile', 'image', configs.CLASS_OC_IMAGE_MEDIA,),
        ('oc-gen:fullfile', 'text/csv', configs.CLASS_OC_DATATABLE_MEDIA,),
        ('oc-gen:fullfile', 'spreadsheetml', configs.CLASS_OC_DATATABLE_MEDIA,),
        ('oc-gen:x3dom-model', 'x3d+xml', configs.CLASS_OC_3D_MEDIA,),
        ('oc-gen:preview', 'vnd.geo+json', configs.CLASS_OC_VECTOR_GIS_MEDIA,),
    ]
    
    media_class_id = media_class_mappings.get(old_man_obj.class_uri)
    if not media_class_id:
        for old_f in old_media_files:
            for file_type, f_type, class_id in media_class_file_tups:
                if not old_f.file_type == file_type:
                    continue
                if not f_type in old_f.mime_type_uri:
                    continue
                media_class_id = class_id

    if not media_class_id:
        print(
            f'Old media {old_id} {old_man_obj.label} missing mediafile item class {old_man_obj.class_uri}.'
        )
        return None

    man_dict = {
        'publisher': new_project.publisher,
        'project': new_project,
        'item_class_id': media_class_id,
        'source_id': SOURCE_ID,
        'item_type': 'media',
        'data_type': 'id',
        'context': new_project,
        'meta_json': new_meta_json,
    }
    man_dict = copy_attributes(old_man_obj=old_man_obj, new_dict=man_dict)
    new_man_obj = check_manage_manifest_duplicate(old_man_obj, man_dict)
    if not new_man_obj:
        new_man_obj, _ = AllManifest.objects.get_or_create(
            uuid=new_uuid,
            defaults=man_dict
        )
        print(
            f'Migrated {new_man_obj.label} ({new_man_obj.uuid}) with: '
            f'{str(new_man_obj.meta_json)}'
        )
    save_legacy_id_object(new_man_obj, old_id)

    for old_mediafile_obj in old_media_files:
        # Now migrate all the old file objects for this media item.
        if not old_mediafile_obj.file_type in type_mapping_ranks:
            type_mapping_ranks[old_mediafile_obj.file_type] = 0
        else:
            type_mapping_ranks[old_mediafile_obj.file_type] += 1
            old_mediafile_obj.highlight += type_mapping_ranks[old_mediafile_obj.file_type]
        _ = migrate_legacy_media_file(new_man_obj, old_mediafile_obj)

    return new_man_obj


def migrate_legacy_subject(old_man_obj, parent_new_id=None):
    """Migrates a legacy type object """
    new_man_obj, new_project = migrated_item_proj_check(old_man_obj, 'subjects')
    if new_man_obj:
        # Congrats, we already migrated this, so skip all the rest.
        return new_man_obj
    if not new_project:
        # Skip out, can't find the related project.
        return None

    old_id, new_uuid = update_old_id(old_man_obj.uuid)
    parent_old_id = None
    if not parent_new_id:
        p_ass = OldAssertion.objects.filter(
            object_uuid=old_id, 
            predicate_uuid=OldAssertion.PREDICATES_CONTAINS
        ).exclude(
            uuid=old_id
        ).first()
        if not p_ass:
            print(
                f'Cannot find old containment relation for '
                f'{old_man_obj.uuid} {old_man_obj.label}'
            )
            return None
        parent_old_id = p_ass.uuid
        parent_old_man_obj = OldManifest.objects.filter(uuid=parent_old_id).first()
        if not parent_old_man_obj:
            print(
                f'Cannot find old manifest item {parent_old_id} a '
                f'parent of {old_man_obj.uuid} {old_man_obj.label}'
            )
            return None
        new_parent_obj = migrate_legacy_subject(parent_old_man_obj)
    else:
        new_parent_obj = AllManifest.objects.filter(uuid=parent_new_id).first()
    
    if not new_parent_obj:
        print(
            f'Cannot find new manifest item new_id: {parent_new_id}, '
            f'old id: {parent_old_id}, a '
            f'parent of {old_man_obj.uuid} {old_man_obj.label}'
        )
        return None

    # We have what we need, now go forth and migrate to a new object.
    new_meta_json = make_new_meta_json_from_old_man_obj(old_man_obj)
    man_dict = {
        'publisher': new_project.publisher,
        'project': new_project,
        'item_class': legacy_to_new_item_class(old_man_obj.class_uri),
        'source_id': SOURCE_ID,
        'item_type': 'subjects',
        'data_type': 'id',
        'context': new_parent_obj,
        'meta_json': new_meta_json,
    }
    man_dict = copy_attributes(old_man_obj=old_man_obj, new_dict=man_dict)
    new_man_obj = check_manage_manifest_duplicate(old_man_obj, man_dict)
    if not new_man_obj:
        new_man_obj, _ = AllManifest.objects.get_or_create(
            uuid=new_uuid,
            defaults=man_dict
        )
        print(
            f'Migrated {new_man_obj.label} ({new_man_obj.uuid}) with: '
            f'{str(new_man_obj.meta_json)}'
        )
    save_legacy_id_object(new_man_obj, old_id)

    assert_dict = {
        'project': new_man_obj.project,
        'publisher': new_man_obj.publisher,
        'source_id': SOURCE_ID,
        'subject': new_parent_obj,
        'predicate_id': configs.PREDICATE_CONTAINS_UUID,
        'object': new_man_obj,
    }
    ass_obj, _ = AllAssertion.objects.get_or_create(
        uuid=AllAssertion().primary_key_create(
            subject_id=assert_dict['subject'].uuid,
            predicate_id=assert_dict['predicate_id'],
            object_id=assert_dict['object'].uuid,
        ),
        defaults=assert_dict
    )
    print(
        f'Assertion {ass_obj.uuid}: '
        f'is {ass_obj.subject.label} [{ass_obj.subject.uuid}]'
        f'-> {ass_obj.predicate.label} [{ass_obj.predicate.uuid}]'
        f'-> {ass_obj.object.label} [{ass_obj.object.uuid}]'
    )
    return new_man_obj


def get_new_manifest_obj_from_old_id_db(old_id):
    """Gets a new manifest obj corresponding to an old id, using the DB"""
    new_mapping_id = LEGACY_MANIFEST_MAPPINGS.get(old_id)
    if new_mapping_id:
        # We have a configured mapping between an old_id and a new id.
        return AllManifest.objects.filter(uuid=new_mapping_id).first()

    old_man_obj = OldManifest.objects.filter(uuid=old_id).first()
    if not old_man_obj:
        return None
    item_type_functions = {
        'predicates': migrate_legacy_predicate,
        'types': migrate_legacy_type,
        'persons': migrate_legacy_person,
        'documents': migrate_legacy_document,
        'media': migrate_legacy_media,
        'subjects': migrate_legacy_subject,
        'projects': migrate_old_project,
    }
    item_type_function = item_type_functions.get(old_man_obj.item_type)
    if not item_type_function:
        return None
    # The new manifest object returned from an item_type specific function.
    new_man_obj = item_type_function(old_man_obj)
    return new_man_obj


def get_cache_new_manifest_obj_from_old_id(old_id, use_cache=True):
    """Gets and optionally caches a new manifest obj corresponding to an old_id"""
    if not use_cache:
        return get_new_manifest_obj_from_old_id_db(old_id)
    hash_obj = hashlib.sha1()
    hash_obj.update(str(old_id).encode('utf-8'))
    hash_id = hash_obj.hexdigest()
    cache_key = f'l_id_allman_{hash_id}'
    cache = caches['memory']
    new_man_obj = cache.get(cache_key)
    if new_man_obj is not None:
        # We've already cached this, so returned the cached object
        return new_man_obj
    new_man_obj = get_new_manifest_obj_from_old_id_db(old_id)
    try:
        cache.set(cache_key, new_man_obj)
    except:
        pass
    return new_man_obj


def migrate_obs_metadata_db(project_uuid, source_id, obs_num):
    """Gets legacy metadata object for an observation node, that
        provides some context on assertions made in an observation
    """
    obs_meta = ObsMetadata.objects.filter(
        project_uuid=project_uuid,
        source_id=source_id,
        obs_num=obs_num,
    ).first()
    if not obs_meta:
        # Return the default observation.
        return AllManifest.objects.get(uuid=configs.DEFAULT_OBS_UUID)
    
    # Make a more unique ID for an observation so as to make it easier
    # to make a deterministically generated true uuid for the new
    # observation manifest object.
    old_id_seed = f'obs-{project_uuid}-{source_id}-obs-{obs_num}'

    # For observation new manifest object, determinstically make a
    # new_uuid from the old_id_seed
    _, new_uuid = update_old_id(old_id_seed)

    _, new_proj_uuid = update_old_id(project_uuid)
    # Get the new project, and fail loudly if we can't find it.
    project = AllManifest.objects.get(uuid=new_proj_uuid)

    man_dict = {
        'publisher': project.publisher,
        'project': project,
        'source_id': SOURCE_ID,
        'item_type': 'observations',
        'data_type': 'id',
        'context': project,
        'label': obs_meta.label.strip(),
        'meta_json': {
            'sort': obs_num,
            'legacy_oc_obsmetadata_id': obs_meta.pk,
            'legacy_source_id': obs_meta.source_id,
            'legacy_project_uuid': obs_meta.project_uuid,
            'legacy_updated': obs_meta.updated.date().isoformat(),
            'legacy_note': obs_meta.note,
        }
    }

    hash_id = AllManifest().make_hash_id(
        item_type=man_dict['item_type'],
        data_type=man_dict['data_type'],
        label=man_dict['label'],
        project_id=project.uuid,
        context_id=project.uuid,
        path=str(man_dict['meta_json'].get('sort', ''))
    )
    new_man_obj = AllManifest.objects.filter(hash_id=hash_id).first()
    if new_man_obj:
        # We already have an observation object that "counts" as
        # the same thing we're looking for.
        return new_man_obj

    new_man_obj, _ = AllManifest.objects.get_or_create(
        uuid=new_uuid,
        defaults=man_dict
    )
    print(
        f'Migrated {new_man_obj.label} ({new_man_obj.uuid}) with: '
        f'{str(new_man_obj.meta_json)}'
    )
    skos_note = None
    if obs_meta.note and obs_meta.note != new_man_obj.label:
        skos_note = obs_meta.note

    if not skos_note:
        # We're done. Skip out now.
        return new_man_obj

    # Add the skos-note.
    utilities.add_string_assertion_simple(
        subject_obj=new_man_obj,
        predicate_id=configs.PREDICATE_SKOS_NOTE_UUID,
        str_content=skos_note,
        publisher_id=new_man_obj.publisher.uuid,
        project_id=new_man_obj.project.uuid,
        source_id=SOURCE_ID,
    )
    return new_man_obj


def get_cache_migrated_obs_metadata(project_uuid, source_id, obs_num, use_cache=True):
    """Gets legacy metadata object for an observation node, that
        provides some context on assertions made in an observation
    """
    if not use_cache:
        return migrate_obs_metadata_db(project_uuid, source_id, obs_num)
    cache_key = f'obs-{project_uuid}-{source_id.replace(" ", "")}-obs-{obs_num}'
    cache = caches['memory']
    new_obs_man_obj = cache.get(cache_key)
    if new_obs_man_obj is not None:
        # We've already cached this, so returned the cached object
        return new_obs_man_obj
    new_obs_man_obj = migrate_obs_metadata_db(project_uuid, source_id, obs_num)
    try:
        cache.set(cache_key, new_obs_man_obj)
    except:
        pass
    return new_obs_man_obj


def migrate_legacy_assertion(old_assert, project=None, index=None, total_count=None, use_cache=True):
    """Migrates a legacy assertion object"""
    subject_obj = get_cache_new_manifest_obj_from_old_id(
        old_assert.uuid, 
        use_cache=use_cache
    )
    predicate_obj = get_cache_new_manifest_obj_from_old_id(
        old_assert.predicate_uuid,
        use_cache=use_cache
    )
    if not subject_obj or not predicate_obj:
        # Missing needed data.
        return None
    
    # Get or migrate to a new observation manifest object.
    observation_obj = get_cache_migrated_obs_metadata(
        old_assert.project_uuid,
        old_assert.source_id, 
        old_assert.obs_num, 
        use_cache=use_cache,
    )

    if isinstance(old_assert.sup_json, dict):
        meta_json = old_assert.sup_json.copy()
    else:
        meta_json = {}

    # The legacy data didn't have a well controlled vocabulary for 'object_type' so default to
    # id if it wasn't specifically a literal object type.
    if old_assert.object_type not in ['xsd:double', 'xsd:integer', 'xsd:boolean', 'xsd:date', 'xsd:string']:
        old_assert.object_type = 'id'
    
    # Make a dictionary for the new assertion object.
    assert_dict = {
        'project_id': project.uuid,
        'publisher_id': project.publisher.uuid,
        'source_id': SOURCE_ID,
        'subject_id': subject_obj.uuid,
        'predicate_id': predicate_obj.uuid,
        'observation_id': observation_obj.uuid,
        'sort': float(old_assert.sort),
        'visible': (old_assert.visibility > 0),
        'created': old_assert.created,
        'object_id': configs.DEFAULT_NULL_OBJECT_UUID,
        'obj_string': None,
        'obj_boolean': None,
        'obj_integer': None,
        'obj_double': None,
        'obj_datetime': None,
    }

    if predicate_obj.data_type == 'xsd:string' and old_assert.object_type == 'xsd:string':
        old_str_obj = OCstring.objects.filter(uuid=old_assert.object_uuid).first()
        if not old_str_obj:
            # Skip out. We can't find a string for this assertion.
            return None
        assert_dict['obj_string'] = old_str_obj.content.strip()
        meta_json['legacy_string_uuid'] = old_str_obj.uuid
    elif predicate_obj.data_type == 'xsd:string' and old_assert.object_type == 'id':
        # We have a string predicate, but an id object type. Use the label for the
        # old manifest object as the string content.
        old_man_obj = OldManifest.objects.filter(uuid=old_assert.object_uuid).first()
        if not old_man_obj:
            # Skip out. We can't find a string for this assertion.
            return None
        assert_dict['obj_string'] = old_man_obj.label.strip()
        meta_json['legacy_object_uuid'] = old_man_obj.uuid
        old_assert.object_type = 'xsd:string'
    elif (
            predicate_obj.data_type == 'xsd:string' 
            and old_assert.object_type in ['xsd:double', 'xsd:integer', 'xsd:boolean', 'xsd:date',]
         ):
        # We have a string predicate a different kind of literal.
        if old_assert.data_num:
            meta_json['legacy_object_data_num'] = old_assert.data_num
            assert_dict['obj_string'] = str(old_assert.data_num)
        elif old_assert.data_date:
            meta_json['legacy_object_data_date'] = old_assert.data_date.date().isoformat()
            assert_dict['obj_string'] = old_assert.data_date.date().isoformat()
        old_assert.object_type = 'xsd:string'
    elif predicate_obj.data_type == 'xsd:boolean':
        assert_dict['obj_boolean'] = bool(old_assert.data_num)
    elif predicate_obj.data_type == 'xsd:integer':
        assert_dict['obj_integer'] = int(old_assert.data_num)
    elif predicate_obj.data_type == 'xsd:double':
        assert_dict['obj_double'] = old_assert.data_num
    elif predicate_obj.data_type == 'xsd:date':
        assert_dict['obj_datetime'] = old_assert.data_date
    else:
        object_obj = get_cache_new_manifest_obj_from_old_id(
            old_assert.object_uuid,
            use_cache=use_cache,
        )
        if not object_obj:
            # Skip out. We can't find a string for this assertion.
            return None
        assert_dict['object_id'] = object_obj.uuid

    if predicate_obj.data_type != old_assert.object_type:
        raise ValueError(
            f'Assertion {old_assert.hash_id} has object_type {old_assert.object_type} '
            f'but should be {predicate_obj.data_type}'
        )
    
    # This list specifies keys for parts of the assert_dict that will be used
    # to generate the new assertion's uuid deterministically
    uuid_dict_keys = [
        'subject_id',
        'predicate_id',
        'obj_string',
        'observation_id',
        'object_id',
        'obj_string',
        'obj_boolean',
        'obj_integer',
        'obj_double',
        'obj_datetime',
    ]
    uuid_args = {k:assert_dict.get(k) for k in uuid_dict_keys}

    ass_obj, _ = AllAssertion.objects.get_or_create(
        # Make the new assertion object with a deterministically
        # generated uuid primary key.
        uuid=AllAssertion().primary_key_create(
            **uuid_args,
        ),
        defaults=assert_dict
    )
    if index is not None and total_count is not None:
        num_digits = len(str(total_count))
        print(f'{index:07}-of-{total_count:07}' + '-'*54)
    else:
        print('-'*72)
    print(
        f'Assertion {ass_obj.uuid}: '
        f'is {ass_obj.subject.label} [{ass_obj.subject.uuid}]'
        f'-> {ass_obj.predicate.label} [{ass_obj.predicate.uuid}]'
        f'-> {ass_obj.object.label} [{ass_obj.object.uuid}] '
        f'Str: {ass_obj.obj_string} '
        f'Bool: {ass_obj.obj_boolean} '
        f'Int: {ass_obj.obj_integer} '
        f'Double: {ass_obj.obj_double} '
        f'Date: {ass_obj.obj_datetime}'
    )
    return ass_obj


def migrate_root_subjects(root_subjects=LEGACY_ROOT_SUBJECTS):
    """Migrates tuples of root subject items"""
    for old_id, label, parent_new_id in root_subjects:
        old_man_obj = OldManifest.objects.filter(uuid=old_id).first()
        if not old_man_obj:
            print(
                f'Cannot find old manifest {old_id} {label}'
            )
            continue
        migrate_legacy_subject(old_man_obj, parent_new_id)


def migrate_legacy_projects():
    """Migrates project entities to the new schema"""
    for old_proj in Project.objects.all().exclude(uuid='0'):
        new_proj = migrate_old_project(old_proj)
        migrate_legacy_link_annotations(old_proj.uuid)


def migrate_legacy_predicates_for_project(project_uuid='0'):
    """Migrates a queryset of manifest predicates items"""
    old_qs = OldManifest.objects.filter(
        item_type='predicates',
        project_uuid=project_uuid
    )
    for old_man_obj in old_qs:
        new_man_obj = migrate_legacy_predicate(old_man_obj)


def migrate_legacy_types_for_project(project_uuid='0'):
    """Migrates a queryset of manifest types items """
    old_qs = OldManifest.objects.filter(
        item_type='types',
        project_uuid=project_uuid
    )
    for old_man_obj in old_qs:
        new_man_obj = migrate_legacy_type(old_man_obj)


def migrate_legacy_persons_for_project(project_uuid='0'):
    """Migrates a queryset of manifest persons items"""
    if project_uuid == '0':
        return None
    old_qs = OldManifest.objects.filter(
        item_type='persons',
        project_uuid=project_uuid
    )
    for old_man_obj in old_qs:
        new_man_obj = migrate_legacy_person(old_man_obj)


def migrate_legacy_documents_for_project(project_uuid='0'):
    """Migrates a queryset of manifest documents items"""
    old_qs = OldManifest.objects.filter(
        item_type='documents',
        project_uuid=project_uuid
    )
    for old_man_obj in old_qs:
        new_man_obj = migrate_legacy_document(old_man_obj)


def migrate_legacy_media_for_project(project_uuid='0'):
    """Migrates a queryset of manifest media items"""
    old_qs = OldManifest.objects.filter(
        item_type='media',
        project_uuid=project_uuid
    )
    for old_man_obj in old_qs:
        new_man_obj = migrate_legacy_media(old_man_obj)


def migrate_legacy_subjects_for_project(project_uuid='0'):
    """Migrates a queryset of manifest subjects items"""
    old_qs = OldManifest.objects.filter(
        item_type='subjects',
        project_uuid=project_uuid
    )
    for old_man_obj in old_qs:
        new_man_obj = migrate_legacy_subject(old_man_obj)


def migrate_legacy_id(old_id_obj, use_cache=True):
    """Migrates a legacy StableIdentifier object"""
    man_obj = get_cache_new_manifest_obj_from_old_id(
        old_id_obj.uuid, 
        use_cache=use_cache
    )
    if not man_obj:
        # Missing needed data.
        return None
    id_dict = {
        'item': man_obj,
        'scheme': old_id_obj.stable_type.lower(),
        'id': old_id_obj.stable_id,
        'meta_json': {
            'legacy_hash_id': old_id_obj.hash_id,
        }
    }
    new_id_obj, _ = AllIdentifier.objects.get_or_create(
        # Make the new assertion object with a deterministically
        # generated uuid primary key.
        uuid=AllIdentifier().primary_key_create(
            item_id=man_obj.uuid, scheme=id_dict['scheme'],
        ),
        defaults=id_dict
    )
    print(f'Migrated: {new_id_obj}')
    return new_id_obj


def migrate_legacy_identifiers_for_project(project_uuid='0'):
    """Migrates a queryset of old stable identifier objects"""
    old_qs = OldIdentifier.objects.filter(
        project_uuid=project_uuid
    )
    for old_id_obj in old_qs:
        new_id_obj = migrate_legacy_id(old_id_obj)


def migrate_legacy_assertions_for_project(project_uuid, use_cache=True):
    """Migrates the assertions for a project"""
    errors = []
    project = get_cache_new_manifest_obj_from_old_id(
        project_uuid, 
        use_cache=use_cache
    )
    if not project:
        print(f'Cannot find project {project_uuid}')
    # Get the count of the old assertions.
    old_assert_count = old_asserts_qs = OldAssertion.objects.filter(
        project_uuid=project_uuid
    ).exclude(
        predicate_uuid=OldAssertion.PREDICATES_CONTAINS
    ).count()

    old_asserts_qs = OldAssertion.objects.filter(
        project_uuid=project_uuid
    ).exclude(
        predicate_uuid=OldAssertion.PREDICATES_CONTAINS
    ).order_by(
        'uuid', 
        'obs_num', 
        'sort'
    ).iterator()
    i = 0
    for old_assert in old_asserts_qs:
        i += 1
        ass_obj = migrate_legacy_assertion(
            old_assert,
            project=project,
            use_cache=use_cache,
            index=i,
            total_count=old_assert_count,
        )
        if ass_obj:
            continue
        errors.append(old_assert)
    return errors


def migrate_legacy_assertions_from_csv(project_uuid, file_path=None, df=None, use_cache=True):
    """Migrates legacy assertions from a csv file"""
    errors = []
    project = get_cache_new_manifest_obj_from_old_id(
        project_uuid, 
        use_cache=use_cache
    )
    if df is None and file_path:
        df = pd.read_csv(file_path)
    old_assert_count = len(df.index)
    for i, row in df.iterrows():
        old_assert = OldAssertion.objects.filter(
            project_uuid=project_uuid,
            hash_id=row['hash_id'],
        ).first()
        if not old_assert:
            continue
        ass_obj = migrate_legacy_assertion(
            old_assert,
            project=project,
            use_cache=use_cache,
            index=(i + 1),
            total_count=old_assert_count,
        )
        if ass_obj:
            continue
        errors.append(old_assert)
    return errors


def save_old_assertions_to_csv(file_path, old_assertions, attribute_keys=None):
    """Saves old assertion objects to a csv output"""
    if not attribute_keys:
        attribute_keys = [
            'hash_id',
            'uuid',
            'predicate_uuid',
            'object_type',
            'object_uuid',
            'data_num',
            'data_date',
        ]
    data = {key:[] for key in attribute_keys}
    for old_assert in old_assertions:
        assert_dict = old_assert.__dict__
        for key in attribute_keys:
            key_val = assert_dict.get(key)
            if key == 'data_date':
                key_val = str(key_val)
            data[key].append(key_val)
    df = pd.DataFrame(data=data)
    df.to_csv(file_path, index=False)
    print('-'*72)
    print(f'Dataframe with {len(df.index)} rows output to: {file_path}')
    print('-'*72)
    return df


def migrate_legacy_manifest_for_project(project_uuid='0'):
    """Migrates main manifest item types for a project"""
    migrate_legacy_predicates_for_project(project_uuid)
    migrate_legacy_types_for_project(project_uuid)
    migrate_legacy_persons_for_project(project_uuid)
    migrate_legacy_documents_for_project(project_uuid)
    migrate_legacy_media_for_project(project_uuid)
    migrate_legacy_subjects_for_project(project_uuid)


def migrate_legacy_spacetime_for_item(new_man_obj, old_id):
    """Migrates legacy spacetime data for an new_manifest item with old_id"""
    outputs = []
    old_geo_qs = OldGeospace.objects.filter(uuid=old_id)
    old_event_qs = OldEvent.objects.filter(
        uuid=old_id
    ).order_by('earliest', 'latest')
    if not len(old_geo_qs) and not len(old_event_qs):
        # This item has no geospatial or event data to migrate.
        return None
    if not len(old_geo_qs):
        old_geos = [None]
    else:
        old_geos = [g for g in old_geo_qs]
    if not len(old_event_qs):
        old_events = [None]
    else:
        old_events = [e for e in old_event_qs]
    # Iterate over the cross product of these two lists.
    for o_geo, o_event in list(itertools.product(old_geos, old_events)):
        sp_tm_dict = {
            'item_id': new_man_obj.uuid,
            'earliest': None,
            'start': None,
            'stop': None,
            'latest': None,
            'latitude': None,
            'longitude': None,
            'geometry': None,
        }

        if o_geo:
            # We have a legacy geospatial record.
            sp_tm_dict['latitude'] = o_geo.latitude
            sp_tm_dict['longitude'] = o_geo.longitude
            geometry = {}
            geometry['type'] =  o_geo.ftype
            if o_geo.ftype != 'Point':
                # Make sure we have valid GeoJSON coordinate order.
                coord_obj = json.loads(o_geo.coordinates)
            else:
                # Make the coordinates for points.
                coord_obj = [float(o_geo.longitude), float(o_geo.latitude)]
            # Add the coordinates.
            geometry['coordinates'] = coord_obj
            sp_tm_dict['geometry'] = geometry

        if o_event:
            # We have a legacy chronological record.
            sp_tm_dict['earliest'] = o_event.earliest
            sp_tm_dict['start'] = o_event.start
            sp_tm_dict['stop'] = o_event.stop
            sp_tm_dict['latest'] = o_event.latest
        
        # Make the spacetime uuid using the sp_tm_dict for
        # kwargs
        spacetime_uuid = AllSpaceTime().primary_key_create(
            **sp_tm_dict
        )

        # Figure out the feature ID.
        sp_tm_dict['feature_id'] = AllSpaceTime().determine_feature_id(
            new_man_obj.uuid,
            exclude_uuid=spacetime_uuid,
        )

        meta_json = {}
        if o_geo:
            if o_geo.meta_type == 'oc-gen:geo-coverage':
                # This is a non-default event type.
                sp_tm_dict['event_class_id'] =  configs.OC_EVENT_TYPE_COVERAGE_UUID

            sp_tm_dict['geometry_type'] =  o_geo.ftype
            sp_tm_dict['geo_specificity'] =  o_geo.specificity
            meta_json['legacy_geo_hash_id'] = o_geo.hash_id
            meta_json['legacy_geo_feature_id'] = o_geo.feature_id
            meta_json['legacy_geo_source_id'] = o_geo.source_id
            if o_geo.note:
                meta_json['legacy_geo_note'] = o_geo.note
        if o_event:
            # Add legacy metadata to the meta_json.
            meta_json['legacy_event_hash_id'] = o_event.hash_id
            meta_json['legacy_event_event_id'] = o_event.event_id
            meta_json['legacy_event_feature_id'] = o_event.feature_id
            meta_json['legacy_event_source_id'] = o_event.source_id
            if o_event.note:
                meta_json['legacy_event_note'] = o_event.note

        sp_tm_dict['source_id'] = SOURCE_ID,
        sp_tm_dict['meta_json'] = meta_json

        new_space_time_obj, _ = AllSpaceTime.objects.get_or_create(
            uuid=spacetime_uuid,
            defaults=sp_tm_dict
        )
        print(
            f'SpaceTime object {new_space_time_obj.uuid} for '
            f'{new_space_time_obj.item.uuid} {new_space_time_obj.item.label} '
            f'({new_space_time_obj.start} - {new_space_time_obj.stop}) '
            f'({new_space_time_obj.latitude}, {new_space_time_obj.longitude}) '
        )
        outputs.append(new_space_time_obj)
    return outputs


def migrate_legacy_spacetime_for_project(project_uuid='0'):
    """Migrates legacy geospace and event data to new spacetime data"""
    old_geo_ids = OldGeospace.objects.filter(
        project_uuid=project_uuid,
    ).order_by(
        'uuid'
    ).distinct(
        'uuid'
    ).values_list(
        'uuid', 
        flat=True
    )
    old_event_ids = OldEvent.objects.filter(
        project_uuid=project_uuid,
    ).order_by(
        'uuid'
    ).distinct(
        'uuid'
    ).values_list(
        'uuid', 
        flat=True
    )
    old_ids = list(set(list(old_geo_ids) + list(old_event_ids)))
    for old_id in old_ids:
        old_id, new_uuid = update_old_id(old_id)
        new_man_obj = AllManifest.objects.filter(
            uuid=new_uuid,
        ).first()
        if not new_man_obj:
            print(
                f'Cannot find migrated item with old_id {old_id}'
            )
            continue
        migrate_legacy_spacetime_for_item(new_man_obj, old_id)