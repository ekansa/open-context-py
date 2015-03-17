import re
import json
import requests
from time import sleep
from django.utils.http import urlquote, quote_plus, urlquote_plus
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI


class CatalLivingArchiveAPI():
    """ Interacts with the Catalhoyuk Living Archive (Stanford) API
        First use-case is to add additional data to supplement
        the Catalhoyuk animal bone data published by Open Context
    """
    REL_PROJECT_URIS = ['http://opencontext.org/projects/02594C48-7497-40D7-11AE-AB942DC513B8',
                        'http://opencontext.org/projects/1B426F7C-99EC-4322-4069-E8DBD927CCF1']
    REL_CATEGORIES = ['oc-gen:cat-exc-unit']
    BASE_JSON_URL = 'http://dh.stanford.edu/catal07/api/unit-json/'
    BASE_HTML_URL = 'http://catalhoyuk.stanford.edu/index.php'

    def __init__(self):
        self.base_json_url = self.BASE_JSON_URL
        self.base_html_url = self.BASE_HTML_URL
        self.request_url = False
        self.request_error = False
        self.relevant = False
        self.has_data = False
        self.props_count = False
        self.properties = False
        self.finds_count = False
        self.finds = False
        self.id_results = False

    def check_relevance(self,
                        category_list,
                        project_list):
        """ Checks to see if category and project lists
            for an item are relevant to Catal
        """
        if isinstance(category_list, list) and\
           isinstance(project_list, list):
            cat_ok = False
            proj_ok = False
            for cat in category_list:
                if cat in self.REL_CATEGORIES:
                    cat_ok = True
            for proj_item in project_list:
                if proj_item['id'] in self.REL_PROJECT_URIS:
                    proj_ok = True
            if cat_ok and proj_ok:
                self.relevant = True
        return self.relevant

    def get_unit(self, unit_label):
        """ get json for a unit """
        if self.relevant:
            unit_id = unit_label.replace('Unit ', '')
            results = False
            json_r = self.get_unit_json(unit_id)
            if isinstance(json_r, dict):
                if 'properties' in json_r:
                    if isinstance(json_r['properties'], dict):
                        self.properties = []
                        for prop_key, value in json_r['properties'].items():
                            if prop_key != 'uid':
                                oc_obj = LastUpdatedOrderedDict()
                                if self.id_results:
                                    oc_obj['id'] = self.BASE_HTML_URL + '#unit-' + str(unit_id)
                                    oc_obj['slug'] = 'unit-' + str(unit_id)
                                    oc_obj['label'] = prop_key + ': ' + str(value)
                                else:
                                    oc_obj['id'] = '#' + urlquote(self.BASE_HTML_URL + '#unit-' + str(unit_id))
                                    oc_obj['xsd:string'] = '<strong>' + prop_key.title() + '</strong>: ' + str(value)
                                self.properties.append(oc_obj)
                        self.props_count = len(self.properties)
                        if self.props_count > 0:
                            self.has_data = True
                if 'features' in json_r:
                    if isinstance(json_r['features'], list):
                        self.finds = []
                        for feature in json_r['features']:
                            find_id = False
                            class_id = False
                            descript = False
                            if 'find_id' in feature:
                                find_id = feature['find_id']
                            if 'class' in feature:
                                class_id = feature['class']
                                class_id = re.sub('([a-z])([A-Z])', '\g<1> \g<2>', class_id)
                            if 'description' in feature:
                                descript = feature['description']
                            if find_id is not False \
                               and class_id is not False \
                               and class_id != 'FaunalBone' \
                               and class_id != 'Faunal Bone':
                                oc_obj = LastUpdatedOrderedDict()
                                if self.id_results:
                                    oc_obj['id'] = self.BASE_HTML_URL + '#find-' + urlquote(find_id)
                                    oc_obj['slug'] = 'find-' + urlquote(find_id)
                                    oc_obj['label'] = find_id
                                    oc_obj['label'] += ' (' + class_id + ')'
                                    if descript is not False \
                                       and descript is not None:
                                        oc_obj['label'] += ', ' + descript
                                else:
                                    oc_obj['id'] = '#' + urlquote(self.BASE_HTML_URL + '#find-' + str(find_id))
                                    oc_obj['xsd:string'] = '<strong>' + find_id + '</strong>'
                                    oc_obj['xsd:string'] += ' (' + class_id + ')'
                                    if descript is not False \
                                       and descript is not None:
                                        oc_obj['xsd:string'] += ', ' + descript
                                self.finds.append(oc_obj)
                        self.finds_count = len(self.finds)
                        if self.finds_count > 0:
                            self.has_data = True
        return self.has_data

    def get_unit_json(self, unit_id):
        """
        gets json data from tDAR in response to a keyword search
        """
        url = self.base_json_url + unit_id
        try:
            gapi = GeneralAPI()
            r = requests.get(url,
                             timeout=240,
                             headers=gapi.client_headers)
            self.request_url = r.url
            r.raise_for_status()
            json_r = r.json()
        except:
            self.request_error = True
            json_r = False
        return json_r
 