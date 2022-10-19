
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities

from opencontext_py.apps.linkdata.geonames.api import GeonamesAPI


# ---------------------------------------------------------------------
# NOTE: These functions are used to load and model Geonames entities.
# ---------------------------------------------------------------------

"""
# Example Use:
from opencontext_py.apps.linkdata.geonames import data as geonames_data

# Add a Geonames URI and it's spatial geometry.
raw_url = 'https://www.geonames.org/2782113/republic-of-austria.html'
geonames_obj, spacetime_obj = geonames_data.add_get_geonames_manifest_obj_and_spacetime_obj(
    raw_url
)
"""

GEONAMES_VOCAB_URI = 'https://www.geonames.org/'
GEONAMES_BASE_URL = 'https://www.geonames.org/'
ENTITY_SOURCE = 'geonames-api'
GEONAMES_PLACE_ITEM_TYPE = 'uri'


def get_geonames_vocabulary_obj():
    """Get the Manifest object for the vocabulary object"""
    m = AllManifest.objects.filter(
        uri=AllManifest().clean_uri(GEONAMES_VOCAB_URI),
        item_type='vocabularies'
    ).first()
    return m


def get_geonames_id_from_uri(uri):
    """Gets the Geonames ID from a URI"""
    uri = AllManifest().clean_uri(uri)
    geo_ex = uri.split('/')
    geonames_id = geo_ex[-1]
    return int(geonames_id)


def validate_normalize_geonames_url(raw_url):
    """Makes a Geonames URL fit our normal pattern"""
    url = AllManifest().clean_uri(raw_url)
    if not 'geonames.org' in url:
        # This is not a Geonames URL.
        return None
    url_last = url.split('geonames.org')[-1].strip('/')
    if '/' in url_last:
        # This gets rid of trailing place names in the URL.
        geonames_id = url_last.split('/')[0]
    else:
        geonames_id = url_last
    try:
        geonames_id = int(geonames_id)
    except:
        geonames_id = None
    if not geonames_id:
        # We don't have the integer ID part of the URL
        # found.
        return None
    return GEONAMES_BASE_URL + str(geonames_id)


def add_geonames_alt_label(geonames_obj, skip_if_exists=True, alt_label=None):
    """Add a vernacular name to a GBIF species object"""
    if skip_if_exists:
        as_qs = AllAssertion.objects.filter(
            subject=geonames_obj,
            predicate_id=configs.PREDICATE_SKOS_ALTLABEL_UUID,
        ).first()
        if as_qs:
            # Skip out, because we already have an alternate label.
            return None

    if not alt_label:
        # We did not pass an alt_label as an arg, so get it via an
        # API call.
        api = GeonamesAPI()
        _, alt_label = api.get_labels_for_uri(geonames_obj.uri)

    if not alt_label or alt_label == geonames_obj.label:
        # The alternate label either can't be retrieved or is
        # the same as the existing geonames_obj.label
        return None

    # Add the vernacular name as a SKOS_ALTLABEL_UUID.
    utilities.add_string_assertion_simple(
        subject_obj=geonames_obj,
        predicate_id=configs.PREDICATE_SKOS_ALTLABEL_UUID,
        source_id=ENTITY_SOURCE,
        str_content=alt_label,
    )


def add_get_geonames_manifest_entity(raw_url):
    """Gets or adds a manifest entity for a Geonames URI"""
    uri = validate_normalize_geonames_url(raw_url)
    if not uri:
        # This does not appear to be a valid Geonames URL.
        return None

    vocab_obj = get_geonames_vocabulary_obj()

    # Get the Geonames item for this place URI.
    geonames_obj = AllManifest.objects.filter(
        uri=AllManifest().clean_uri(uri),
        context=vocab_obj,
    ).first()
    if geonames_obj:
        # Already in the database, return it.
        return geonames_obj

    # We don't have a manifest object for this
    # entity, so make one. First, go get the canonnical
    # name for the place via the Geonames API.
    api = GeonamesAPI()
    label, alt_label = api.get_labels_for_uri(uri)
    if not label:
        return None

    # Make a new manifest dictionary object.
    man_dict = {
        'publisher_id': vocab_obj.publisher.uuid,
        'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
        'item_class_id': None,
        'source_id': ENTITY_SOURCE,
        'item_type': GEONAMES_PLACE_ITEM_TYPE,
        'data_type': 'id',
        'label': label,
        'uri': uri,
        'context_id': vocab_obj.uuid,
    }
    geonames_obj, _ = AllManifest.objects.get_or_create(
        uri=uri,
        defaults=man_dict
    )
    # Add an alternate label to this item, if one can be retrieved.
    add_geonames_alt_label(geonames_obj, alt_label=alt_label)
    return geonames_obj


