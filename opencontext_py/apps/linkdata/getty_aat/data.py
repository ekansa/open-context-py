
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)
from opencontext_py.apps.all_items import utilities

from opencontext_py.apps.linkdata.getty_aat.api import GettyAATapi
from opencontext_py.apps.linkdata.getty_aat import configs as aat_configs

# ---------------------------------------------------------------------
# NOTE: These functions are used to load and model Getty AAT
# (Art and Architecture Thesaurus) entities.
# ---------------------------------------------------------------------

"""
# Example Use:
import importlib
from opencontext_py.apps.linkdata.getty_aat import data as aat_data
importlib.reload(aat_data)

aat_data.contextualize_items_without_parents()

# Add a Getty AAT uri and it's hierarchy.
aat_uri = 'https://vocab.getty.edu/aat/300011101'
aat_obj = aat_data.add_get_aat_manifest_obj_and_hierarchy(aat_uri)
"""


ENTITY_LABEL_SOURCE = 'getty-aat-api'
HIERARCHY_SOURCE = 'getty-aat-api'
CATEGORY_ITEM_TYPE = 'class'


def normalize_aat_uri(raw_uri):
    """Makes sure an AAT URI is for the linked data resource"""
    if raw_uri and '/aat/' in raw_uri:
        uri_ex = raw_uri.split('/aat/')
        raw_uri = f'https://{aat_configs.GETTY_AAT_BASE_URI}{uri_ex[-1]}'
    return raw_uri


def validate_normalize_aat_uri(raw_uri):
    """Validates and normalizes a Getty AAT URI"""
    if not 'vocab.getty.edu' in raw_uri:
        return None
    if not '/aat/' in raw_uri:
        return None
    return normalize_aat_uri(raw_uri)


def get_getty_aat_vocabulary_obj():
    """Get the Manifest object for the vocabulary object"""
    m = AllManifest.objects.filter(
        uri=AllManifest().clean_uri(aat_configs.GETTY_AAT_VOCAB_URI),
        item_type='vocabularies'
    ).first()
    return m


def add_get_getty_aat_manifest_entity(aat_uri):
    """Gets or adds a manifest entity for a Getty AAT URI"""
    aat_uri = normalize_aat_uri(aat_uri)
    aat_uri = AllManifest().clean_uri(aat_uri)
    if not aat_uri.startswith(aat_configs.GETTY_AAT_BASE_URI):
        return None
    vocab_obj = get_getty_aat_vocabulary_obj()

    aat_obj = AllManifest.objects.filter(
        uri=AllManifest().clean_uri(aat_uri),
        context=vocab_obj,
    ).first()
    if aat_obj:
        # Already in the database, return it.
        return aat_obj

    # OK. We don't have a manifest object for this
    # entity, so make one. First, go get the label
    # for the concept via the Gety AAT API.
    api = GettyAATapi()
    obj_data = api.get_aat_json(aat_uri)
    if not obj_data:
        return None

    # Make a new manifest dictionary object.
    man_dict = {
        'publisher_id': vocab_obj.publisher.uuid,
        'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
        'item_class_id': None,
        'source_id': ENTITY_LABEL_SOURCE,
        'item_type': CATEGORY_ITEM_TYPE,
        'data_type': 'id',
        'label': obj_data.get('_label', f'NO LABEL {aat_uri}'),
        'uri': aat_uri,
        'context_id': vocab_obj.uuid,
    }
    aat_obj, _ = AllManifest.objects.get_or_create(
        uri=aat_uri,
        defaults=man_dict
    )
    print(f'Database added {aat_obj.label} ({aat_obj.uri})')
    return aat_obj


