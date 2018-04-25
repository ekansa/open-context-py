import json
import requests
import feedparser
from time import sleep
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI


class tdarAPI():
    """ Interacts with the tDAR API
        First use-case is to relate DINAA trinomials with
        tDAR keywords
    """
    KEYWORD_API_BASE_URL = 'http://core.tdar.org/api/lookup/keyword'
    SITE_SEARCH_FEED_BASE_URL = 'http://core.tdar.org/search/rss'
    SITE_SEARCH_HTML_BASE_URL = 'http://core.tdar.org/search/results'
    BASE_URI = 'http://core.tdar.org'
    SLEEP_TIME = .5

    def __init__(self):
        self.request_error = False
        self.request_url = False
        self.results = False
        self.best_match = False
        self.html_url = False
        self.delay_before_request = self.SLEEP_TIME

    def get_site_keyword(self, site_keyword):
        """ get a key word for a site """
        results = False
        json_r = self.get_keyword_search_json(site_keyword,
                                              'sitenamekeyword')
        if isinstance(json_r, dict):
            if 'items' in json_r:
                if len(json_r['items']) > 0:
                    results = []
                    for item in json_r['items']:
                        result = {'label': False,
                                  'id': False,
                                  'tdar': item}
                        if 'label' in item:
                            # get the item label
                            result['label'] = item['label']
                        if 'detailUrl' in item:
                            # make a full URI for the keyword
                            result['id'] = self.BASE_URI + item['detailUrl']
                        if result['id'] is not False \
                           and result['label'] is not False:
                            # Data is complete, so we can use it. Append to results
                            results.append(result)
        if results is not False:
            self.best_match = results[0]
        return results

    def get_keyword_search_json(self, keyword, keyword_type):
        """
        gets json data from tDAR in response to a keyword search
        """
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
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

    def get_tdar_items_by_site_keyword_objs(self, keyword_objs):
        """ gets site information by tdar keyword objects """
        output = False
        keyword_uris = []
        if isinstance(keyword_objs, list):
            for keyword_obj in keyword_objs:
                if isinstance(keyword_obj, dict):
                    if 'id' in keyword_obj:
                        keyword_uris.append(keyword_obj['id'])
        if len(keyword_uris) > 0:
            output = self.search_by_site_keyword_uris(keyword_uris,
                                                      True)
        return output

    def search_by_site_keyword_uris(self,
                                    keyword_uris,
                                    add_templating_keys=False):
        """
        sets an Atom feed (sorta) from tDAR related to site
        keywords
        """
        output = False
        site_names = []
        if not isinstance(keyword_uris, list):
            keyword_uris = [keyword_uris]
        for keyword_uri in keyword_uris:
            if self.BASE_URI in keyword_uri \
               and 'site-name' in keyword_uri:
                # is a tDAR site-name URI
                uri_ex = keyword_uri.split('/')
                site_name = uri_ex[-1]  # last part of URI is the site-name
                site_names.append(site_name)
        if len(site_names) > 0:
            feed_url = self.SITE_SEARCH_FEED_BASE_URL
            self.html_url = self.SITE_SEARCH_HTML_BASE_URL
            # Add a bunch of query parameters
            params = '?_tdar.searchType=advanced&sortField=RELEVANCE&groups%5B0%5D'
            params += '.operator=AND&groups%5B0%5D.fieldTypes%5B0%5D=FFK_SITE'
            feed_url += params
            self.html_url += params
            i = 0
            for site_name in site_names:
                act_param = '&groups%5B0%5D.siteNames%5B' + str(i) + '%5D='
                act_param += urlquote(site_name)
                feed_url += act_param
                self.html_url += act_param
                i += 1
            feed = feedparser.parse(feed_url)
            print(feed_url)
            if feed.bozo == 1 \
               or feed.status >= 400:
                feed = False
            else:
                output = []
                for entry in feed.entries:
                    item = LastUpdatedOrderedDict()
                    item['id'] = entry.id
                    item['label'] = entry.title
                    if add_templating_keys:
                        # keys useful for templating the tDAR content
                        item['vocabulary'] = 'tDAR archived content'
                        item['vocab_uri'] = 'http://tdar.org/'
                        item['vocabulary'] = False
                        item['vocab_uri'] = False
                    output.append(item)
        return output

    def pause_request(self):
        """ pauses between requests """
        sleep(self.delay_before_request)