import requests
from time import sleep

from opencontext_py.apps.all_items.models import (
    AllManifest,
)

from django.core.cache import caches

from opencontext_py.apps.linkdata.getty_aat import configs as aat_configs


SLEEP_TIME = 0.25


class GettyAATapi():
    """ Interacts with the Getty Art and Architecture Thesaurus (AAT)
    to get useful classification categories to describe material culture
    """

    def __init__(self):
        self.delay_before_request = SLEEP_TIME
        self.json_data = None
        self.request_url = None

    def get_aat_json_via_http(self, aat_uri):
        """Gets concept JSON data for a Getty AAT URI using HTTP"""
        sleep(self.delay_before_request)
        aat_uri = AllManifest().clean_uri(aat_uri)
        if not aat_uri.startswith(aat_configs.GETTY_AAT_BASE_URI):
            return None
        url = f'https://{aat_uri}.json'
        self.request_url = url
        r = requests.get(url)
        r.raise_for_status()
        return r.json()

    def get_aat_json(self, aat_uri, use_cache=True):
        """Gets Getty AAT concept JSON data by URI, using the cache"""
        if not use_cache:
            # Skip using the cache, just to a web request.
            return self.get_aat_json_via_http(aat_uri)
        cache_key = f'getty_aat_json_{aat_uri}'
        cache = caches['redis']
        # Look for the JSON in the cache
        obj = cache.get(cache_key)
        if obj is not None:
            # We have the cached JSON, return it.
            return obj
        # We don't have it cached, so get it via HTTP request
        # then cache.
        obj = self.get_aat_json_via_http(aat_uri)
        try:
            cache.set(cache_key, obj)
        except:
            pass
        return obj
