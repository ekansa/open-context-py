import json
import requests
from time import sleep
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.ldata.linkentities.models import LinkEntityGeneration


class eolAPI():
    """ Interacts with the Encyclopeidia of Life
        (EOL) to get useful data about biological taxa
    """
    VOCAB_URI = 'http://eol.org/'
    JSON_BASE_URL = 'http://eol.org/api/pages/1.0/'
    SLEEP_TIME = .5

    def __init__(self):
        self.request_error = False
        self.json_base_url = self.JSON_BASE_URL
        self.delay_before_request = self.SLEEP_TIME
        self.json_data = False
        self.request_url = False

    def get_labels_for_uri(self, eol_uri):
        """ just returns the label, if found """
        output = False
        json_data = self.get_basic_json_for_eol_uri(eol_uri)
        if isinstance(json_data, dict):
            output = {}
            if 'scientificName' in json_data:
                output['label'] = json_data['scientificName']
                output['alt_label'] = json_data['scientificName']
            elif 'taxonConcept' in json_data:
                if 'scientificName' in json_data['taxonConcept']:
                    output['label'] = json_data['taxonConcept']['scientificName']
                    output['alt_label'] = json_data['taxonConcept']['scientificName']
        return output

    def get_basic_json_for_eol_uri(self, eol_uri):
        """
        gets json daa from the EOL
        """
        le_gen = LinkEntityGeneration()
        eol_uri = le_gen.make_clean_uri(eol_uri)  # strip off any cruft in the URI
        eol_ex = eol_uri.split('/')
        eol_id = eol_ex[-1]
        url = self.json_base_url + str(eol_id)
        url += '.json'
        self.request_url = url
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
