import json
import requests
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI


class PeriodoAPI():
    """ Interacts with Periodo """
    DEFAULT_DATA_URL = 'http://n2t.net/ark:/99152/p0d.jsonld'
    URI_PREFIX = 'http://n2t.net/ark:/99152/'

    def __init__(self):
        self.data_url = self.DEFAULT_DATA_URL
        self.periodo_data = False

    def get_oc_periods(self):
        """ Makes list of PeriodO entities
            related to Open Context types
        """
        oc_refs = []
        period_collections = self.get_period_collections()
        if isinstance(period_collections, dict):
            for col_key, pcollection in period_collections.items():
                collection_title = False
                if 'source' in pcollection:
                    if 'title' in pcollection['source']:
                        collection_title = pcollection['source']['title']
                if 'definitions' in pcollection:
                    for p_key, period in pcollection['definitions'].items():
                        if 'url' in period:
                            if 'opencontext.org' in period['url']:
                                if 'label' in period:
                                    label = period['label']
                                else:
                                    label = False
                                oc_ref = {'collection_id': col_key,
                                          'collection_uri': self.URI_PREFIX + col_key,
                                          'collection_label': collection_title,
                                          'period_id': p_key,
                                          'period_uri': self.URI_PREFIX + p_key,
                                          'period_label': label,
                                          'oc-uri': period['url']}
                                oc_refs.append(oc_ref)
        return oc_refs
    
    def organize_oc_refs(self, oc_refs):
        """ organizes oc refs into hierarchies """
        if isinstance(oc_refs, list):
            for oc_ref in oc_refs:
                period = self.get_period_by_keys(oc_ref['collection_id'],
                                                 oc_ref['period_id'])
                

    def get_period_by_keys(self, collection_id, period_id):
        """ gets a period by looking up keys """
        period = False
        period_collections = self.get_period_collections()
        if isinstance(period_collections, dict):
            if collection_id in period_collections:
                pcollection = period_collections[collection_id]
                if 'definitions' in pcollection:
                    period_defs = pcollection['definitions']
                    if period_id in period_defs:
                        period = period_defs[period_id]
        return period

    def get_period_collections(self):
        """ gets period collections from the periodo data """
        period_collections = False
        if isinstance(self.periodo_data, dict):
            if 'periodCollections' in self.periodo_data:
                period_collections = self.periodo_data['periodCollections']
        return period_collections
    
    def get_period_collections(self):
        """ gets period collections from the periodo data """
        period_collections = False
        if isinstance(self.periodo_data, dict):
            if 'periodCollections' in self.periodo_data:
                period_collections = self.periodo_data['periodCollections']
        return period_collections

    def get_periodo_data(self):
        """
        gets json-ld data from Periodo
        """
        url = self.data_url
        try:
            gapi = GeneralAPI()
            r = requests.get(url,
                             timeout=240,
                             headers=gapi.client_headers)
            r.raise_for_status()
            json_r = r.json()
        except:
            json_r = False
        self.periodo_data = json_r
        return json_r
