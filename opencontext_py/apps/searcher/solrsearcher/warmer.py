import json
import requests
from unidecode import unidecode
from time import sleep
from django.conf import settings
from opencontext_py.libs.generalapi import GeneralAPI


class indexWarmer():
    """ Interacts with the Open Context API
        to make requests to warm up the solr index
    """
    SPACETIME_FACET_TYPES = ['oc-api:has-form-use-life-ranges',
                             'features']
    FACET_TYPES = ['oc-api:has-facets',
                   'oc-api:oc-api:has-numeric-facets',
                   'oc-api:oc-api:has-date-facets']
    OPTION_TYPES = ['oc-api:has-id-options',
                    'oc-api:has-numeric-options',
                    'oc-api:has-date-options',
                    'oc-api:has-text-options',
                    'oc-api:has-rel-media-options',
                    'oc-api:has-range-options']
    SLEEP_TIME = .33

    def __init__(self):
        self.request_errors = []
        self.request_url = False
        self.results = False
        self.best_match = False
        self.recursion_depth = 0
        self.max_recursion_depth = 3
        self.delay_before_request = self.SLEEP_TIME

    def get_search_links(self, url, recursion_depth=0):
        """ get a key word for a site """
        results = False
        if recursion_depth <= self.max_recursion_depth:
            recursion_depth += 1
            json_r = self.get_search_json(url)
            new_urls = []
            if isinstance(json_r, dict):
                for facet_type in self.SPACETIME_FACET_TYPES:
                    if facet_type in json_r:
                        for option in json_r[facet_type]:
                            if 'json' in option:
                                new_urls.append(option['json'])
                for facet_type in self.FACET_TYPES:
                    if facet_type in json_r:
                        for facet in json_r[facet_type]:
                            for option_type in self.OPTION_TYPES:
                                if option_type in facet:
                                    for option in facet[option_type]:
                                        new_urls.append(option['json'])
                print(str(len(new_urls)) + ' urls in: ' + unidecode(url))
                for new_url in new_urls:
                    print('Getting: ' + unidecode(new_url) + ', level: ' + str(recursion_depth))
                    self.get_search_links(new_url, recursion_depth)
            else:
                self.request_errors.append(url)
                print('New error ! ' + unidecode(url))
        else:
            print('*****************************************')
            print('At maximum depth from this path.')
            print('Error count: ' + str(len(self.request_errors)))
            print('*****************************************')

    def get_search_json(self, url):
        """
        gets json data from Open Context in response to a keyword search
        """
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        try:
            gapi = GeneralAPI()
            r = requests.get(url,
                             timeout=240,
                             headers=gapi.client_headers)
            self.request_url = r.url
            r.raise_for_status()
            json_r = r.json()
        except:
            self.request_error = True
            json_r = False
        return json_r
