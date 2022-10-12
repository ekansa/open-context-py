
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
)

from opencontext_py.apps.linkdata.uberon.api import UberonAPI


# ---------------------------------------------------------------------
# NOTE: These functions are used to load and model Geonames entities.
# ---------------------------------------------------------------------

"""
# Example Use:
from opencontext_py.apps.linkdata.uberon import data as uberon_data

# Add a Pleiades URI and it's spatial geometry.
raw_url = 'http://purl.obolibrary.org/obo/UBERON_0018577'
uberon_obj = uberon_data.add_get_pleiades_manifest_entity(
    raw_url
)
"""

UBERON_VOCAB_URI = 'https://uberon.org/'
ENTITY_SOURCE = 'uberon-api'
UBERON_ITEM_TYPE = 'class'


def get_uberon_vocabulary_obj():
    """Get the Manifest object for the vocabulary object"""
    m = AllManifest.objects.filter(
        uri=AllManifest().clean_uri(UBERON_VOCAB_URI), 
        item_type='vocabularies'
    ).first()
    return m


def validate_normalize_uberon_url(raw_url):
    """Makes an UBERON URL fit our normal pattern"""
    url = AllManifest().clean_uri(raw_url)
    if not 'obo/UBERON_' in url:
        # This is not an UBERON URL.
        return None
    return url


def add_get_pleiades_manifest_entity(raw_url):
    """Gets or adds a manifest entity for a Pleiades URI"""
    uri = validate_normalize_uberon_url(raw_url)
    if not uri:
        # This does not appear to be a valid Pleiades URL.
        return None

    vocab_obj = get_uberon_vocabulary_obj()

    # Get the Uberon item for this URI.
    uberon_obj = AllManifest.objects.filter(
        uri=AllManifest().clean_uri(uri), 
        context=vocab_obj,
    ).first()
    if uberon_obj:
        # Already in the database, return it.
        return uberon_obj

    # We don't have a manifest object for this
    # entity, so make one. First, go get the canonnical
    # label for the place via the Uberon API.
    api = UberonAPI()
    label = api.get_label_for_uri(uri)

    # Make a new manifest dictionary object.
    man_dict = {
        'publisher_id': vocab_obj.publisher.uuid,
        'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
        'item_class_id': None,
        'source_id': ENTITY_SOURCE,
        'item_type': UBERON_ITEM_TYPE,
        'data_type': 'id',
        'label': label,
        'uri': uri,
        'context_id': vocab_obj.uuid,
    }
    uberon_obj, _ = AllManifest.objects.get_or_create(
        uri=uri,
        defaults=man_dict
    )
    return uberon_obj