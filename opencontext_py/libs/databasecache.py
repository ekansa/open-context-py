import hashlib
from django.conf import settings
from django.core.cache import caches
from django.template.defaultfilters import slugify
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict


class DatabaseCache():
    """ Methods to store entities and data in the database
        mainly for faceted search requests
    """

    def __init__(self):
        self.do_caching = False

    def make_cache_key(self, prefix, identifier):
        """ makes a valid OK cache key """
        hash_obj = hashlib.sha1()
        concat_string = str(prefix) + " " + str(identifier)
        hash_obj.update(concat_string.encode('utf-8'))
        output = str(hash_obj.hexdigest())
        slug_prefix = str(slugify(prefix))
        if len(slug_prefix) < 20:
            # human readable output
            output = slug_prefix + '-' + output
        return output

    def get_cache_object(self, key):
        """ gets a cached object """
        obj = None
        if self.do_caching:
            try:
                cache = caches['default']
                obj = cache.get(key)
            except:
                obj = None
        return obj

    def save_cache_object(self, key, obj):
        """ saves a cached object """
        ok = False
        if self.do_caching:
            try:
                cache = caches['default']
                cache.set(key, obj)
                ok = True
            except:
                ok = False
        return ok

    def remove_cache_object(self, key):
        """ deletes a cached object """
        ok = False
        if self.do_caching:
            try:
                cache = caches['default']
                cache.delete(key)
                ok = True
            except:
                ok = False
        return ok
