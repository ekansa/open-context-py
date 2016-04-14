import re
import json
import requests
from opencontext_py.libs.isoyears import ISOyears
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
            for col_id_key, pcollection in period_collections.items():
                collection = self.get_collection_metadata(col_id_key,
                                                          pcollection)
                if 'definitions' in pcollection:
                    for p_id_key, period in pcollection['definitions'].items():
                        if 'url' in period:
                            if 'opencontext.org' in period['url']:
                                period_meta = self.get_period_metadata(p_id_key,
                                                                       period)
                                oc_ref = {'collection': collection,
                                          'period-meta':period_meta,
                                          # 'period': period,
                                          'oc-uri': period['url']}
                                oc_refs.append(oc_ref)
        return oc_refs
    
    def get_period_by_uri(self, period_uri):
        """ gets period information by URI
            it is not at all efficient, but it works
            in a simple manner ok for the scale of the
            data
        """
        output = False
        period_collections = self.get_period_collections()
        if isinstance(period_collections, dict):
            # last part of the period URI is the period-ID
            if self.URI_PREFIX in period_uri:
                # full uri
                per_uri_ex = period_uri.split('/')
                p_id_key = per_uri_ex[-1]
            else:
                # assume it is just the identifier, not a full uri
                p_id_key = period_uri
                period_uri = self.URI_PREFIX + period_uri
            for col_id_key, pcollection in period_collections.items():
                collection = self.get_collection_metadata(col_id_key,
                                                          pcollection)
                if 'definitions' in pcollection:
                    if p_id_key in pcollection['definitions']:
                        period = pcollection['definitions'][p_id_key]
                        period_meta = self.get_period_metadata(p_id_key,
                                                               period)
                        output = {'collection': collection,
                                  'period-meta':period_meta,
                                  'period': period}
        return output

    def get_collection_metadata(self, col_id_key, pcollection):
        """ gets some simple metadata about a collection """
        collection = {'id': col_id_key,
                      'uri': self.URI_PREFIX + col_id_key,
                      'label': False}
        if 'source' in pcollection:
            if 'title' in pcollection['source']:
                collection['label'] = pcollection['source']['title']
        return collection
    
    def get_period_metadata(self, p_id_key, period):
        """ gets some simple metadata about a period """
        period_meta = {'id': p_id_key,
                       'uri': self.URI_PREFIX + p_id_key,
                       'label': False,
                       'alt_label': False,
                       'all_labels': [],
                       'coverage': [],
                       'start': self.get_period_numeric_year(period, 'start'),
                       'stop': self.get_period_numeric_year(period, 'stop'),
                       'range': self.make_date_range(period),
                       'label-range': False # label, combined label with time range
                       }
        if 'label' in period:
            period_meta['label'] = period['label']
            period_meta['alt_label'] = period['label']
            period_meta['all_labels'].append(period['label']) 
            t_number = re.sub('[^0-9]', '', period['label'])
            if t_number is None:
                add_range = True
            elif t_number is False:
                add_range = True
            elif len(t_number) < 1:
                add_range = True
            else:
                add_range = False
            if add_range and period_meta['range'] is not False:
                period_meta['label-range'] = period['label'] \
                                             + ' (' + period_meta['range'] + ')'
            else:
                period_meta['label-range'] = period['label']
        if 'localizedLabels' in period:
            for lang_key, label_obj in period['localizedLabels'].items():
                if isinstance(label_obj, str):
                    if lang_key == 'eng-latn':
                        period_meta['alt_label'] =label_obj
                    if label_obj not in period_meta['all_labels']:
                        period_meta['all_labels'].append(label_obj)
                elif isinstance(label_obj, list):
                    if lang_key == 'eng-latn':
                        period_meta['alt_label'] =label_obj[0]
                    for label in label_obj:
                        if label not in period_meta['all_labels']:
                            period_meta['all_labels'].append(label)
        if 'spatialCoverage' in period:
            for cov_item in period['spatialCoverage']:
                period_meta['coverage'].append(cov_item['label'])
        return period_meta
    
    def make_date_range(self, period):
        """ gets a year, if it exists and translates from
            ISO 8601 values to numeric BCE / CE
        """
        output = False
        iso_years = ISOyears()
        start_date = self.get_period_numeric_year(period, 'start')
        if isinstance(start_date, float):
            start_date = int(start_date)
            start_date = iso_years.bce_ce_suffix(start_date)
            output = start_date
            end_date = self.get_period_numeric_year(period, 'stop')
            if isinstance(end_date, float):
                end_date = int(end_date)
                end_date = iso_years.bce_ce_suffix(end_date)
                output += ' - ' + end_date
        # print('Range: ' + output)
        return output
    
    def get_period_numeric_year(self, period, start_stop='start'):
        """ gets a year, if it exists and translates from
            ISO 8601 values to numeric BCE / CE
        """
        output = False
        if start_stop in period:
            act_dict = period[start_stop]
            if 'in' in act_dict:
                act_dict = act_dict['in']
                if 'year' in act_dict:
                    iso_years = ISOyears()
                    output = iso_years.make_float_from_iso(act_dict['year'])
        return output

    def get_period_collections(self):
        """ gets period collections from the periodo data """
        period_collections = False
        if isinstance(self.periodo_data, dict):
            if 'periodCollections' in self.periodo_data:
                period_collections = self.periodo_data['periodCollections']
        return period_collections
    
    def get_period_collection(self, collection_ark):
        """ gets period collections from the periodo data """
        if self.URI_PREFIX in collection_ark:
            collection_ark = collection_ark.replace(self.URI_PREFIX, '')
        period_collection = False
        period_collections = self.get_period_collections()
        if isinstance(period_collections, dict):
            if collection_ark in period_collections:
                period_collection = period_collections[collection_ark]
        return period_collection

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
