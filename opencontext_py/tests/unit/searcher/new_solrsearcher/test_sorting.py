import pytest
import logging
from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.sorting import SortingOptions

logger = logging.getLogger("tests-unit-logger")


TESTS_REQUEST_TO_SOLR = [
    # Tuples of test cases, with input dicts and expected output strings:
    #
    # (request_dict, sort value for solr),
    #
    ({}, configs.SOLR_SORT_DEFAULT,),
    ({'sort':[]}, configs.SOLR_SORT_DEFAULT,),
    ({'sort':False}, configs.SOLR_SORT_DEFAULT,),
    
    # Test cases on interest score sorting
    ({'sort':'interest'}, 'interest_score asc, sort_score asc, slug_type_uri_label asc',),
    ({'sort': ['interest']}, 'interest_score asc, sort_score asc, slug_type_uri_label asc',),
    
    # Test cases on item (type, labeling) sorting
    ({'sort': 'item'}, 'slug_type_uri_label asc, interest_score desc',),
    ({'sort': 'item--desc'}, 'slug_type_uri_label desc, interest_score desc',),
    ({'sort': 'item--asc'}, 'slug_type_uri_label asc, interest_score desc',),
    ({'sort': ['item--asc']}, 'slug_type_uri_label asc, interest_score desc',),
    
    # Test cases on multiple criteria sorting
    ({'sort': 'item--asc---interest'}, 'slug_type_uri_label asc, interest_score asc',),
    ({'sort': 'item--asc---interest--desc'}, 'slug_type_uri_label asc, interest_score desc',),
    ({'sort': 'published'}, 'published asc, sort_score asc, slug_type_uri_label asc',),
    ({'sort': 'published--desc'}, 'published desc, sort_score asc, slug_type_uri_label asc',),
    ({'sort': 'published--desc', 'foo': 'bar'}, 'published desc, sort_score asc, slug_type_uri_label asc',),
]


def test_make_solr_sort_param_from_request_dict():
    """Tests translation of client request to sorting for solr query."""
    sort_opts = SortingOptions()
    for request_dict, expected_solr_sort in TESTS_REQUEST_TO_SOLR:
        solr_sort = sort_opts.make_solr_sort_param_from_request_dict(
            request_dict
        )
        assert solr_sort == expected_solr_sort