def recursive_aat_parent_fetch(
    first_child_uri,
    act_uri,
    parent_uris=None,
    lookup_count=0,
):
    act_uri = normalize_aat_uri(act_uri)
    act_uri = AllManifest().clean_uri(act_uri)
    if not parent_uris:
        parent_uris = []
    if not act_uri in parent_uris:
        parent_uris.append(act_uri)
    api = GettyAATapi()
    obj_data = api.get_aat_json(act_uri)
    if not obj_data:
        print(f'Failed to get JSON for: {act_uri}')
        return parent_uris
    lookup_count += 1
    act_label = obj_data.get('_label', f'Unlabeled {act_uri}')
    print(f'{first_child_uri} [{lookup_count}] Check for parent of {act_label} ({act_uri})')
    broader_items = []
    if aat_configs.AAT_PREFERRED_URI_TO_PARENT_URI_DICT.get(act_uri):
        broader_items.append(aat_configs.AAT_PREFERRED_URI_TO_PARENT_URI_DICT.get(act_uri))
    for key in ['broader', 'part_of']:
        act_broader = obj_data.get(key)
        if isinstance(act_broader, dict):
            broader_items += [act_broader]
            continue
        if isinstance(act_broader, list) and len(act_broader) > 0:
            broader_items += act_broader
            continue
    # Go up all of the different parent paths in the broader
    # hierarchy. One of these paths may be configured to be preferred
    # for the Open Context AAT hierarchy.
    for broader_item in broader_items:
        if isinstance(broader_item, dict):
            new_act_uri = broader_item.get('id')
        elif isinstance(broader_item, str):
            new_act_uri = broader_item
        if not new_act_uri:
            continue
        new_act_uri = AllManifest().clean_uri(new_act_uri)
        # Look up the parent of the broader parent that we just found.
        new_parent_uris = recursive_aat_parent_fetch(
            first_child_uri=first_child_uri,
            act_uri=new_act_uri,
            parent_uris=parent_uris,
            lookup_count=lookup_count,
        )
        for new_parent_uri in new_parent_uris:
            if new_parent_uri in parent_uris:
                continue
            parent_uris.append(new_parent_uri)
    return parent_uris


def get_add_aat_parent(child_uri, child_obj=None):
    """Checks to add a parent relation to a GBIF entity

    Returns a tuple:
    parent_manifest_object, Is_new_relationship

    """
    if not child_obj:
        # We didn't pass child manifest object, so look it
        # up or create it from it's URI
        child_obj = add_get_getty_aat_manifest_entity(child_uri)

    if not child_obj:
        # We can't find a child manifest object. Is this
        # really a Getty AAT entity?
        return None, False

    # Vocabulary Getty AAT manifest object.
    vocab_obj = get_getty_aat_vocabulary_obj()
    # Check if the child_obj has a broader parent
    # item in the AAT vocabulary.
    parent_assert_obj = AllAssertion.objects.filter(
        subject=child_obj,
        predicate_id=configs.PREDICATE_SKOS_BROADER_UUID,
        object__context=vocab_obj,
        visible=1,
    ).first()
    if parent_assert_obj:
        # A linking relation to a parent already
        # exists, so return the parent object (which
        # is the object of the assertion), and a False
        # to indicate no new assertion was created.
        return parent_assert_obj.object, False

    # -----------------------------------------------------------------
    # Unlike biological taxa, we're going to limit the depth of the
    # Getty AAT hierarchy to two levels (for now!), so we will call
    # parent items until we find a parent URI that's in our list
    # of AAT parents
    # -----------------------------------------------------------------
    parent_uris = recursive_aat_parent_fetch(
        first_child_uri=child_obj.uri,
        act_uri=child_obj.uri,
    )
    pref_parent_uri = None
    # Iterate through the list of configured preferred parents in their
    # order of preference. The first configured preferred parent is the
    # one we will select for use in the hierarchy.
    for act_config_uri in aat_configs.AAT_PREFERRED_PARENT_URI_LIST:
        if not pref_parent_uri and act_config_uri in parent_uris:
            pref_parent_uri = act_config_uri
            break

    if not pref_parent_uri:
        print(f'COULD NOT FIND a recognized parent for: {child_obj.uri}')
        return None, False

    parent_obj = add_get_getty_aat_manifest_entity(pref_parent_uri)
    if not parent_obj:
        print(f'COULD NOT FIND OR ADD DB record for parent: {pref_parent_uri}')
        return None, False

    if parent_obj.uuid == child_obj.uuid:
        # We're trying to make a parent-child relationship with the same object.
        return parent_obj, False

    ass_obj, _ = AllAssertion.objects.get_or_create(
        uuid=AllAssertion().primary_key_create(
            subject_id=child_obj.uuid,
            predicate_id=configs.PREDICATE_SKOS_BROADER_UUID,
            object_id=parent_obj.uuid,
        ),
        defaults={
            'project': child_obj.project,
            'source_id': HIERARCHY_SOURCE,
            'subject': child_obj,
            'predicate_id': configs.PREDICATE_SKOS_BROADER_UUID,
            'object': parent_obj,
        }
    )
    print(
        f'Assertion {ass_obj.uuid}: '
        f'{ass_obj.subject.label} [{ass_obj.subject.uuid}]'
        f'-> {ass_obj.predicate.label} [{ass_obj.predicate.uuid}]'
        f'-> {ass_obj.object.label} [{ass_obj.object.uuid}]'
    )
    print('-'*72)
    return parent_obj, True


