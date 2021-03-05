
import hashlib
import uuid as GenUUID


from django.core.cache import caches
from django.db.models import Q

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities
from opencontext_py.apps.all_items.legacy_all import update_old_id

from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation


"""
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
LinkAnnotation.objects.filter(object_uri='http://vocab.getty.edu/aat/30023').delete()

obj_replace = [
    (
        'http://opencontext.org/vocabularies/open-context-zooarch/dist-f',
        'http://opencontext.org/vocabularies/open-context-zooarch/dist-epi-fused',
    ),
    (
        'http://opencontext.org/vocabularies/open-context-zooarch/dist-u',
        'http://opencontext.org/vocabularies/open-context-zooarch/dist-epi-unfused',
    ),
    (
        'http://opencontext.org/vocabularies/open-context-zooarch/dist-uf',
        'http://opencontext.org/vocabularies/open-context-zooarch/dist-epi-fusing',
    ),
    (
        'http://opencontext.org/vocabularies/open-context-zooarch/prox-f',
        'http://opencontext.org/vocabularies/open-context-zooarch/prox-epi-fused',
    ),
    (
        'http://opencontext.org/vocabularies/open-context-zooarch/prox-u',
        'http://opencontext.org/vocabularies/open-context-zooarch/prox-epi-unfused',
    ),
    (
        'http://opencontext.org/vocabularies/open-context-zooarch/prox-uf',
        'http://opencontext.org/vocabularies/open-context-zooarch/prox-epi-fusing',
    ),
    (
        'Nicomedia 9',
        'http://numismatics.org/ocre/id/ric.7.nic.9',
    ),
    (
        'RIC VIII Antioch 45',
        'http://numismatics.org/ocre/id/ric.8.anch.45',
    ),
    (
        'RIC VIII Antioch 55A',
        'http://numismatics.org/ocre/id/ric.8.anch.55a',
    ),
]
for f_uri, r_uri in obj_replace:
    for la in LinkAnnotation.objects.filter(object_uri=f_uri):
        la.pk = None
        la.object_uri = r_uri
        delete_bad = False
        try:
            la.save()
        except:
            delete_bad = True
        if not delete_bad:
            continue
        print(f'Duplicate {la.subject} {la.predicate_uri} {la.object_uri}')
    LinkAnnotation.objects.filter(object_uri=f_uri).delete()


"""



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
    ('bibo:status/forthcoming', '')
}

