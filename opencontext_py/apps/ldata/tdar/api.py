import json
import requests
from time import sleep
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI


class tdarAPI():
    """ Interacts with the tDAR API
        First use-case is to relate DINAA trinomials with
        tDAR keywords
    """
    KEYWORD_API_BASE_URL = 'http://core.tdar.org/lookup/keyword'
    BASE_URI = 'http://core.tdar.org'
    SLEEP_TIME = .5

    def __init__(self):
        self.request_error = False
        self.request_url = False
        self.results = False
        self.best_match = False
        self.delay_before_request = self.SLEEP_TIME

    def get_site_keyword(self, site_keyword):
        """ get a key word for a site """
        result = False
        json_r = self.get_keyword_search_json(site_keyword,
                                              'SiteNameKeyword')
        if isinstance(json_r, dict):
            if 'items' in json_r:
                if len(json_r['items']) > 0:
                    result = {'label': False,
                              'id': False,
                              'tdar': json_r['items'][0]}
                    if 'label' in json_r['items'][0]:
                        # get the item label
                        result['label'] = json_r['items'][0]['label']
                    if 'detailUrl' in json_r['items'][0]:
                        # make a full URI for the keyword
                        result['id'] = self.BASE_URI + json_r['items'][0]['detailUrl']
                    if result['id'] is False \
                       or result['label'] is False:
                        # something wrong, incomplete data. Result is false.
                        result = False
        if result is not False:
            self.best_match = result
        return result

    def get_keyword_search_json(self, keyword, keyword_type):
        """
        gets json data from Arachne in response to a keyword search
        """
        if self.delay_before_request > 0:
            sleep(self.delay_before_request)
        payload = {'term': keyword,
                   'keywordType': keyword_type}
        url = self.KEYWORD_API_BASE_URL
        try:
            gapi = GeneralAPI()
            r = requests.get(url,
                             params=payload,
                             timeout=240,
                             headers=gapi.client_headers)
            self.request_url = r.url
            r.raise_for_status()
            json_r = r.json()
        except:
            self.request_error = True
            json_r = False
        return json_r
