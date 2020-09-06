import copy
import pytz
import hashlib
import uuid as GenUUID

from django.db.models import Q
from django.utils import timezone

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
from opencontext_py.apps.all_items.legacy_all import update_old_id
from opencontext_py.apps.all_items.legacy_ld import migrate_legacy_link_annotations

from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation

from opencontext_py.apps.ocitems.projects.models import Project
from opencontext_py.apps.ocitems.predicates.models import Predicate
from opencontext_py.apps.ocitems.manifest.models import Manifest as OldManifest
from opencontext_py.apps.ocitems.octypes.models import OCtype
from opencontext_py.apps.ocitems.assertions.models import Assertion as OldAssertion
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ocitems.documents.models import OCdocument
from opencontext_py.apps.ocitems.persons.models import Person
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ocitems.subjects.models import Subject

"""
from opencontext_py.apps.all_items.legacy_oc import *
migrate_legacy_projects()
migrate_root_subjects()
migrate_legacy_manifest_for_project(project_uuid='0')
murlo = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
migrate_legacy_manifest_for_project(project_uuid=murlo)
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
    ('feda369d-2dbc-4b16-b0ed-83524bafa620', 'Algeria', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ("a3efae9e-7826-46db-82a1-6f7c04b4af1e", 'Argentina', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('7351C966-B876-4B29-F525-5B33CBE895B7', 'Australia', configs.DEFAULT_SUBJECTS_OCEANIA_UUID),
    ('2a9d6e29-5485-4999-9435-1a836fd57b4f', 'Belize', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('90959e36-d1e7-45b7-be4b-109c944f3f55', 'Bolivia', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('f7d43b2c-b033-4cbe-9b87-8df3f3691f9c', 'Borneo', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('34053a4c-44f8-4824-beab-9dadb5a66a82', 'Brazil', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('c75c197b-e532-4968-a4a0-dd11be56bef2', 'Bulgaria', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('994cbb14-e1e1-43be-b179-e3f839b87c4f', 'Cameroon', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('b582c768-0d90-4420-850c-fde4fc2d43fa', 'Canada', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('dae26993-762d-4145-8060-116665674b0e', 'Central African Republic', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('d3f31ae6-365a-4820-afc2-9eb8699a060a', 'Chile', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('e6237a65-452d-44aa-a661-dd0400e4e57d', 'China', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    # ('99e74a38-8178-41a0-83aa-13f78499f327', 'Clermont County'),
    ('239419cf-e7ea-4e41-8cbe-78d817ed3ae8', 'Colombia', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('b97e416b-9684-4fec-990f-5ca974fe657e', 'Costa Rica', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
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
    ('1e13889f-188b-408f-ac1e-133cda2c7482', 'Guinea', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('367616d7-9dd4-41ff-b072-704abf72da29', 'Guinea-Bissau', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
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
    ('251C032B-684D-445E-156B-5710AA407B11', 'Malaysia', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('20AF0BD0-B152-4A48-E19D-3A951EEF4A58', 'Mauritius', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('ee431393-7ab1-4d7a-abec-bb05f53babda', 'Mexico', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('b3cab722-fb1f-4b8a-b7ab-2627b2eba70e', 'Morocco', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('bc2c325c-4f4a-4eb6-aea1-50b2474b8814', 'Myanmar', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('44d061ca-4aec-402e-9dec-12d0223465b3', 'Nicaragua', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('39656aad-ef90-4c98-8700-6487dd8d4d23', 'Nigeria', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('32B3883A-B007-405D-C4E0-ED129C587DFA', 'Northern Mariana Islands', configs.DEFAULT_SUBJECTS_OCEANIA_UUID),
    ('4_global_Palestine', 'Palestinian Authority', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('e6a2d6f1-c86d-454c-98a7-fdb2b1ead222', 'Peru', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('A659B68E-EC36-4477-0C79-D48B370118FC', 'Philippines', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('a2f952b7-baef-49d8-9cfb-c32a630ac64e', 'Poland', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('d9814d86-cbe1-4ba3-bdc4-b3f757443e88', 'Portugal', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('56F99175-F90F-4978-362A-5B6FE27E8B6B', 'Russia', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('c373317b-5c35-4e3e-b618-0f2a022918a9', 'Rwanda', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('cd518ce5-801d-4e30-af66-3972c4622f7e', 'Senegal', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('75EE4254-7C5A-4B0F-F809-A1AFAC016C53', 'South Africa', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('A11CD813-68C7-4F02-4DDA-4C388C422231', 'South Atlantic Ocean', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('3776e3e7-91ea-4c35-9481-0b1fae3afa9a', 'Spain', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    # ('18EA072A-726B-4019-4378-305257EB3AAB', 'Special Project  84', ),
    ('73738647-5987-40ac-ac13-12f11e58c60f', 'Sumatra', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('b8151439-71c0-41ee-87e7-1fcb155c0cf6', 'Surinam', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('2bf133ba-d0cb-411f-8e39-cd728e5bd72b', 'Sweden', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('2230cb43-fd24-4d14-bfac-dced6cbe3f23', 'Switzerland', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('d73cdb54-a47a-48a7-bc40-52a36e4ac0c8', 'Syria', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('8C2F0C28-2D8F-4DAF-DD92-D34561E753C3', 'Taiwan', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('e4d3ed3d-ede0-4854-92be-4d151a0d168f', 'Tanzania', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('0194DA55-F6BE-413D-C288-EF201FC4F2D0', 'Thailand', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('1_Global_Spatial', 'Turkey', configs.DEFAULT_SUBJECTS_ASIA_UUID),
    ('b0054729-c5d6-40a6-89fa-6fce2fd1d2ca', 'Uganda', configs.DEFAULT_SUBJECTS_AFRICA_UUID),
    ('4A7C4A4A-FC66-411A-CDF4-870D153375F3', 'United Kingdom', configs.DEFAULT_SUBJECTS_EUROPE_UUID),
    ('2A1B75E6-8C79-49B9-873A-A2E006669691', 'United States', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),
    ('a8e5898b-4f6a-4f1c-96e7-0d9da4da8a69', 'Venezuala', configs.DEFAULT_SUBJECTS_AMERICAS_UUID),

    # This is for the Palestine Authority.
    ('4d42c6a0-4e19-48d5-bb1c-493fdec0dd60', 'East Jerusalem', 'bc6fd3bd-d934-0afe-60aa-51d63daf650a'),
]


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
            f'Legacy {old_man_obj.item_type}, {old_man_obj.uuid}: {old_man_pred.label} '
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
        project_uuid=man_dict['project'].uuid, 
        context_uuid=man_dict['context'].uuid,
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
    
    p_dtypes = OldAssertion.objects.filter(
        predicate_uuid=old_id
    ).order_by(
        'object_type'
    ).distinct(
        'object_type'
    ).values_list('object_type', flat=True)
    if len(p_dtypes) > 1:
        dtypes = [d for d in p_dtypes]
        print('-'*50)
        print(
            f'Legacy pred: {old_man_obj.uuid}, {old_man_obj.label} '
            'has too many data types: '
        )
        print(str(dtypes))
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
        'data_type': old_pred.data_type,
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
        predicate_id=configs.PREDICATE_BIBO_CONTENT_UUID,
        str_content=old_doc.content,
        publisher_id=new_man_obj.publisher.uuid,
        project_id=new_man_obj.project.uuid,
        source_id=SOURCE_ID,
    )
    return new_man_obj


def migrate_legacy_media_file(new_man_obj, old_mediafile_obj):
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
    resourcetype_id, rank =  res_type_mappings.get(old_mediafile_obj.file_type)
    rank += old_mediafile_obj.highlight

    res_obj, _ = AllResource.objects.get_or_create(
        uuid=AllResource().primary_key_create(
            item_id=new_man_obj.uuid,
            resourcetype_id=resourcetype_id,
            rank=rank,
        ),
        defaults={
            'item': new_man_obj,
            'project': new_man_obj.project,
            'resourcetype_id': resourcetype_id,
            'rank': rank,
            'source_id': SOURCE_ID,
            'uri': old_mediafile_obj.file_uri,
            'meta_json': meta_json,
        }
    )
    return res_obj


def migrate_legacy_media(old_man_obj):
    """Migrates a legacy type object """
    new_man_obj, new_project = migrated_item_proj_check(old_man_obj, 'media')
    if new_man_obj:
        # Congrats, we already migrated this, so skip all the rest.
        return new_man_obj
    if not new_project:
        # Skip out, can't find the related project.
        return None

    old_id, new_uuid = update_old_id(old_man_obj.uuid)

    old_media_files = Mediafile.objects.filter(uuid=old_id)
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
    # fullfile associated with a media resource.
    full_types = [
        ('application/pdf', configs.CLASS_OC_DOCUMENT_MEDIA,),
        ('image', configs.CLASS_OC_IMAGE_MEDIA,),
        ('text/csv', configs.CLASS_OC_DATATABLE_MEDIA,),
        ('spreadsheetml', configs.CLASS_OC_DATATABLE_MEDIA,),
    ]
    media_class_id = media_class_mappings.get(old_man_obj.class_uri)
    if not media_class_id:
        for old_f in old_media_files:
            if old_f.file_type != 'oc-gen:fullfile':
                continue
            for f_type, class_id in full_types:
                if not f_type in old_f.mime_type_uri:
                    continue
                media_class_id = class_id

    if not media_class_id:
        print(
            f'Old media {old_id} {old_man_obj.label} missing mediafile item class.'
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
        f'-> {ass_obj.obj_string.content} [{ass_obj.obj_string.uuid}]'
    )
    return new_man_obj


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


def migrate_legacy_manifest_for_project(project_uuid='0'):
    """Migrates main manifest item types for a project"""
    migrate_legacy_predicates_for_project(project_uuid)
    migrate_legacy_types_for_project(project_uuid)
    migrate_legacy_persons_for_project(project_uuid)
    migrate_legacy_documents_for_project(project_uuid)
    migrate_legacy_media_for_project(project_uuid)
    migrate_legacy_subjects_for_project(project_uuid)