import json
import requests
from urllib.parse import urlparse, parse_qs
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI


class ArachneAPI():
    """ Interacts with Arachne """
    ARACHNE_SEARCH = 'arachne.dainst.org/search'
    DEFAULT_API_BASE_URL = 'https://arachne.dainst.org/data/search'
    DEFAULT_HTML_BASE_URL = 'https://arachne.dainst.org/search'
    DEFAULT_IMAGE_BASE_URL = 'https://arachne.dainst.org/data/image/height/'
    DEFAULT_ENTITY_BASE_URL = 'https://arachne.dainst.org/entity/'
    DEFAULT_IMAGE_HEIGHT = 120

    def __init__(self):
        self.arachne_json_r = False
        self.arachne_json_url = False
        self.arachne_html_url = False
        self.filter_by_images = True
        self.image_height = self.DEFAULT_IMAGE_HEIGHT
        self.result_count = False
        self.results = False

    def get_keyword_results(self, keyword):
        """ sends JSON request, makes list of oc_object entities if
            search finds entities
        """
        self.get_keyword_search_json(keyword)
        self.get_result_metadata()
        self.generate_results_list()
        return self.results
    
    def get_results_from_search_url(self, search_url):
        """ parses a search URL, then makes a lost of
            oc_object entities if search finds entities
        """
        self.get_json_from_search_url(search_url)
        self.get_result_metadata()
        self.generate_results_list()
        return self.results

    def get_result_metadata(self):
        """ gets metadata about the search result """
        if self.arachne_json_r is not False:
            if 'size' in self.arachne_json_r:
                self.result_count = self.arachne_json_r['size']

    def generate_results_list(self):
        """ makes a list of results with full URLs """
        if self.arachne_json_r is not False:
            if 'entities' in self.arachne_json_r:
                self.results = []
                for entity in self.arachne_json_r['entities']:
                    oc_obj = LastUpdatedOrderedDict()
                    oc_obj['id'] = self.generate_entity_url(entity['entityId'])
                    oc_obj['slug'] = oc_obj['id']
                    if 'title' in entity:
                        oc_obj['label'] = entity['title']
                    elif 'subtitle' in entity:
                        oc_obj['label'] = entity['subtitle']
                    else:
                        oc_obj['label'] = '[No Arachne Label]'
                    oc_obj['oc-gen:thumbnail-uri'] = self.generate_thumbnail_image_src(entity['thumbnailId'])
                    oc_obj['type'] = 'oc-gen:image'
                    self.results.append(oc_obj)

    def generate_entity_url(self, entity_id):
        """
        makes a URL for the entity
        """
        url = self.DEFAULT_ENTITY_BASE_URL + str(entity_id)
        return url

    def generate_thumbnail_image_src(self, thumb_id):
        """
        makes a URL for the thumbnail image bitmap file
        """
        url = self.DEFAULT_IMAGE_BASE_URL + str(thumb_id)
        url += '?height=' + str(self.image_height)
        return url

    def get_json_from_search_url(self, search_url):
        """ gets json data from Arachne by first parsing
            a search url and then converting that into a
            keyword search
        """
        self.arachne_html_url = search_url
        payload = parse_qs(urlparse(search_url).query)
        print('payload: ' + str(payload))
        json_r = self.get_arachne_json(payload)
        return json_r

    def get_keyword_search_json(self, keyword):
        """
        gets json data from Arachne in response to a keyword search
        """
        payload = {}
        payload['q'] = keyword
        json_r = self.get_arachne_json(payload)
        return json_r
    
    def get_arachne_json(self, payload):
        """
        executes a search for json data from arachne
        """
        if isinstance(payload, dict):
            if self.filter_by_images:
                payload['fq'] = 'facet_image:"ja"'
            url = self.DEFAULT_API_BASE_URL
            try:
                gapi = GeneralAPI()
                r = requests.get(url,
                                 params=payload,
                                 timeout=240,
                                 headers=gapi.client_headers)
                print('r url: ' + r.url)
                self.set_arachne_search_urls(r.url)
                r.raise_for_status()
                json_r = r.json()
            except:
                json_r = False
        else:
            json_r = False
        self.arachne_json_r = json_r
        return json_r

    def set_arachne_search_urls(self, arachne_json_url):
        """ Sets URLs for Arachne searches, JSON + HTML """
        self.arachne_json_url = arachne_json_url
        if not isinstance(self.arachne_html_url, str):
            self.arachne_html_url = arachne_json_url.replace(self.DEFAULT_API_BASE_URL,
                                                             self.DEFAULT_HTML_BASE_URL)