def save_spacetime_obj_for_geonames_obj(geonames_obj, fetch_if_point=False):
    """Saves a spacetime object for a geonames object"""
    spacetime_qs = AllSpaceTime.objects.filter(
        item=geonames_obj
    ).exclude(geometry_type=None)
    if fetch_if_point:
        spacetime_qs = spacetime_qs.exclude(geometry_type='Point')
    spacetime_obj = spacetime_qs.first()
    if spacetime_obj:
        # We already have a spacetime object (with spatial data)
        # for this geonames object.
        return spacetime_obj

    api = GeonamesAPI()
    json_data = api.get_json_for_geonames_uri(geonames_obj.uri)
    if not json_data:
        # The request to get JSON data for this geonames object
        # failed.
        return None

    geometry_type = None
    lat = None
    lon = None
    if 'bbox' in json_data:
        east = json_data['bbox']['east']
        south = json_data['bbox']['south']
        west = json_data['bbox']['west']
        north = json_data['bbox']['north']
        coordinates = []
        cood_inner = []
        cood_inner.append([east, south])
        cood_inner.append([east, north])
        cood_inner.append([west, north])
        cood_inner.append([west, south])
        cood_inner.append([east, south])
        coordinates.append(cood_inner)
        geometry_type = 'Polygon'
        geometry = {
            'type': geometry_type,
            'coordinates': coordinates,
        }
    else:
        geometry_type = 'Point'
        geometry = None
        if 'lat' in json_data:
            lat = float(json_data['lat'])
        else:
            # Missing data, we can't make a spacetime obj.
            geometry_type = None
        if 'lng' in json_data:
            lon = float(json_data['lng'])
        else:
            # Missing data, we can't make a spacetime obj.
            geometry_type = None

    if not geometry_type:
        # We couldn't put together enough
        # valid data.
        return None

    point_f_1_obj = None
    if fetch_if_point:
        point_f_1_obj = AllSpaceTime.objects.filter(
            item=geonames_obj,
            geometry_type='Point',
            feature_id=1,
        ).first()

    if point_f_1_obj and geometry_type == 'Point':
        # We already have a point geometry for this item, so skip out.
        return None

    sp_tm_dict = {
        'item_id': geonames_obj.uuid,
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
    feature_id = AllSpaceTime().determine_feature_id(
        geonames_obj.uuid,
        exclude_uuid=spacetime_uuid,
    )
    if point_f_1_obj and geometry_type != 'Point':
        # Make the old point the new feature id
        point_f_1_obj.feature_id = feature_id
        point_f_1_obj.save()
        # Make our new spacetime object feature 1
        feature_id = 1
    sp_tm_dict['feature_id'] = feature_id
    sp_tm_dict['source_id'] = ENTITY_SOURCE,
    spacetime_obj, _ = AllSpaceTime.objects.get_or_create(
        uuid=spacetime_uuid,
        defaults=sp_tm_dict
    )
    return spacetime_obj


def add_get_geonames_manifest_obj_and_spacetime_obj(raw_url, fetch_if_point=False):
    """Adds geonames entity and spacetime object"""
    geonames_obj = add_get_geonames_manifest_entity(raw_url)
    if not geonames_obj:
        # We couldn't find or create a geonames manifest
        # object for the raw_url.
        return None, None
    # We found a geonames manifest object, now get a spacetime object
    # for it.
    spacetime_obj = save_spacetime_obj_for_geonames_obj(
        geonames_obj,
        fetch_if_point=fetch_if_point
    )
    return geonames_obj, spacetime_obj