import json
import requests
from time import sleep

from django.core.cache import caches

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.ldata.linkentities.models import (
    LinkEntity, 
    LinkEntityGeneration
)
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.gbif.api import gbifAPI


GBIF_VOCAB_URI = 'http://gbif.org/species'
GBIF_BASE_URI = 'http://www.gbif.org/species/'

HIERARCHY_SOURCE = 'gbif-api'
SKOS_BROADER = 'skos:broader'


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


def add_get_gbif_link_entity(raw_uri):
    """Gets or adds a link_entity for a GBIF URI"""
    species_id = get_gbif_species_id_from_uri(raw_uri)
    uri = GBIF_BASE_URI + str(species_id)
    le = LinkEntity.objects.filter(uri=uri).first()
    if le:
        # Already in the database
        return le
    api = gbifAPI()
    can_name = api.get_gbif_cannonical_name(species_id)
    vern_name = api.get_gbif_vernacular_name(species_id)
    if not vern_name:
        vern_name = can_name
    print('Saving {} as {}, {}'.format(
            uri,
            can_name,
            vern_name,
        )
    )
    le = LinkEntity()
    le.uri = uri
    le.label = can_name
    le.alt_label = vern_name
    le.vocab_uri = GBIF_VOCAB_URI
    le.ent_type = 'class'
    le.sort = ''
    le.save()
    return le


def get_add_gbif_parent(child_uri, child_le=None):
    """Checks to add a parent relation to a GBIF entity
    
    Returns a tuple:
    parent_link_enity, Is_new_relationship
    
    """
    if not child_le:
        child_le = add_get_gbif_link_entity(child_uri)
    la_exist = LinkAnnotation.objects.filter(
        subject=child_le.uri,
        predicate_uri=SKOS_BROADER,
    ).first()
    if la_exist:
        # A linking relation to a parent already
        # exists, so skip out.
        parent_le = add_get_gbif_link_entity(
            la_exist.object_uri
        )
        return parent_le, False
    api = gbifAPI()
    child_id = get_gbif_species_id_from_uri(child_le.uri)
    parent_id = api.get_gbif_parent_key(child_id)
    if not parent_id:
        # We're at the top of the hierarchy.
        return None, False
    parent_le = add_get_gbif_link_entity(
        (GBIF_BASE_URI + str(parent_id))
    )
    print('Make {} ({}) a child of: {} ({})'.format(
            child_le.uri,
            child_le.label,
            parent_le.uri,
            parent_le.label,
        )
    )
    la = LinkAnnotation()
    la.subject = child_le.uri
    la.subject_type = 'uri'
    la.project_uuid = '0'
    la.source_id = HIERARCHY_SOURCE
    la.predicate_uri = SKOS_BROADER
    la.object_uri = parent_le.uri
    la.creator_uuid = ''
    la.save()
    return parent_le, True


def add_get_gbif_link_entity_and_hierarchy(
    raw_uri, 
    check_all_hierarchy=False
):
    """Adds GBIF entity and its hierarchy"""
    gbif_le = add_get_gbif_link_entity(raw_uri)
    add_new_hierarchy = True
    child_le = gbif_le
    while add_new_hierarchy:
        parent_le, new_added = get_add_gbif_parent(
            child_le.uri, 
            child_le=child_le
        )
        if not check_all_hierarchy:
            add_new_hierarchy = new_added
        if not parent_le:
            add_new_hierarchy = False
            break
        # Make the child_le the parent_le for the 
        # next iteration of the loop.
        child_le = parent_le
    return gbif_le