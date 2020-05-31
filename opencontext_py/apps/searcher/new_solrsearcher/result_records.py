import copy
import json
import logging

from django.conf import settings
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks
from opencontext_py.apps.searcher.new_solrsearcher import utilities


logger = logging.getLogger(__name__)


PRED_ID_FIELD_SUFFIX = (
    SolrDocument.SOLR_VALUE_DELIM 
    + SolrDocument.FIELD_SUFFIX_PREDICATE
)


def get_record_uuids_from_solr(solr_json):
    """Gets a list of UUIDs from the solr json response"""
    doc_list = utilities.get_dict_path_value(
        configs.RECORD_PATH_KEYS,
        solr_json,
        default=[]
    )
    uuids = [doc.get('uuid') for doc in doc_list if doc.get('uuid')]
    return uuids


def get_specific_attribute_values(solr_doc, parent_dict, specific_predicate_dict):
    """Gets the most specific attribute and value"""
    outputs = []
    slug_prefix = parent_dict['slug'] + SolrDocument.SOLR_VALUE_DELIM
    specific_pred_field_part = (
        SolrDocument.SOLR_VALUE_DELIM
        + specific_predicate_dict['slug']
        + SolrDocument.SOLR_VALUE_DELIM
    )

    for key, solr_vals in solr_doc.items():
        if not key.startswith(slug_prefix):
            # This is not the key we are looking for.
            continue

        if specific_pred_field_part not in key:
            # The current solr field key does not have the 
            # specific pred field part in it, so we're going
            # to make an update so that the new specific
            # predicate dict is the parent dict.
            specific_predicate_dict = parent_dict.copy()

        if not key.endswith(PRED_ID_FIELD_SUFFIX):
            # The values are literals, so return those as a tuple of
            # the predicate for this attribute and the values for this
            # attribute.
            outputs += [(specific_predicate_dict, solr_vals,)]
            continue
    
        val_dicts = []
        for solr_val in solr_vals:
            val_dict = utilities.parse_solr_encoded_entity_str(
                solr_val,
                solr_slug_format=True,
            )
            if not val_dict:
                # Weird. This is not a valid solr entity string.
                continue
            deeper_outputs = get_specific_attribute_values(
                solr_doc=solr_doc, 
                parent_dict=val_dict, 
                specific_predicate_dict=specific_predicate_dict,
            )
            if len(deeper_outputs):
                outputs += deeper_outputs
                continue
            # There are no deeper outputs for this solr_val
            # which means we're at the bottom of the hierarchy, and
            # we should add this value dict to the list of values
            # for this specific_predicate_dict
            val_dicts.append(val_dict)

        if len(val_dicts):
            outputs += [(specific_predicate_dict, val_dicts,)]
    return outputs


def get_predicate_attributes(solr_doc, root_key=SolrDocument.ROOT_PREDICATE_SOLR):
    """Gets nonstandard predicate attributes from a solr doc"""
    attribute_values_tuples = []
    root_preds = solr_doc.get(root_key)
    if not root_preds:
        # No root predicates, so return an empty list.
        return attribute_values_tuples
    for pred in root_preds:
        pred_dict = utilities.parse_solr_encoded_entity_str(
            pred,
            solr_slug_format=True,
        )
        if not pred_dict:
            # Weird. This is not a valid solr entity string.
            continue
        attribute_values_tuples += get_specific_attribute_values(
            solr_doc, 
            parent_dict=pred_dict.copy(), 
            specific_predicate_dict=pred_dict.copy(),
        )
    return attribute_values_tuples


def get_linked_data_attributes(solr_doc):
    """Gets linked data attributes from a solr doc"""
    return get_predicate_attributes(
        solr_doc, 
        root_key=SolrDocument.ROOT_LINK_DATA_SOLR
    )


# ---------------------------------------------------------------------
# Methods to generate results records (individual items, not facets)
# ---------------------------------------------------------------------
class ResultRecords():

    """ Methods to prepare result records """

    def __init__(self, 
        request_dict=None, 
        current_filters_url=None, 
        base_search_url='/search/'
    ):
        rp = RootPath()
        self.base_url = rp.get_baseurl()
        self.base_search_url = base_search_url
        self.request_dict = copy.deepcopy(request_dict)
        if current_filters_url is None:
            current_filters_url = self.base_search_url
        self.current_filters_url = current_filters_url
    

    def get_record_uuids_from_solr(self, solr_json):
        """Gets a list of UUIDs from the solr json response"""
        doc_list = utilities.get_dict_path_value(
            configs.RECORD_PATH_KEYS,
            solr_json,
            default=[]
        )
        uuids = [doc.get('uuid') for doc in doc_list if doc.get('uuid')]
        return uuids
    

