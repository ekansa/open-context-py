import hashlib
import requests
from time import sleep

from django.core.cache import caches

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI

from opencontext_py.apps.all_items.models import (
    AllManifest,
)



SLEEP_TIME = 0.5


class PleiadesAPI():
    """ Interacts with the pleiades.stoa.org API to get useful information
    about place entities.
    """

    def __init__(self):
        self.delay_before_request = SLEEP_TIME
    

    def http_get_json_for_pleiades_uri(self, pleiades_uri):
        """Make a Web request to get json data from a pleiades_uri"""
        # Strip off any cruft in the URI
        pleiades_uri = AllManifest().clean_uri(pleiades_uri)
        url = f'https://{pleiades_uri}/json'
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        try:
            gapi = GeneralAPI()
            r = requests.get(
                url,
                timeout=240,
                headers=gapi.client_headers
            )
            r.raise_for_status()
            json_r = r.json()
        except:
            json_r = None
        return json_r
    

    def get_json_for_pleiades_uri(self, pleiades_uri, use_cache=True):
        """Get json data from a pleiades_uri, from cache or Web."""
        # Strip off any cruft in the URI
        pleiades_uri = AllManifest().clean_uri(pleiades_uri)
        if not use_cache:
            return self.http_get_json_for_pleiades_uri(pleiades_uri)
        hash_obj = hashlib.sha1()
        hash_obj.update(str(pleiades_uri).encode('utf-8'))
        hash_id = hash_obj.hexdigest()
        cache_key = f'pleiades_api_{hash_id}'
        cache = caches['memory']
        json_r = cache.get(cache_key)
        if json_r is not None:
            # We've already cached this, so returned the cached object
            return json_r
        json_r = self.http_get_json_for_pleiades_uri(pleiades_uri)
        try:
            cache.set(cache_key, json_r)
        except:
            pass
        return json_r


    def get_label_for_uri(self, pleiades_uri, use_cache=True):
        """
        gets the label for the URI referenced entity
        """
        json_data = self.get_json_for_pleiades_uri(pleiades_uri=pleiades_uri, use_cache=use_cache)
        if not json_data:
            return None
        # Success at getting the data!
        return json_data.get('title')
