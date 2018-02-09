import re
import json
import requests
from time import sleep
from requests.auth import HTTPBasicAuth
from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.ocitems.identifiers.ezid.metaark import metaARK


class EZID():
    """ Interacts with the EZID
        identifier service to make and manage
        persistent identifiers (DOIs, ARKs)
        
from opencontext_py.apps.ocitems.identifiers.ezid.ezid import EZID
ezid = EZID()
ezid.ark_shoulder = EZID.ARK_TEST_SHOULDER
meta = {
   'erc.who': 'Open Context Tester',
   'erc.what': 'My Fake Stuff: Test Minting an ID',
   'erc.when': 2018
}
anvl = ezid.make_anvl_metadata_str(meta)
meta_b = ezid.parse_anvl_str(anvl)
url = 'https://opencontext.org/media/5ffb91c9-18b2-4e61-8cea-470f1049037b'
resp = ezid.mint_identifier(url, meta, 'ark')
    """
    
    EZID_BASE_URL = 'https://ezid.cdlib.org'
    SLEEP_TIME = .5
    ARK_TEST_SHOULDER = 'ark:/99999/fk4'  # default for testing
    DOI_TEST_SHOULDER = 'doi:10.5072/FK2' # default for testing

    def __init__(self):
        self.delay_before_request = self.SLEEP_TIME
        self.username = settings.EZID_USERNAME  # http authentication username
        self.password = settings.EZID_PASSWORD  # http authentication password
        self.ark_shoulder = settings.EZID_ARK_SHOULDER  # shoulder (first part) for minting ARKs
        self.doi_shoulder = settings.EZID_DOI_SHOULDER  # shoulder (first part) for minting DOIs
        self.request_error = False
        self.request_url = False
        self.new_ids = []

    def mint_identifier(self, oc_uri, metadata, id_type='ark'):
        """ mints a stable identifier of a given type, defaulting to ark
        """
        new_id = None
        metadata['_target'] = oc_uri
        anvl = self.make_anvl_metadata_str(metadata)
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        try:
            if id_type == 'doi':
                url = self.EZID_BASE_URL + '/shoulder/' + self.doi_shoulder
            else:
                url = self.EZID_BASE_URL + '/shoulder/' + self.ark_shoulder
            gapi = GeneralAPI()
            headers = gapi.client_headers
            headers['Content-Type'] = 'text/plain; charset=UTF-8'
            headers['Accept'] = 'text/plain'
            headers['_target'] = oc_uri
            r = requests.post(url,
                              auth=(self.username, self.password),
                              timeout=240,
                              data=anvl,
                              headers=headers)
            r.raise_for_status()
            self.request_url = r.url
            resp_txt = r.text
            if 'success:' in r.text:
                text_ex = r.text.split('success:')
                if len(text_ex) < 2:
                    new_id = False
                else:
                    new_id = text_ex[1].strip()
                    new_id_dict = LastUpdatedOrderedDict()
                    new_id_dict['uri'] = oc_uri
                    new_id_dict['id'] = new_id
                    self.new_ids.append(new_id_dict)
        except:
            self.request_url = r.url
            print('Error ' + str(r.text))
            new_id = False
        return new_id

    def make_anvl_metadata_str(self, metadata):
        """ converts a dict of metadata into an ANVL formated
            string
        """
        anvl_lines = []
        for key, value in metadata.items():
            esc_key = self.escape_anvl(key)
            if isinstance(value, list):
                value = '; '.join(value)   # concatenat a list of values
            else:
                value = str(value)
            esc_value = self.escape_anvl(value)
            anvl_line = esc_key + ': ' + esc_value
            anvl_lines.append(anvl_line)
        anvl = '\n'.join(anvl_lines).encode("UTF-8")
        return anvl
        
    def escape_anvl(self, str_val):
        """ makes ANVL safe strings by escaping certain values """
        return re.sub("[%:\r\n]", lambda c: "%%%02X" % ord(c.group(0)), str_val)
    
    def parse_anvl_str(self, anvl):
        """ parse an anvl string into a dictionary object of metadata """
        metadata = LastUpdatedOrderedDict()
        for anvl_line in anvl.decode("UTF-8").splitlines():
            if ':' in anvl_line:
                line_ex = anvl_line.split(':')
                if len(line_ex) > 1:
                    esc_key = line_ex[0].strip()
                    esc_value = line_ex[1].strip()
                    key = self.unescape_anvl(esc_key).strip()
                    value = self.unescape_anvl(esc_value).strip()
                    if len(key) > 0 and len(value) > 0:
                        metadata[key] = value
        return metadata
    
    def unescape_anvl(self, str_val):
        """ unescapes an escaped ANVL string """
        return re.sub("%([0-9A-Fa-f][0-9A-Fa-f])",
                      lambda m: chr(int(m.group(1), 16)), str_val)
        