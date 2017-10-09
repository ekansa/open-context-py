import hashlib
from django.conf import settings
from django.db import models
from django.core.cache import caches
from opencontext_py.apps.entities.entity.models import Entity


class ItemGenerationCache():
    """
    methods for using the Reddis cache to
    streamline making item JSON-LD
    """

    def __init__(self):
        self.redis_ok = True
        self.print_caching = False

    def get_entity(self, identifier):
        """ gets an entity either from the cache or from
            database lookups
        """
        cache_id = self.make_memory_cache_key('entities', identifier)
        item = self.get_cache_object(cache_id)
        if item is not None:
            output = item
        else:
            entity = Entity()
            found = entity.dereference(identifier)
            if found:
                output = entity
                self.save_cache_object(cache_id, entity)
            else:
                output = False
        return output

    def get_entity_w_thumbnail(self, identifier):
        """ gets an entity with thumbnail (useful for item json) """
        cache_id = self.make_memory_cache_key('entities-thumb', identifier)
        item = self.get_cache_object(cache_id)
        if item is not None:
            output = item
            # print('YEAH found entity: ' + cache_id)
        else:
            entity = Entity()
            entity.get_thumbnail = True
            found = entity.dereference(identifier)
            if found:
                output = entity
                self.save_cache_object(cache_id, entity)
            else:
                output = False
        return output

    def make_memory_cache_key(self, prefix, identifier):
        """ makes a valid OK cache key """
        hash_obj = hashlib.sha1()
        concat_string = str(prefix) + " " + str(identifier)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def get_cache_object(self, key):
        """ gets a cached reddis object """
        try:
            cache = caches['redis']
            obj = cache.get(key)
            if self.print_caching:
                print('Cache checked: ' + key)
        except:
            obj = None
            if self.print_caching:
                print('Cache Fail checked: ' + key)
        return obj

    def save_cache_object(self, key, obj):
        """ saves a cached reddis object """
        try:
            cache = caches['redis']
            cache.set(key, obj)
            ok = True
            if self.print_caching:
                print('Cache Saved: ' + key)
        except:
            self.redis_ok = False
            ok = False
            if self.print_caching:
                print('Failed to cache: ' + key)
        return ok
