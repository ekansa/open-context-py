import copy
import json
import logging

from django.conf import settings
from django.core.cache import caches

from opencontext_py.libs.globalmaptiles import GlobalMercator

from opencontext_py.libs.isoyears import ISOyears

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
)

from opencontext_py.apps.indexer import solrdocument_new_schema as solr_doc

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities


logger = logging.getLogger(__name__)


def make_spacetime_obj_cache_key(uuid):
    """Makes a cache key for looking up SpaceTime objects keyed by uuid"""
    return f'event-obj-geom-{str(uuid)}'


def make_cache_spacetime_obj_dict(
    uuids, 
    excludes={'geometry_type__in': ['Point', 'point']},
):
    """Make a dict of SpaceTime objects keyed by uuid"""
    cache = caches['redis']
    uuids_for_qs = []
    uuid_event_dict = {}
    for uuid in uuids:
        cache_key = make_spacetime_obj_cache_key(uuid)
        event_obj = cache.get(cache_key)
        if event_obj is None:
            uuids_for_qs.append(uuid)
        else:
            uuid_event_dict[uuid] = event_obj
    
    if not len(uuids_for_qs):
        # Found them all from the cache!
        # Return without touching the database.
        return uuid_event_dict
    
    # Lookup the remaining geospace objects from a
    # database query. We order by uuid then reverse
    # of feature_id so that the lowest feature id is the
    # thing that actually gets cached.
    event_qs = AllSpaceTime.objects.filter(
        item_id__in=uuids_for_qs,
    ).select_related(
        'item'
    ).order_by('item', '-feature_id')
    
    if event_qs:
        event_qs = event_qs.exclude(**excludes)

    for event_obj in event_qs:
        cache_key = make_spacetime_obj_cache_key(str(event_obj.item.uuid))
        try:
            cache.set(cache_key, event_obj)
        except:
            pass
        uuid_event_dict[str(event_obj.item.uuid)] = event_obj
    
    return uuid_event_dict


