
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)
from opencontext_py.apps.all_items import utilities

from opencontext_py.apps.linkdata.gbif.api import gbifAPI


# ---------------------------------------------------------------------
# NOTE: These functions are used to load and model GBIF 
# (Global Biodiversity Information Facility) entities.
# ---------------------------------------------------------------------

"""
# Example Use:
from opencontext_py.apps.linkdata.gbif import data as gbif_data

# Add a GBIF uri and it's hierarchy.
uri = 'http://www.gbif.org/species/2498238'
gbif_species_obj = gbif_data.add_get_gbif_manifest_obj_and_hierarchy(uri)
"""

GBIF_VOCAB_URI = 'http://gbif.org/species'
GBIF_BASE_URI = 'http://www.gbif.org/species/'

SPECIES_ENTITY_SOURCE = 'gbif-api'
HIERARCHY_SOURCE = 'gbif-tree-api'

GBIF_SPECIES_ITEM_TYPE = 'class'


def get_gbif_vocabulary_obj():
    """Get the Manifest object for the vocabulary object"""
    m = AllManifest.objects.filter(
        uri=AllManifest().clean_uri(GBIF_VOCAB_URI), 
        item_type='vocabularies'
    ).first()
    return m


def get_gbif_species_id_from_uri(uri):
    """Gets the GBIF species ID from a URI"""
    if uri.endswith('/'):
        # Remove the trailing slash
        uri = uri[0:-1]
    if not 'gbif.org/species/' in uri:
        # Not a GBIF uri
        return None
    uri_parts = uri.split('gbif.org/species/')
    return int(uri_parts[-1])


def add_gbif_vernacular_name(gbif_species_obj, skip_if_exists=True):
    """Add a vernacular name to a GBIF species object"""
    if skip_if_exists:
        as_qs = AllAssertion.objects.filter(
            subject=gbif_species_obj,
            predicate_id=configs.PREDICATE_SKOS_ALTLABEL_UUID,
        ).first()
        if as_qs:
            # Skip out, because we already have an alternate label.
            return None

    # Get a vernacular name for a species.
    species_id = get_gbif_species_id_from_uri(gbif_species_obj.uri)
    if not species_id:
        return None
    
    api = gbifAPI()
    vernacular_name = api.get_gbif_vernacular_name(species_id)
    if not vernacular_name or vernacular_name == gbif_species_obj.label:
        # The vernacular_name can't be found or is the same
        # as the gbif_species_obj.label.
        return None
    
    # Add the vernacular name as a SKOS_ALTLABEL_UUID.
    utilities.add_string_assertion_simple(
        subject_obj=gbif_species_obj, 
        predicate_id=configs.PREDICATE_SKOS_ALTLABEL_UUID,
        source_id=SPECIES_ENTITY_SOURCE,
        str_content=vernacular_name,
    )


def add_get_gbif_manifest_entity(raw_uri):
    """Gets or adds a manifest entity for a GBIF URI"""
    species_id = get_gbif_species_id_from_uri(raw_uri)
    if not species_id:
        return None

    vocab_obj = get_gbif_vocabulary_obj()
    uri = GBIF_BASE_URI + str(species_id)

    # Get the GBIF item for these species URI.
    gbif_species_obj = AllManifest.objects.filter(
        uri=AllManifest().clean_uri(uri), 
        context=vocab_obj,
    ).first()
    if gbif_species_obj:
        # Already in the database, return it.
        return gbif_species_obj

    # OK. We don't have a manifest object for this
    # entity, so make one. First, go get the canonnical
    # name for the species via the GBIF API.
    api = gbifAPI()
    can_name = api.get_gbif_cannonical_name(species_id)

    # Make a new manifest dictionary object.
    man_dict = {
        'publisher_id': vocab_obj.publisher.uuid,
        'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
        'item_class_id': None,
        'source_id': SPECIES_ENTITY_SOURCE,
        'item_type': GBIF_SPECIES_ITEM_TYPE,
        'data_type': 'id',
        'label': can_name,
        'uri': uri,
        'context_id': vocab_obj.uuid,
    }
    gbif_species_obj, _ = AllManifest.objects.get_or_create(
        uri=uri,
        defaults=man_dict
    )
    # Add a vernacular name to this item, if one can be retrieved.
    add_gbif_vernacular_name(gbif_species_obj)
    return gbif_species_obj


