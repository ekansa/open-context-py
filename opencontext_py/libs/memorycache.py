import hashlib
from django.conf import settings
from django.core.cache import caches
import django.utils.http as http
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity


class MemoryCache():
    """ Methods to store entities and data in memory
        to limit database requests
    """

    def __init__(self, request_dict_json=False):
        self.cache_names = [
            'local_memory',
            'memory',
            'redis',
        ]
        self.entity_prefix = 'entity'
        self.entity_context_prefix = 'entity-context'
    
    def get_entity(self, identifier):
        """ gets an entity either from the cache or from
            database lookups.
        """
        cache_key = self.make_cache_key(
            self.entity_prefix,
            identifier
        )
        item = self.get_cache_object(cache_key)
        if item is not None:
            return item
        else:
            return self._get_cache_entity_db(identifier)
    
    def _get_cache_entity_db(self, identifier):
        """Get an entity object from the database, if successful, cache it."""
        found = False
        entity = Entity()
        entity.get_context = True
        entity.get_thumbnail = True
        entity.get_ld_data_type = True
        found = entity.dereference(identifier)
        if not found:
            # case of linked data slugs
            found = entity.dereference(identifier, identifier)
        if not found:
            return False
        else:
            # cache the entity now
            return self.cache_entity(entity)
    
    def get_entity_by_context(self, context):
        cache_key = self.make_cache_key(self.entity_context_prefix,
                                        context)
        item = self.get_cache_object(cache_key)
        if item is not None:
            return item
        else:
            return self._get_cache_context_entity_db(context)
    
    def _get_cache_context_entity_db(self, context):
        """ dereference an item by spatial context path """
        found = False
        entity = Entity()
        entity.get_context = True
        found = entity.context_dereference(context)
        # print('look for ' + context)
        if not found:
            # maybe we're passing a uuid, uri or slug?
            found = entity.dereference(context)
        if not found:
            # case of linked data slugs
            found = entity.dereference(context, context)
        if not found:
            # give up, we can't find it.
            return False
        # cache the entity now
        return self.cache_entity(entity)
    
    def cache_entity(self, entity):
        """Caches an entity so it can be accessed by multiple keys """
        cache_keys = []
        if isinstance(entity.uuid, str):
            cache_keys.append(self.make_cache_key(self.entity_prefix,
                                                  entity.uuid))
        if isinstance(entity.slug, str):
            cache_keys.append(self.make_cache_key(self.entity_prefix,
                                                  entity.slug))
        if isinstance(entity.uri, str):
            cache_keys.append(self.make_cache_key(self.entity_prefix,
                                                  entity.uri))
        if isinstance(entity.context, str) and entity.item_type == 'subjects':
            cache_keys.append(self.make_cache_key(self.entity_context_prefix,
                                                  entity.context))
        # cache this item, with multiple cache keys, into multiple caches.
        for cache_key in cache_keys:
            self.save_cache_object(cache_key, entity)
        return entity
    
    def get_cache_object(self, cache_key, cache_names=None):
        """Gets an object, of key cache_key,
        from a list of caches specified by cache_names."""
        if cache_names is None:
            cache_names = self.cache_names
        obj = None
        for cache_name in cache_names:
            if obj is None:
                try:
                    cache = caches[cache_name]
                    obj = cache.get(cache_key)
                except:
                    obj = None
        return obj
    
    def save_cache_object(self, cache_key, obj, cache_names=None):
        """Saves an object, of key cache_key, into caches specified by cache_names."""
        ok = True
        if cache_names is None:
            cache_names = self.cache_names
        for cache_name in cache_names:
            try:
                cache = caches[cache_name]
                cache.set(cache_key, obj)
            except:
                ok = False
        return ok
        
    def make_cache_key(self, prefix, identifier):
        """Make a valid alphanumeric cache key from an identifier."""
        hash_obj = hashlib.sha1()
        concat_string = str(prefix) + " " + str(identifier)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()