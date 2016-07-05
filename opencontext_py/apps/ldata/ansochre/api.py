import json
import requests
from time import sleep
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.ldata.linkentities.models import LinkEntityGeneration


class ANSochreAPI():
    """ Interacts with the American Numismatic Society (ANS)
        OCHRE API to get JSON-LD for
        useful data about controlled vocabulary concepts
    """
    VOCAB_URI = 'http://numismatics.org/ocre/'
    SLEEP_TIME = .5

    def __init__(self):
        self.request_error = False
        self.delay_before_request = self.SLEEP_TIME
        self.json_data = False
        self.request_url = False

    def get_labels_for_uri(self, uri):
        """ just returns the label, if found """
        output = False
        json_ld = self.get_jsonld_for_uri(uri)
        if json_ld is not False:
            output = {'label': False,
                      'alt_label': False}
            if '@graph' in json_ld:
                for json_data in json_ld['@graph']:
                    if output['label'] is False:
                        if 'skos:prefLabel' in json_data:
                            pref_labels = json_data['skos:prefLabel']
                            output['label'] = self.get_language_label_from_list(pref_labels)
                    if output['alt_label'] is False:
                        if 'http://www.w3.org/2004/02/skos/core#altLabel' in json_data:
                            alt_labels = json_data['http://www.w3.org/2004/02/skos/core#altLabel']
                            output['alt_label'] = self.get_language_label_from_list(alt_labels)
                    if output['label'] is not False:
                        # we got our label, no need to keep looping through
                        break
            if output['alt_label'] is False:
                output['alt_label'] = output['label']
        return output

    def get_language_label_from_list(self, labels_list, language_code='en'):
        """ gets a label from a list of label value items """
        label = False
        if isinstance(labels_list, list):
            for label_item in labels_list:
                if '@language' in label_item and '@value' in label_item:
                    if label_item['@language'] == language_code:
                        # label with the right language code
                        label = label_item['@value'].strip()
                        # print('Got label! ' + label)
                        break
        return label

    def get_jsonld_for_uri(self, uri):
        """
        gets json-ld daa from the OCHRE URI
        """
        le_gen = LinkEntityGeneration()
        uri = le_gen.make_clean_uri(uri)  # strip off any cruft in the URI
        url = uri + '.jsonld'
        self.request_url = url
        if self.delay_before_request > 0:
            # default to sleep BEFORE a request is sent, to
            # give the remote service a break.
            sleep(self.delay_before_request)
        try:
            gapi = GeneralAPI()
            r = requests.get(url,
                             timeout=240,
                             headers=gapi.client_headers)
            r.raise_for_status()
            self.request_url = r.url
            json_r = r.json()
        except:
            json_r = False
        self.json_data = json_r
        return self.json_data