def get_add_gbif_parent(child_uri, child_obj=None):
    """Checks to add a parent relation to a GBIF entity
    
    Returns a tuple:
    parent_manifest_object, Is_new_relationship
    
    """
    if not child_obj:
        # We didn't pass child manifest object, so look it 
        # up or create it from it's URI
        child_obj = add_get_gbif_manifest_entity(child_uri)
    
    if not child_obj:
        # We can't find a child manifest object. Is this
        # really a GBIF species entity?
        return None, False
    
    # Vocabulary GBIF manifest object.
    vocab_obj = get_gbif_vocabulary_obj()
    # Check if the child_obj has a broader parent 
    # item in the GBIF vocabulary.
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
    # We don't have a parent assertion for this child_obj,
    # so make a request to the GBIF API to ask for the parent
    # entity to this child.
    # -----------------------------------------------------------------
    
    # First, get the integer ID of the species for the child_obj.
    child_species_id = get_gbif_species_id_from_uri(child_obj.uri)
    if not child_species_id:
        return None, False
    
    api = gbifAPI()
    parent_species_id = api.get_gbif_parent_key(child_species_id)
    if not parent_species_id:
        # GBIF says we're at the top of the hierarchy.
        return None, False
    
    # Now get or create the parent manifest object.
    parent_species_obj = add_get_gbif_manifest_entity(
        (GBIF_BASE_URI + str(parent_species_id))
    )
    ass_obj, _ = AllAssertion.objects.get_or_create(
        uuid=AllAssertion().primary_key_create(
            subject_id=child_obj.uuid,
            predicate_id=configs.PREDICATE_SKOS_BROADER_UUID,
            object_id=parent_species_obj.uuid,
        ),
        defaults={
            'project': child_obj.project,
            'source_id': HIERARCHY_SOURCE,
            'subject': child_obj,
            'predicate_id': configs.PREDICATE_SKOS_BROADER_UUID,
            'object': parent_species_obj,
        }
    )
    print(
        f'Assertion {ass_obj.uuid}: '
        f'{ass_obj.subject.label} [{ass_obj.subject.uuid}]'
        f'-> {ass_obj.predicate.label} [{ass_obj.predicate.uuid}]'
        f'-> {ass_obj.object.label} [{ass_obj.object.uuid}]'
    )
    print('-'*72)
    return parent_species_obj, True


def add_get_gbif_manifest_obj_and_hierarchy(raw_uri):
    """Adds GBIF entity and its hierarchy"""
    gbif_obj = add_get_gbif_manifest_entity(raw_uri)
    if not gbif_obj:
        # This is not a GBIF object.
        return None
    add_new_hierarchy = True
    child_obj = gbif_obj
    while add_new_hierarchy:
        parent_species_obj, new_added = get_add_gbif_parent(
            child_obj.uri, 
            child_obj=child_obj
        )
        add_new_hierarchy = new_added
        if not parent_species_obj:
            add_new_hierarchy = False
            break
        # Make the child_obj the parent_species_obj for the 
        # next iteration of the loop.
        child_obj = parent_species_obj
    return gbif_obj


def contextualize_items_without_parents():
    """Adds parent items to GBIF entities without hierarchies"""
    vocab_obj = get_gbif_vocabulary_obj()
    gbif_qs = AllManifest.objects.filter(
        item_type=GBIF_SPECIES_ITEM_TYPE,
        data_type='id',
        context=vocab_obj,
    )
    for gbif_obj in gbif_qs:
        has_parent = AllAssertion.objects.filter(
            subject=gbif_obj,
            predicate_id=configs.PREDICATE_SKOS_BROADER_UUID
        ).first()
        if has_parent:
            continue
        print(f'Needs a parent: {gbif_obj.label} ({gbif_obj.uri})')
        get_add_gbif_parent(gbif_obj.uri, child_obj=gbif_obj)
        add_gbif_vernacular_name(gbif_obj)