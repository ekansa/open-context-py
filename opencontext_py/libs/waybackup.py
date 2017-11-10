import re
import json
import requests
from time import sleep
from bs4 import BeautifulSoup
from urllib.parse import quote
from urllib.parse import urljoin
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.filecache import FileCacheJSON


class WaybackUp():
    '''
    Utilities to accession URLs into the Internet
    Archive's Wayback machine for preservation.
    
    
    This does not require using all of Open Context. It
    is meant to be a stand alone class.
    
    To run this, you will need to install (via pip or easy_install):
    (1) beautifulsoup4
    (2) requests
    
    
    To use this, you'll need to adapt the following for your Python
    setup:
from opencontext_py.libs.filecache import FileCacheJSON
from opencontext_py.libs.waybackup import WaybackUp
wb = WaybackUp()
wb.delay_before_request = 1.5
wb.do_img_src = True
wb.skip_parameters = [
    't=publication',
    't=report',
    't=letter',
    't=monument',
    't=drawing',
    't=image',
    't=object',
    't=coin',
    't=deposit',
    't=notebook',
    'v=icons',
    'v=table',
    'v=map',
    '&details=',
    'p=4',
    'p=8',
    'p=20',
    'p=40',
    'http://ascsa.net/help',
]
path = ['ascsa.net']  # only follow links in these paths
url = 'http://ascsa.net/research?q=&t=&v=list&s=9&sort=&p=100'
wb.scrape_urls(url, path, 10)  # archive pages discovered from the url, going 6 steps away
wb.urls = wb.failed_urls
# archive the previous failures
wb.archive_urls()

from opencontext_py.libs.waybackup import WaybackUp
urls = [] # your list of URLs to archive
wb = WaybackUp()
wb.delay_before_request = 3
wb.urls = urls
wb.archive_urls()
wb.check_available_urls()

urls = []
for e in wb.errors:
    url = e.replace('Snapshot request failed for url: ', '')
    urls.append(url)
new_urls = []
for url in urls:
    url = url.replace('\'', '')
    url = url.replace('\\', '')
    url = url.replace('https://', 'https:||')
    url = url.replace('//', '/')
    url = url.replace('https:||', 'https://')
    new_urls.append(url)
    
    '''
    CLIENT_HEADERS = {
        'User-Agent': 'Python Wayback Backup API-Client'
    }
    
    def __init__(self):
        # skip parameters
        self.skip_parameters = []
        # list of URLs to archive in the way back machine
        self.urls = []
        # image url root
        self.img_src_root = ''
        # get src for images
        self.do_img_src = True
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
        self.delay_before_request = 1.5
        # Archive while scrapping URLs
        self.archive_in_scrape = True
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
        # a special function for transforming javascript hrefs into a URL, if None then skip
        self.transform_href_obj = None
        # filecach object, if none don't keep track of urls, if
        # not none, then keep track and save as JSON on disk
        self.filecache = None
        self.working_dir = 'web-archiving'
        self.cache_filekey = 'web-archive-urls'
        self.cached_json = None
    
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
                    self.failed_urls.append(url)
            if url in self.archived_urls:
                archive_ok = False    
            if archive_ok:
                # archive the URL
                ok = self.archive_url(url)
                if ok:
                    print('Archived: ' + url)
                    self.archived_urls.append(url)
                else:
                    # try again after a longish wait
                    print('2nd attempt after pause...')
                    sleep(2.5 + self.delay_before_request*2)
                    ok = self.archive_url(url)
                    if ok:
                        print('Archived: ' + url)
                        self.archived_urls.append(url)
                    else:
                        print('Problem saving:' + url)
                        self.failed_urls.append(url)
            else:
                print('Skipping: ' + url)
        # now update the file cache with the results
        self.update_url_filecache()

    def archive_url(self, url):
        """ Archive the URL with the Wayback Machine """
        ok = False
        if url not in self.archived_urls:
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
                r.raise_for_status()
                ok = True
            except:
                ok = False
                error = 'Snapshot request failed for url: ' + str(url)
                self.errors.append(error)
        else:
            ok = True
        return ok
    
    def scrape_urls(self,
                    url,
                    path_limit=None,
                    max_depth=1,
                    current_depth=0):
        """ downloads a web page and extracts URLs,
            works recursively
        """
        if not isinstance(self.cached_json, dict):
            json_obj = self.get_state_from_filecache()
            self.cached_json = json_obj
        do_download = True
        skip_extensions = [
            # common files we don't want to download
            '.pdf',
            '.ppt',
            '.doc',
            '.xls',
            '.jpg',
            '.png',
            '.tif',
            '.gif',
            '.zip',
            '.tgz',
            '.exe',
            '.EXE'
        ]
        skip_domains = [
            'plus.google.com',
            'twitter.com',
            'www.facebook.com',
            'pinterest.com'
        ]
        skip_domains += self.skip_parameters
        l_url = url.lower()
        for skip_ex in skip_extensions:
            if skip_ex in l_url:
                do_download = False
                break
        urls = []
        html = None
        if current_depth < max_depth and do_download:
            # only get the page if we're not at maximum crawl depth
            if self.delay_before_request > 0:
                # default to sleep BEFORE a request is sent, to
                # give the remote service a break.
                sleep(self.delay_before_request)
            try:
                r = requests.get(url,
                                 timeout=240,
                                 headers=self.client_headers)
                r.raise_for_status()
                html = str(r.content)
            except:
                html = False
                error = 'Get request failed for url: ' + str(url)
                self.errors.append(error)
        if self.archive_in_scrape and do_download is False:
            # we should try to archive it, even if we haven't downloaded it
            print('Try to archive media from: ' + url)
            ok = self.archive_url(url)
            if ok is False:
                print('PROBLEM ARCHIVING!')
                if url not in self.failed_urls:
                    self.failed_urls.append(url)
            else:
                if url not in self.archived_urls:
                    self.archived_urls.append(url)
            self.update_url_filecache()
        if isinstance(html, str):
            if self.archive_in_scrape:
                print('Try to archive page: ' + url)
                ok = self.archive_url(url)
                if ok is False:
                    if url not in self.failed_urls:
                        self.failed_urls.append(url)
                else:
                   self.archived_urls.append(url)
            print('Archived: ' + str(len(self.archived_urls)) \
                  + ', failed '  + str(len(self.failed_urls)) \
                  + ' level: ' + str(current_depth))
            print('> Getting urls from: ' + url)
            soup = None
            try:
                soup = BeautifulSoup(html, 'lxml')
            except:
                soup = None
            if soup is not None:
                for link in soup.find_all('a'):
                    do_raw_url = True
                    raw_url = link.get('href')
                    raw_url = self.transform_raw_url(raw_url)
                    if isinstance(raw_url, str):
                        for skip_domain in skip_domains:
                            if skip_domain in raw_url:
                                # skip it, it's for a social media site
                                do_raw_url = False
                        if do_raw_url:
                            # do it
                            if raw_url[0:7] == 'http://' or \
                               raw_url[0:8] == 'https://':
                                # we have an absolute URL
                                if raw_url not in urls:
                                    urls.append(raw_url)
                            else:
                                # we have a relative URL, make it absolute
                                new_url = urljoin(url, raw_url)
                                if new_url not in urls:
                                    urls.append(new_url)
                if self.do_img_src:
                    print('Searching for image URLs...')
                    img_src_urls = []
                    for img in soup.find_all('img'):
                        do_raw_url = True
                        raw_url = img.get('src')
                        if isinstance(raw_url, str):
                            raw_url = raw_url.strip() # remove whitespaces, etc.
                            raw_url = raw_url.replace('\\r', '')  # common URL problem
                            raw_url = raw_url.replace('\\n', '')  # common URL problem
                            if '#' in raw_url:
                                # skip fragment identifiers in URLs
                                url_ex = raw_url.split('#')
                                raw_url = url_ex[0]
                            for skip_domain in skip_domains:
                                if skip_domain in raw_url:
                                    # skip it, it's for a social media site
                                    do_raw_url = False
                            if do_raw_url:
                                # do it
                                if raw_url[0:7] == 'http://' or \
                                   raw_url[0:8] == 'https://':
                                    # we have an absolute URL
                                    if raw_url not in img_src_urls:
                                        img_src_urls.append(raw_url)
                                else:
                                    # we have a relative URL, make it absolute
                                    new_url = urljoin(url, raw_url)
                                    if new_url not in img_src_urls:
                                        img_src_urls.append(new_url)
                    print('Found image URLs: ' + str(len(img_src_urls)))
                    for src_url in img_src_urls:
                        if src_url not in self.failed_urls \
                           and src_url not in self.archived_urls:
                            print('Try to archive image: ' + src_url)
                            ok = self.archive_url(src_url)
                            if ok is False:
                                print('PROBLEM ARCHIVING IMAGE!')
                                if src_url not in self.failed_urls:
                                    self.failed_urls.append(src_url)
                            else:
                                if src_url not in self.archived_urls:
                                    self.archived_urls.append(src_url)
                        else:
                            pass
        # update our progress!
        self.update_url_filecache()
        # now do urls that we found.
        if len(urls) > 0:
            current_depth += 1
            if current_depth < max_depth:
                current_page_urls = urls
                for page_url in current_page_urls:
                    if isinstance(path_limit, str):
                        # limit to URLs with a certain path
                        if path_limit in page_url:
                            ok_new = True
                        else:
                            ok_new = False
                    elif isinstance(path_limit, list):
                        # we have a list of OK paths to crawl
                        ok_new = False
                        for pl in path_limit:
                            if pl in page_url:
                                ok_new = True
                    else:
                        ok_new = True
                    if ok_new:
                        new_page_urls = self.scrape_urls(page_url,
                                                         max_depth,
                                                         current_depth)
                        for new_url in new_page_urls:
                            # add new urls we don't already have
                            if new_url not in urls:
                                urls.append(new_url)
                # now update with new urls
                self.update_url_filecache(urls)
        return urls               
    
    def transform_raw_url(self, raw_url):
        """ code to clean and transform a raw_href into something
            that looks like a clean URL
        """
        if isinstance(raw_url, str):
            raw_url = raw_url.strip() # remove whitespaces, etc.
            raw_url = raw_url.replace('\\r', '')  # common URL problem
            raw_url = raw_url.replace('\\n', '')  # common URL problem
            if '#' in raw_url:
                # skip fragment identifiers in URLs
                url_ex = raw_url.split('#')
                raw_url = url_ex[0]
            if self.transform_href_obj is not None:
                raw_url = self.transform_href_obj.transform_href(raw_url)
        return raw_url
    
    def update_url_filecache(self, new_urls=[]):
        """ updates the file cache to save the state of a urls """
        if self.filecache is not None:
            # print('Cache update !: ' + self.cache_filekey)
            self.filecache.working_dir = self.working_dir
            json_obj = None
            if not isinstance(self.cached_json, dict):
                json_obj = self.get_state_from_filecache()
                self.cached_json = json_obj
            if not isinstance(json_obj, dict):
                json_obj = LastUpdatedOrderedDict()
            json_obj['urls'] = self.urls
            for new_url in new_urls:
                if new_url not in json_obj['urls']:
                    json_obj['urls'].append(new_url)
            json_obj['archived_urls'] = self.archived_urls
            json_obj['broken_urls'] = self.broken_urls
            json_obj['failed_urls'] = self.failed_urls
            self.filecache.save_serialized_json(self.cache_filekey,
                                                json_obj)
            
    def get_state_from_filecache(self):
        """ gets the current state of the web-crawling process from the file cache"""
        json_obj = None
        if self.filecache is not None:
            print('Look for prior work in file cache: ' + self.cache_filekey)
            self.filecache.working_dir = self.working_dir
            json_obj = self.filecache.get_dict_from_file(self.cache_filekey)
            if isinstance(json_obj, dict):
                print('Loading prior work from file cache: ' + self.cache_filekey)
                if 'urls' in json_obj:
                    self.urls = json_obj['urls']
                if 'archived_urls' in json_obj:
                    self.archived_urls = json_obj['archived_urls']
                if 'broken_urls' in json_obj:
                    self.broken_urls = json_obj['broken_urls']
                if 'failed_urls' in json_obj:
                    self.failed_urls= json_obj['failed_urls']
        return json_obj
    
    def check_available_urls(self):
        """ Checks a list of URLs to make sure they have been entered
            into the Wayback Machine as an available resource
        """
        for url in self.urls:
            archive_ok = True
            available = self.check_url_available(url,
                                                 self.check_timestamp)
            if available:
                self.archived_urls.append(url)
            else:
                self.failed_urls.append(url)
        return self.archived_urls
    
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