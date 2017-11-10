import re
import json
import os
import codecs
import requests
import hashlib
from lxml import etree
from time import sleep
from io import StringIO, BytesIO
from django.conf import settings
from django.db import connection
from django.db import models
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.edit.dinaa.trinomials.manage import TrinomialManage
from opencontext_py.apps.ldata.oaipmh.api import OaiPmhClientAPI
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.strings.models import OCstring
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ldata.linkannotations.manage import LinkAnnoManagement
from opencontext_py.apps.ldata.linkentities.models import LinkEntity
from opencontext_py.apps.indexer.reindex import SolrReIndex


class OaiPmhDinaaLink():
    """ Interacts with an OAI-PMH service to find smithsonian trinomials in a the metadata """
        
    """

from opencontext_py.apps.ldata.oaipmh.dinaalink import OaiPmhDinaaLink
url = 'http://scholarworks.sfasu.edu/do/oai/?verb=ListRecords&metadataPrefix=oai_dc&set=publication:ita'
oai_dinaa = OaiPmhDinaaLink()
xml = oai_dinaa.get_list_records_xml(url)
oai_dinaa.find_trinomials_in_metadata(xml)
    """
    
    NAMESPACES = {
        'oai': 'http://www.openarchives.org/OAI/2.0/',
        'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
    }
    
    
    def __init__(self):
        self.results = False
        self.project_uuids = None
        self.uuids = None
        self.source_id = 'oai-pmh-client-lookup'
        self.all_docs_lists_key = 'all-document-list'
        self.dinaa_matches_key = 'dinaa-matches'
        self.checked_docs_key = 'all-docs-checked'
        self.tri_predicate = 'a5c308c3-52f8-4076-b315-d3258d485572'
        self.only_valid_state_id = None  # string for a valid state code, none if we don't check
        self.trinomial_refs = []
        self.unique_trinomials = []
        self.unique_state_counties = []
        self.namespaces = OaiPmhClientAPI().NAMESPACES
        self.request_url = None
        self.resumption_tokens = []
        # filecach object, if none don't keep track of urls, if
        # not none, then keep track and save as JSON on disk
        self.filecache = None
        self.working_dir = 'web-archiving'
        self.cache_filekey = 'ita-oai-trinomials'
    
    def find_trinomials_in_repository(self, url, resumption_token=None):
        """ finds all trinomials in a repository """
        xml = self.get_list_records_xml(url, resumption_token)
        if xml is not None:
            self.find_trinomials_in_metadata(xml)    
            self.update_url_filecache()
            resumption_token = self.get_xml_resumption_token(xml)
            if isinstance(resumption_token, str):
                if resumption_token not in self.resumption_tokens:
                    # only make a new request if we have a new resumption token
                    self.resumption_tokens.append(resumption_token)
                    # a hack, because the resumption token is screwed up
                    url = 'http://scholarworks.sfasu.edu/do/oai/?verb=ListRecord'
                    self.find_trinomials_in_repository(url,
                                                       resumption_token)
    
    def get_list_records_xml(self, url, resumption_token=None):
        """
        gets an XML etree from OAI-PMH list records, with an optional resumption_token
        """
        xml = None
        oai_client = OaiPmhClientAPI()
        url_content =  oai_client.get_list_records(url, resumption_token)
        self.request_url = oai_client.request_url
        print('Completed request to URL: ' + self.request_url)
        if url_content is not None:
            # we have text content from a URL, now parse it into
            # an XML object
            # url_content = url_content.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
            # xml = etree.fromstring(url_content, encoding='utf-8')
            xml = etree.parse(BytesIO(url_content))
            try:
                # xml = etree.fromstring(url_content)
                xml = etree.parse(BytesIO(url_content))
            except:
                print('XML Parsing failed')
                print('-------------------------------------------------')
                print(url_content)
                xml = None
        else:
             print('OAI-PMH request failed')
        return xml

    def find_trinomials_in_metadata(self, xml):
        """ finds trimomials in metadata """
        recs = xml.xpath('//oai:record', namespaces=self.namespaces)
        print('Number of records in XML: ' + str(len(recs)))
        for rec in recs:
            tri_dict = {
                'rec_uri': None,
                'title': None,
                'citation_html': None,
                'source_label': 'Index of Texas Archaeology: Open Access Gray Literature from the Lone Star State',
                'source_uri': 'http://scholarworks.sfasu.edu/ita',
                'request_url': self.request_url,
                'trinomials' : []
            }
            idents = rec.xpath('oai:metadata/oai_dc:dc/dc:identifier',
                               namespaces=self.namespaces)
            rec_uri = None
            for ident_dom in idents:
                act_uri = ident_dom.text
                if rec_uri is None:
                    rec_uri = act_uri
                if 'viewcontent.cgi' not in act_uri:
                    rec_uri = act_uri
            tri_dict['rec_uri'] = rec_uri
            titles = rec.xpath('oai:metadata/oai_dc:dc/dc:title',
                               namespaces=self.namespaces)
            for title_dom in titles:
                tri_dict['title'] = title_dom.text
                tri_dict['trinomials'] = self.extract_texas_trinomials_from_text(title_dom.text,
                                                                                 tri_dict['trinomials'])
            descripts = rec.xpath('oai:metadata/oai_dc:dc/dc:description',
                                  namespaces=self.namespaces)
            for description_dom in descripts:
                tri_dict['trinomials'] = self.extract_texas_trinomials_from_text(description_dom.text,
                                                                                 tri_dict['trinomials'])
            subjects = rec.xpath('oai:metadata/oai_dc:dc/dc:subject',
                                 namespaces=self.namespaces)
            for subject_dom in subjects:
                tri_dict['trinomials'] = self.extract_texas_trinomials_from_text(subject_dom.text,
                                                                                 tri_dict['trinomials'])
            tri_dict['citation_html'] = self.make_citation_html(rec)
            print('-----------------------------------')
            print(tri_dict['citation_html'])
            print('Trinomials: ' + str(tri_dict['trinomials']))
            print('-----------------------------------')
            if len(tri_dict['trinomials']) > 0:
                # we found trinomials! So add to our list of publications with trinomials
                self.trinomial_refs.append(tri_dict)
                for trinomial in tri_dict['trinomials']:
                    if trinomial not in self.unique_trinomials:
                        self.unique_trinomials.append(trinomial)
                        # now add the trinomialstate and county code to the list
                        # of unique state and county codes if it is new
                        # fist, we parse the trinomial to find the state and county parts
                        tri_m = TrinomialManage()
                        tri_p = tri_m.parse_trinomial(trinomial)
                        state_county = tri_p['state'] + tri_p['county']
                        if state_county not in self.unique_state_counties:
                            # we have a new state and county code, so add it to the list
                            self.unique_state_counties.append(state_county)
                    
     
    def make_citation_html(self, rec):
        """ returns citation html from a rec etree OAI-PHM dublin core xml object """
        idents = rec.xpath('oai:metadata/oai_dc:dc/dc:identifier',
                           namespaces=self.namespaces)
        rec_uri = ''
        volume = ''
        issue = ''
        for ident_dom in idents:
            act_uri = ident_dom.text
            if rec_uri == '':
                rec_uri = act_uri
            if 'viewcontent.cgi' not in act_uri:
                rec_uri = act_uri
        if '/vol' in rec_uri:
            rec_ex = rec_uri.split('/vol')
            if len(rec_ex) > 1:
                vol_part = rec_ex[1]
                vol_part_ex = vol_part.split('/')
                if len(vol_part_ex) > 1:
                    volume = 'Vol. ' + vol_part_ex[0]
                    issue = vol_part_ex[-1]
        title = ''
        titles = rec.xpath('oai:metadata/oai_dc:dc/dc:title',
                           namespaces=self.namespaces)
        for title_dom in titles:
            title = title_dom.text
        year = ''
        dates = rec.xpath('oai:metadata/oai_dc:dc/dc:date',
                           namespaces=self.namespaces)
        for date_dom in dates:
            date_ex = date_dom.text.split('-')
            if len(date_ex) > 0:
                year = date_ex[0]
        source = ''
        sources = rec.xpath('oai:metadata/oai_dc:dc/dc:source',
                           namespaces=self.namespaces)
        for source_dom in sources:
            source = source_dom.text
        authors = ''
        creators = rec.xpath('oai:metadata/oai_dc:dc/dc:creator',
                             namespaces=self.namespaces)
        num_creators = len(creators)
        i = 0
        for creator_dom in creators:
            i += 1
            if num_creators > 1 and i < (num_creators - 1):
                sep = ', '
            elif num_creators > 1 and i == (num_creators -1):
                sep = ' and '
            else:
                sep = ''
            authors += creator_dom.text + sep
        # now get the record id from the OAI header
        rec_id = self.get_record_oai_identifier(rec)
        if not isinstance(rec_id, str):
            rec_id = ''
        html_list = [
            '<div id="' +  rec_id + '" rel="dcterms:isReferencedBy" class="biblio-item">',
            '<a style="display:none;" href="#' +  rec_id + '"></a>',
            '<div typeof="dcterms:BibliographicResource bibo:Article" resource="#' +  rec_id + '">'
            '<div property="dcterms:bibliographicCitation">',
            '<p class="authors">' + authors + '</p>',
            '<div>',
            '<div class="pub-date">' + year + '</div>',
            '<div class="ref-title-pub">"' + title + '," ',
            '<span class="collection-title">' + source + '</span> ' + volume + '(' + issue + ')</div>',
            '<div class="ref-end"></div>',
            '</div>',
            '</div>',
            '<div class="ref-links">',
            '[<a rel="rdfs:isDefinedBy" href="' + rec_uri + '">Open Access</a>]',
            '</div>',
            '</div>',
            '</div>'
        ]
        html = '\r\n'.join(html_list)
        return html
    
    
    def get_record_oai_identifier(self, rec, remove_prefix=True):
        """ gets a record identifier from record OAI-PMH header """
        rec_id = None
        header_ids = rec.xpath('oai:header/oai:identifier',
                               namespaces=self.namespaces)
        for header_id_dom in header_ids:
            header_id = header_id_dom.text
            if ':' in header_id and remove_prefix:
                # grab the last part of the header for the the id
                id_ex = header_id.split(':')
                if len(id_ex) > 0:
                    rec_id = id_ex[-1]
            else:
                rec_id = header_id
        return rec_id

    def extract_texas_trinomials_from_text(self, text, trinomials=[]):
        """ extracts a list of trinomials from a text """
        # first, turn all non-alphanumeric characters into spaces
        text = self.text_clean(text)
        tokens = text.split(' ')
        i = 0
        alt_checks = []  # a list of up to 3 tokens that together may be a trinomial
        for token in tokens:
            if len(token) > 0:
                if token == '41' and len(alt_checks) == 0:
                    # 41 is the texas code, so we may have some tokens
                    # that follow may be a trinomial
                    alt_checks = [token]
                elif len(alt_checks) > 0:
                    if len(alt_checks) >= 3:
                        # reset alt checks, it has too many tokens in it to
                        # have a valid trinomial
                        alt_checks = []
                    else:
                        # check to see if the 2 to 3 tokens in alt_checks make a valid trinomial
                        ok_alt_trinomial = True
                        alt_checks.append(token)
                        if len(alt_checks) == 3:
                            # check for integer values in the 3rd (site position)
                            try:
                                int_token = int(float(token))
                            except:
                                int_token = None
                            if int_token is None:
                                # we have a non integer for the 3rd token
                                # in a possibly space seperated trinomial.
                                # so set ok_at_trinomial to False so we don't check
                                # all of the alt_checks values, as the 3rd value is invalid
                                ok_alt_trinomial = False
                        if ok_alt_trinomial:
                            # first, make a token to check by joining together all the tokens in alt_checks
                            alt_token = ''.join(alt_checks)  # no spaces between the items in alt_checks
                            alt_trinomial = self.validate_token_trinomial(alt_token)
                            if isinstance(alt_trinomial, str):
                                # we found something that looks like a trinomial based on multiple tokens!
                                print('Found seperated trinomial: ' + str(alt_checks))
                                if alt_trinomial not in trinomials:
                                    # add the newly found trinomial to the list of discovered trinomials
                                    trinomials.append(alt_trinomial)
                # do this for ALL tokens, to check if the token is by itself a trinomial
                trinomial = self.validate_token_trinomial(token)
                if isinstance(trinomial, str):
                    # found a trinomial that may not be new
                    if trinomial not in trinomials:
                        # found a new trinomial
                        trinomials.append(trinomial)
        return trinomials
            
    def validate_token_trinomial(self, token):
        """ checks to see if a token is a trinomial """
        # make the token upper case, so all county codes are upper case, if this
        # token happens to be a trinomial
        token = token.upper()
        ok = False
        trinomial = None
        tri_m = TrinomialManage()
        try:
            tri_p = tri_m.parse_trinomial(token)
        except:
            # could not parse as a trinomial
            # so it's not a trinomial
            tri_p = None
        if isinstance(tri_p, dict):
            ok = True
            # make sure the county part is only letters
            tri_p['county'] = re.sub('[^a-zA-Z]+', '', tri_p['county'])
            # now validate different parts of the trinomial
            if len(tri_p['state']) < 1 or len(tri_p['state']) > 2:
                # the state code has the wrong length not 1 or 2 characters
                ok = False
            else:
                # state length is OK, but check if it is an integer
                state_is_int = True
                try:
                    state_int = int(float(tri_p['state']))
                    state_is_int = True
                except:
                    state_is_int = False
                if state_is_int is False:
                    ok = False
                if isinstance(self.only_valid_state_id, str):
                    # we need to validate by an allowed state code
                    if tri_p['state'] != self.only_valid_state_id:
                        # the state part of the trinomial is not
                        # the allowed state id
                        ok = False
            if len(tri_p['county']) != 2:
                # county part of trinomial is the wrong length
                ok = False
            if len(tri_p['site']) < 1:
                # can't have a blank site number
                ok = False
            else:
                # site number is not blank, but check if it is an integer
                site_is_int = True
                try:
                    state_int = int(float(tri_p['state']))
                    state_is_int = True
                except:
                    state_is_int = False
                if state_is_int is False:
                    # not an integer so not a good trinomial
                    ok = False
            if ok:
                # now put together the trinomial parts into a well formated full trinomial
                trinomial = tri_p['state'] + tri_p['county'] + tri_p['site']
        return trinomial
    
    def text_clean(self, text):
        # replace all line breaks, and non alphanumeric charachers with spaces
        # this is useful for making a continual block of text. Also good for removing
        # different spacing characters from potential trinomials.
        sub_text = re.sub(r"\r", " ", text)
        sub_text = re.sub(r"\n", " ", sub_text)
        sub_text = re.sub('[^0-9a-zA-Z ]+', ' ',  sub_text)
        return sub_text
    
    
    def get_xml_resumption_token(self, xml):
        """ gets a record identifier from record OAI-PMH header """
        resumption_token = None
        comp_list_size = 0
        cursor = 0
        resumption_tokens = xml.xpath('//oai:resumptionToken',
                                      namespaces=self.namespaces)
        for resumption_dom in resumption_tokens:
            resumption_token = resumption_dom.text
            comp_list_size_r = resumption_dom.xpath('@completeListSize',
                                                    namespaces=self.namespaces)
            cursor_r = resumption_dom.xpath('@cursor',
                                            namespaces=self.namespaces)
            if len(comp_list_size_r) > 0 and len(cursor_r) > 0:
                try:
                    comp_list_size = int(float(comp_list_size_r[0]))
                    cursor = int(float(cursor_r[0]))
                except:
                    comp_list_size = 0
                    cursor = 0
        print('Complete List Size: ' + str(comp_list_size) + ', cursor: ' + str(cursor) + ', token: ' + str(resumption_token))
        return resumption_token
    
    def update_url_filecache(self):
        """ updates the file cache to save the state of a urls """
        if self.filecache is not None:
            # print('Cache update !: ' + self.cache_filekey)
            self.filecache.working_dir = self.working_dir
            json_obj = LastUpdatedOrderedDict()
            json_obj['count_trinomials'] = len(self.unique_trinomials)
            json_obj['count_trinomial_refs'] = len(self.trinomial_refs)
            json_obj['unique_trinomials'] = self.unique_trinomials
            json_obj['unique_state_counties'] = self.unique_state_counties
            json_obj['trinomial_refs'] = self.trinomial_refs
            self.filecache.save_serialized_json(self.cache_filekey,
                                                json_obj)
    