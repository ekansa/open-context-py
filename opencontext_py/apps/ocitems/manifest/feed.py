import json
import datetime
from django.conf import settings
from django.utils.http import urlencode
from django.core.paginator import Paginator
from django.utils import feedgenerator
from django.utils.feedgenerator import SyndicationFeed, Atom1Feed
from django.contrib.syndication.views import Feed
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.ocitem.models import OCitem


class ManifestFeed():
    """
    This class creates a feed for the manifest
    """
    DEFAULT_ENTRIES_PER_PAGE = 25
    DEFAULT_PAGE = 1

    def __init__(self):
        self.entries_per_page = self.DEFAULT_ENTRIES_PER_PAGE
        self.page = self.DEFAULT_PAGE
        self.count = 0
        self.updated = False
        self.last_page = False
        rp = RootPath()
        self.base_url = rp.get_baseurl()

    def make_feed(self, get_data):
        """ makes a feed based on paging data """
        self.set_request_paging(get_data)
        self.get_manifest_basics()
        self.set_last_page()
        page_items = self.get_manifest_page()
        f = OCfeedMaker(
            title="Open Context Manifest Feed",
            link="http://www.example.com/",
            subtitle=self.make_feed_subtitle(),
            pubdate=self.updated,
            updateddate=self.updated,
            description="In which I write about what I ate today.",
            language="en",
            author_name="Myself",
            feed_url=self.base_url + '/manifest/.atom')
        f.base_url = self.base_url + '/manifest/.atom'
        f.page = self.page
        f.count = self.count
        f.recs = self.entries_per_page
        f.default_recs = self.DEFAULT_ENTRIES_PER_PAGE
        for man_obj in page_items:
            url = '/'.join([self.base_url,
                            man_obj.item_type,
                            man_obj.uuid])
            json_ld = self.get_json_ld_obj(man_obj.uuid)
            f.add_item(title=self.get_item_tile(json_ld),
                       link=url,
                       unique_id=self.get_item_id(json_ld, url),
                       pubdate=man_obj.published,
                       updateddate=man_obj.revised,
                       description='')
        return f.writeString('UTF-8')

    def get_json_ld_obj(self, uuid):
        """ gets the item's JSON-LD """
        ocitem = OCitem().get_item(uuid)
        return ocitem.json_ld
    
    def get_item_tile(self, json_ld):
        """ returns the title, if not, the label """
        if 'dc-terms:title' in json_ld:
            output = json_ld['dc-terms:title']
        else:
            output = json_ld['label']
        return output
    
    def add_authors(self, json_ld):
        """ add author information """
        pass
   
    def get_item_id(self, json_ld, url):
        """ returns the title, if not, the label """
        if 'id' in json_ld:
            output = json_ld['id']
        else:
            output = url
        return output

    def set_request_paging(self, get_data):
        """ sets the current page number """
        if 'page' in get_data:
            page = self.return_integer_value(get_data['page'])
            if page is not False:
                self.page = page
        if 'recs' in get_data:
            recs = self.return_integer_value(get_data['recs'])
            if recs is not False:
                self.entries_per_page = recs

    def get_manifest_basics(self):
        """ gets the count of manifest items """
        self.count = Manifest.objects\
                           .filter(indexed__isnull=False)\
                           .count()
        man_list = Manifest.objects\
                           .filter(indexed__isnull=False)\
                           .order_by('-revised')[:1]
        if len(man_list) > 0:
            self.updated = man_list[0].revised

    def get_manifest_page(self):
        """ gets the manifest list """
        man_list = Manifest.objects\
                           .filter(indexed__isnull=False)\
                           .order_by('-revised')
        paginator = Paginator(man_list, self.entries_per_page)
        page_list = paginator.page(self.page)
        return page_list
    
    def set_last_page(self):
        """ sets the last page """
        last = self.count / self.entries_per_page
        if last == round(last, 0):
            self.last_page = int(round(last))
        else:
            self.last_page = int(round(last)) + 1
    
    def make_feed_subtitle(self):
        """ makes a string of the feed's subtitle """
        start_index = (self.page - 1) * self.entries_per_page + 1
        end_index = (self.page) * self.entries_per_page
        subtitle = ' '.join(['This update-time sorted (most recent first)',
                             'feed provides a comprehensive list',
                             'of all content in Open Context.',
                             'Digital archives can use this paged feed',
                             'to retrieve all resources relevant to data',
                             'curation from Open Context. This page',
                             'includes entries',
                             str(start_index),
                             'to',
                             str(end_index),
                             'of',
                             str(self.count),
                             'entries.'])
        return subtitle
        
    def return_integer_value(self, raw_value):
        """ returns an integer value or false
        """
        try:
            value = int(float(raw_value))
        except:
            value = False
        return value
    
    def date_convert(self, date_val):
        """ converts to a python datetime if not already so """
        if isinstance(date_val, str):
            date_val = date_val.replace('Z', '')
            dt = datetime.datetime.strptime(date_val, '%Y-%m-%dT%H:%M:%S')
        else:
            dt = date_val
        return dt
    


class OCfeedMaker(Atom1Feed):
    page = 1
    count = 1
    entries_per_page = 20
    default_recs = 20
    last_page = False
    base_url = ''
    
    def root_attributes(self):
        attrs = super(OCfeedMaker, self).root_attributes()
        attrs['xmlns:dc-terms'] = 'http://purl.org/dc/terms/'
        attrs['xmlns:opensearch'] = 'http://a9.com/-/spec/opensearch/1.1/'
        return attrs
    
    def set_last_page(self):
        """ sets the last page """
        last = self.count / self.entries_per_page
        if last == round(last, 0):
            self.last_page = int(round(last))
        else:
            self.last_page = int(round(last)) + 1
    
    def make_paging_link_href(self, new_page):
        """ makes a URL for another page """
        if new_page > self.last_page:
            new_page = self.last_page
        if new_page < 1:
            new_page = 1
        req_params = {'page': new_page}
        if self.default_recs != self.entries_per_page:
            req_params['recs'] = self.entries_per_page
        url = self.base_url + '?' + urlencode(req_params)
        return url

    def add_root_elements(self, handler):
        super(OCfeedMaker, self).add_root_elements(handler)
        handler.addQuickElement('opensearch:totalResults', str(self.count))
        handler.addQuickElement('opensearch:itemsPerPage', str(self.recs))
        start_index = (self.page - 1) * self.entries_per_page + 1
        handler.addQuickElement('opensearch:startIndex', str(start_index))
        self.set_last_page()
        # add the self page link
        url = self.make_paging_link_href(self.page)
        handler.addQuickElement('link',
                                None,
                                {'rel': 'self',
                                 'type': 'application/atom+xml',
                                 'href': url})
        # add the first page link
        url = self.make_paging_link_href(1)
        handler.addQuickElement('link',
                                None,
                                {'rel': 'first',
                                 'type': 'application/atom+xml',
                                 'href': url})
        url = self.make_paging_link_href(self.last_page)
        handler.addQuickElement('link',
                                None,
                                {'rel': 'last',
                                 'type': 'application/atom+xml',
                                 'href': url})
        if self.page > 1:
            # add the prev page link
            url = self.make_paging_link_href(self.page - 1)
            handler.addQuickElement('link',
                                    None,
                                    {'rel': 'prev',
                                     'type': 'application/atom+xml',
                                     'href': url})
        if self.page < self.last_page:
            # add the next page link
            url = self.make_paging_link_href(self.page + 1)
            handler.addQuickElement('link',
                                    None,
                                    {'rel': 'next',
                                     'type': 'application/atom+xml',
                                     'href': url})
        

