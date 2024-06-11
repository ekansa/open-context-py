import hashlib
import requests
from time import sleep

from django.core.cache import caches

from opencontext_py.libs.generalapi import GeneralAPI

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
)



SLEEP_TIME = 0.5
USE_CACHE = True
DEFAULT_LANG_CODE_KEY = configs.DEFAULT_LANGUAGE_DICT['item_key']
WIKI_COORDINATE_LOCATION_PROP_ID = 'P625'


def get_wikidata_id_from_uri(wikidata_uri):
    """Extracts a Wikidata ID from a Wikidata URI"""
    if not 'wikidata.org/wiki' in wikidata_uri:
        return None
    wikidata_uri = AllManifest().clean_uri(wikidata_uri)
    wikidata_id = wikidata_uri.split('/')[-1]
    return wikidata_id


class WikidataAPI():
    """ Interacts with the Wikidata.org API to get useful information
    about entities.
    """

    def __init__(self):
        self.delay_before_request = SLEEP_TIME


    def make_wikidata_api_url(self, wikidata_uri):
        """Make a URL to get data about a Wikidata_uri entity"""
        wikidata_id = get_wikidata_id_from_uri(wikidata_uri)
        if not wikidata_id:
            return None
        return f'https://www.wikidata.org/wiki/Special:EntityData/{wikidata_id}.json?flavor=simple'


    def http_get_json_for_wikidata_uri(self, wikidata_uri):
        """Make a Web request to get json data from a wikidata_uri"""
        # Convert a wikidata URI into an API url
        url = self.make_wikidata_api_url(wikidata_uri)
        if not url:
            return None
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
    

    def get_json_for_wikidata_uri(self, wikidata_uri, use_cache=USE_CACHE):
        """Get json data from a wikidata_uri, from cache or Web."""
        # Strip off any cruft in the URI
        wikidata_uri = AllManifest().clean_uri(wikidata_uri)
        if not use_cache:
            return self.http_get_json_for_wikidata_uri(wikidata_uri)
        wikidata_id = get_wikidata_id_from_uri(wikidata_uri)
        hash_obj = hashlib.sha1()
        hash_obj.update(str(wikidata_id).encode('utf-8'))
        hash_id = hash_obj.hexdigest()
        cache_key = f'wikidata_api_{hash_id}'
        cache = caches['memory']
        json_r = cache.get(cache_key)
        if json_r is not None:
            # We've already cached this, so returned the cached object
            return json_r
        json_r = self.http_get_json_for_wikidata_uri(wikidata_uri)
        try:
            cache.set(cache_key, json_r)
        except:
            pass
        return json_r


    def get_label_for_uri(self, wikidata_uri, use_cache=USE_CACHE):
        """
        gets the label for the URI referenced entity
        """
        json_data = self.get_json_for_wikidata_uri(wikidata_uri=wikidata_uri, use_cache=use_cache)
        if not json_data:
            return None
        # Success at getting the data!
        wikidata_id = get_wikidata_id_from_uri(wikidata_uri)
        ent_dict = json_data.get('entities', {}).get(wikidata_id)
        if not ent_dict:
            return None
        label_dict =  ent_dict.get('labels')
        if not label_dict:
            return None
        default_label_dict = label_dict.get(DEFAULT_LANG_CODE_KEY)
        if default_label_dict and default_label_dict.get('value'):
            # we have a label in our default language!
            return default_label_dict.get('value')
        for lang_key, val_dict in label_dict.items():
            # just return the first label we find.
            return val_dict.get('value')
    

    def get_coordinate_lat_lon_dict_for_uri(self, wikidata_uri, use_cache=USE_CACHE):
        """
        Gets coordinates for 
        """
        json_data = self.get_json_for_wikidata_uri(wikidata_uri=wikidata_uri, use_cache=use_cache)
        if not json_data:
            return None
        # Success at getting the data!
        wikidata_id = get_wikidata_id_from_uri(wikidata_uri)
        ent_dict = json_data.get('entities', {}).get(wikidata_id)
        if not ent_dict:
            return None
        claims_dict =  ent_dict.get('claims')
        if not claims_dict:
            return None
        coord_list = claims_dict.get(WIKI_COORDINATE_LOCATION_PROP_ID, [])
        if not coord_list:
            return None
        coord_dict = coord_list[0]
        val_dict = coord_dict.get('mainsnak', {}).get('datavalue', {}).get('value', {})
        if not val_dict:
            return None
        if not val_dict.get('latitude') or not val_dict.get('longitude'):
            return None
        return {
            'latitude': float(val_dict.get('latitude')),
            'longitude': float(val_dict.get('longitude')),
        }
