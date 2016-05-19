import json
import requests
from time import sleep
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.ldata.linkentities.models import LinkEntityGeneration


class gettyAPI():
    """ Interacts with the Getty SPARQL end point
        to get useful data about controlled vocabulary concepts
    """
    VOCAB_URI = 'http://vocab.getty.edu/aat/'
    SLEEP_TIME = .5

    def __init__(self):
        self.request_error = False
        self.delay_before_request = self.SLEEP_TIME
        self.json_data = False
        self.request_url = False

    def get_labels_for_uri(self, aat_uri):
        """ just returns the label, if found """
        output = False
        json_list = self.get_jsonld_for_aat_uri(aat_uri)
        if json_list is not False:
            if isinstance(json_list, dict):
                json_list = [json_list]
            output = {'label': False,
                      'alt_label': False}
            for json_data in json_list:
                if output['label'] is False:
                    if 'http://www.w3.org/2004/02/skos/core#prefLabel' in json_data:
                        pref_labels = json_data['http://www.w3.org/2004/02/skos/core#prefLabel']
                        output['label'] = self.get_language_label_from_list(pref_labels)
                if output['alt_label'] is False:
                    if 'http://www.w3.org/2004/02/skos/core#altLabel' in json_data:
                        alt_labels = json_data['http://www.w3.org/2004/02/skos/core#altLabel']
                        output['alt_label'] = self.get_language_label_from_list(alt_labels)
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
                        label = label_item['@value']
                        # print('Got label! ' + label)
                        break
        return label

    def get_jsonld_for_aat_uri(self, aat_uri):
        """
        gets json daa from the Getty AAT URI
        """
        le_gen = LinkEntityGeneration()
        aat_uri = le_gen.make_clean_uri(aat_uri)  # strip off any cruft in the URI
        url = aat_uri + '.jsonld'
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
