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



def get_record_uuids_from_solr(solr_json):
    """Gets a list of UUIDs from the solr json response"""
    doc_list = utilities.get_dict_path_value(
        configs.RECORD_PATH_KEYS,
        solr_json,
        default=[]
    )
    uuids = [doc.get('uuid') for doc in doc_list if doc.get('uuid')]
    return uuids


def get_non_standard_attributes(solr_doc):
    """Gets nonstandard solr attributes from a solr doc"""
    root_preds = solr_doc.get(SolrDocument.ROOT_PREDICATE_SOLR)
    if not root_preds:
        # No root predicates, so return an empty list.
        return []


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
    

