
import uuid as GenUUID

from django.db.models import Q

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllString,
    AllAssertion,
    AllHistory,
)
from opencontext_py.apps.all_items import utilities
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation


LEGACY_LINK_ENT_TYPES_ITEM_TYPES_MAPS = {
    '': 'class',
    'class': 'class',
    'instance': 'uri',
    'property': 'property',
    'type': 'class',
    'unit': 'class',
    'vocabulary': 'vocabularies',
}

SKIP_URIS = [
    'www.worldcat.org',
    'sw.opencyc.org/2008/06/10/concept/Mx4rHs7hMuxiQdaeRI29oZztbw',
]

INSTANCE_URIS = [
    'geonames.org',
    'core.tdar.org/browse/site-name/',
    'pleiades.stoa.org/places/',
    'scholarworks.sfasu.edu/ita/',
    'www.jstor.org/stable/',
    'www.federalregister.gov/documents/',
]

REPLACE_URIS = {
    ('www.worldcat.org', 'www.worldcat.org/oclc',),
    ('opencontext.org/about/concepts', 'opencontext.org/vocabularies/oc-general'),
}

SOURCE_ID = 'legacy-linked-entity-migrate'

SPELLING_FIXES = [
    ('Identiers', 'Identifiers',),
]

OC_ITEM_URI_STRS = [
    'opencontext.org/subjects/',
    'opencontext.org/media/',
    'opencontext.org/persons/',
    'opencontext.org/documents/',
    'opencontext.org/projects/',
    'opencontext.org/types/',
    'opencontext.org/predicates/',
    'opencontext.org/tables/',
]


"""
from opencontext_py.apps.all_items.legacy import *
load_legacy_link_entities_vocabs()
load_legacy_link_entities()
"""


def add_le_alt_label(old_le, new_man_obj):
    """Adds an assertion for alt-labels to a new manifest obj"""
    alt_label = old_le.alt_label.strip()
    label =  old_le.label.strip()

    for f_sp, r_sp in SPELLING_FIXES:
        alt_label = alt_label.replace(f_sp, r_sp)

    if not alt_label or label == alt_label:
        # The alt label is the same so skip out.
        return None
    
    utilities.add_string_assertion_simple(
        subject_obj=new_man_obj, 
        predicate_id=configs.PREDICATE_SKOS_ALTLABEL_UUID,
        source_id=SOURCE_ID,
        str_content=alt_label,
    )


def load_legacy_link_entity(old_le):
    """Loads a legacy linked entity if not moved"""
    if not old_le.uri:
        # Skip out. No uri.
        return None
    uri = AllManifest().clean_uri(old_le.uri)
    uri = uri.strip()
    if not uri:
        print('Skip a blank uri')
        return None
    if uri in SKIP_URIS:
        print(
            f'Skip migration of legacy {uri}'
        )
        return None
    # Check to see it this is already imported.
    new_man_obj = AllManifest.objects.filter(
        uri=uri
    ).first()
    if new_man_obj:
        print(
            'Already have {}; {} at uri: {}'.format(
                new_man_obj.label,
                new_man_obj.item_type,
                new_man_obj.uri
            )
        )
        add_le_alt_label(old_le, new_man_obj)
        return None
    # We need to add the legacy item.
    print('Need to add {} at uri: {}'.format(
            old_le.label,
            old_le.uri
        )
    )
    publisher_id = configs.OPEN_CONTEXT_PUB_UUID
    if old_le.ent_type == 'vocabulary':
        context_id = configs.OPEN_CONTEXT_PROJ_UUID
    else:
        vocab_uri = AllManifest().clean_uri(
            old_le.vocab_uri
        )
        for f_uri, r_uri in REPLACE_URIS:
            if vocab_uri.startswith(f_uri):
                vocab_uri = r_uri
        vocab_obj = AllManifest.objects.get(
            uri=vocab_uri 
        )
        publisher_id = vocab_obj.publisher.uuid
        context_id = vocab_obj.uuid

    item_type = LEGACY_LINK_ENT_TYPES_ITEM_TYPES_MAPS.get(
        old_le.ent_type
    )
    if item_type == 'class':
        for uri_check in INSTANCE_URIS:
            if uri_check in uri:
                # change to an instance item type.
                item_type = 'uri'

    # Make a new manifest dictionary object.
    man_dict = {
        'publisher_id': publisher_id,
        'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
        'item_class_id': None,
        'source_id': SOURCE_ID,
        'item_type': item_type,
        'data_type': 'id',
        'slug': old_le.slug,
        'label': old_le.label,
        'uri': uri,
        'context_id': context_id,
        'meta_json': {
            'skos_alt_label': {
                'en': [
                    old_le.alt_label
                ],
            },
        }
    }
    new_man_obj, _ = AllManifest.objects.get_or_create(
        uri=uri,
        defaults=man_dict
    )
    add_le_alt_label(old_le, new_man_obj)
    print(f'Item {new_man_obj.uuid}, {new_man_obj.label} created')


def load_legacy_link_entities_vocabs():
    """Loads legacy link entity vocabularies"""
    old_vocabs_qs = LinkEntity.objects.filter(
        ent_type='vocabulary'
    )
    for old_le in old_vocabs_qs:
        load_legacy_link_entity(old_le)


