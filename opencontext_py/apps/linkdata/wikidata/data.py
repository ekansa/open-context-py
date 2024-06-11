
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
)

from opencontext_py.apps.linkdata.wikidata.api import (
    get_wikidata_id_from_uri, 
    WikidataAPI
)

# ---------------------------------------------------------------------
# NOTE: These functions are used to load and model Geonames entities.
# ---------------------------------------------------------------------

"""
# Example Use:
from opencontext_py.apps.linkdata.wikidata import data as wikidata_data

# Add a Wikidata URI and it's spatial geometry.
raw_url = 'https://www.wikidata.org/wiki/Q6939471'
wikidata_obj, spacetime_obj = wikidata_data.add_get_wikidata_manifest_obj_and_spacetime_obj(
    raw_url
)
"""

WIKIDATA_VOCAB_URI = 'https://www.wikidata.org/'
WIKIDATA_BASE_URL = 'https://www.wikidata.org/'
ENTITY_SOURCE = 'wikidata-api'
WIKIDATA_PLACE_ITEM_TYPE = 'uri'
WIKIDATA_CONCEPT_ITEM_TYPE = 'class'
WIKIDATA_PROPERTY_ITEM_TYPE = 'property'


def get_wikidata_vocabulary_obj():
    """Get the Manifest object for the vocabulary object"""
    m = AllManifest.objects.filter(
        uri=AllManifest().clean_uri(WIKIDATA_VOCAB_URI), 
        item_type='vocabularies'
    ).first()
    return m


def validate_normalize_wikidata_url(raw_url):
    """Makes a PWikidata URL fit our normal pattern"""
    wikidata_id = get_wikidata_id_from_uri(raw_url)
    if not wikidata_id:
        # We don't have an ID
        return None
    return f'{WIKIDATA_BASE_URL}wiki/{wikidata_id}'


def add_get_wikidata_manifest_entity(raw_url):
    """Gets or adds a manifest entity for a Wikidata URI"""
    uri = validate_normalize_wikidata_url(raw_url)
    if not uri:
        # This does not appear to be a valid Wikidata URL.
        return None

    vocab_obj = get_wikidata_vocabulary_obj()

    # Get the Pleiades item for this place URI.
    wikidata_obj = AllManifest.objects.filter(
        uri=AllManifest().clean_uri(uri), 
        context=vocab_obj,
    ).first()
    if wikidata_obj:
        # Already in the database, return it.
        return wikidata_obj

    # We don't have a manifest object for this
    # entity, so make one. First, go get the canonnical
    # name for the place via the Pleiades API.
    api = WikidataAPI()
    label = api.get_label_for_uri(uri)

    if not label:
        print(f'Cannot get a label for {uri}, no manifest entity created')
        return None
    
    wikidata_id = get_wikidata_id_from_uri(uri)
    item_type = WIKIDATA_CONCEPT_ITEM_TYPE
    if wikidata_id.startswith('P'):
        item_type = WIKIDATA_PROPERTY_ITEM_TYPE
    
    lat_lon_dict = api.get_coordinate_lat_lon_dict_for_uri(uri)
    if lat_lon_dict:
        item_type = WIKIDATA_PLACE_ITEM_TYPE
    
    # Make a new manifest dictionary object.
    man_dict = {
        'publisher_id': vocab_obj.publisher.uuid,
        'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
        'item_class_id': None,
        'source_id': ENTITY_SOURCE,
        'item_type': item_type,
        'data_type': 'id',
        'label': label,
        'uri': uri,
        'context_id': vocab_obj.uuid,
    }
    wikidata_obj, _ = AllManifest.objects.get_or_create(
        uri=uri,
        defaults=man_dict
    )
    return wikidata_obj


def save_spacetime_obj_for_wikidata_obj(wikidata_obj):
    """Saves a spacetime object for a wikidata object"""
    spacetime_obj = AllSpaceTime.objects.filter(
        item=wikidata_obj
    ).exclude(geometry_type=None).first()
    if spacetime_obj:
        # We already have a spacetime object (with spatial data)
        # for this wikidata object.
        return spacetime_obj
    
    api = WikidataAPI()
    lat_lon_dict = api.get_coordinate_lat_lon_dict_for_uri(wikidata_obj.uri)
    if not lat_lon_dict:
        # No coordinate data can be retrieved
        return None
    
    geometry_type = 'Point'
    # NOTE: the geometry coordinates have GeoJSON coordinate ordering.

    geometry = {
        'type': geometry_type,
        'coordinates': [
            lat_lon_dict['longitude'],
            lat_lon_dict['latitude'],
        ],
    }
    
    sp_tm_dict = {
        'item_id': wikidata_obj.uuid,
        'earliest': None,
        'start': None,
        'stop': None,
        'latest': None,
        'latitude': lat_lon_dict['latitude'],
        'longitude': lat_lon_dict['longitude'],
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
        wikidata_obj.uuid,
        exclude_uuid=spacetime_uuid,
    )
    sp_tm_dict['source_id'] = ENTITY_SOURCE,
    spacetime_obj, _ = AllSpaceTime.objects.get_or_create(
        uuid=spacetime_uuid,
        defaults=sp_tm_dict
    )
    return spacetime_obj


def add_get_wikidata_manifest_obj_and_spacetime_obj(raw_url):
    """Adds wikidata entity and spacetime object"""
    wikidata_obj = add_get_wikidata_manifest_entity(raw_url)
    if not wikidata_obj:
        # We couldn't find or create a wikidata manifest
        # object for the raw_url.
        return None, None
    # We found a wikidata manifest object, now get a spacetime object
    # for it.
    spacetime_obj = save_spacetime_obj_for_wikidata_obj(wikidata_obj)
    return wikidata_obj, spacetime_obj