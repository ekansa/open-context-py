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

    def __init__(self, id_href=True):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.http_resp_code = 200
        self.verb = False
        self.valid_verb = False
        self.errors = []
        self.root = False
        self.metadata_facets = None

    def process_request(self, request):
        """ processes a request verb,
            determines the correct
            responses and http response codes
        """
        ok = self.check_validate_verb(request)
        self.make_xml_root()
        self.make_general_xml()
        self.make_request_xml()
        self.process_verb()
        return ok

    def check_validate_verb(self, request):
        """ Checks and validates the verb in the request """
        if 'verb' in request.GET:
            self.verb = request.GET['verb']
            if self.verb == 'Identify':
                self.valid_verb = True
        return self.valid_verb

    def process_verb(self):
        """ processes the request for a verb """
        if self.valid_verb:
            # only do this with valid verbs!
            if self.verb == 'Identify':
                self.make_identify_xml()

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
        if self.root is False:
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
            request = etree.SubElement(self.root, 'request', verb=self.verb)
        else:
            request = etree.SubElement(self.root, 'request')
            self.make_error_xml('badVerb')
        request.text = self.base_url + '/oai'

    def make_error_xml(self, code):
        """ makes an XML error message """
        if code == 'badVerb':
            error = etree.SubElement(self.root, 'error', code=code)
            error.text = 'Illegal OAI verb'

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
 