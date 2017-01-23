import json
import requests
from time import sleep
from urllib.parse import quote


class WaybackUp():
    '''
    Utilities to accession URLs into the Internet
    Archive's Wayback machine for preservation.
    
from opencontext_py.libs.waybackup import WaybackUp
wb = WaybackUp()
wb.urls = urls
wb.check_url_available(url)

    '''
    CLIENT_HEADERS = {
        'User-Agent': 'Python Wayback Backup API-Client'
    }
    
    def __init__(self):
        # list of URLs to archive in the way back machine
        self.urls = []
        # True or False to check URLs prior to archive attempt
        self.check_urls = True
        # True or False, archive only new URLs, if True, then we first
        # check to see if the Wayback Machine already has a given URL in the
        # archive
        self.only_new_urls = False
        # a string, 1-14 digits (YYYYMMDDhhmmss), to be used for checking
        # available URLs
        self.check_timestamp = None
        # URL for the Way Back Machine's API to check availability
        self.wb_available_api_url = 'https://archive.org/wayback/available'
        self.wb_save_url = 'https://web.archive.org/save/'
        # Time (in seconds) to pause between requests
        self.delay_before_request = .5
        # User Agent for this code, so we self-identify to the Internet
        # Archive when we use their APIs
        self.client_headers = self.CLIENT_HEADERS
        # List of errors encountered while processing
        self.errors = []
        # list of archived URLs
        self.archived_urls = []
        # list of brocken URLs (now giving errors, so can't archive)
        self.broken_urls = []
        # list of not archived URLs
        self.failed_urls = []
    
    def archive_urls(self):
        """ Archives a list of URLs to the Way Back machine,
            if self.only_new_urls is True, it will check to see
            if the URL is already availble.
        """
        for url in self.urls:
            archive_ok = True
            if self.only_new_urls:
                available = self.check_url_available(url,
                                                     self.check_timestamp)
                if available:
                    # Wayback already has it available, so don't archive it.
                    archive_ok = False
            if archive_ok and self.check_urls:
                archive_ok = self.check_url_ok(url)
                if archive_ok is False:
                    print('Problem with: ' + url)
                    self.broken_urls.append(url)
            if archive_ok:
                # archive the URL
                ok = self.archive_url(url)
                if ok:
                    print('Archived: ' + url)
                    self.archived_urls.append(url)
                else:
                    print('Problem saving:' + url)
                    self.failed_urls.append(url)
            else:
                print('Skipping: ' + url)

    def archive_url(self, url):
        """ Archive the URL with the Wayback Machine """
        ok = False
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        try:
            # now execute the request to the internet archive API
            # s_url = self.wb_save_url + quote(url, safe='')
            s_url = self.wb_save_url + url
            r = requests.get(s_url,
                             timeout=240,
                             headers=self.client_headers)
            request_url = r.url
            r.raise_for_status()
            ok = True
        except:
            ok = False
            error = 'Snapshot request failed for url: ' + str(url)
            error += ' request: ' + request_url
            self.errors.append(error)
        return ok
    
    def check_url_ok(self, url):
        """ checks to see if a URL gives an OK status
        """
        ok = False
        try:
            # now execute the request to check the URL
            r = requests.head(url,
                              headers=self.client_headers)
            r.raise_for_status()
            ok = True
        except:
            ok = False
        return ok
    
    def check_url_available(self, url, timestamp=None):
        """ checks to see if the URL is available in the Wayback
            Machine.
            
            Returns True if a snapshot is available, False if not,
            None if there was an error or problem.
            
            The optional parameter timestamp can be a string
            formatted as 1-14 digits (YYYYMMDDhhmmss) to represent
            the time the snapshot was taken. See documentation:
            https://archive.org/help/wayback_api.php
        """
        available = None
        json_resp = self.get_url_available_json(url, timestamp)
        if isinstance(json_resp, dict):
            # we got a response for checking URL availability
            if 'archived_snapshots' in json_resp:
                # default to False on availability
                available = False
                for key, arch_dict in json_resp['archived_snapshots'].items():
                    if 'available' in arch_dict:
                        if arch_dict['available']:
                            # we found an available snapshot
                            available = True
                            break
        return available
    
    def get_url_available_json(self, url, timestamp=None):
        """ gets JSON data for the availability of a URL in the
            Wayback Machine
        """
        json_resp = None
        request_url = ''
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        try:
            # now execute the request to the internet archive API
            params = {'url': url}
            if timestamp is not None:
                params['timestamp'] = timestamp
            r = requests.get(self.wb_available_api_url,
                             params=params,
                             timeout=240,
                             headers=self.client_headers)
            request_url = r.url
            r.raise_for_status()
            json_resp = r.json()
        except:
            json_resp = False
            error = 'Check available request failed for url: ' + str(url)
            error += ' request: ' + request_url
            self.errors.append(error)
        return json_resp