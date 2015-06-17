import json
import requests
from time import sleep
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.ldata.linkentities.models import LinkEntityGeneration


class orcidAPI():
    """ Interacts with ORCID to get useful information about people
    """
    JSON_BASE_URL = 'http://pub.orcid.org/'
    SLEEP_TIME = .5

    def __init__(self):
        self.url = False
        self.request_error = False
        self.json_base_url = self.JSON_BASE_URL
        self.delay_before_request = self.SLEEP_TIME
        self.json_data = False
        self.response_headers = False

    def get_basic_json_from_uri(self, orcid_uri):
        """
        gets json daa from the ORCID URI
        """
        url = self.make_orcid_api_url(orcid_uri)
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        try:
            gapi = GeneralAPI()
            headers = gapi.client_headers
            headers['Accept'] = 'application/json'
            r = requests.get(url,
                             timeout=240,
                             headers=headers)
            r.raise_for_status()
            self.response_headers = r.headers
            self.request_url = r.url
            json_r = r.json()
        except:
            json_r = False
        self.json_data = json_r
        return self.json_data

    def make_orcid_api_url(self, orcid_uri):
        """ makes an orcid API uri based on
            an ORCID URI
        """
        uri_ex = orcid_uri.split('/')
        orcid_id = uri_ex[-1]
        url = self.json_base_url + str(orcid_id) + '/orcid-profile'
        self.url = url
        return url
