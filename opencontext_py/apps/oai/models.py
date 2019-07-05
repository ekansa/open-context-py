import time
import datetime
import json
import requests
from lxml import etree
from django.conf import settings
from django.db.models import Max, Min, Count, Avg
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.apps.entities.uri.models import URImanagement
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.searcher.solrsearcher.complete import CompleteQuery


class OAIpmh():
    """
    Open Archives Initiative, Protocol for Metadata
    Harvesting Methods

    Supports OAI-DC and OAI-Datacite and Datacite

from opencontext_py.apps.ocitems.ocitem.models import OCitem, itemConstructionCache
icc = itemConstructionCache()
icc.print_caching = True
identifier = 'oc-3'
cache_id = icc.make_memory_cache_key('entities-thumb', identifier)
icc.get_entity_w_thumbnail(identifier)
icc.get_cache_object(cache_id)

    """

    OAI_PMH_NS = 'http://www.openarchives.org/OAI/2.0/'
    XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
    SL_NS = 'http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd'
    METADATA_FORMATS = [
        {'prefix': 'oai_dc',
         'schema': 'http://www.openarchives.org/OAI/2.0/oai_dc.xsd',
         'ns': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
         'schemaLocation': 'http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd',
         'label': 'OAI Dublin Core'},
        {'prefix': 'oai_datacite',
         'schema': 'http://schema.datacite.org/oai/oai-1.0/oai.xsd',
         'ns': 'http://schema.datacite.org/oai/oai-1.0/',
         'schemaLocation': 'http://schema.datacite.org/oai/oai-1.0/ http://schema.datacite.org/oai/oai-1.0/oai.xsd',
         'label': 'OAI DataCite'},
        {'prefix': 'datacite',
         'schema': 'http://schema.datacite.org/meta/nonexistant/nonexistant.xsd',
         'ns': 'http://datacite.org/schema/nonexistant',
         'schemaLocation': 'http://datacite.org/schema/kernel-2.1 http://schema.datacite.org/meta/kernel-2.1/metadata.xsd',
         'label': 'DataCite'}
    ]
    DATACITE_RESOURCE = {
        'ns': 'http://datacite.org/schema/kernel-2.1',
        'schemaLocation': 'http://datacite.org/schema/kernel-2.1 http://schema.datacite.org/meta/kernel-2.1/metadata.xsd'
    }

    DC_FORMATS = {'subjects': ['text/html',
                               'application/json',
                               'application/vnd.geo+json',
                               'application/ld+json'],
                  'media': ['text/html',
                            'application/json',
                            'application/vnd.geo+json',
                            'application/ld+json'],
                  'projects': ['text/html',
                               'application/json',
                               'application/vnd.geo+json',
                               'application/ld+json'],
                  'documents': ['text/html',
                                'application/json',
                                'application/vnd.geo+json',
                                'application/ld+json'],
                  'other': ['text/html',
                            'application/json',
                            'application/ld+json']}

    DATACITE_RESOURCE_TYPES = {
        'subjects': {'ResourceTypeGeneral': 'InteractiveResource',
                     'oc': 'Data Record'},
        'media': {'ResourceTypeGeneral': 'InteractiveResource',
                  'oc': 'Media resource'},
        'projects': {'ResourceTypeGeneral': 'Dataset',
                     'oc': 'Data publication project'},
        'documents': {'ResourceTypeGeneral': 'Text',
                      'oc': 'Document, diary, or notes'},
        'types': {'ResourceTypeGeneral': 'InteractiveResource',
                  'oc': 'Vocabulary category or concept'},
        'predicates': {'ResourceTypeGeneral': 'InteractiveResource',
                       'oc': 'Predicate, property or relation'},
        'other': {'ResourceTypeGeneral': 'InteractiveResource',
                  'oc': 'Resource'}
    }

    BASE_SETS = {
        'subjects': {'params': {'type': 'subjects'},
                     'label': 'Data Records'},
        'media': {'params': {'type': 'media'},
                  'label': 'Media resources'},
        'documents': {'params': {'type': 'documents'},
                      'label': 'Documents, Diaries, and Notes'},
        'projects':  {'params': {'type': 'projects'},
                      'label': 'Data Publication Projects'},
        'types': {'params': {'type': 'types'},
                  'label': 'Vocabulary Categories and Concepts'},
        'predicates': {'params': {'type': 'predicates'},
                       'label': 'Predicates, Properties and Relations'},
    }

    def __init__(self, id_href=True):
        rp = RootPath()
        self.blank_oc_item = None
        self.publisher_name = 'Open Context'
        self.base_url = rp.get_baseurl()
        self.http_resp_code = 200
        self.verb = None
        self.valid_verb = None
        self.metadata_prefix = None
        self.metadata_prefix_valid = None
        self.errors = []
        self.root = None
        self.request_xml = None
        self.resumption_token = None
        self.rows = 100
        self.default_sort = 'published--desc'  # default sort of items (Publication date, descending)
        self.requested_set = None
        self.requested_set_valid = None
        self.identifier = None
        self.from_date = None
        self.until_date = None
        self.from_date_solr = None
        self.until_date_solr = None

    def process_request(self, request):
        """ processes a request verb,
            determines the correct
            responses and http response codes
        """
        self.check_validate_verb(request)
        self.check_metadata_prefix(request)
        self.check_resumption_token(request)
        self.check_validate_set(request)
        self.check_identifier(request)
        self.check_from_date(request)
        self.check_until_date(request)
        self.validate_from_until_dates()  # makes sure dates have same granularity
        self.make_xml_root()
        self.make_general_xml()
        self.make_request_xml()
        self.process_verb()
        self.make_error_xml()
        return True

    def check_request_param(self, param, request):
        """ Checks to see if a given
            parameter is in the request
            GET or POST
        """
        output = None
        if request.method == 'GET':
            if param in request.GET:
                output = request.GET[param]
        elif request.method == 'POST':
            if param in request.POST:
                output = request.POST[param]
        return output

    def check_validate_verb(self, request):
        """ Checks and validates the verb in the request """
        self.verb = self.check_request_param('verb',
                                             request)
        if self.verb is not None:
            valid_verbs = ['Identify',
                           'ListMetadataFormats',
                           'ListIdentifiers',
                           'ListRecords',
                           'ListSets',
                           'GetRecord']
            if self.verb in valid_verbs:
                self.valid_verb = True
        if self.valid_verb is not True:
            self.errors.append('badVerb')
        return self.valid_verb

    def check_metadata_prefix(self, request):
        """ Checks to see if a metadata prefix is in a request """
        self.metadata_prefix = self.check_request_param('metadataPrefix',
                                                        request)
        if self.metadata_prefix is not None:
            self.metadata_prefix_valid = False
            for meta_f in self.METADATA_FORMATS:
                if meta_f['prefix'] == self.metadata_prefix:
                    self.metadata_prefix_valid = True
                    break
            if self.metadata_prefix_valid is False:
                self.errors.append('cannotDisseminateFormat')
        return self.metadata_prefix_valid

    def check_validate_set(self, request):
        self.requested_set = self.check_request_param('set',
                                                      request)
        if self.requested_set is not None:
            if self.requested_set in self.BASE_SETS:
                self.requested_set_valid = True
            else:
                self.requested_set_valid = False
                self.errors.append('noRecordsMatch')
        return self.requested_set_valid

    def check_resumption_token(self, request):
        """ Checks to see if a resumption token is in
            the request, and if it is, validate it
            as a JSON object with the correct keys
        """
        r_token = None
        token_str = self.check_request_param('resumptionToken',
                                             request)
        if token_str is not None:
            valid_token = True
            try:
                resumption_token = json.loads(token_str)
            except:
                resumption_token = False
                valid_token = False
            if isinstance(resumption_token, dict):
                # now a quick validation to make sure the keys exist
                req_keys = ['start',
                            'rows',
                            'sort',
                            'published']
                for key in req_keys:
                    if key not in resumption_token:
                        valid_token = False
                        break
            else:
                r_token = False
            if valid_token:
                r_token = resumption_token
            else:
                r_token = False
                self.errors.append('badResumptionToken')
        self.resumption_token = r_token
        return r_token

    def check_identifier(self, request):
        """ Checks and validates the verb in the request """
        self.identifier = self.check_request_param('identifier',
                                                   request)
        return self.identifier

    def check_from_date(self, request):
        """ Checks the for a 'from' (date) parameter
        """
        from_date = self.check_request_param('from',
                                             request)
        if from_date is not None:
            from_solr = self.make_solr_date(from_date)
            if from_solr is not False:
                self.from_date = from_date
                self.from_date_solr = from_solr
            else:
                self.from_date = False
                self.errors.append('badArgument')

    def check_until_date(self, request):
        """ Checks the for a 'until' (date) parameter
        """
        until_date = self.check_request_param('until',
                                              request)
        if until_date is not None:
            until_solr = self.make_solr_date(until_date)
            if until_solr is not False:
                self.until_date = until_date
                self.until_date_solr = until_solr
            else:
                self.until_date = False
                self.errors.append('badArgument')

    def validate_from_until_dates(self):
        """ Checks to make sure the 'from' and
            'until' dates (if they are both requested)
             have the same length (granularity)
        """
        if self.from_date is not None \
           and self.until_date is not None:
            if len(self.from_date) != len(self.until_date):
                self.errors.append('badArgument')
        dt_from = None
        dt_until = None
        if self.from_date_solr is not None:
            from_solr = self.from_date_solr[:19]
            dt_from = datetime.datetime.strptime(from_solr, '%Y-%m-%dT%H:%M:%S')
        if self.until_date_solr is not None:
            until_solr = self.until_date_solr[:19]
            dt_until = datetime.datetime.strptime(until_solr, '%Y-%m-%dT%H:%M:%S')
        if dt_from is not None or dt_until is not None:
            dt_earliest = self.get_cache_earliest_date()
            if dt_from is not None and dt_until is not None:
                if dt_from > dt_until:
                    # from date is greater than or equal to the until date
                    # or the from date is greater than the earliet date
                    # in the manifest
                    self.errors.append('badArgument')
                if dt_from == dt_until:
                    dt_until = dt_from + datetime.timedelta(days=1)
                    self.until_date_solr = dt_until.strftime('%Y-%m-%dT%H:%M:%SZ')
            if dt_until is not None:
                if dt_until < dt_earliest:
                    # until date is less than the earliest publication date
                    # in the manifest
                    self.errors.append('noRecordsMatch')

    def make_solr_date(self, date_str):
        """ Converts a date into a valid date for Solr """
        output = False
        if len(date_str) >= 19:
            date_str = date_str[:19]
            try:
                dt = datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
                output = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            except:
                output = False
        else:
            date_str = date_str[:10]
            try:
                dt = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                output = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            except:
                output = False
        return output

    def process_verb(self):
        """ processes the request for a verb """
        if self.valid_verb:
            # only do this with valid verbs!
            if self.verb == 'Identify':
                self.make_identify_xml()
            elif self.verb == 'ListMetadataFormats':
                self.make_list_metadata_formats_xml()
            elif self.verb == 'ListIdentifiers':
                self.make_list_identifiers_xml()
            elif self.verb == 'ListRecords':
                self.make_list_records_xml()
            elif self.verb == 'ListSets':
                self.make_list_sets_xml()
            elif self.verb == 'GetRecord':
                self.make_get_record_xml()

    def make_get_record_xml(self):
        """ Makes the XML for the GetRecord
            verb
        """
        if len(self.errors) < 1:
            # only bother doing this if we don't have any errors
            if self.identifier is not None\
               and self.metadata_prefix is not None:
                metadata_uris = self.get_metadata_uris()
                if isinstance(metadata_uris, dict):
                    if 'oc-api:has-results' in metadata_uris:
                        if isinstance(metadata_uris['oc-api:has-results'], list):
                            if len(metadata_uris['oc-api:has-results']) > 0:
                                list_recs_xml = etree.SubElement(self.root, 'GetRecord')
                                item = metadata_uris['oc-api:has-results'][0]
                                rec_xml = etree.SubElement(list_recs_xml, 'record')
                                self.make_item_identifier_xml(rec_xml, item)
                                self.make_record_metatata_xml(rec_xml, item)
                            else:
                                if self.requested_set is None:
                                    self.errors.append('idDoesNotExist')
                                else:
                                    self.errors.append('noRecordsMatch')
            else:
                self.errors.append('badArgument')

    def make_list_records_xml(self):
        """ Makes the XML for the ListIdentifiers
            verb
        """
        if len(self.errors) < 1:
            # only bother doing this if we don't have any errors
            if self.metadata_prefix is None \
               and self.resumption_token is not None:
                # default to oai_dc if there's a resumption token but
                # not a metadata_prefix in the request
                self.metadata_prefix = 'oai_dc'
                self.metadata_prefix_valid = True
            if self.metadata_prefix is not None:
                metadata_uris = self.get_metadata_uris()
                if isinstance(metadata_uris, dict):
                    if 'oc-api:has-results' in metadata_uris:
                        if isinstance(metadata_uris['oc-api:has-results'], list):
                            if len(metadata_uris['oc-api:has-results']) > 0:
                                list_recs_xml = etree.SubElement(self.root, 'ListRecords')
                                for item in metadata_uris['oc-api:has-results']:
                                    # make an item header XML
                                    rec_xml = etree.SubElement(list_recs_xml, 'record')
                                    self.make_item_identifier_xml(rec_xml, item)
                                    self.make_record_metatata_xml(rec_xml, item)
                                # now add the new sumption token
                                self.make_resumption_token_xml(self.resumption_token,
                                                               list_recs_xml,
                                                               metadata_uris)
                            else:
                                self.errors.append('noRecordsMatch')
            else:
                self.errors.append('badArgument')

    def make_record_metatata_xml(self, parent_node, item):
        """ makes metadata about a record """
        json_ld = self.get_item_json_ld(item)
        if isinstance(json_ld, dict):
            metadata_xml = etree.SubElement(parent_node, 'metadata')
            if self.metadata_prefix == 'oai_dc':
                self.make_dc_metadata_xml(metadata_xml, json_ld)
            elif self.metadata_prefix == 'oai_datacite':
                self.make_oai_datacite_metadata_xml(metadata_xml, json_ld)
            elif self.metadata_prefix == 'datacite':
                self.make_datacite_metadata_xml(metadata_xml, json_ld)

    def make_dc_metadata_xml(self, parent_node, json_ld):
        """ makes metadata in the dublin core format """
        act_format = self.get_metadata_format_attributes('oai_dc')
        if act_format is not False:
            tcheck = URImanagement.get_uuid_from_oc_uri(json_ld['id'], True)
            if tcheck is False:
                item_type = False
            else:
                item_type = tcheck['item_type']
            dc = 'http://purl.org/dc/elements/1.1/'
            ns = {'dc': dc,
                  'oai_dc': act_format['ns'],
                  'xsi': self.XSI_NS}
            format_xml = etree.SubElement(parent_node,
                                          '{' + act_format['ns'] + '}dc',
                                          nsmap=ns,
                                          attrib={'{' + self.XSI_NS + '}schemaLocation': act_format['schemaLocation']})
            title_xml = etree.SubElement(format_xml, '{' + dc + '}title')
            if 'dc-terms:title' in json_ld:
                title_xml.text = json_ld['dc-terms:title']
            elif 'label' in json_ld:
                title_xml.text = json_ld['label']
            if 'dc-terms:issued' in json_ld:
                dt_date = json_ld['dc-terms:issued']
                date_xml = etree.SubElement(format_xml, '{' + dc + '}date')
                date_xml.text = dt_date
            if 'dc-terms:creator' in json_ld:
                if isinstance(json_ld['dc-terms:creator'], list):
                    for ld_item in json_ld['dc-terms:creator']:
                        act_xml = etree.SubElement(format_xml, '{' + dc + '}creator')
                        if 'label' in ld_item:
                            act_xml.text = ld_item['label']
            if 'dc-terms:contributor' in json_ld:
                if isinstance(json_ld['dc-terms:contributor'], list):
                    for ld_item in json_ld['dc-terms:contributor']:
                        act_xml = etree.SubElement(format_xml, '{' + dc + '}contributor')
                        if 'label' in ld_item:
                            act_xml.text = ld_item['label']
            if 'owl:sameAs' in json_ld:
                if isinstance(json_ld['owl:sameAs'], list):
                    for ld_item in json_ld['owl:sameAs']:
                        act_xml = etree.SubElement(format_xml, '{' + dc + '}identifier')
                        act_xml.text = ld_item['id']
            if 'id' in json_ld:
                act_xml = etree.SubElement(format_xml, '{' + dc + '}identifier')
                act_xml.text = json_ld['id']
            if item_type in self.DATACITE_RESOURCE_TYPES:
                act_rt = self.DATACITE_RESOURCE_TYPES[item_type]
            else:
                act_rt = self.DATACITE_RESOURCE_TYPES['other']
            rt_xml = etree.SubElement(format_xml, '{' + dc + '}type')
            rt_xml.text = act_rt['ResourceTypeGeneral']
            publisher = etree.SubElement(format_xml, '{' + dc + '}publisher')
            publisher.text = self.publisher_name
            if item_type in self.DC_FORMATS:
                format_list = self.DC_FORMATS[item_type]
                if item_type == 'media':
                    if 'oc-gen:has-files' in json_ld:
                        if isinstance(json_ld['oc-gen:has-files'], list):
                            for act_f in json_ld['oc-gen:has-files']:
                                if 'type' in act_f and 'dc-terms:hasFormat' in act_f:
                                    if act_f['type'] == 'oc-gen:fullfile':
                                        mime_uri = act_f['dc-terms:hasFormat']
                                        format_list.append(mime_uri.replace('http://purl.org/NET/mediatypes/',
                                                                            ''))
            else:
                format_list = self.DC_FORMATS['other']
            for mime in format_list:
                act_xml = etree.SubElement(format_xml, '{' + dc + '}format')
                act_xml.text = mime
            subjects_list = []
            if 'category' in json_ld:
                cat = json_ld['category'][0]
                cat_label = self.get_category_label(cat, json_ld)
                if cat_label is not False:
                    subjects_list.append(cat_label)
            if 'dc-terms:subject' in json_ld:
                if isinstance(json_ld['dc-terms:subject'], list):
                    for subj in json_ld['dc-terms:subject']:
                        if 'label' in subj:
                            subjects_list.append(subj['label'])
            if len(subjects_list) > 0:
                for subject in subjects_list:
                    act_xml = etree.SubElement(format_xml, '{' + dc + '}subject')
                    act_xml.text = subject

    def make_oai_datacite_metadata_xml(self, parent_node, json_ld):
        """ makes metadata in the OAI-datacite specification """
        act_format = self.get_metadata_format_attributes('oai_datacite')
        if act_format is not False:
            format_xml = etree.SubElement(parent_node,
                                          'oai_datacite',
                                          nsmap={None: act_format['ns']},
                                          attrib={'{' + self.XSI_NS + '}schemaLocation': act_format['schemaLocation']})
            payload_xml = etree.SubElement(format_xml, 'payload')
            # now the rest is just the datacite specification
            self.make_datacite_metadata_xml(payload_xml, json_ld)

    def make_datacite_metadata_xml(self, parent_node, json_ld):
        """ makes metadata for the datacite specification, which
            is also used in the oai_datacite specification
        """
        tcheck = URImanagement.get_uuid_from_oc_uri(json_ld['id'], True)
        if tcheck is False:
            item_type = False
        else:
            item_type = tcheck['item_type']
        resource_xml = etree.SubElement(parent_node,
                                        'resoure',
                                        nsmap={None: self.DATACITE_RESOURCE['ns']},
                                        attrib={'{' + self.XSI_NS + '}schemaLocation': self.DATACITE_RESOURCE['schemaLocation']})
        identifiers = {}
        if 'id' in json_ld:
            identifiers['URL'] = json_ld['id']
        if 'owl:sameAs' in json_ld:
            if isinstance(json_ld['owl:sameAs'], list):
                for ld_item in json_ld['owl:sameAs']:
                    if 'doi' in ld_item['id']:
                        identifiers['DOI'] = ld_item['id'].replace('http://dx.doi.org/', '')
                    if 'ark' in ld_item['id']:
                        identifiers['ARK'] = ld_item['id'].replace('http://n2t.net/', '')
        if 'DOI' in identifiers:
            act_xml = etree.SubElement(resource_xml,
                                       'identifier',
                                       attrib={'identifierType': 'DOI'})
            act_xml.text = identifiers['DOI']
        elif 'ARK' in identifiers:
            act_xml = etree.SubElement(resource_xml,
                                       'identifier',
                                       attrib={'identifierType': 'ARK'})
            act_xml.text = identifiers['ARK']
        elif 'URL' in identifiers:
            act_xml = etree.SubElement(resource_xml,
                                       'identifier',
                                       attrib={'identifierType': 'URL'})
            act_xml.text = identifiers['URL']
        act_node = etree.SubElement(resource_xml, 'titles')
        dc_title = None
        if 'dc-terms:title' in json_ld:
            act_xml = etree.SubElement(act_node, 'title')
            act_xml.text = json_ld['dc-terms:title']
            dc_title = json_ld['dc-terms:title']
        if 'label' in json_ld:
            if dc_title != json_ld['label']:
                act_xml = etree.SubElement(act_node, 'title')
                act_xml.text = json_ld['label']
        if 'dc-terms:creator' in json_ld:
            if isinstance(json_ld['dc-terms:creator'], list):
                act_node = etree.SubElement(resource_xml, 'creators')
                for ld_item in json_ld['dc-terms:creator']:
                    act_xml = etree.SubElement(act_node, 'creator')
                    if 'label' in ld_item:
                        act_xml.text = ld_item['label']
        if 'dc-terms:contributor' in json_ld:
            if isinstance(json_ld['dc-terms:contributor'], list):
                act_node = etree.SubElement(resource_xml, 'contributors')
                for ld_item in json_ld['dc-terms:contributor']:
                    act_xml = etree.SubElement(act_node, 'contributor')
                    if 'label' in ld_item:
                        act_xml.text = ld_item['label']
        act_node = etree.SubElement(resource_xml, 'dates')
        create_date = time.strftime('%Y-%m-%d')
        if 'dc-terms:issued' in json_ld:
            create_date = json_ld['dc-terms:issued']
            date_xml = etree.SubElement(act_node,
                                        'date',
                                        attrib={'dateType': 'Available'})
            date_xml.text = create_date
        if 'dc-terms:modified' in json_ld:
            mod_date = json_ld['dc-terms:modified']
            date_xml = etree.SubElement(act_node,
                                        'date',
                                        attrib={'dateType': 'Updated'})
            date_xml.text = mod_date
        act_node = etree.SubElement(resource_xml, 'publisher')
        act_node.text = self.publisher_name
        act_node = etree.SubElement(resource_xml, 'publicationYear')
        act_node.text = create_date[:4]  # the year, first 4 characters
        # now add the Datacite resource type
        if item_type in self.DATACITE_RESOURCE_TYPES:
            act_rt = self.DATACITE_RESOURCE_TYPES[item_type]
        else:
            act_rt = self.DATACITE_RESOURCE_TYPES['other']
        rt_xml = etree.SubElement(resource_xml,
                                  'resourceType',
                                  attrib={'resourceTypeGeneral': act_rt['ResourceTypeGeneral']})
        rt_xml.text = act_rt['oc']
        # now add relevant mime-types
        if item_type in self.DC_FORMATS:
            format_list = self.DC_FORMATS[item_type]
            if item_type == 'media':
                if 'oc-gen:has-files' in json_ld:
                    if isinstance(json_ld['oc-gen:has-files'], list):
                        for act_f in json_ld['oc-gen:has-files']:
                            if 'type' in act_f and 'dc-terms:hasFormat' in act_f:
                                if act_f['type'] == 'oc-gen:fullfile':
                                    mime_uri = act_f['dc-terms:hasFormat']
                                    format_list.append(mime_uri.replace('http://purl.org/NET/mediatypes/',
                                                                        ''))
        else:
            format_list = self.DC_FORMATS['other']
        act_node = etree.SubElement(resource_xml, 'formats')
        for mime in format_list:
            act_xml = etree.SubElement(act_node, 'format')
            act_xml.text = mime
        subjects_list = []
        if 'category' in json_ld:
            cat = json_ld['category'][0]
            cat_label = self.get_category_label(cat, json_ld)
            if cat_label is not False:
                subjects_list.append(cat_label)
        if 'dc-terms:subject' in json_ld:
            if isinstance(json_ld['dc-terms:subject'], list):
                for subj in json_ld['dc-terms:subject']:
                    if 'label' in subj:
                        subjects_list.append(subj['label'])
        if len(subjects_list) > 0:
            act_node = etree.SubElement(resource_xml, 'subjects')
            for subject in subjects_list:
                act_xml = etree.SubElement(act_node, 'subject')
                act_xml.text = subject
        if 'dc-terms:isPartOf' in json_ld:
            if isinstance(json_ld['dc-terms:isPartOf'], list):
                for rel in json_ld['dc-terms:isPartOf']:
                    if 'id' in rel:
                        related = rel['id']
                        act_xml = etree.SubElement(resource_xml,
                                                   'RelatedIdentifier',
                                                   attrib={'relatedIdentifierType': 'URL',
                                                           'relationType': 'IsPartOf'})
                        act_xml.text = related

    def make_list_identifiers_xml(self):
        """ Makes the XML for the ListIdentifiers
            verb
        """
        if len(self.errors) < 1:
            # only bother doing this if we don't have any errors
            metadata_uris = self.get_metadata_uris()
            if isinstance(metadata_uris, dict):
                if 'oc-api:has-results' in metadata_uris:
                    if isinstance(metadata_uris['oc-api:has-results'], list):
                        if len(metadata_uris['oc-api:has-results']) > 0:
                            list_ids_xml = etree.SubElement(self.root, 'ListIdentifiers')
                            for item in metadata_uris['oc-api:has-results']:
                                # make an item header XML
                                self.make_item_identifier_xml(list_ids_xml, item)
                            # now add the new sumption token
                            self.make_resumption_token_xml(self.resumption_token,
                                                           list_ids_xml,
                                                           metadata_uris)
                        else:
                            self.errors.append('noRecordsMatch')

    def make_item_identifier_xml(self, parent_node, item):
        """ Makes XML for an item, in with the "header" element
            and attaches this to a parent node
        """
        header = etree.SubElement(parent_node, 'header')
        identifier = etree.SubElement(header, 'identifier')
        date_stamp = etree.SubElement(header, 'datestamp')
        if 'uri' in item:
            identifier.text = item['uri']
            for item_type, item_set_description in self.BASE_SETS.items():
                if item_type in item['uri']:
                    # found the item type, which defines its set
                    set_xml = etree.SubElement(header, 'setSpec')
                    set_xml.text = item_type
                    break
        if 'published' in item:
            date_stamp.text = item['published'][:10]

    def make_resumption_token_xml(self,
                                  r_token,
                                  parent_node_xml,
                                  api_json_obj):
        """ makes the XML for a resumption token """
        if isinstance(api_json_obj, dict):
            now_dt = datetime.datetime.now()
            expiration_dt = now_dt + datetime.timedelta(days=1)
            expiration_date = expiration_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            if 'startIndex' in api_json_obj:
                start_index = api_json_obj['startIndex']
            else:
                start_index = 0
            if 'totalResults' in api_json_obj:
                complete_list_size = api_json_obj['totalResults']
            else:
                complete_list_size = 0
            if isinstance(r_token, dict):
                new_resumption_obj = self.make_update_resumption_object(api_json_obj,
                                                                        r_token)
            else:
                new_resumption_obj = self.make_update_resumption_object(api_json_obj,
                                                                        {})
            if 'response' in new_resumption_obj:
                # reduce clutter in these tokens, remove uneeded keys
                new_resumption_obj.pop('response', None)
            new_resumption_token_text = json.dumps(new_resumption_obj,
                                                   ensure_ascii=False)
            resumption_token = etree.SubElement(parent_node_xml,
                                                'resumptionToken',
                                                expirationDate=str(expiration_date),
                                                completeListSize=str(complete_list_size),
                                                cursor=str(start_index))
            resumption_token.text = new_resumption_token_text

    def make_list_sets_xml(self):
        """ Makes the XML for hte ListSets
            verb
        """
        metadata_facets = self.get_general_summary_facets()
        if isinstance(metadata_facets, dict):
            list_sets_xml = etree.SubElement(self.root, 'ListSets')
            for item_type, item_set_des in self.BASE_SETS.items():
                set_xml = etree.SubElement(list_sets_xml, 'set')
                set_spec = etree.SubElement(set_xml, 'setSpec')
                set_spec.text = item_type
                set_name = etree.SubElement(set_xml, 'setName')
                set_name.text = item_set_des['label']
        else:
            error = etree.SubElement(self.root, 'error')
            error.text = 'Internal Server Error: Failed to get index of needed to generate sets'
            self.http_resp_code = 500

    def make_list_metadata_formats_xml(self):
        """ Makes the XML for the ListMetadataFormats
            verb
        """
        l_m_f = etree.SubElement(self.root, 'ListMetadataFormats')
        for meta_f in self.METADATA_FORMATS:
            meta_xml = etree.SubElement(l_m_f, 'metadataFormat')
            prefix = etree.SubElement(meta_xml, 'metadataPrefix')
            prefix.text = meta_f['prefix']
            schema = etree.SubElement(meta_xml, 'schema')
            schema.text = meta_f['schema']
            meta_ns = etree.SubElement(meta_xml, 'metadataNamespace')
            meta_ns.text = meta_f['ns']

    def make_identify_xml(self):
        """ Makes the XML for the
            Identify verb
        """
        metadata_facets = self.get_general_summary_facets()
        identify = etree.SubElement(self.root, 'Identify')
        name = etree.SubElement(identify, 'repositoryName')
        name.text = settings.DEPLOYED_SITE_NAME
        base_url = etree.SubElement(identify, 'baseURL')
        base_url.text = self.base_url + '/oai/'
        p_v = etree.SubElement(identify, 'protocolVersion')
        p_v.text = '2.0'
        admin_email = etree.SubElement(identify, 'adminEmail')
        admin_email.text = settings.ADMIN_EMAIL
        if isinstance(metadata_facets, dict):
            if 'oai-pmh:earliestDatestamp' in metadata_facets:
                e_d_t = etree.SubElement(identify, 'earliestDatestamp')
                e_d_t.text = metadata_facets['oai-pmh:earliestDatestamp'][:10]
            else:
                error = etree.SubElement(self.root, 'error')
                error.text = 'Internal Server Error: Failed to get earliest time-stamp'
                self.http_resp_code = 500
        deletions = etree.SubElement(identify, 'deletedRecord')
        deletions.text = 'no'
        granularity = etree.SubElement(identify, 'granularity')
        granularity.text = 'YYYY-MM-DD'

    def make_xml_root(self):
        """ makes the Root XML with namespaces for the document """
        if self.root is None:
            self.root = etree.Element('{' + self.OAI_PMH_NS + '}OAI-PMH',
                                      nsmap={None: self.OAI_PMH_NS, 'xsi': self.XSI_NS},
                                      attrib={'{' + self.XSI_NS + '}schemaLocation': self.SL_NS})

    def make_general_xml(self):
        """ makes general xml used for all responses """
        response_date = etree.SubElement(self.root, 'responseDate')
        response_date.text = time.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'

    def make_request_xml(self):
        """ makes the XML for a verb request """
        if self.valid_verb:
            self.request = etree.SubElement(self.root, 'request', verb=self.verb)
        else:
            self.request = etree.SubElement(self.root, 'request')
        if self.metadata_prefix is not None:
            self.request.attrib['metadataPrefix'] = self.metadata_prefix
        self.request.text = self.base_url + '/oai/'

    def make_error_xml(self):
        """ makes an error message for each error noted """
        if len(self.errors) > 0:
            for error in self.errors:
                self.make_error_item_xml(error)

    def make_error_item_xml(self, code):
        """ makes an XML error message """
        error = etree.SubElement(self.root, 'error', code=code)
        if code == 'badVerb':
            error.text = 'Illegal OAI verb'
        elif code == 'cannotDisseminateFormat':
            pass
        elif code == 'badResumptionToken':
            error.text = 'The value of the resumptionToken argument is invalid or expired'
        elif code == 'noRecordsMatch':
            error.text = 'The combination of the values of the from, until, \
                         set, and metadataPrefix arguments results in an empty list.'
        elif code == 'idDoesNotExist':
            error.text = '"' + str(self.identifier) + '" is unknown or illegal in Open Context.'
        elif code == 'badArgument':
            error.text = 'The request includes illegal arguments, missing required argument(s), \
                          repeated argument(s), or values for arguments have an illegal syntax.'

    def make_update_resumption_object(self,
                                      api_json_obj=None,
                                      resumption_obj={}):
        """ makes or update a flow control resumption object
            This is a dict object that
            includes query parameters to pass to an API request.
            The parameters restrict by publication date to allow
            consistent pagination,
            even if new material gets published
        """
        if 'start' not in resumption_obj:
            resumption_obj['start'] = 0
        if 'rows' not in resumption_obj:
            resumption_obj['rows'] = self.rows
        if 'sort' not in resumption_obj:
            resumption_obj['sort'] = self.default_sort
        if isinstance(api_json_obj, dict):
            # this is the first request, without an existing
            # resumption token. So the next one will be for the
            # next page of results
            if 'itemsPerPage' in api_json_obj and \
               'startIndex' in api_json_obj:
                # make the 'start' key at the next page
                resumption_obj['start'] = api_json_obj['startIndex'] + api_json_obj['itemsPerPage']
                resumption_obj['rows'] = api_json_obj['itemsPerPage']
            if 'published' not in resumption_obj:
                if 'oai-pmh:earliestDatestamp' in api_json_obj and \
                   'dcmi:created' in api_json_obj:
                    resumption_obj['published'] = self.add_from_until_date_limits(api_json_obj['oai-pmh:earliestDatestamp'],
                                                                                  api_json_obj['dcmi:created'])
        else:
            # Add date limits if these are requested
            if self.from_date_solr is not None or \
               self.until_date_solr is not None:
                resumption_obj['published'] = self.add_from_until_date_limits(self.from_date_solr,
                                                                              self.until_date_solr)
        return resumption_obj

    def add_from_until_date_limits(self, api_earliest, api_latest):
        """ Adds dates limits request by the client
            in the 'from' and 'until' parameters
        """
        use_earliest = api_earliest
        use_latest = api_latest
        if self.from_date_solr is not None:
            use_earliest = self.from_date_solr
        if self.until_date_solr is not None:
            use_latest = self.until_date_solr
        if use_earliest is None:
            use_earliest = '*'
        if use_latest is None:
            use_latest = '*'
        output = '[' + use_earliest + ' TO ' + use_latest + ']'
        return output

    def get_metadata_format_attributes(self, metadata_prefix):
        """ gets attributes about a given metadata format """
        output = False
        for act_format in self.METADATA_FORMATS:
            if act_format['prefix'] == metadata_prefix:
                output = act_format
                break
        return output

    def output_xml_string(self):
        """ outputs the string of the XML """
        output = etree.tostring(self.root,
                                xml_declaration=True,
                                pretty_print=True,
                                encoding='utf-8')
        return output

    def get_general_summary_facets(self):
        """ gets summary information about
            the facets, metadata
        """
        oc_url = self.base_url + '/search/'
        payload = {'response': 'metadata,facet'}
        payload = self.add_set_params_to_payload(payload)
        cq = CompleteQuery()
        try:
            metadata_facets = cq.get_json_query(payload)
        except:
            metadata_facets = False
            error = etree.SubElement(self.root, 'error')
            error.text = 'Internal Server Error: Failed to get collection metadata summary'
            self.http_resp_code = 500
        return metadata_facets

    def get_metadata_uris(self):
        """ gets metadata and uris
        """
        oc_url = self.base_url + '/search/'
        if isinstance(self.resumption_token, dict):
            # pass the validated resumption token provided in request
            resumption_obj = self.resumption_token
        else:
            # first request, so we're not passing a resumption object
            # but need to make one
            resumption_obj = self.make_update_resumption_object(None,
                                                                {})
        payload = resumption_obj
        payload['response'] = 'metadata,uri-meta'
        payload['attributes'] = 'dc-terms-creator,dc-terms-contributor'
        payload = self.add_set_params_to_payload(payload)
        if self.identifier is not None:
            payload['id'] = str(self.identifier)
        cq = CompleteQuery()
        try:
            metadata_uris = cq.get_json_query(payload)
        except:
            metadata_uris = False
            error = etree.SubElement(self.root, 'error')
            error.text = 'Internal Server Error: Failed to get collection metadata summary'
            self.http_resp_code = 500
        return metadata_uris

    def add_set_params_to_payload(self, payload):
        """ adds extra query parameters to the request
            payload that are needed to filter by
            OAI "set"
        """
        set_params = {}
        if self.requested_set_valid:
            # limit to a valid requested set, using the query
            # params defined for the set
            set_params = self.BASE_SETS[self.requested_set]['params']
        else:
            # request all avalable sets, since there
            # is no requested limit on the set
            item_types = list(self.BASE_SETS.keys())
            set_params['type'] = '||'.join(item_types)
        # now add the set_params to the payload
        for param_key, param_value in set_params.items():
            payload[param_key] = param_value
        return payload

        def get_item_json_ld(self, item):
            """ gets metadata and uris
            """
            output = False
            if 'uri' in item:
                tcheck = URImanagement.get_uuid_from_oc_uri(item['uri'], True)
                if tcheck is False:
                    item_type = False
                else:
                    uuid = tcheck['uuid']
                    item_type = tcheck['item_type']
                    url = self.base_url + '/' + item_type + '/' + uuid
                    header = {'Accept': 'application/json'}
                    try:
                        r = requests.get(url,
                                         headers=header,
                                         timeout=60)
                        r.raise_for_status()
                        output = r.json()
                    except:
                        output = False
            return output

    def get_item_json_ld(self, item):
        """ gets metadata and uris
        """
        output = False
        if 'uri' in item:
            tcheck = URImanagement.get_uuid_from_oc_uri(item['uri'], True)
            if tcheck is False:
                item_type = False
            else:
                uuid = tcheck['uuid']
                item_type = tcheck['item_type']
                ocitem = OCitem()
                ocitem.get_item(uuid)
                if ocitem.manifest is not False:
                    output = ocitem.json_ld
                else:
                    output = False
        return output

    def get_category_label(self, cat, json_ld):
        """ Gets a label for a category by looking in the
            JSON-LD
        """
        output = False
        if '@graph' in json_ld:
            for act_item in json_ld['@graph']:
                if '@id' in act_item:
                    act_id = act_item['@id']
                elif 'id' in act_item:
                    act_id = act_item['id']
                else:
                    act_id = None
                if act_id == cat:
                    if 'label' in act_item:
                        output = act_item['label']
                        break
        return output

    def get_cache_earliest_date(self):
        """ Gets and caches the earliest date
            as a date_time object!
        """
        mc = MemoryCache()
        cache_key = mc.make_cache_key('early_date', 'manifest')
        early_date = mc.get_cache_object(cache_key)
        if early_date is None:
            sum_man = Manifest.objects\
                              .filter(published__gt='2001-01-01')\
                              .aggregate(Min('published'))
            early_date = sum_man['published__min']
            mc.save_cache_object(cache_key, early_date)
        return early_date
