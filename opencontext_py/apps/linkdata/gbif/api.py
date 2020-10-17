import json
import requests
from time import sleep

from django.core.cache import caches

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI


JSON_BASE_URL = 'https://api.gbif.org/v1/species/{}'
VERNACULAR_NAME_BASE_URL = 'http://api.gbif.org/v1/species/{}/vernacularNames'
SLEEP_TIME = 0.25


class gbifAPI():
    """ Interacts with the Global Biodiversity Information Facility (GBIF)
    to get useful data about biological taxa
    """

    def __init__(self):
        self.json_base_url = JSON_BASE_URL
        self.vern_json_base_url = VERNACULAR_NAME_BASE_URL
        self.delay_before_request = SLEEP_TIME
        self.json_data = None
        self.request_url = None

    def get_gbif_species_json_via_http(self, gbif_id):
        """Gets species JSON data for a GBIF id"""
        sleep(self.delay_before_request)
        url = self.json_base_url.format(int(gbif_id))
        self.request_url = url
        r = requests.get(url)
        r.raise_for_status()
        return r.json()

    def get_gbif_species_json(self, gbif_id, use_cache=True):
        """Gets species JSON data for a GBIF id"""
        if not use_cache:
            # Skip using the cache, just to a web request.
            return self.get_gbif_species_json_via_http(gbif_id)
        cache_key = 'gbif_species_json_{}'.format(int(gbif_id))
        cache = caches['redis']
        # Look for the JSON in the cache
        obj = cache.get(cache_key)
        if obj is not None:
            # We have the cached JSON, return it.
            return obj
        # We don't have it cached, so get it via HTTP request
        # then cache.
        obj = self.get_gbif_species_json_via_http(gbif_id)
        try:
            cache.set(cache_key, obj)
        except:
            pass
        return obj


    def get_gbif_cannonical_name(self, gbif_id, use_cache=True):
        """Get the cannonical name from the GBIF API for an ID"""
        json_r = self.get_gbif_species_json(gbif_id, use_cache=use_cache)
        return json_r.get('canonicalName')


    def get_gbif_parent_key(
        self, 
        gbif_id, 
        use_cache=False, 
        no_parent_default=None
    ):
        """Get the parent GBIF ID from the GBIF API for an ID"""
        json_r = self.get_gbif_species_json(gbif_id, use_cache=use_cache)
        # Default to None to indicate no parent found in a check.
        return json_r.get('parentKey', no_parent_default)

    
    def get_gbif_vernacular_name(self, gbif_id, lang_code='eng'):
        """Get the first vernacular name from the GBIF API for an ID"""
        sleep(self.delay_before_request)
        url = self.vern_json_base_url.format(int(gbif_id))
        r = requests.get(url)
        r.raise_for_status()
        json_r = r.json()
        vern_name = None
        for result in json_r.get('results', []):
            if result.get('language') != lang_code:
                continue
            vern_name = result.get("vernacularName")
            if vern_name is not None:
                break
        return vern_name

