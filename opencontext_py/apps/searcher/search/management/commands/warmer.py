import time
import json
import requests
from unidecode import unidecode
from time import sleep

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.libs.rootpath import RootPath


class SearchWarmer():
    """ Interacts with the Open Context API
        to make requests to warm up the solr index
    """
    SPACETIME_FACET_TYPES = [
        # 'oc-api:has-form-use-life-ranges',
        'features',
    ]
    FACET_TYPES = [
        'oc-api:has-facets',
        'oc-api:oc-api:has-numeric-facets',
        'oc-api:oc-api:has-date-facets'
    ]
    OPTION_TYPES = [
        'oc-api:has-id-options',
        # 'oc-api:has-numeric-options',
        # 'oc-api:has-date-options',
        # 'oc-api:has-text-options',
        'oc-api:has-rel-media-options',
        'oc-api:has-range-options'
    ]
    SLEEP_TIME = .5

    def __init__(self):
        self.request_errors = []
        self.done_urls = []
        self.follow_count = 200000
        self.start_time = 0
        self.delay_before_request = self.SLEEP_TIME
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.urls = [
            (self.base_url + '/subjects-search/'),
            (self.base_url + '/media-search/'),
            (self.base_url + '/search/'),
        ]

    def warm(self):
        """Warms the search by recursively following facet search options
           with more than a certain number of records. The more records
           the slower, so this helps keep cached search results fresh.
        """
        self.time_start = time.time()
        for url in self.urls:
            self.follow_url(url, True) 
    
    
    def follow_url(self, url, recursive=True):
        """ Follows a URL, gets data for links above the threshold (follow_count)
        and then follow those links. Following those links warms the search API
        so that data are pre-cached for users.
        """
        new_urls = []
        if url in self.done_urls or url in self.request_errors:
            return new_urls
        print('Following: ' + url)
        json_r = self.get_search_json(url)
        if json_r:
            self.get_search_html(url)
            self.done_urls.append(url)
            for facet_type in self.SPACETIME_FACET_TYPES:
                if facet_type in json_r:
                    for option in json_r[facet_type]:
                        if ('id' in option and
                            'count' in option and
                            option['id'] not in new_urls and
                            option['count'] >= self.follow_count):
                            new_urls.append(option['id'])
                for facet_type in self.FACET_TYPES:
                    if facet_type in json_r:
                        for facet in json_r[facet_type]:
                            for option_type in self.OPTION_TYPES:
                                if option_type in facet:
                                    for option in facet[option_type]:
                                        if ('id' in option and
                                            'count' in option and
                                            option['id'] not in new_urls and
                                            option['count'] >= self.follow_count):
                                            new_urls.append(option['id'])
        elapsed = round((time.time() - self.time_start), 2)
        print('New links with more than {} items: {}, ({} done, {} secs.)'.format(self.follow_count,
                                                         len(new_urls),
                                                         len(self.done_urls),
                                                         elapsed))
        if recursive:
            for new_url in new_urls:
                self.follow_url(new_url)

    def get_search_json(self, url):
        """
        Gets json data from Open Context search API
        """
        gapi = GeneralAPI()
        headers = gapi.client_headers
        headers['accept'] = 'application/json'
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        try:
            r = requests.get(url,
                             timeout=240,
                             headers=headers)
            r.raise_for_status()
            json_r = r.json()
        except:
            self.request_errors.append(url)
            json_r = False
        return json_r
    
    def get_search_html(self, url):
        """
        Get HTML from Open Context from a URL, do nothing with the data
        however.
        """
        gapi = GeneralAPI()
        headers = gapi.client_headers
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        try:
            r = requests.get(url,
                             timeout=240,
                             headers=headers)
            r.raise_for_status()
            ok = True
        except:
            ok = False
        return ok


class Command(BaseCommand):
    help = 'Warms faceted search by following links to large result sets'

    def add_arguments(self, parser):
        parser.add_argument('--url',
                            default=None,
                            help='URL to follow for warmer')
        parser.add_argument('--sleep',
                            default=SearchWarmer.SLEEP_TIME,
                            type=float,
                            help='Sleep delay between requests')

    def handle(self, *args, **options):
        sw = SearchWarmer()
        if options.get('sleep') > SearchWarmer.SLEEP_TIME:
            sw.delay_before_request = options['sleep']
        op_url = options.get('url', None)
        if op_url:
            sw.follow_url(op_url)
        else:
            sw.warm()