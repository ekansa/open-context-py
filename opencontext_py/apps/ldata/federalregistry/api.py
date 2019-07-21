import json
import os
import codecs
import requests
import feedparser
import hashlib
from time import sleep
from django.conf import settings
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI


class FederalRegistryAPI():
    """ Interacts with the Federal Registry API
        Fo relate DINAA trinomials with
        Federal Registry documents
        
from opencontext_py.apps.ldata.federalregistry.api import FederalRegistryAPI
fed_api = FederalRegistryAPI()
fed_api.get_cache_keyword_searches()

    """
    API_BASE_URL = 'https://www.federalregister.gov/api/v1/documents.json'
    SLEEP_TIME = .5

    def __init__(self):
        self.request_error = False
        self.request_url = False
        self.results = False
        self.best_match = False
        self.html_url = False
        self.cache_batch_prefix = '2019-07-20'
        self.delay_before_request = self.SLEEP_TIME
        self.root_act_dir = settings.STATIC_IMPORTS_ROOT
        self.working_search_dir = 'federal-reg-search'
        self.working_doc_dir = 'federal-reg-docs'
        self.recs_per_page = 500
        self.json_url_list = []
        self.raw_text_url_list = []
        self.keyword_a_list = [
            'archeology',
            'archeological',
            'archaeology',
            'archaeological',
            'NAGPRA',
            'cultural',
            'heritage',
        ]
        self.keyword_bb_list = [
            'Alabama', 
            'Alaska', 
            'Arizona', 
            'Arkansas', 
            'California', 
            'Colorado', 
            'Connecticut', 
            'Delaware', 
            'Florida', 
            'Georgia', 
            'Idaho', 
            'Illinois', 
            'Indiana', 
            'Iowa', 
            'Kansas', 
            'Kentucky', 
            'Louisiana', 
            'Maine', 
            'Maryland', 
            'Massachusetts', 
            'Michigan', 
            'Minnesota', 
            'Mississippi', 
            'Missouri', 
            'Montana', 
            'Nebraska', 
            'Nevada', 
            'New Hampshire', 
            'New Jersey', 
            'New Mexico', 
            'New York', 
            'North Carolina', 
            'North Dakota', 
            'Ohio', 
            'Oklahoma', 
            'Oregon', 
            'Pennsylvania', 
            'Rhode Island', 
            'South Carolina', 
            'South Dakota', 
            'Tennessee', 
            'Texas', 
            'Texas', 
            'Utah', 
            'Vermont', 
            'Virginia', 
            'Virginia', 
            'Washington', 
            'West Virginia', 
            'Wisconsin', 
            'Wyoming', 
        ]
        self.keyword_b_list = [
           'site',
           'sites',
           'place',
           'places',
        ]

    def get_list_cached_keyword_searches(self):
        """ makes a list of search results from keyword searches """
        file_list = []
        for keyword_a in self.keyword_a_list:
            for keyword_b in self.keyword_b_list:
                act_keywords = [
                    keyword_a,
                    keyword_b
                ]
                url = self.make_search_json_url(act_keywords)
                key =  self.make_cache_key(self.cache_batch_prefix, url)
                file_list.append(key)
        return file_list       

    def get_cache_keyword_searches(self):
        """ gets search results and caches them based on
            literating though two list of key words
        """
        for keyword_a in self.keyword_a_list:
            for keyword_b in self.keyword_b_list:
                act_keywords = [
                    keyword_a,
                    keyword_b
                ]
                print('------------------------')
                print('Working on: ' + str(act_keywords))
                print('------------------------')
                url = self.make_search_json_url(act_keywords)
                json_r = self.get_cache_keyword_search_json(url)
        docs = LastUpdatedOrderedDict()
        docs['raw'] = self.raw_text_url_list
        docs['json'] = self.json_url_list
        key = 'all-document-list'
        self.save_serialized_json(key, docs)
        # now iterate through the raw_text_urls to save these docs
        for raw_text_url in self.raw_text_url_list:
            self.get_cache_raw_doc_text(raw_text_url)
    
    def get_cache_raw_doc_text(self, url):
        """ gets and caches raw text for found documents """
        ok = False
        url_ex = url.split('/')
        file_name = url_ex[-1]
        exists = self.check_exists(file_name, self.working_doc_dir)
        if exists is False:
            text = self.get_remote_text_from_url(url)
            if isinstance(text, str):
                path = self.prep_directory(self.working_doc_dir)
                dir_file = path + file_name
                print('save to path: ' + dir_file)
                file = codecs.open(dir_file, 'w', 'utf-8')
                file.write(text)
                file.close()
                ok = True
        else:
            # found it already
            ok = True
        return ok
    
    def add_to_doc_lists(self, json_r):
        """ adds to lists of json and raw document urls """
        if isinstance(json_r, dict):
            if 'results' in json_r:
                for result in json_r['results']:
                    if 'json_url' in result:
                        json_url = result['json_url']
                        if json_url not in self.json_url_list:
                            self.json_url_list.append(json_url)
                    if 'raw_text_url' in result:
                        raw_text_url = result['raw_text_url']
                        if raw_text_url not in self.raw_text_url_list:
                            self.raw_text_url_list.append(raw_text_url)
    
    def make_search_json_url(self, keyword_list):
        """ makes a search url from a keyword list """
        url_key_words = ' '.join(keyword_list)
        url = self.API_BASE_URL
        url += '?fields%5B%5D=agencies&fields%5B%5D=json_url&fields%5B%5D=raw_text_url'
        url += '&fields%5B%5D=document_number&fields%5B%5D=html_url&fields%5B%5D=title'
        url += '&order=relevance'
        url += '&per_page=' + str(self.recs_per_page)
        url += '&conditions%5Bterm%5D=' + urlquote_plus(url_key_words)
        return url

    def get_cache_keyword_search_json(self, url, recursive=True):
        """
        gets json data from API in response to a keyword search
        """
        key =  self.make_cache_key(self.cache_batch_prefix, url)
        json_r = self.get_dict_from_file(key)
        if not isinstance(json_r, dict):
            json_r = self.get_remote_json_from_url(url)
            self.save_serialized_json(key, json_r)
        # add to the list of documents in the search results
        self.add_to_doc_lists(json_r)
        if recursive and isinstance(json_r, dict):
            if 'next_page_url' in json_r:
                next_url = json_r['next_page_url']
                print('Getting next page of results: ' + str(next_url))
                json_r = self.get_cache_keyword_search_json(next_url, recursive)
        return json_r
    
    def get_remote_json_from_url(self, url):
        """ gets remote data from a URL """
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
    
    def get_remote_text_from_url(self, url):
        """ gets remote text content from a URL """
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
            text = r.text
        except:
            self.request_error = True
            text = False
        return text
    
    def get_dict_from_file(self, key):
        """ gets the file string
            if the file exists,
        """
        if '.json' not in key:
            file_name = key + '.json'
        json_obj = None
        ok = self.check_exists(file_name, self.working_search_dir)
        if ok:
            path = self.prep_directory(self.working_search_dir)
            dir_file = path + file_name
            try:
                json_obj = json.load(codecs.open(dir_file,
                                                 'r',
                                                 'utf-8-sig'))
            except:
                print('Cannot parse as JSON: ' + dir_file)
                json_obj = False
        return json_obj
    
    def get_string_from_file(self, file_name, act_dir):
        """ gets the file string
            if the file exists,
        """
        text = None
        ok = self.check_exists(file_name, act_dir)
        if ok:
            path = self.prep_directory(act_dir)
            dir_file = path + file_name
            text = open(dir_file, 'r').read()
        return text
    
    def check_exists(self, file_name, act_dir):
        """ checks to see if a file exists """
        path = self.prep_directory(act_dir)
        dir_file = path + file_name
        if os.path.exists(dir_file):
            output = True
        else:
            # print('Cannot find: ' + dir_file)
            output = False
        return output
    
    def save_serialized_json(self, key, dict_obj):
        """ saves a data in the appropriate path + file """
        file_name = key + '.json'
        path = self.prep_directory(self.working_search_dir)
        dir_file = path + file_name
        print('save to path: ' + dir_file)
        json_output = json.dumps(dict_obj,
                                 indent=4,
                                 ensure_ascii=False)
        file = codecs.open(dir_file, 'w', 'utf-8')
        file.write(json_output)
        file.close()

    def prep_directory(self, act_dir):
        """ Prepares a directory to receive export files """
        output = False
        full_dir = self.root_act_dir + act_dir + '/'
        full_dir.replace('//', '/')
        if not os.path.exists(full_dir):
            print('Prepared directory: ' + str(full_dir))
            os.makedirs(full_dir)
        if os.path.exists(full_dir):
            output = full_dir
        if output[-1] != '/':
            output += '/'
        return output

    def make_cache_key(self, prefix, identifier):
        """ makes a valid OK cache key """
        hash_obj = hashlib.sha1()
        concat_string = str(prefix) + " " + str(identifier)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()

    def pause_request(self):
        """ pauses between requests """
        sleep(self.delay_before_request)