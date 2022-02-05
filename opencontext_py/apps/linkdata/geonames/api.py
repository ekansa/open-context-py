import hashlib
import requests
from time import sleep

from django.core.cache import caches

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI

from opencontext_py.apps.all_items.models import (
    AllManifest,
)


SEARCH_BASE_URL = 'http://api.geonames.org/searchJSON'
JSON_BASE_URL = 'http://www.geonames.org/getJSON?id='
SLEEP_TIME = 0.5


class GeonamesAPI():
    """ Interacts with the Geonames.org API to get useful information
    about place entities.
    """

    def __init__(self):
        self.json_base_url = JSON_BASE_URL
        self.search_base_url = SEARCH_BASE_URL
        self.delay_before_request = SLEEP_TIME
    

    def http_get_json_for_geonames_uri(self, geonames_uri):
        """Make a Web request to get json data from a geonames_uri"""
        # Strip off any cruft in the URI
        geonames_uri = AllManifest().clean_uri(geonames_uri)
        
        geo_ex = geonames_uri.split('/')
        geonames_id = int(geo_ex[-1])
        url = self.json_base_url + str(geonames_id)
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
    

    def get_json_for_geonames_uri(self, geonames_uri, use_cache=True):
        """Get json data from a geonames_uri, from cache or Web."""
        # Strip off any cruft in the URI
        geonames_uri = AllManifest().clean_uri(geonames_uri)
        if not use_cache:
            return self.http_get_json_for_geonames_uri(geonames_uri)
        hash_obj = hashlib.sha1()
        hash_obj.update(str(geonames_uri).encode('utf-8'))
        hash_id = hash_obj.hexdigest()
        cache_key = f'geonames_api_{hash_id}'
        cache = caches['memory']
        json_r = cache.get(cache_key)
        if json_r is not None:
            # We've already cached this, so returned the cached object
            return json_r
        json_r = self.http_get_json_for_geonames_uri(geonames_uri)
        try:
            cache.set(cache_key, json_r)
        except:
            pass
        return json_r


    def get_labels_for_uri(self, geonames_uri, use_cache=True):
        """
        gets the label for the URI referenced entity
        """
        json_data = self.get_json_for_geonames_uri(geonames_uri, use_cache=use_cache)
        if not json_data:
            return None, None
        # Success at getting the data!
        # Return a tuple that we can interpret as 'label' and SKOS Alt-label.
        return json_data.get('name'), json_data.get('toponymName')


    def search_admin_entity(
        self,
        q_str,
        admin_level=0,
        username='demo',
        lat=None,
        lon=None,
        degree_dif=0.5,
    ):
        """Searches for an entity of a given administrative type for a given q_str"""
        all_params = {
            'q': q_str,
            'username': username,
            'maxRows': 1,
        }
        if (isinstance(lat, float) and isinstance(lon, float) 
            and isinstance(degree_dif, float)):
            all_params['east'] = lon - degree_dif
            all_params['west'] = lon + degree_dif
            all_params['south'] = lat - degree_dif
            all_params['north'] = lat + degree_dif
        if admin_level == 0:
            fcodes = ['PCLI', 'OCN']
        elif admin_level == 1:
            fcodes = ['ADM1']
        elif admin_level == 2:
            fcodes = ['ADM2']
        else:
            fcodes = [None]
        for fcode in fcodes:
            params = all_params.copy()
            if fcode is not None:
                params['fcode'] = fcode
            if self.delay_before_request > 0:
                # default to sleep BEFORE a request is sent, to
                # give the remote service a break.
                sleep(self.delay_before_request)
            try:
                gapi = GeneralAPI()
                r = requests.get(
                    self.search_base_url,
                    params=params,
                    timeout=10,
                    headers=gapi.client_headers
                )
                r.raise_for_status()
                json_r = r.json()
            except:
                json_r = None
            if json_r:
                # We have a result for this query.
                return json_r
        # We found nothing.
        return None


