import copy
import json
import logging

from django.conf import settings


from opencontext_py.libs.globalmaptiles import GlobalMercator

from opencontext_py.libs.isoyears import ISOyears
from opencontext_py.libs.memorycache import MemoryCache

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
)

from opencontext_py.apps.indexer import solrdocument_new_schema as solr_doc

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities


logger = logging.getLogger(__name__)



def make_cache_spacetime_obj_dict(
    uuids, 
    excludes={'geometry_type__in': ['Point', 'point']},
    cache_key_prefix='event-obj-geom-'
):
    """Make a dict of SpaceTime objects keyed by uuid"""
    m_cache = MemoryCache()
    uuids_for_qs = []
    uuid_event_dict = {}
    for uuid in uuids:
        cache_key = m_cache.make_cache_key(
            prefix=cache_key_prefix,
            identifier=uuid
        )
        event_obj = m_cache.get_cache_object(
            cache_key
        )
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
        cache_key = m_cache.make_cache_key(
            prefix=cache_key_prefix,
            identifier=str(event_obj.item.uuid)
        )
        m_cache.save_cache_object(
            cache_key, event_obj
        )
        uuid_event_dict[str(event_obj.item.uuid)] = event_obj
    
    return uuid_event_dict


