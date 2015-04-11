import json
import requests
from time import sleep
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI


class GeonamesAPI():
    """ Interacts with Periodo """
    JSON_BASE_URL = 'http://www.geonames.org/getJSON?id='
    SLEEP_TIME = .5

    def __init__(self):
        self.request_error = False
        self.json_base_url = self.JSON_BASE_URL
        self.delay_before_request = self.SLEEP_TIME
        self.json_data = False

    def get_json_for_geonames_uri(self, geonames_uri):
        """
        gets json daa from a geonames_uri
        """
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
