
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
)

from opencontext_py.apps.linkdata.pleiades.api import PleiadesAPI


# ---------------------------------------------------------------------
# NOTE: These functions are used to load and model Geonames entities.
# ---------------------------------------------------------------------

"""
# Example Use:
from opencontext_py.apps.linkdata.pleiades import data as pleiades_data

# Add a Pleiades URI and it's spatial geometry.
raw_url = 'https://pleiades.stoa.org/places/197552'
pleiades_obj, spacetime_obj = pleiades_data.add_get_pleiades_manifest_obj_and_spacetime_obj(
    raw_url
)
"""

PLEIADES_VOCAB_URI = 'https://pleiades.stoa.org/'
PLEIADES_BASE_URL = 'https://pleiades.stoa.org/'
ENTITY_SOURCE = 'pleiades-api'
PLEIADES_PLACE_ITEM_TYPE = 'uri'


def get_pleiades_vocabulary_obj():
    """Get the Manifest object for the vocabulary object"""
    m = AllManifest.objects.filter(
        uri=AllManifest().clean_uri(PLEIADES_VOCAB_URI), 
        item_type='vocabularies'
    ).first()
    return m


def get_pleiades_id_from_uri(uri):
    """Gets the Pleiades (place) ID from a URI"""
    uri = AllManifest().clean_uri(uri)
    uri_ex = uri.split('/')
    pleiades_id = uri_ex[2]
    return int(pleiades_id)


def validate_normalize_pleiades_url(raw_url):
    """Makes a Pleiades URL fit our normal pattern"""
    url = AllManifest().clean_uri(raw_url)
    if not 'pleiades.stoa.org' in url:
        # This is not a Pleiades URL.
        return None
    pleiades_id = get_pleiades_id_from_uri(url)
    if not pleiades_id:
        # We don't have the integer ID part of the URL
        # found.
        return None
    return f'{PLEIADES_BASE_URL}places/{pleiades_id}'


def add_get_pleiades_manifest_entity(raw_url):
    """Gets or adds a manifest entity for a Pleiades URI"""
    uri = validate_normalize_pleiades_url(raw_url)
    if not uri:
        # This does not appear to be a valid Pleiades URL.
        return None

    vocab_obj = get_pleiades_vocabulary_obj()

    # Get the Pleiades item for this place URI.
    pleiades_obj = AllManifest.objects.filter(
        uri=AllManifest().clean_uri(uri), 
        context=vocab_obj,
    ).first()
    if pleiades_obj:
        # Already in the database, return it.
        return pleiades_obj

    # We don't have a manifest object for this
    # entity, so make one. First, go get the canonnical
    # name for the place via the Pleiades API.
    api = PleiadesAPI()
    label = api.get_label_for_uri(uri)

    # Make a new manifest dictionary object.
    man_dict = {
        'publisher_id': vocab_obj.publisher.uuid,
        'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
        'item_class_id': None,
        'source_id': ENTITY_SOURCE,
        'item_type': PLEIADES_PLACE_ITEM_TYPE,
        'data_type': 'id',
        'label': label,
        'uri': uri,
        'context_id': vocab_obj.uuid,
    }
    pleiades_obj, _ = AllManifest.objects.get_or_create(
        uri=uri,
        defaults=man_dict
    )
    return pleiades_obj


def save_spacetime_obj_for_pleiades_obj(pleiades_obj):
    """Saves a spacetime object for a pleiades object"""
    spacetime_obj = AllSpaceTime.objects.filter(
        item=pleiades_obj
    ).exclude(geometry_type=None).first()
    if spacetime_obj:
        # We already have a spacetime object (with spatial data)
        # for this pleiades object.
        return spacetime_obj
    
    api = PleiadesAPI()
    json_data = api.get_json_for_pleiades_uri(pleiades_obj.uri)
    if not json_data:
        # The request to get JSON data for this pleiades object
        # failed.
        return None
    
    repr_point = json_data.get('reprPoint', [])
    if len(repr_point) != 2:
        # This pleiades place does not have any location data.
        return None
    
    geometry_type = 'Point'
    # NOTE: the repr_point has GeoJSON coordinate ordering.
    lat = repr_point[1]
    lon = repr_point[0]

    geometry = {
        'type': geometry_type,
        'coordinates': repr_point,
    }
    
    sp_tm_dict = {
        'item_id': pleiades_obj.uuid,
        'earliest': None,
        'start': None,
        'stop': None,
        'latest': None,
        'latitude': lat,
        'longitude': lon,
        'geometry': geometry,
    }
    # Make the spacetime uuid using the sp_tm_dict for
    # kwargs
    spacetime_uuid = AllSpaceTime().primary_key_create(
        **sp_tm_dict
    )
    sp_tm_dict['geometry_type'] = geometry_type
    # Figure out the feature ID.
    sp_tm_dict['feature_id'] = AllSpaceTime().determine_feature_id(
        pleiades_obj.uuid,
        exclude_uuid=spacetime_uuid,
    )
    sp_tm_dict['source_id'] = ENTITY_SOURCE,
    spacetime_obj, _ = AllSpaceTime.objects.get_or_create(
        uuid=spacetime_uuid,
        defaults=sp_tm_dict
    )
    return spacetime_obj


def add_get_pleiades_manifest_obj_and_spacetime_obj(raw_url):
    """Adds pleiades entity and spacetime object"""
    pleiades_obj = add_get_pleiades_manifest_entity(raw_url)
    if not pleiades_obj:
        # We couldn't find or create a pleiades manifest
        # object for the raw_url.
        return None, None
    # We found a pleiades manifest object, now get a spacetime object
    # for it.
    spacetime_obj = save_spacetime_obj_for_pleiades_obj(pleiades_obj)
    return pleiades_obj, spacetime_obj