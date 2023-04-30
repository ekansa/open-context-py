# Import code for interacting with APIs of common Linked Data Sources
from opencontext_py.apps.linkdata.gbif import data as gbif_data
from opencontext_py.apps.linkdata.geonames import data as geonames_data
from opencontext_py.apps.linkdata.getty_aat import data as aat_data
from opencontext_py.apps.linkdata.pleiades import data as pleiades_data
from opencontext_py.apps.linkdata.uberon import data as uberon_data

from opencontext_py.apps.all_items.models import (
    AllManifest,
)

def linked_data_obj_get_or_api_create(raw_uri):
    """Gets or creates via API calls a linked data manifest object for a URI"""
    if not isinstance(raw_uri, str):
        return None
    raw_uri = AllManifest().clean_uri(raw_uri)
    if not raw_uri:
        return None
    if gbif_data.get_gbif_species_id_from_uri(raw_uri):
        # We have a GBIF URI, so add (if needed) and get the item
        ld_obj = gbif_data.add_get_gbif_manifest_obj_and_hierarchy(raw_uri)
    elif geonames_data.validate_normalize_geonames_url(raw_uri):
        ld_obj, _ = geonames_data.add_get_geonames_manifest_obj_and_spacetime_obj(raw_uri)
    elif aat_data.validate_normalize_aat_uri(raw_uri):
        aat_uri = aat_data.validate_normalize_aat_uri(raw_uri)
        ld_obj = aat_data.add_get_aat_manifest_obj_and_hierarchy(aat_uri)
    elif pleiades_data.validate_normalize_pleiades_url(raw_uri):
        ld_obj, _ = pleiades_data.add_get_pleiades_manifest_obj_and_spacetime_obj(raw_uri)
    elif uberon_data.validate_normalize_uberon_url(raw_uri):
        ld_obj = uberon_data.add_get_uberon_manifest_entity(raw_uri)
    else:
        ld_obj = None
    return ld_obj