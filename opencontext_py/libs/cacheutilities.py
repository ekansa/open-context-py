import hashlib
from django.conf import settings
from django.db import models
from django.core.cache import caches
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile
from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence


class CacheUtilities():
    """ Methods to use different caches to
        make common requests
    
    """
    def __init__(self):
        self.a_level_cache_name = 'redis'
        self.b_level_cache_name = 'default'
        self.ok_caches = {
            'redis': True,
            'default': True
        }
        self.print_caching = False

    def make_cache_key(self, prefix, identifier):
        """ makes a valid OK cache key """
        hash_obj = hashlib.sha1()
        concat_string = str(prefix) + " " + str(identifier)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def make_memory_cache_key(self, prefix, identifier):
        """ makes a valid OK cache key """
        return self.make_cache_key(prefix, identifier)

    def get_cache_object(self,
                         key,
                         try_b_level_also=False,
                         cache_name='redis'):
        """ gets a cached reddis object """
        cache_name = self.use_ok_cache(cache_name)
        try:
            cache = caches[cache_name]
            obj = cache.get(key)
        except:
            obj = None
        if obj is None or try_b_level_also:
            try:
                cache = caches[self.b_level_cache_name]
                obj = cache.get(key)
            except:
                obj = None
        return obj

    def save_cache_object(self,
                          key,
                          obj,
                          save_b_level_also=False,
                          cache_name='redis'):
        """ saves a cached reddis object """
        cache_name = self.use_ok_cache(cache_name)
        try:
            cache = caches[cache_name]
            cache.set(key, obj)
            ok = True
            if self.print_caching:
                print('Cache Saved: ' + key)
        except:
            if cache_name in self.ok_caches:
                self.ok_caches[cache_name] = False
            ok = False
        if ok is False or save_b_level_also:
            # now try to save again, using the b-level-cache
            try:
                cache = caches[self.b_level_cache_name]
                cache.set(key, obj)
                ok = True
                if self.print_caching:
                    print('Cache Saved: ' + key)
            except:
                ok = False
        if ok is False:    
            if self.print_caching:
                print('Failed to cache: ' + key)
        return ok

    def use_ok_cache(self, cache_name):
        """ fall back to the
            self.b_level_cache_name
            if the a_level_cache isn't working
            or has missing data
        """
        if cache_name in self.ok_caches:
            if self.ok_caches[cache_name]:
                use_cache_name = cache_name
            else:
                # use the default b level cache
                use_cache_name = self.b_level_cache_name
        else:
            use_cache_name = self.b_level_cache_name
        return use_cache_name