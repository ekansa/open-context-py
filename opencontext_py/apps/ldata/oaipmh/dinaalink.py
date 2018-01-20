import re
import json
import os
import codecs
import requests
import hashlib
import csv
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
from opencontext_py.apps.ocitems.strings.manage import StringManagement
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration
from opencontext_py.apps.ocitems.geospace.models import Geospace
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
# xml = oai_dinaa.get_list_records_xml(url)
# oai_dinaa.find_trinomials_in_metadata(xml)
    """
    
    NAMESPACES = {
        'oai': 'http://www.openarchives.org/OAI/2.0/',
        'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
    }
    COUNTY_PREFIXES = {
        '41AN': 'Anderson County', 
        '41AS': 'Aransas County', 
        '41BC': 'Blanco County', 
        '41BL': 'Bell County', 
        '41BN': 'Bandera County', 
        '41BO': 'Brazoria County', 
        '41BP': 'Bastrop County', 
        '41BR': 'Brown County', 
        '41BT': 'Burnet County', 
        '41BU': 'Burleson County', 
        '41BX': 'Bexar County', 
        '41CC': 'Concho County', 
        '41CD': 'Colorado County', 
        '41CH': 'Chambers County', 
        '41CI': 'Childress County', 
        '41CJ': 'Comanche County', 
        '41CK': 'Coke County', 
        '41CM': 'Comal County', 
        '41CP': 'Camp County', 
        '41CV': 'Coryell County', 
        '41CW': 'Caldwell County', 
        '41DL': 'Dallas County', 
        '41DW': 'DeWitt County', 
        '41EP': 'El Paso County', 
        '41FB': 'Fort Bend County', 
        '41FT': 'Freestone County', 
        '41FY': 'Fayette County', 
        '41GD': 'Goliad County', 
        '41GL': 'Gillespie County', 
        '41GM': 'Grimes County', 
        '41GU': 'Guadalupe County', 
        '41HA': 'Hale County', 
        '41HE': 'Henderson County', 
        '41HK': 'Haskell County', 
        '41HM': 'Hamilton County', 
        '41HR': 'Harris County', 
        '41HS': 'Harrison County', 
        '41HY': 'Hays County', 
        '41JS': 'Jones County', 
        '41JW': 'Jim Wells County', 
        '41KA': 'Karnes County', 
        '41KE': 'Kendall County', 
        '41KF': 'Kaufman County', 
        '41KM': 'Kimble County', 
        '41KR': 'Kerr County', 
        '41KT': 'Kent County', 
        '41KY': 'Kinney County', 
        '41LE': 'Lee County', 
        '41LK': 'Live Oak County', 
        '41LM': 'Lampasas County', 
        '41LR': 'Lamar County', 
        '41LT': 'Limestone County', 
        '41MD': 'Midland County', 
        '41ME': 'Medina County', 
        '41MI': 'Mills County', 
        '41MK': 'McCulloch County', 
        '41MM': 'Milam County', 
        '41MN': 'Menard County', 
        '41MS': 'Mason County', 
        '41MV': 'Maverick County', 
        '41MX': 'Morris County', 
        '41NL': 'Nolan County', 
        '41NU': 'Nueces County', 
        '41DM': 'Dimmit County', 
        '41PC': 'Pecos County', 
        '41PK': 'Polk County', 
        '41PN': 'Panola County', 
        '41PR': 'Parker County', 
        '41PS': 'Presidio County', 
        '41RB': 'Roberts County', 
        '41RF': 'Refugio County', 
        '41RK': 'Rusk County', 
        '41RT': 'Robertson County', 
        '41SL': 'Schleicher County', 
        '41SM': 'Smith County', 
        '41SP': 'San Patricio', 
        '41SR': 'Starr County', 
        '41SS': 'San Saba', 
        '41SV': 'Somervell', 
        '41TG': 'Tom Green County', 
        '41TR': 'Tarrant County', 
        '41TT': 'Titus County', 
        '41TV': 'Travis County', 
        '41UR': 'Upshur County', 
        '41VT': 'Victoria County', 
        '41VV': 'Val Verde County', 
        '41WA': 'Walker County', 
        '41WB': 'Webb County', 
        '41WE': 'Wheeler County', 
        '41WH': 'Wharton County', 
        '41WL': 'Waller County', 
        '41WM': 'Williamson County', 
        '41WN': 'Wilson County', 
        '41YN': 'Young County', 
        '41ZP': 'Zapata County', 
        '41ZV': 'Zavala County'
    }
    
    COUNTY_GEO = {
        '41AN': {'lat': 31.81333, 'lon': -95.65255}, 
        '41AS': {'lat': 28.01501, 'lon': -97.07382}, 
        '41BC': {'lat': 30.26638, 'lon': -98.39987}, 
        '41BL': {'lat': 31.03767, 'lon': -97.4782}, 
        '41BN': {'lat': 29.74721, 'lon': -99.24624}, 
        '41BO': {'lat': 29.16783, 'lon': -95.43426}, 
        '41BP': {'lat': 30.10361, 'lon': -97.31201}, 
        '41BR': {'lat': 31.77426, 'lon': -98.99979}, 
        '41BT': {'lat': 30.7883, 'lon': -98.18245}, 
        '41BU': {'lat': 30.49248, 'lon': -96.62146}, 
        '41BX': {'lat': 29.44896, 'lon': -98.52002}, 
        '41CC': {'lat': 31.3265, 'lon': -99.86396}, 
        '41CD': {'lat': 29.62082, 'lon': -96.52628}, 
        '41CH': {'lat': 29.70826, 'lon': -94.67138}, 
        '41CI': {'lat': 34.5292, 'lon': -100.20757}, 
        '41CJ': {'lat': 31.94798, 'lon': -98.55826}, 
        '41CK': {'lat': 31.88853, 'lon': -100.52991}, 
        '41CM': {'lat': 29.80818, 'lon': -98.27825}, 
        '41CP': {'lat': 32.97322, 'lon': -94.97848}, 
        '41CV': {'lat': 31.39091, 'lon': -97.7992}, 
        '41CW': {'lat': 29.83712, 'lon': -97.62}, 
        '41DL': {'lat': 32.76663, 'lon': -96.77787}, 
        '41DW': {'lat': 29.08208, 'lon': -97.35678}, 
        '41EP': {'lat': 31.76855, 'lon': -106.23483}, 
        '41FB': {'lat': 29.52749, 'lon': -95.77089}, 
        '41FT': {'lat': 31.70489, 'lon': -96.14909}, 
        '41FY': {'lat': 29.87679, 'lon': -96.91976}, 
        '41GD': {'lat': 28.6571, 'lon': -97.42649}, 
        '41GL': {'lat': 30.31806, 'lon': -98.94648}, 
        '41GM': {'lat': 30.54347, 'lon': -95.9855}, 
        '41GU': {'lat': 29.58305, 'lon': -97.94858}, 
        '41HA': {'lat': 34.07051, 'lon': -101.82688}, 
        '41HE': {'lat': 32.21189, 'lon': -95.85356}, 
        '41HK': {'lat': 33.17823, 'lon': -99.7303}, 
        '41HM': {'lat': 31.7048, 'lon': -98.11073}, 
        '41HR': {'lat': 29.85728, 'lon': -95.39234}, 
        '41HS': {'lat': 32.54813, 'lon': -94.37149}, 
        '41HY': {'lat': 30.05815, 'lon': -98.03106}, 
        '41JS': {'lat': 32.7399, 'lon': -99.87874}, 
        '41JW': {'lat': 27.7313, 'lon': -98.08994}, 
        '41KA': {'lat': 28.90574, 'lon': -97.8594}, 
        '41KE': {'lat': 29.94469, 'lon': -98.71156}, 
        '41KF': {'lat': 32.5993, 'lon': -96.2878}, 
        '41KM': {'lat': 30.48678, 'lon': -99.7487}, 
        '41KR': {'lat': 30.06148, 'lon': -99.35016}, 
        '41KT': {'lat': 33.18142, 'lon': -100.77757}, 
        '41KY': {'lat': 29.35021, 'lon': -100.41795}, 
        '41LE': {'lat': 30.31068, 'lon': -96.9657}, 
        '41LK': {'lat': 28.35137, 'lon': -98.12479}, 
        '41LM': {'lat': 31.19619, 'lon': -98.24145}, 
        '41LR': {'lat': 33.66726, 'lon': -95.5712}, 
        '41LT': {'lat': 31.54546, 'lon': -96.58053}, 
        '41MD': {'lat': 31.86917, 'lon': -102.03162}, 
        '41ME': {'lat': 29.3557, 'lon': -99.11013}, 
        '41MI': {'lat': 31.49519, 'lon': -98.59546}, 
        '41MK': {'lat': 31.19887, 'lon': -99.34748}, 
        '41MM': {'lat': 30.78634, 'lon': -96.97685}, 
        '41MN': {'lat': 30.88978, 'lon': -99.82064}, 
        '41MS': {'lat': 30.71772, 'lon': -99.22613}, 
        '41MV': {'lat': 28.74259, 'lon': -100.31451}, 
        '41MX': {'lat': 33.11348, 'lon': -94.73265}, 
        '41NL': {'lat': 32.30349, 'lon': -100.40605}, 
        '41NU': {'lat': 27.73506, 'lon': -97.51632}, 
        '41DM': {'lat': 28.42254, 'lon': -99.75673}, 
        '41PC': {'lat': 30.78106, 'lon': -102.72357}, 
        '41PK': {'lat': 30.79272, 'lon': -94.83002}, 
        '41PN': {'lat': 32.16236, 'lon': -94.30565}, 
        '41PR': {'lat': 32.77765, 'lon': -97.8051}, 
        '41PS': {'lat': 29.9998, 'lon': -104.24052}, 
        '41RB': {'lat': 35.83849, 'lon': -100.81344}, 
        '41RF': {'lat': 28.32158, 'lon': -97.15952}, 
        '41RK': {'lat': 32.10772, 'lon': -94.76188}, 
        '41RT': {'lat': 31.02704, 'lon': -96.51279}, 
        '41SL': {'lat': 30.89745, 'lon': -100.53855}, 
        '41SM': {'lat': 32.37504, 'lon': -95.26918}, 
        '41SP': {'lat': 28.00878, 'lon': -97.51827}, 
        '41SR': {'lat': 26.56215, 'lon': -98.7384}, 
        '41SS': {'lat': 31.1552, 'lon': -98.81758}, 
        '41SV': {'lat': 32.22229, 'lon': -97.77434}, 
        '41TG': {'lat': 31.4044, 'lon': -100.46207}, 
        '41TR': {'lat': 32.77156, 'lon': -97.29124}, 
        '41TT': {'lat': 33.2166, 'lon': -94.96567}, 
        '41TV': {'lat': 30.33469, 'lon': -97.78195}, 
        '41UR': {'lat': 32.73628, 'lon': -94.94148}, 
        '41VT': {'lat': 28.79635, 'lon': -96.97153}, 
        '41VV': {'lat': 29.89296, 'lon': -101.15172}, 
        '41WA': {'lat': 30.73905, 'lon': -95.57228}, 
        '41WB': {'lat': 27.76106, 'lon': -99.33157}, 
        '41WE': {'lat': 35.40128, 'lon': -100.26965}, 
        '41WH': {'lat': 29.27786, 'lon': -96.2221}, 
        '41WL': {'lat': 30.01081, 'lon': -95.98765}, 
        '41WM': {'lat': 30.64804, 'lon': -97.60076}, 
        '41WN': {'lat': 29.17401, 'lon': -98.08657}, 
        '41YN': {'lat': 33.1767, 'lon': -98.68777}, 
        '41ZP': {'lat': 27.00078, 'lon': -99.16861}, 
        '41ZV': {'lat': 28.86621, 'lon': -99.7606} 
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
        self.project_uuid = ''
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
    
    def save_csv_from_filecache(self):
        """ updates Open Context to save new sites
            and annotations from the 
            file cache
        """
        if self.filecache is not None:
            # print('Cache update !: ' + self.cache_filekey)
            self.filecache.working_dir = self.working_dir
            json_obj = self.filecache.get_dict_from_file(self.cache_filekey)
            filename = self.cache_filekey + '.csv'
            directory = self.filecache.prep_directory(self.working_dir)
            dir_filename = os.path.join(directory,
                                        filename)
            if isinstance(json_obj, dict):
                if 'trinomial_refs' in json_obj:
                    field_name_row = [
                        'County Code',
                        'County Name',
                        'Trinomial',
                        'Citation',
                        'URI',
                        'Title',
                        'Note'
                    ]
                    f = codecs.open(dir_filename, 'w', encoding='utf-8')
                    writer = csv.writer(f, dialect=csv.excel, quoting=csv.QUOTE_ALL)
                    writer.writerow(field_name_row)
                    for tri_ref in json_obj['trinomial_refs']:
                        citation = tri_ref['citation_html']
                        uri = tri_ref['rec_uri']
                        title = tri_ref['title']
                        if len(title) > 194:
                            title = title[0:190] + '... '
                        l_exists = LinkEntity.objects.filter(uri=uri)[:0]
                        if len(l_exists) < 1:
                            l_ent = LinkEntity()
                            l_ent.uri = uri
                            l_ent.label = title
                            l_ent.alt_label = title
                            l_ent.vocab_uri = tri_ref['source_uri']
                            l_ent.ent_type = 'class'
                            l_ent.save()
                        if 'note' in tri_ref:
                            note = tri_ref['note']
                        else:
                            note = ''
                        for trinomial in tri_ref['trinomials']:
                            county_code = trinomial[0:4]
                            act_county_name = None
                            for key, county_name in self.COUNTY_PREFIXES.items():
                                if county_code == key:
                                    act_county_name = county_name
                                    break
                            print('County code: ' + county_code + ' is ' + str(act_county_name))
                            row = [
                                county_code,
                                act_county_name,
                                trinomial,
                                citation,
                                uri,
                                title,
                                note
                            ]
                            writer.writerow(row)
                    print('Done!')
                    f.closed
    
    def link_sites_from_filecache(self):
        """ updates Open Context to save new sites
            and annotations from the 
            file cache
        """
        if self.filecache is not None:
            # print('Cache update !: ' + self.cache_filekey)
            self.filecache.working_dir = self.working_dir
            json_obj = self.filecache.get_dict_from_file(self.cache_filekey)
            if isinstance(json_obj, dict):
                if 'trinomial_refs' in json_obj:
                    for tri_ref in json_obj['trinomial_refs']:
                        uri = tri_ref['rec_uri']
                        title = tri_ref['title']
                        if len(title) > 194:
                            title = title[0:190] + '... '
                        l_exists = LinkEntity.objects.filter(uri=uri)[:1]
                        if len(l_exists) < 1:
                            l_ent = LinkEntity()
                            l_ent.uri = uri
                            l_ent.label = title
                            l_ent.alt_label = title
                            l_ent.vocab_uri = tri_ref['source_uri']
                            l_ent.ent_type = 'class'
                            l_ent.save()
                        for trinomial in tri_ref['trinomials']:
                            man_objs = Manifest.objects.filter(label=trinomial,
                                                               class_uri='oc-gen:cat-site')
                            if len(man_objs) > 0:
                                man_obj = man_objs[0]
                                la = LinkAnnotation()
                                la.subject = uri  # the subordinate is the subject
                                la.subject_type = 'uri'
                                la.project_uuid = man_obj.project_uuid
                                la.source_id = self.source_id
                                la.predicate_uri = "skos:broader"
                                la.object_uri = tri_ref['source_uri']
                                la.save()
                                try:
                                    la.save()
                                except:
                                    pass
                                links = LinkAnnotation.objects\
                                                      .filter(subject=man_obj.uuid,
                                                              object_uri=uri)[:1]
                                if len(links) < 1:
                                    print('Link ' + man_obj.label + ' (' +   man_obj.uuid + ') to ' + uri)
                                    la = LinkAnnotation()
                                    la.subject = man_obj.uuid  # the subordinate is the subject
                                    la.subject_type = man_obj.item_type
                                    la.project_uuid = man_obj.project_uuid
                                    la.source_id = self.source_id
                                    la.predicate_uri = 'dc-terms:isReferencedBy'
                                    la.object_uri = uri
                                    la.save()
                                    try:
                                        la.save()
                                    except:
                                        pass
    
    def add_sites_geo_from_filecache(self):
        """ updates Open Context to save new sites
            location information
        """
        if self.filecache is not None:
            # print('Cache update !: ' + self.cache_filekey)
            self.filecache.working_dir = self.working_dir
            json_obj = self.filecache.get_dict_from_file(self.cache_filekey)
            if isinstance(json_obj, dict):
                if 'trinomial_refs' in json_obj:
                    for tri_ref in json_obj['trinomial_refs']:
                        for trinomial in tri_ref['trinomials']:
                            man_objs = Manifest.objects.filter(label=trinomial,
                                                               class_uri='oc-gen:cat-site')
                            if len(man_objs) > 0:
                                man_obj = man_objs[0]
                                county_code = trinomial[0:4]
                                if county_code in self.COUNTY_GEO:
                                    county_geo = self.COUNTY_GEO[county_code]
                                    print('County code: ' + county_code + ' is ' + str(county_geo))
                                    geos = Geospace.objects.filter(uuid=man_obj.uuid)[:1]
                                    if len(geos) < 1:
                                        geo = Geospace()
                                        geo.uuid = man_obj.uuid
                                        geo.project_uuid = man_obj.project_uuid
                                        geo.source_id = self.source_id
                                        geo.item_type = man_obj.item_type
                                        geo.feature_id = 1
                                        geo.meta_type = "oc-gen:discovey-location"
                                        geo.ftype = 'Point'
                                        geo.latitude = county_geo['lat']
                                        geo.longitude = county_geo['lon']
                                        geo.specificity = -11
                                        geo.save()
                                