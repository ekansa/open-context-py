import time
import json
import requests
from lxml import etree
from datetime import datetime
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict


class OAIpmh():
    """
    Open Archives Initiative, Protocol for Metadata
    Harvesting Methods
    """
    OAI_PMH_NS = 'http://www.openarchives.org/OAI/2.0/'
    XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
    SL_NS = 'http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd'
    METADATA_FORMATS = [
        {'prefix': 'oai_dc',
         'schema': 'http://www.openarchives.org/OAI/2.0/oai_dc.xsd',
         'ns': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
         'label': 'OAI Dublin Core'},
        {'prefix': 'oai_datacite',
         'schema': 'http://schema.datacite.org/oai/oai-1.0/oai.xsd',
         'ns': 'http://schema.datacite.org/oai/oai-1.0/',
         'label': 'OAI DataCite'}
    ]

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
        self.metadata_facets = None
        self.cursor = 0
        self.rows = 100

    def process_request(self, request):
        """ processes a request verb,
            determines the correct
            responses and http response codes
        """
        self.check_validate_verb(request)
        self.check_metadata_prefix(request)
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
            if self.verb == 'Identify':
                self.valid_verb = True
            elif self.verb == 'ListMetadataFormats':
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

    def process_verb(self):
        """ processes the request for a verb """
        if self.valid_verb:
            # only do this with valid verbs!
            if self.verb == 'Identify':
                self.make_identify_xml()
            elif self.verb == 'ListMetadataFormats':
                self.make_list_metadata_formats_xml()

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
            self.request.attrib['metadataPredix'] = self.metadata_prefix
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

    def make_resumption_token(self, api_json_obj):
        """ makes a flow controll resumption token """
        # TODO: make an ordered json-dict, then make it a
        # string with published date ranges,
        # startIndex (cursor), and rows
        # including published date range links in the token will
        # allow consistent pagination, even if new material gets published
        pass

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