def add_get_aat_manifest_obj_and_hierarchy(aat_uri):
    """Adds a Getty AAT entity and it's hierarchy to the database if it doesn't exist"""
    aat_uri = normalize_aat_uri(aat_uri)
    aat_obj = add_get_getty_aat_manifest_entity(aat_uri)
    if not aat_obj:
        return None
    parent_obj, is_new = get_add_aat_parent(child_uri=aat_obj.uri, child_obj=aat_obj)
    return aat_obj


def ensure_db_has_pref_parents():
    """Checks to make sure we have all the AAT preferred parent entities loaded. Adds if
    missing entities if they're not already in the database
    """
    parent_objs = []
    for aat_uri in aat_configs.AAT_PREFERRED_PARENT_URI_LIST:
        # Make sure we have each of the AAT preferred parents.
        aat_obj = add_get_getty_aat_manifest_entity(aat_uri)
        if not aat_obj:
            print(f'Cannot find or add {aat_uri}')
            continue
        parent_objs.append(aat_obj)
    # Make sure we have all of the parent objects in the database
    return len(set(parent_objs)) == len(set(aat_configs.AAT_PREFERRED_PARENT_URI_LIST))


def contextualize_items_without_parents():
    """Adds parent items to Getty AAT entities without hierarchies"""
    parents_ok = ensure_db_has_pref_parents()
    if not parents_ok:
        print('Problem with highest level parent entities in Getty hierarchies')
        return None
    vocab_obj = get_getty_aat_vocabulary_obj()
    aat_qs = AllManifest.objects.filter(
        item_type=CATEGORY_ITEM_TYPE,
        data_type='id',
        context=vocab_obj,
    ).order_by('sort')
    i = 0
    for aat_obj in aat_qs:
        if aat_obj.uri in aat_configs.AAT_PREFERRED_PARENT_URI_LIST:
            # We're at the top level of the hierarchy.
            continue
        i += 1
        print('-'*50)
        p_ass = AllAssertion.objects.filter(
            subject=aat_obj,
            predicate_id=configs.PREDICATE_SKOS_BROADER_UUID
        ).first()
        if p_ass:
            print(f'[{i}] "{p_ass.subject.label}" ({p_ass.subject.uri}) has parent "{p_ass.object.label}" ({p_ass.object.uri})')
            continue
        print(f'[{i}] Needs a parent: "{aat_obj.label}" ({aat_obj.uri})')
        parent_obj, is_new = get_add_aat_parent(child_uri=aat_obj.uri, child_obj=aat_obj)
        if not parent_obj:
            break


def db_delete_getty_aat_auto_hierarchy():
    """Deletes automatically generated Getty AAT hierarchy assertions"""
    vocab_obj = get_getty_aat_vocabulary_obj()
    n = AllAssertion.objects.filter(
        subject__context=vocab_obj,
        source_id=HIERARCHY_SOURCE,
        predicate_id=configs.PREDICATE_SKOS_BROADER_UUID,
        object__context=vocab_obj,
    ).delete()
    print(f'DELETED autogenerated Getty AAT hierarchy assertions {n}')