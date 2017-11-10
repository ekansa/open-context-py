import json
import requests
import hashlib
from lxml import etree
from time import sleep
from django.conf import settings
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI


class OaiPmhClientAPI():
    """ A simple, not fully functional client API for OAI-PMH services
    """

    NAMESPACES = {
        'oai': 'http://www.openarchives.org/OAI/2.0/',
        'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
    }
    SLEEP_TIME = .5

    def __init__(self):
        self.request_error = False
        self.delay_before_request = self.SLEEP_TIME
        self.graph = False
        self.request_url = False

    def get_list_records(self, url, resumption_token=None):
        """
        gets OAI-PMH list records, with an optional resumption_token
        """
        xml = None
        params = None
        if 'verb=ListRecords' not in url:
            params = {}
            params['verb'] = 'ListRecords'
        if isinstance(resumption_token, str):
            if '?' in url:
                # do this to avoid URL encoding the resumption token
                url += '&resumptionToken=' + resumption_token
            else:
                url += '?resumptionToken=' + resumption_token
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        url_content = None
        if isinstance(params, dict):
            try:
                gapi = GeneralAPI()
                r = requests.get(url,
                                 params=params,
                                 timeout=240,
                                 headers=gapi.client_headers)
                self.request_url = r.url
                r.raise_for_status()
                url_content = r.content
            except:
                self.request_error = True
                url_content = None
        else:
            try:
                gapi = GeneralAPI()
                r = requests.get(url,
                                 timeout=240,
                                 headers=gapi.client_headers)
                self.request_url = r.url
                r.raise_for_status()
                url_content = r.content
            except:
                self.request_error = True
                url_content = None
        return url_content 
