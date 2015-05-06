#!/usr/bin/env python
from collections import OrderedDict


class LastUpdatedOrderedDict(OrderedDict):
    """
    Stores items in the order the keys were last added
    """
    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        OrderedDict.__setitem__(self, key, value)

class DCterms():
    """
    Some methods for accessing some commonly used
    Dublin core terms predicates
    """
    DC_META_PREDICATES = {'dc-terms:subject': 'dc_terms_subject___pred_id',
                          'dc-terms:spatial': 'dc_terms_spatial___pred_id',
                          'dc-terms:coverage': 'dc_terms_coverage___pred_id',
                          'dc-terms:temporal': 'dc_terms_temporal___pred_id',
                          'dc-terms:isReferencedBy': 'dc_terms_isreferencedby___pred_id'}
    
    DC_META_FIELDS = {'dc-subject': 'dc_terms_subject___pred_id',
                      'dc-spatial': 'dc_terms_spatial___pred_id',
                      'dc-coverage': 'dc_terms_coverage___pred_id',
                      'dc-temporal': 'dc_terms_temporal___pred_id',
                      'dc-isReferencedBy': 'dc_terms_isreferencedby___pred_id'}
    
    def __init__(self):
        pass
    
    def get_dc_terms_list(self):
        """ returns a list of dc-terms predicates """
        dc_terms = []
        for dc_term_key, dc_solr_key in self.DC_META_PREDICATES.items():
            dc_terms.append(dc_term_key)
        return dc_terms
    
    def get_dc_params_list(self):
        """ returns a list of dc-params (for searches) """
        dc_params = []
        for dc_param_key, dc_solr_key in self.DC_META_FIELDS.items():
            dc_params.append(dc_param_key)
        return dc_params