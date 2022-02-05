import hashlib
import requests
from time import sleep

from django.core.cache import caches

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI

# JSON URL from a numeric pleiades ID
JSON_ID_BASE_URL = 'https://pleiades.stoa.org/places/{}/json'

# JSON URL from a Pleiades URI
JSON_URI_BASE_URL = '{}/json'

SLEEP_TIME = 0.25


class pleiadesAPI():
    """ Interacts with Pleiades to get JSON data
    """

    def __init__(self):
        self.json_id_base_url = JSON_ID_BASE_URL
        self.json_uri_base_url = JSON_URI_BASE_URL 
        self.delay_before_request = SLEEP_TIME
        self.json_data = None
        self.request_url = None


    def make_json_url_and_hash(self, pleiades_uri=None, pleiades_id=None):
        """Makes the JSON url and hash to use as a cache key"""
        if pleiades_uri:
            # Use the full pleiades uri to make the request url
            url = self.json_uri_base_url.format(pleiades_uri)
        else:
            # Use a pleiades integer ID to make the request url
            url = self.json_id_base_url.format(int(pleiades_id))
        
        hash_obj = hashlib.sha1()
        hash_obj.update(url.encode('utf-8'))
        return url, hash_obj.hexdigest()
        

    def get_pleiades_json_via_http(self, pleiades_uri=None, pleiades_id=None):
        """Gets place JSON data for a pleiades_id"""
        sleep(self.delay_before_request)
        url, _ =  self.make_json_url_and_hash(
            pleiades_uri=pleiades_uri, 
            pleiades_id=pleiades_id
        )
        self.request_url = url
        r = requests.get(url)
        r.raise_for_status()
        return r.json()


    def get_pleiades_json(self, pleiades_uri=None, pleiades_id=None, use_cache=True):
        """Gets species JSON data for a GBIF id"""
        if not use_cache:
            # Skip use of the cache
            return self.get_pleiades_json_via_http(
                pleiades_uri=pleiades_uri, 
                pleiades_id=pleiades_id
            )
        url, url_hash =  self.make_json_url_and_hash(
            pleiades_uri=pleiades_uri, 
            pleiades_id=pleiades_id
        )
        cache_key = f'pleiades_json_{url_hash}'
        cache = caches['redis']
        # Look for the JSON in the cache
        obj = cache.get(cache_key)
        if obj is not None:
            # We have the cached JSON, return it.
            return obj
        # We don't have it cached, so get it via HTTP request
        # then cache.
        obj = self.get_pleiades_json_via_http(
            pleiades_uri=pleiades_uri, 
            pleiades_id=pleiades_id
        )
        try:
            cache.set(cache_key, obj)
        except:
            pass
        return obj


    def get_place_title(self, pleiades_uri=None, pleiades_id=None, use_cache=True):
        """Get the main title / label for a pleiades place"""
        json_r = self.get_pleiades_json(
            pleiades_uri=pleiades_uri, 
            pleiades_id=pleiades_id, 
            use_cache=use_cache
        )
        return json_r.get('title')


