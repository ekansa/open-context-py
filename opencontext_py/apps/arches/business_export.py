
import copy
import hashlib
import uuid as GenUUID

from opencontext_py.apps.all_items.configs import *
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

DEFAULT_LABEL_TITLE_DATA_KEY_UUID = 'c4e449da-9f31-11ec-8aa7-00155d13e783'
DEFAULT_LABEL_TILE_CONFIG = {
    'data': {
        'c4e448e0-9f31-11ec-8aa7-00155d13e783': None,
        'c4e4496c-9f31-11ec-8aa7-00155d13e783': 'Label',
        DEFAULT_LABEL_TITLE_DATA_KEY_UUID: 'Fake Site',
        'c4e44a48-9f31-11ec-8aa7-00155d13e783': None
    },
    'nodegroup_id': 'c4e446e2-9f31-11ec-8aa7-00155d13e783',
    'parenttile_id': None,
    'provisionaledits': None,
    'sortorder': None,
}


CONFIGS = {
    # Keyed by item_class__slug.
    'oc-gen-cat-site': {
        'graph_id': 'adf81abc-9f31-11ec-bad4-00155d13e783',
        'label_tile_config': DEFAULT_LABEL_TILE_CONFIG.copy(),
        'label_tile_data_key_uuid': DEFAULT_LABEL_TITLE_DATA_KEY_UUID,
    },

}


def make_deterministic_uuid(item_uuid, salt):
    hash_val = f'{salt}-{item_uuid}'
    hash_obj = hashlib.sha1()
    hash_obj.update(hash_val.encode('utf-8'))
    hash_id =  hash_obj.hexdigest()
    # Now convert that hash into a uuid. Note, we're only using
    # the first 32 characters. This should still be enough to have
    # really, really high certainty we won't have hash-collisions on
    # data that should not be considered unique. If we run into a problem
    # we can always override this.
    uuid_from_hash_id = str(
        GenUUID.UUID(hex=hash_id[:32])
    )
    return uuid_from_hash_id


def make_resource_label_tile(man_obj, config):
    tile_config = config.get('label_tile_config')
    if not tile_config:
        return None
    label_tile_data_key_uuid = config.get('label_tile_data_key_uuid')
    if not label_tile_data_key_uuid:
        return None
    tile = tile_config.copy()
    tile['resourceinstanceid'] = str(man_obj.uuid)
    tile['tileid'] = make_deterministic_uuid(
        str(man_obj.uuid),
        'label'
    )
    tile['data'][label_tile_data_key_uuid] = man_obj.label
    return tile


def make_resource_instance_business_data(man_obj, configs):
    config = configs.get(man_obj.item_class.slug)
    if not config:
        # We don't have a configuration for this item type.
        return None
    resource = {
        'resourceinstance': {
            'graph_id': config.get('graph_id'),
            'legacy_id': None,
            'resourceinstanceid': str(man_obj.uuid),
        },
        'tiles': [],
    }
    label_tile = make_resource_label_tile(man_obj, config)
    if label_tile:
        resource['tiles'].append(label_tile)
    a_qs = AllAssertion.objects.filter(subject=man_obj)

    return resource

def make_all_resources_business_data(manifest_qs, configs):
    resources = []
    for man_obj in manifest_qs:
        resource = make_resource_instance_business_data(man_obj, configs)
        if resource is None:
            # We don't have a configuration for this type of manifest object to Arches.
            continue
        resources.append(resource)
    return resources