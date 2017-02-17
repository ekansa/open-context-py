import json
import requests
from time import sleep
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.ldata.linkentities.models import LinkEntityGeneration


class GeonamesAPI():
    """ Interacts with Geonames """
    SEARCH_BASE_URL = 'http://api.geonames.org/searchJSON'
    JSON_BASE_URL = 'http://www.geonames.org/getJSON?id='
    VOCAB_URI = 'http://www.geonames.org'
    SLEEP_TIME = .5

    def __init__(self):
        self.request_error = False
        self.json_base_url = self.JSON_BASE_URL
        self.delay_before_request = self.SLEEP_TIME
        self.json_data = False

    def get_labels_for_uri(self, geonames_uri):
        """
        gets the label for the URI referenced entity
        """
        output = False
        json_data = self.get_json_for_geonames_uri(geonames_uri)
        if isinstance(json_data, dict):
            # success at getting the data!
            output = {}
            if 'name' in json_data:
                output['label'] = json_data['name']
            if 'toponymName' in json_data:
                output['alt_label'] = json_data['toponymName']
        return output

    def get_json_for_geonames_uri(self, geonames_uri):
        """
        gets json data from a geonames_uri
        """
        le_gen = LinkEntityGeneration()
        geonames_uri = le_gen.make_clean_uri(geonames_uri) # strip off any cruft in the URI
        geo_ex = geonames_uri.split('/')
        geonames_id = geo_ex[-1]
        url = self.json_base_url + str(geonames_id)
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        try:
            gapi = GeneralAPI()
            r = requests.get(url,
                             timeout=240,
                             headers=gapi.client_headers)
            r.raise_for_status()
            self.request_url = r.url
            json_r = r.json()
        except:
            json_r = False
        self.json_data = json_r
        return self.json_data
    
    def search_admin_entity(self,
                            q_str,
                            admin_level=0,
                            username='demo',
                            lat=None,
                            lon=None,
                            degree_dif=.5):
        """ searches for an entity of a given administrative type
            associated for a given q_str
        """
        output = None
        all_params = {}
        all_params['q'] = q_str
        all_params['username'] = username
        all_params['maxRows'] = 1
        if isinstance(lat, float) \
           and isinstance(lon, float) \
           and isinstance(degree_dif, float):
            all_params['east'] = lon - degree_dif
            all_params['west'] = lon + degree_dif
            all_params['south'] = lat - degree_dif
            all_params['north'] = lat + degree_dif
        if admin_level == 0:
            fcodes = ['PCLI',
                      'OCN']
        elif admin_level == 1:
            fcodes = ['ADM1']
        elif admin_level == 2:
            fcodes = ['ADM2']
        else:
            fcodes = [None]
        for fcode in fcodes:
            params = all_params
            if isinstance(fcode, str):
                params['fcode'] = fcode
            if self.delay_before_request > 0:
                # default to sleep BEFORE a request is sent, to
                # give the remote service a break.
                sleep(self.delay_before_request)
            try:
                gapi = GeneralAPI()
                r = requests.get(self.SEARCH_BASE_URL,
                                 params=params,
                                 timeout=10,
                                 headers=gapi.client_headers)
                r.raise_for_status()
                # print('Checking: ' + r.url)
                json_r = r.json()
            except:
                json_r = False
            if json_r is not False:
                output = json_r
                break
        return output