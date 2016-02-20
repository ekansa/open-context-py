import time
import datetime
import json
import requests
from lxml import etree
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement


class OAIpmh():
    """
    Open Archives Initiative, Protocol for Metadata
    Harvesting Methods

    Supports OAI-DC and OAI-Datacite

    OAI-DC example
    <oai_dc:dc xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd">
    <dc:title>Implementation of Axiomatic Language </dc:title>
    <dc:creator>Wilson, Walter W.</dc:creator>
    <dc:publisher>Schloss Dagstuhl - Leibniz-Zentrum fuer Informatik GmbH, Wadern/Saarbruecken, Germany</dc:publisher>
    <dc:date>2011</dc:date>
    <dc:identifier>doi:10.4230/LIPIcs.ICLP.2011.290</dc:identifier>
    <dc:subject>Computer Science</dc:subject>
    <dc:subject>000 Computer science, knowledge, general works</dc:subject>
    <dc:description>Other</dc:description>
    <dc:description>
        This report summarizes a PhD research effort to implement a type of logic programming language called "axiomatic language". Axiomatic language is intended as a specification language, so its implementation involves the transformation of specifications to efficient algorithms. The language is described and the implementation task is discussed.
        </dc:description>
    <dc:contributor>Herbstritt, Marc</dc:contributor>
    <dc:language>eng</dc:language>
    <dc:type>Text</dc:type>
    <dc:type>ConferencePaper</dc:type>
    <dc:format>6 pages</dc:format>
    <dc:format>application/pdf</dc:format>
    <dc:rights>Creative Commons Attribution-NonCommercial-NoDerivs 3.0 Unported license (CC-BY-NC-ND)</dc:rights>
    </oai_dc:dc>

    Datacite example
    <oai_datacite xmlns="http://schema.datacite.org/oai/oai-1.0/" xsi:schemaLocation="http://schema.datacite.org/oai/oai-1.0/ http://schema.datacite.org/oai/oai-1.0/oai.xsd">
<isReferenceQuality>false</isReferenceQuality>
<schemaVersion>2.1</schemaVersion>
<datacentreSymbol>TIB.DAGST</datacentreSymbol>
<payload>
<resource xmlns="http://datacite.org/schema/kernel-2.1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-2.1 http://schema.datacite.org/meta/kernel-2.1/metadata.xsd">
<identifier identifierType="DOI">10.4230/LIPIcs.ICLP.2011.290</identifier>
<creators>
<creator>
<creatorName>Wilson, Walter W.</creatorName>
</creator>
</creators>
<titles>
<title>Implementation of Axiomatic Language </title>
</titles>
<publisher>Schloss Dagstuhl - Leibniz-Zentrum fuer Informatik GmbH, Wadern/Saarbruecken, Germany</publisher>
<publicationYear>2011</publicationYear>
<subjects>
<subject>Computer Science</subject>
<subject subjectScheme="DDC">000 Computer science, knowledge, general works</subject>
</subjects>
<contributors>
<contributor contributorType="Editor">
<contributorName>Herbstritt, Marc</contributorName>
</contributor>
</contributors>
<dates>
<date dateType="Available">2011-06-27</date>
</dates>
<language>eng</language>
<resourceType resourceTypeGeneral="Text">ConferencePaper</resourceType>
<sizes>
<size>6 pages</size>
</sizes>
<formats>…</formats>
<version>1.0</version>
<rights>Creative Commons Attribution-NonCommercial-NoDerivs 3.0 Unported license (CC-BY-NC-ND)</rights>
<descriptions>…</descriptions>
</resource>
</payload>
</oai_datacite>


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
         'label': 'OAI DataCite'}
    ]
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

    def __init__(self, id_href=True):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.http_resp_code = 200
        self.verb = None
        self.valid_verb = None
        self.metadata_prefix = None
        self.metadata_prefix_valid = None
        self.errors = []
        self.root = None
        self.request_xml = None
        self.metadata_facets = None  # object for general metadata for the Identify verb
        self.metadata_uris = None  # object for general metadata and identifiers
        self.resumption_token = None
        self.rows = 100
        self.default_sort = 'published--desc'  # default sort of items (Publication date, descending)

    def process_request(self, request):
        """ processes a request verb,
            determines the correct
            responses and http response codes
        """
        self.check_validate_verb(request)
        self.check_metadata_prefix(request)
        self.check_resumption_token(request)
        self.make_xml_root()
        self.make_general_xml()
        self.make_request_xml()
        self.process_verb()
        self.make_error_xml()
        return True

    def check_validate_verb(self, request):
        """ Checks and validates the verb in the request """
        if 'verb' in request.GET:
            self.verb = request.GET['verb']
            valid_verbs = ['Identify',
                           'ListMetadataFormats',
                           'ListIdentifiers',
                           'ListRecords',
                           'ListSets']
            if self.verb in valid_verbs:
                self.valid_verb = True
        if self.valid_verb is not True:
            self.errors.append('badVerb')
        return self.valid_verb

    def check_metadata_prefix(self, request):
        """ Checks to see if a metadata prefix is in a request """
        if self.metadata_prefix is None and \
           'metadataPrefix' in request.GET:
            self.metadata_prefix = request.GET['metadataPrefix']
            self.metadata_prefix_valid = False
            for meta_f in self.METADATA_FORMATS:
                if meta_f['prefix'] == self.metadata_prefix:
                    self.metadata_prefix_valid = True
                    break
            if self.metadata_prefix_valid is False:
                self.errors.append('cannotDisseminateFormat')
        return self.metadata_prefix_valid

    def check_resumption_token(self, request):
        """ Checks to see if a resumption token is in
            the request, and if it is, validate it
            as a JSON object with the correct keys
        """
        if self.resumption_token is None and \
           'resumptionToken' in request.GET:
            valid_token = True
            token_str = request.GET['resumptionToken']
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
                valid_token = False
            if valid_token:
                self.resumption_token = resumption_token
            else:
                self.resumption_token = False
                self.errors.append('badResumptionToken')

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
                self.rows = 20
                self.make_list_records_xml()

    def make_list_records_xml(self):
        """ Makes the XML for the ListIdentifiers
            verb
        """
        if len(self.errors) < 1:
            # only bother doing this if we don't have any errors
            self.get_metadata_uris()
            if isinstance(self.metadata_uris, dict):
                list_recs_xml = etree.SubElement(self.root, 'ListRecords')
                if 'oc-api:has-results' in self.metadata_uris:
                    if isinstance(self.metadata_uris['oc-api:has-results'], list):
                        for item in self.metadata_uris['oc-api:has-results']:
                            # make an item header XML
                            rec_xml = etree.SubElement(list_recs_xml, 'record')
                            self.make_item_identifier_xml(rec_xml, item)
                            self.make_record_metatata_xml(rec_xml, item)
                # now add the new sumption token
                self.make_resumption_token_xml(list_recs_xml,
                                               self.metadata_uris)

    def make_record_metatata_xml(self, parent_node, item):
        """ makes metadata about a record """
        json_ld = self.get_item_json_ld(item)
        if isinstance(json_ld, dict):
            metadata_xml = etree.SubElement(parent_node, 'metadata')
            if self.metadata_prefix == 'oai_dc':
                self.make_dc_metadata_xml(metadata_xml, json_ld)
            elif self.metadata_prefix == 'oai_datacite':
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
            publisher = etree.SubElement(format_xml, '{' + dc + '}publisher')
            publisher.text = settings.DEPLOYED_SITE_NAME
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

    def make_datacite_metadata_xml(self, parent_node, json_ld):
        """ makes metadata in the datacite specification """
        act_format = self.get_metadata_format_attributes('oai_datacite')
        if act_format is not False:
            format_xml = etree.SubElement(parent_node,
                                          'oai_datacite',
                                          nsmap={None: act_format['ns']},
                                          attrib={'{' + self.XSI_NS + '}schemaLocation': act_format['schemaLocation']})

    def make_list_identifiers_xml(self):
        """ Makes the XML for the ListIdentifiers
            verb
        """
        if len(self.errors) < 1:
            # only bother doing this if we don't have any errors
            self.get_metadata_uris()
            if isinstance(self.metadata_uris, dict):
                list_ids_xml = etree.SubElement(self.root, 'ListIdentifiers')
                if 'oc-api:has-results' in self.metadata_uris:
                    if isinstance(self.metadata_uris['oc-api:has-results'], list):
                        for item in self.metadata_uris['oc-api:has-results']:
                            # make an item header XML
                            self.make_item_identifier_xml(list_ids_xml, item)
                # now add the new sumption token
                self.make_resumption_token_xml(list_ids_xml,
                                               self.metadata_uris)

    def make_item_identifier_xml(self, parent_node, item):
        """ Makes XML for an item, in with the "header" element
            and attaches this to a parent node
        """
        header = etree.SubElement(parent_node, 'header')
        identifier = etree.SubElement(header, 'identifier')
        date_stamp = etree.SubElement(header, 'datestamp')
        if 'uri' in item:
            identifier.text = item['uri']
        if 'published' in item:
            date_stamp.text = item['published']

    def make_resumption_token_xml(self, parent_node_xml, api_json_obj):
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
            if isinstance(self.resumption_token, dict):
                new_resumption_obj = self.make_update_resumption_object(api_json_obj,
                                                                        self.resumption_token)
            else:
                new_resumption_obj = self.make_update_resumption_object(api_json_obj)
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

    def make_identify_xml(self):
        """ Makes the XML for the
            Identify verb
        """
        self.get_general_summary_facets()
        identify = etree.SubElement(self.root, 'Identify')
        name = etree.SubElement(identify, 'repositoryName')
        name.text = settings.DEPLOYED_SITE_NAME
        base_url = etree.SubElement(identify, 'baseURL')
        base_url.text = self.base_url + '/oai'
        p_v = etree.SubElement(identify, 'protocolVersion')
        p_v.text = '2.0'
        admin_email = etree.SubElement(identify, 'adminEmail')
        admin_email.text = settings.ADMIN_EMAIL
        if isinstance(self.metadata_facets, dict):
            if 'oai-pmh:earliestDatestamp' in self.metadata_facets:
                e_d_t = etree.SubElement(identify, 'earliestDatestamp')
                e_d_t.text = self.metadata_facets['oai-pmh:earliestDatestamp']
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
        self.request.text = self.base_url + '/oai'

    def make_error_xml(self):
        """ makes an error message for each error noted """
        if len(self.errors) > 0:
            for error in self.errors:
                self.make_error_item_xml(error)

    def make_error_item_xml(self, code):
        """ makes an XML error message """
        if code == 'badVerb':
            error = etree.SubElement(self.root, 'error', code=code)
            error.text = 'Illegal OAI verb'
        elif code == 'cannotDisseminateFormat':
            error = etree.SubElement(self.root, 'error', code=code)
        elif code == 'badResumptionToken':
            error = etree.SubElement(self.root, 'error', code=code)
            error.text = 'The value of the resumptionToken argument is invalid or expired'

    def make_update_resumption_object(self,
                                      api_json_obj=None,
                                      resumption_obj=LastUpdatedOrderedDict()):
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
                    resumption_obj['published'] = '[' + api_json_obj['oai-pmh:earliestDatestamp']
                    resumption_obj['published'] += ' TO '
                    resumption_obj['published'] += api_json_obj['dcmi:created'] + ']'
        return resumption_obj

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
        if self.metadata_facets is None:
            oc_url = self.base_url + '/search/'
            payload = {'response': 'metadata,facets'}
            header = {'Accept': 'application/json'}
            try:
                r = requests.get(oc_url,
                                 params=payload,
                                 headers=header,
                                 timeout=60)
                r.raise_for_status()
                self.metadata_facets = r.json()
            except:
                self.metadata_facets = False
                error = etree.SubElement(self.root, 'error')
                error.text = 'Internal Server Error: Failed to get collection metadata summary'
                self.http_resp_code = 500
        return self.metadata_facets

    def get_metadata_uris(self):
        """ gets metadata and uris
        """
        if self.metadata_uris is None:
            oc_url = self.base_url + '/search/'
            if isinstance(self.resumption_token, dict):
                # pass the validated resumption token provided in request
                resumption_obj = self.resumption_token
            else:
                # first request, so we're not passing a resumption object
                # but need to make one
                resumption_obj = self.make_update_resumption_object()
            payload = resumption_obj
            payload['response'] = 'metadata,uri-meta'
            payload['attributes'] = 'dc-terms-creator,dc-terms-contributor'
            header = {'Accept': 'application/json'}
            try:
                r = requests.get(oc_url,
                                 params=payload,
                                 headers=header,
                                 timeout=60)
                r.raise_for_status()
                self.metadata_uris = r.json()
            except:
                self.metadata_uris = False
                error = etree.SubElement(self.root, 'error')
                error.text = 'Internal Server Error: Failed to get collection metadata summary'
                self.http_resp_code = 500
        return self.metadata_uris

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
