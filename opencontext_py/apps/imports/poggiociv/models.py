import os
import json
import codecs
import requests
from lxml import etree
import lxml.html
from django.conf import settings
from django.db import connection
from django.db.models import Q
from django.db.models import Avg, Max, Min
from time import sleep
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation as LinkAnnotation
from opencontext_py.apps.ldata.linkentities.models import LinkEntity as LinkEntity
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest as Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.ocitems.mediafiles.models import Mediafile as Mediafile
from opencontext_py.apps.ocitems.persons.models import Person as Person
from opencontext_py.apps.ocitems.projects.models import Project as Project
from opencontext_py.apps.ocitems.documents.models import OCdocument as OCdocument
from opencontext_py.apps.ocitems.strings.models import OCstring as OCstring
from opencontext_py.apps.ocitems.octypes.models import OCtype as OCtype
from opencontext_py.apps.ocitems.predicates.models import Predicate as Predicate
from opencontext_py.apps.ocitems.projects.models import Project as Project
from opencontext_py.apps.ocitems.geospace.models import Geospace
from opencontext_py.apps.ocitems.events.models import Event
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ocitems.obsmetadata.models import ObsMetadata


class PoggioCiv():
    """ Class for getting data from the legacy Poggio Civitate server
    
from opencontext_py.apps.imports.poggiociv.models import PoggioCiv
pc = PoggioCiv(True)
pc.use_cached_tb_index = False
items = pc.get_scrape_trench_book_index()
print(str(items[0:10]))
print(str(items[-10:]))


from opencontext_py.apps.imports.poggiociv.models import PoggioCiv
pc = PoggioCiv(True)
link = 'viewlocus.asp?locus=15&tbtid=439&tbtdid=12186'
pc.scrape_content(link, pc.pc_directory, False)

from opencontext_py.apps.imports.poggiociv.models import PoggioCiv
pc = PoggioCiv(True)
pc.year_after = 1950
pc.year_before = 1980
pc.max_checked_links = 10000
pc.scrape_content_from_index(pc.pc_directory, True)


    """
    
    TRENCH_BOOK_INDEX_URL = 'http://www.poggiocivitate.org/catalog/trenchbooks/index.asp'
    BASE_URL_WEB = 'http://www.poggiocivitate.org'
    BASE_URL_MAG = 'http://gigante'
    SLEEP_TIME = .5

    def __init__(self, do_mag=False):
        self.request_error = False
        self.request_url = False
        self.trench_book_index_url = self.TRENCH_BOOK_INDEX_URL
        if do_mag:
            self.base_url = self.BASE_URL_MAG
            self.trench_book_index_url = self.trench_book_index_url.replace(self.BASE_URL_WEB,
                                                                            self.BASE_URL_MAG)
        else:
            self.base_url = self.BASE_URL_WEB
        self.best_match = False
        self.html_url = False
        self.delay_before_request = self.SLEEP_TIME
        self.root_import_dir = settings.STATIC_EXPORTS_ROOT
        self.act_import_dir = False
        self.pc_directory = 'mag-data'
        self.use_cached_tb_index = True
        self.trench_book_index_json = 'trench-books-index.json'
        self.errors = {}
        self.content_link_prefixes = [
            'viewtrenchbookentry.asp',
            'viewlocus.asp',
            'trenchbookviewer.asp'
        ]
        self.content_url_prefixes = {
            'viewtrenchbookentry': '/catalog/trenchbooks/',
            'viewlocus': '/admin/',
            'trenchbookviewer': False  # don't follow these, no scans
        }
        self.year_after = 1950
        self.year_before = 1980
        self.max_checked_links = 5000
        self.checked_links = []
    
    
    def scrape_content_from_index(self, act_dir, recursive=True):
        """ loads the trench book index, scrapes
            content recursively
        """
        if self.use_cached_tb_index:
            items = self.load_json_file_os_obj(act_dir,
                                               self.trench_book_index_json)
        else:
            items = self.get_scrape_trench_book_index()
        if isinstance(items, list):
            for item in items:
                if item['max_year'] <= self.year_before \
                   and item['max_year'] >= self.year_after:
                    link = item['page']
                    param_sep = '?'
                    for param_key, param_val in item['params'].items():
                        link += param_sep + str(param_key) + '=' + str(param_val)
                        param_sep = '&'
                    print('')
                    print('')
                    print('')
                    print('Starting from index: ' + link)
                    self.scrape_content(link, act_dir, recursive)
    
    def scrape_content(self, link, act_dir, recursive=True):
        """scrapes the content of a page
           gets links to save the next pages also
        """
        if link not in self.checked_links:
            # so we don't repeat follow the same link and get stuck
            # in an infitite loop
            self.checked_links.append(link)
            if len(self.checked_links) >= self.max_checked_links:
                self.checked_links = []
            url = self.compose_url_from_link(link)
            filename = self.compose_filename_from_link(link)
            dir_file = self.define_import_directory_file(act_dir, filename)
            if not isinstance(url, str):
                print('Skipping page for: ' + link)
            else:
                # we have a url to get data
                html_str = None
                if not os.path.exists(dir_file):
                    # new file, we haven't seen this before
                    ok = self.cache_page_locally(url, {}, act_dir, filename)
                    if ok is False:
                        print('***** FAILED: ' + filename + ' *****')
                    else:
                        print('------------------')
                        print('Saved: ' + filename)
                        html_str = self.load_file(dir_file)
                else:
                    print('Using locally saved file: ' + filename) 
                    html_str = self.load_file(dir_file)
                if isinstance(html_str, str):
                    # we have HTML retrieved
                    print('Getting links...')
                    all_links = self.get_links_from_page(html_str)
                    for link_type, links in all_links.items():
                        print('Count ' + link_type + ': ' + str(len(links)))
                        if recursive:
                            for new_link in links:
                                # now save the linked pages
                                self.scrape_content(new_link, act_dir, recursive)
    
    def get_scrape_trench_book_index(self):
        """
        gets the trench book index, parses results
        """
        items = []
        tb_list = self.get_trench_book_list_html()
        if isinstance(tb_list, str):
            valid = self.valid_as_html(tb_list)
            if valid:
                tree = etree.fromstring(tb_list)
                tb_items = tree.xpath('/div/ul/li')
                print('Found trench-books: ' + str(len(tb_items)))
                for tb_item in tb_items:
                    item = LastUpdatedOrderedDict()
                    label_l = tb_item.xpath('./b/a/text()')
                    if len(label_l) > 0:
                        item['label'] = str(label_l[0])
                    else:
                        item['label'] = '[No label]'
                    tm_l = tb_item.xpath('./text()[2]')
                    if len(tm_l) > 0:
                        item['trench-masters'] = []
                        raw_tm = str(tm_l[0])
                        raw_tm = raw_tm.replace('by trenchmaster', '')
                        if ' and ' in raw_tm:
                            raw_tms = raw_tm.split(' and ')
                        elif ',' in raw_tm:
                            raw_tms = raw_tm.split(',')
                        elif '/' in raw_tm:
                            raw_tms = raw_tm.split('/')
                        else:
                            raw_tms = [raw_tm]
                        for tm in raw_tms:
                            item['trench-masters'].append(tm.strip())
                    else:
                        item['trench-master'] = '[No trench master]'
                    href_l = tb_item.xpath('./b/a/@href')
                    href = str(href_l[0])
                    pstr = href.replace("javascript:openViewer('viewtrenchbookentry.asp?",
                                        '')
                    if pstr != href:
                        item['page'] = 'viewtrenchbookentry.asp'
                    else:
                        pstr = href.replace("javascript:openViewer('trenchbookviewer.asp?",
                                            '')
                        item['page'] = 'trenchbookviewer.asp'
                    pstr = pstr.replace("')", '')
                    # print(str(pstr))
                    params = pstr.split('&')
                    item['params'] = LastUpdatedOrderedDict()
                    for param in params:
                        param_ex = param.split('=')
                        key = param_ex[0]
                        val = int(float(param_ex[1]))
                        item[key] = val
                        item['params'][key] = val
                    # now get the trenches and years
                    tr_y_list = tb_item.xpath('./ul/li/text()')
                    item['trenches'] = []
                    item['max_year'] = 0
                    for tr_y in tr_y_list:
                        tr_item = LastUpdatedOrderedDict()
                        tr_y = tr_y.replace(']', '')
                        tr_y_ex = tr_y.split('[')
                        if len(tr_y_ex) == 2:
                            tr_item['label'] = tr_y_ex[0].strip()
                            tr_item['year'] = int(float(tr_y_ex[1]))
                            if item['max_year'] < tr_item['year']:
                                item['max_year'] = tr_item['year']
                        else:
                            print('Weird stuff with: ' + tr_y)
                        item['trenches'].append(tr_item)
                    items.append(item)  
            else:
                print('List is not valid, sadly')
        self.save_as_json_file(self.pc_directory,
                               self.trench_book_index_json,
                               items)
        return items
    
    def get_trench_book_list_html(self):
        """ gets the list of trench book
            items from a file or from a server
        """
        content = None
        tb_list = None
        start_index = None
        end_index = None
        if self.use_cached_tb_index:
            # get from locally saved copy
            content = self.get_trench_book_index_from_file()
        else:
            # get from the website
            content = self.get_trench_book_index()
        if isinstance(content, str):
            # success in getting the content
            start_index_text = '<p class="title">Trench Book Library</p>'
            end_index_text = '</td></tr></table>'
            start_index = content.index(start_index_text)
            if isinstance(start_index, int):
                # found the first part, trim off everything before that    
                first_to_end_content = content[start_index:]
                end_index = first_to_end_content.index(end_index_text)
            if isinstance(end_index, int):
                # now trim away the end of the content
                tb_list = first_to_end_content[0:end_index]
                tb_list = self.clean_html(tb_list)
                print('Start: ' + str(start_index) + ' - ' + str(end_index))
                tb_list += '</ul>'
                tb_list = '<div>' + tb_list + '</div>'
        else:
            print('Crap! No content')
        return tb_list
    
    def clean_html(self, html_str):
        """ clean HTML to make it more likely to validate """
        html_str = html_str.replace('&nbsp;', ' ')
        html_str = html_str.replace('&', '&amp;')
        return html_str

    def get_trench_book_index(self):
        """
        gets the trench book index
        """
        content = None
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        payload = {'oc': True}
        url = self.trench_book_index_url
        try:
            gapi = GeneralAPI()
            r = requests.get(url,
                             params=payload,
                             timeout=240,
                             headers=gapi.client_headers)
            self.request_url = r.url
            r.raise_for_status()
            content = r.text
        except:
            self.request_error = True
            content = self.get_trench_book_index_from_file()
        return content

    def get_trench_book_index_from_file(self):
        """ gets the HTML for the trench book index from a file """
        print('Attempting to get local copy..')
        local_file = self.define_import_directory_file(self.pc_directory,
                                                       'tb_index.html')
        print('Getting: ' + local_file)
        content = self.load_file(local_file)
        return content

    def compose_url_from_link(self, link):
        """ makes a full url from a link """
        url = None
        for link_type, url_path in self.content_url_prefixes.items():
            if link_type in link:
                if isinstance(url_path, str):
                    url = self.base_url + url_path + link
        return url
    
    def get_param_obj(self, url_params_str):
        """ makes a dict of a string of url params """
        params = LastUpdatedOrderedDict()
        param_parts = url_params_str.split('&')
        param_parts.sort()  # make sure the parameters are sorted consistently
        for param_part in param_parts:
            if '=' in param_part:
                param_ex = param_part.split('=')
                if len(param_ex) == 2:
                    param_key = param_ex[0]
                    param_val = param_ex[1]
                    params[param_key] = param_val
        return params
    
    def compose_filename_from_link(self, link):
        """ make a filename from a link """
        filename = None
        for link_prefix in self.content_link_prefixes:
            if link_prefix in link:
                # print(link_prefix)
                link_type = link_prefix.replace('.asp', '')
                q_part_ex = link.split('?') # split link, to get URL params
                if len(q_part_ex) > 0:
                    url_params_str = q_part_ex[1]
                    params = self.get_param_obj(url_params_str)
                    filename = link_type + '-'
                    for param_key, param_val in params.items():
                        filename += '--' + param_key + '-' + param_val
                    filename += '.html'
        return filename
    
    def get_links_from_page(self, html_str):
        """ gets links from a page """
        links = {
            'viewtrenchbookentry': [],
            'viewlocus': [],
            'trenchbookviewer' : []
        }
        html_ex = html_str.split('"')  # split by quotes
        for q_part in html_ex:
            for link_prefix in self.content_link_prefixes:
                if link_prefix in q_part:
                    # string has a link in it
                    link_type = link_prefix.replace('.asp', '')
                    ex_link = link_prefix + '?'  # add the ? for a url
                    q_part_ex = q_part.split(ex_link) # split it, to get URL params
                    if len(q_part_ex) > 0:
                        url_params_str = q_part_ex[1]
                        url_params_str = url_params_str.replace("'", '')
                        url_params_str = url_params_str.replace(')', '')
                        url_params_str = url_params_str.replace('&amp;', '&')
                        if '>' in url_params:
                            # a case where there is a missing end quote
                            # setting off the URL
                            url_params_ex = url_params_str.split('>')
                            url_params_str = url_params_ex[0]
                        params = self.get_param_obj(url_params_str)
                        if link_type == 'viewlocus' and \
                           'lid' in params:
                            # remove kruft from locus data
                            clean_link = link_prefix + '?lid=' + params['lid']    
                        else:
                            clean_link = link_prefix + '?' + url_params_str
                        if '##' not in url_params:
                            #  so we can skip blank links
                            links[link_type].append(clean_link)
        return links               

    def cache_page_locally(self, url, payload, act_dir, filename):
        """ caches content of a page locally if successfuly downloaded
        """
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        file_path = self.define_import_directory_file(act_dir,
                                                      filename)
        ok = False
        try:
            gapi = GeneralAPI()
            r = requests.get(url,
                             params=payload,
                             timeout=240,
                             headers=gapi.client_headers)
            self.request_url = r.url
            r.raise_for_status()
            content = r.text
            saved = False
            try:
                file = codecs.open(file_path, 'w', 'utf-8')
                # file.write(codecs.BOM_UTF8)
                file.write(content)
                file.close()
                saved = True
            except:
                saved = False
            if saved is False:
                try:
                    f = open(file_path, 'w', encoding='utf-8')
                    f.write(content)
                    f.close()
                except:
                    saved = False
            if saved:
                ok = True
            else:
                print('CANNOT SAVE: ' + file_path)
                ok = False
        except:
            ok = False
        return ok

    def valid_as_html(self, check_str):
        """ checks to see if a string is OK as HTML """
        ok = True
        check_str = '<div>' + check_str + '</div>'
        try:
            parser = etree.XMLParser()
            tree = etree.XML(check_str, parser)
            self.errors['html'] = False
        except:
            self.errors['html'] = str(len(parser.error_log)) + ' HTML validation errors,'
            self.errors['html'] += ' 1st error is: ' + str(parser.error_log[0].message)
            ok = False
        return ok

    def save_as_json_file(self, act_dir, filename, data):
        """ saves an object as a json formatted file """
        file_path = self.define_import_directory_file(act_dir,
                                                      filename)
        json_output = json.dumps(data,
                                 indent=4,
                                 ensure_ascii=False)
        file = codecs.open(file_path, 'w', 'utf-8')
        # file.write(codecs.BOM_UTF8)
        file.write(json_output)
        file.close()

    def load_json_file_os_obj(self, act_dir, filename):
        """ load a json file as an object """
        json_obj = None
        dir_file = self.define_import_directory_file(act_dir,
                                                     filename)
        if os.path.exists(dir_file):
            try:
                json_obj = json.load(codecs.open(dir_file,
                                                 'r',
                                                 'utf-8-sig'))
            except:
                print('Cannot parse as JSON: ' + dir_file)
                json_obj = False
        return json_obj
    
    def get_directory_files(self, act_dir):
        """ Gets a list of files from a directory """
        files = False
        full_dir = self.define_import_directory_file(act_dir)
        if os.path.exists(full_dir):
            for dirpath, dirnames, filenames in os.walk(full_dir):
                files = sorted(filenames)
        else:
            print('Cannot find: ' + full_dir)
        return files

    def load_file(self, dir_file):
        """ Loads a file and parse it into a
            json object
        """
        data = None
        if os.path.exists(dir_file):
            try:
                with open(dir_file, 'r') as myfile:
                    data = myfile.read().replace('\n', ' ')
            except:
                data = False
        return data

    def define_import_directory_file(self, act_dir, filename=''):
        """ defines the import directory
            to be the default or somewhere else on the file system
        """
        if self.act_import_dir is not False:
            full_dir = self.act_import_dir + '/' + act_dir
        else:
            full_dir = self.root_import_dir + '/' + act_dir
        if len(filename) > 0:
            full_dir += '/' + filename
        full_dir.replace('//', '/')
        return full_dir
        