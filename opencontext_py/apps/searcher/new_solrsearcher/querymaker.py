from django.conf import settings

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities


# ---------------------------------------------------------------------
# This module contains functions translating requests from clients into
# queries to Solr.
#
# NOTE: The functions will typically require database access to get
# required information about entities involved in the search requests.
# Therefore, these functions will require regression testing.
#
# Functions that do not require database access should probably get
# added to the utilities module.
# ---------------------------------------------------------------------




def process_hiearchic_query_path(
    path,
    hierarchy_delim=configs.REQUEST_PROP_HIERARCHY_DELIM
):
    path_term = None
    return path_term 


def process_hiearchic_query(
    raw_path,
    hierarchy_delim=configs.REQUEST_PROP_HIERARCHY_DELIM,
    or_delim=configs.REQUEST_OR_OPERATOR,
):
    """Process a raw_path request to formulate a solr query"""
    paths_list = utilities.infer_multiple_or_hierarchy_paths(
        raw_path,
        hierarchy_delim=hierarchy_delim,
        or_delim=or_delim,
    )
    path_terms = []
    for path in paths_list:
        path_term = process_hiearchic_query_path(
            path,
            hierarchy_delim=hierarchy_delim
        )
        path_terms.append(path_term)
    return utilities.join_solr_query_terms(path_terms, operator='OR')
    
    