URI_SLUG_MAPPINGS = {
    'concordia.atlantides.org': 'concordia-vocab',
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


URI_PREFIXES = {
    'opencontext.org/vocabularies/oc-general/': 'oc-gen',
    'opencontext.org/vocabularies/open-context-zooarch/': 'oc-zoo',
    'opencontext.org/vocabularies/dinaa/': 'dinaa',
    'purl.org/ontology/bibo': 'bibo',
    'http://erlangen-crm.org/current/': 'cidoc-crm',
    'http://purl.org/ontology/bibo/': 'bibo',
    'https://www.w3.org/2000/01/rdf-schema': 'rdfs',
    'http://www.w3.org/2004/02/skos/core': 'skos',
    'https://www.w3.org/2002/07/owl': 'owl',
    'http://purl.org/dc/terms/': 'dc-terms',
}

# Sorts for equivalence asstions for URIs 
SORTS_FOR_EQUIV_URI_PREFIXES = [
    # This is used for EOL mappings, but we want GBIF to be
    # ranked higher and more prominently, so we have a high
    # sort value here.
    ('purl.org/NET/biol/ns#term_hasTaxonomy', 100,),
    # Most EOL URIs should have a high sort to de-emphasize.
    ('eol.org', 100,),
]

"""
from opencontext_py.apps.all_items.legacy_ld import *
load_legacy_link_entities_vocabs()
load_legacy_link_entities()
missing_entities = migrate_legacy_link_annotations()
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
    item_key = utilities.uri_to_common_prefix(
        uri,
        uri_prefixes=URI_PREFIXES,
    )
    new_man_obj = utilities.get_man_obj_from_uri(
        uri,
        item_key=item_key,
    )
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
        # Default to the old slug, but use a mapping if existing.
        'slug': URI_SLUG_MAPPINGS.get(uri, old_le.slug),
        'label': old_le.label,
        'uri': uri,
        'context_id': context_id,
        'meta_json': {
            'migration': SOURCE_ID,
        },
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


def is_valid_uuid(val):
    try:
        return GenUUID.UUID(str(val))
    except ValueError:
        return False


def add_oc_uuid_uri_variants(la_identifier):
    """Makes a tuple of lists from a legacy la_identifer for new uuid, uri options""" 
    _, new_id = update_old_id(la_identifier)
    uuids = [new_id]
    if is_valid_uuid(la_identifier):
        uuids.append(la_identifier)
        # The la_identifer is not a URI because it's a uuid.
        return uuids, []

    uris = [
        AllManifest().clean_uri(la_identifier)
    ]
    for oc_type in configs.OC_ITEM_TYPES:
        uri_part_oc_type = f'/{oc_type}/'
        if not uri_part_oc_type in la_identifier:
            continue
        old_oc_id = la_identifier.split(uri_part_oc_type)[-1]
        _, new_id = update_old_id(old_oc_id)
        uuids.append(new_id)
        new_uri = la_identifier.replace(old_oc_id, new_id)
        new_uri = AllManifest().clean_uri(new_uri)
        uris.append(new_uri)
    
    return uuids, uris


def db_get_man_obj_from_la(la_identifier):
    """Checks if a legacy link entity URI is in the new manifest"""
    uuids, uris = add_oc_uuid_uri_variants(la_identifier)
    new_man_obj = AllManifest.objects.filter(
        Q(uri__in=uris) 
        | Q(item_key=la_identifier)
        | Q(uuid__in=uuids)
    ).first()
    if not new_man_obj:
        print(f'Cannot find new manifest obj for entity {la_identifier}')
        return None
    return new_man_obj


def get_man_obj_from_la(la_identifier, use_cache=False):
    """Checks if a legacy link entity URI is in the new manifest"""
    if not la_identifier:
        return None
    if not use_cache:
        return db_get_man_obj_from_la(la_identifier)
    # Using the cache, so make a hash key.
    hash_obj = hashlib.sha1()
    hash_obj.update(str(la_identifier).encode('utf-8'))
    hash_id = hash_obj.hexdigest()
    cache_key = f'la_id_allman_{hash_id}'
    cache = caches['memory']
    new_man_obj = cache.get(cache_key)
    if new_man_obj is not None:
        # We've already cached this, so returned the cached object
        return new_man_obj
    new_man_obj = db_get_man_obj_from_la(la_identifier)
    if not new_man_obj:
        return None
    try:
        cache.set(cache_key, new_man_obj)
    except:
        pass
    return new_man_obj


def check_legacy_la_subjects(print_found=False, exclude_strs=OC_ITEM_URI_STRS ):
    """Checks legacy subjects to makes sure they exist in the new manifest
    """
    missing_entities = []
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
            if old_entity_id not in missing_entities:
                missing_entities.append(old_entity_id)
            continue
        if print_found:
            print(
                f'Old entity {old_entity_id} is '
                f'{new_man_obj.label}, {new_man_obj.uri} '
                f'[{new_man_obj.uuid}]'
            )
    return  missing_entities


def check_legacy_la_predicates(print_found=False):
    """Checks legacy predicates to makes sure they exist in the new manifest
    """
    missing_entities = []
    la_qs= LinkAnnotation.objects.all().distinct(
        'predicate_uri'
    ).order_by('predicate_uri').values_list('predicate_uri', flat=True)
    for old_entity_id in la_qs:
        new_man_obj = get_man_obj_from_la(la_uri=old_entity_id)
        if not new_man_obj:
            if old_entity_id not in missing_entities:
                missing_entities.append(old_entity_id)
            continue
        if print_found:
            print(
                f'Old entity {old_entity_id} is '
                f'{new_man_obj.label}, {new_man_obj.uri} '
                f'[{new_man_obj.uuid}]'
            )
    return  missing_entities


def check_legacy_la_objects(print_found=False, exclude_strs=OC_ITEM_URI_STRS ):
    """Checks legacy objects to makes sure they exist in the new manifest
    """
    missing_entities = []
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
            if old_entity_id not in missing_entities:
                missing_entities.append(old_entity_id)
            continue
        if print_found:
            print(
                f'Old entity {old_entity_id} is '
                f'{new_man_obj.label}, {new_man_obj.uri} '
                f'[{new_man_obj.uuid}]'
            )
    return  missing_entities


def migrate_legacy_link_annotations(
    project_uuid='0', 
    more_filters_dict={'subject_type': 'uri'},
    use_cache=False
):
    """Migrates legacy link annotations (limited to entities already in the manifest)"""
    
    old_proj_id, new_proj_uuid = update_old_id(project_uuid)
    new_proj_obj = AllManifest.objects.filter(uuid=new_proj_uuid).first()
    if not new_proj_obj:
        print(
            f'Cannot migrate link annotations, missing project {project_uuid}'
        )
        return None

    missing_entities = []
    
    la_qs = LinkAnnotation.objects.filter( 
        project_uuid=old_proj_id
    ).order_by(
        'subject', 
        'predicate_uri', 
        'sort', 
        'object_uri'
    )
    if more_filters_dict:
        # Add some additional filters to this query set.
        la_qs = la_qs.filter(**more_filters_dict)

    for la in la_qs:
        subj_obj = get_man_obj_from_la(la.subject, use_cache=use_cache)
        pred_obj = get_man_obj_from_la(la.predicate_uri, use_cache=use_cache)
        obj_obj = get_man_obj_from_la(la.object_uri, use_cache=use_cache)
        if not subj_obj or not pred_obj or not obj_obj:
            if not subj_obj and la.subject not in missing_entities:
                missing_entities.append(la.subject)
            if not pred_obj and la.predicate_uri not in missing_entities:
                missing_entities.append(la.predicate_uri)
            if not obj_obj and la.object_uri not in missing_entities:
                missing_entities.append(la.object_uri)
            continue
        if subj_obj == obj_obj:
            # No self assertions.
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
                'project': new_proj_obj,
                'source_id': SOURCE_ID,
                'subject': subj_obj,
                'predicate': pred_obj,
                'sort': sort,
                'object': obj_obj,
                'meta_json': {
                    'migration': SOURCE_ID,
                },
            }
        )
        print(
            f'Assertion {ass_obj.uuid}: '
            f'{ass_obj.subject.label} [{ass_obj.subject.uuid}]'
            f'-> {ass_obj.predicate.label} [{ass_obj.predicate.uuid}]'
            f'-> {ass_obj.object.label} [{ass_obj.object.uuid}]'
        )
        print('-'*72)
    
    return missing_entities


def eol_assertion_fix(
    project_id=None, 
    ranking_tuples=SORTS_FOR_EQUIV_URI_PREFIXES
):
    """Fixes assertions related to the EOL"""
    # NOTE: We will continue to support assertions made to
    # map Open Context published predicates and types to the
    # EOL, but we want to make these sort as a lower priority
    # so that GBIF assertions become more prominent.

    print('De-emphasize equivalence assertions for EOL')
    utilities.update_equivalent_object_uri_sorting(
        ranking_tuples,
        project_id=project_id,
    )