def check_missing_legacy_vocab_uris():
    """Checks for missing legacy vocab uris"""
    missing_uris = []
    vocab_uris = LinkEntity.objects.all().distinct(
        'vocab_uri'
        ).values_list(
        'vocab_uri', 
        flat=True
    )
    for vocab_uri in vocab_uris:
        vocab_uri = AllManifest().clean_uri(
            vocab_uri
        )
        m_vocab = AllManifest.objects.filter(
            uri=vocab_uri 
        ).first()
        if m_vocab:
            # No problem.
            continue
        missing_uris.append(vocab_uri)
    return missing_uris


def load_legacy_link_entities():
    """Loads legacy link entity vocabularies"""
    old_le_qs = LinkEntity.objects.all().exclude(
        ent_type='vocabulary'
    )
    for old_le in old_le_qs:
        load_legacy_link_entity(old_le)


def get_man_obj_from_la(la_uri):
    """Checks if a legacy link entity URI is in the new manifest"""
    new_man_obj = AllManifest.objects.filter(
        Q(uri=AllManifest().clean_uri(
                la_uri
            )
        ) 
        | Q(item_key=la_uri)
    ).first()
    if not new_man_obj:
        print(f'Cannot find new manifest obj for entity {la_uri}')
        return None
    return new_man_obj


def check_legacy_la_subjects(print_found=False, exclude_strs=OC_ITEM_URI_STRS ):
    """Checks legacy subjects to makes sure they exist in the new manifest
    """
    la_qs = LinkAnnotation.objects.filter(subject_type='uri').distinct(
        'subject'
    ).order_by('subject').values_list('subject', flat=True)

    for exclude_str in exclude_strs:
        la_qs = la_qs.exclude(
            subject__contains=exclude_str
        )

    for old_entity_id in la_qs:
        new_man_obj = get_man_obj_from_la(la_uri=old_entity_id)
        if not new_man_obj:
            continue
        if print_found:
            print(
                f'Old entity {old_entity_id} is '
                f'{new_man_obj.label}, {new_man_obj.uri} '
                f'[{new_man_obj.uuid}]'
            )


def check_legacy_la_predicates(print_found=False):
    """Checks legacy predicates to makes sure they exist in the new manifest
    """
    la_qs= LinkAnnotation.objects.all().distinct(
        'predicate_uri'
    ).order_by('predicate_uri').values_list('predicate_uri', flat=True)
    for old_entity_id in la_qs:
        new_man_obj = get_man_obj_from_la(la_uri=old_entity_id)
        if not new_man_obj:
            continue
        if print_found:
            print(
                f'Old entity {old_entity_id} is '
                f'{new_man_obj.label}, {new_man_obj.uri} '
                f'[{new_man_obj.uuid}]'
            )


def check_legacy_la_objects(print_found=False, exclude_strs=OC_ITEM_URI_STRS ):
    """Checks legacy objects to makes sure they exist in the new manifest
    """
    la_qs = LinkAnnotation.objects.all().distinct(
        'object_uri'
    ).order_by('object_uri').values_list('object_uri', flat=True)

    for exclude_str in exclude_strs:
        la_qs = la_qs.exclude(
            object_uri__contains=exclude_str
        )

    for old_entity_id in la_qs:
        new_man_obj = get_man_obj_from_la(la_uri=old_entity_id)
        if not new_man_obj:
            continue
        if print_found:
            print(
                f'Old entity {old_entity_id} is '
                f'{new_man_obj.label}, {new_man_obj.uri} '
                f'[{new_man_obj.uuid}]'
            )



def migrate_legacy_link_annotations(project_uuid='0'):
    """Migrates legacy link annotations (limited to entities already in the manifest)"""
    legacy_new_project_uuids = {
        '0': configs.OPEN_CONTEXT_PROJ_UUID,
    }
    la_qs = LinkAnnotation.objects.filter(
        subject_type='uri', 
        project_uuid=project_uuid
    ).order_by(
        'subject', 
        'predicate_uri', 
        'sort', 
        'object_uri'
    )
    for la in la_qs:
        subj_obj = get_man_obj_from_la(la.subject)
        pred_obj = get_man_obj_from_la(la.predicate_uri)
        obj_obj = get_man_obj_from_la(la.object_uri)
        if not subj_obj or not pred_obj or not obj_obj:
            continue
        if la.sort:
            sort = la.sort
        else:
            sort = 0
        ass_obj, _ = AllAssertion.objects.get_or_create(
            uuid=AllAssertion().primary_key_create(
                subject_id=subj_obj.uuid,
                predicate_id=pred_obj.uuid,
                object_id=obj_obj.uuid,
            ),
            defaults={
                'project_id': legacy_new_project_uuids.get(
                    la.project_uuid,
                    configs.OPEN_CONTEXT_PROJ_UUID
                ),
                'source_id': SOURCE_ID,
                'subject': subj_obj,
                'predicate': pred_obj,
                'sort': sort,
                'object': obj_obj,
            }
        )
        print(
            f'Assertion {ass_obj.uuid}: '
            f'{ass_obj.subject.label} [{ass_obj.subject.uuid}]'
            f'-> {ass_obj.predicate.label} [{ass_obj.predicate.uuid}]'
            f'-> {ass_obj.object.label} [{ass_obj.object.uuid}]'
        )
        print('-'*72)