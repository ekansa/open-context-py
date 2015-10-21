import datetime
from django.conf import settings
from django.utils.http import urlencode
from django.utils import feedgenerator
from django.utils.feedgenerator import SyndicationFeed, Atom1Feed
from django.contrib.syndication.views import Feed
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement


""" Customization on Django's default Atom Feed
    specific for use with Open Context's (paged) manifest feed
"""
class PagedFeedMaker(Atom1Feed):
    page = 1
    count = 1
    entries_per_page = 20
    default_recs = 20
    last_page = False
    limit_item_types = False
    base_url = ''

    
    def root_attributes(self):
        attrs = super(PagedFeedMaker, self).root_attributes()
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
        if isinstance(self.limit_item_types, list):
            if len(self.limit_item_types) > 0:
                req_params['type'] = ','.join(self.limit_item_types)
        if self.default_recs != self.entries_per_page:
            req_params['recs'] = self.entries_per_page
        url = self.base_url + '?' + urlencode(req_params)
        return url

    def add_root_elements(self, handler):
        super(PagedFeedMaker, self).add_root_elements(handler)
        handler.addQuickElement('opensearch:totalResults', str(self.count))
        handler.addQuickElement('opensearch:itemsPerPage', str(self.entries_per_page))
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
        
    def add_item_elements(self, handler, item):
        super(PagedFeedMaker, self).add_item_elements(handler, item)
        handler.addQuickElement('link',
                                None,
                                {'rel': 'alternate',
                                 'type': 'application/ld+json',
                                 'title': 'JSON-LD representation of: ' + item['title'],
                                 'href': (item['link'] + '.json')})
        # now add authors items
        if 'project' in item:
            if item['project'] is not False:
                handler.addQuickElement('link',
                                        None,
                                        {'rel': 'dc-terms:isPartOf',
                                         'type': 'text/html',
                                         'title': item['project']['label'],
                                         'href': item['project']['id']})
        if 'authors' in item:
            if isinstance(item['authors'], list):
                for auth_item in item['authors']:
                    handler.startElement("author", {})
                    handler.addQuickElement("name", auth_item['label'])
                    handler.addQuickElement("uri", auth_item['id'])
                    handler.endElement("author")
        if 'files' in item:
            if isinstance(item['files'], list):
                for file_obj in item['files']:
                    attrs = {'rel': 'dc-terms:hasPart',
                             'href': file_obj['id']}
                    if file_obj['type'] == 'oc-gen:fullfile':
                        attrs['rel'] = 'enclosure'
                    if 'dc-terms:hasFormat' in file_obj:
                        mime_type = file_obj['dc-terms:hasFormat']
                        attrs['type'] = mime_type.replace('http://purl.org/NET/mediatypes/', '')
                    ftype = file_obj['type'].replace('oc-gen:', '')
                    attrs['title'] = item['title'] + ' (' + ftype + ' file)'
                    handler.addQuickElement('link',
                                            None,
                                            attrs)
        if 'stable_ids' in item:
            if isinstance(item['stable_ids'], list):
                for id_str in item['stable_ids']:
                    attrs = {'rel': 'dc-terms:identifier',
                             'href': id_str}
                    if 'ark:' in id_str:
                        attrs['title'] = 'ark'
                    elif 'doi.org' in id_str:
                        attrs['title'] = 'doi'
                    elif 'orcid.org' in id_str:
                        attrs['title'] = 'orcid'
                    handler.addQuickElement('link',
                                            None,
                                            attrs)    