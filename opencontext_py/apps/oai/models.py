import time
import datetime
import json
import requests
from lxml import etree
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
                           'ListIdentifiers']
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
                            header = etree.SubElement(list_ids_xml, 'header')
                            identifier = etree.SubElement(header, 'identifier')
                            date_stamp = etree.SubElement(header, 'datestamp')
                            if 'uri' in item:
                                identifier.text = item['uri']
                            if 'published' in item:
                                date_stamp.text = item['published']
                # now add the new sumption token
                self.make_resumption_token_xml(list_ids_xml,
                                               self.metadata_uris)

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
