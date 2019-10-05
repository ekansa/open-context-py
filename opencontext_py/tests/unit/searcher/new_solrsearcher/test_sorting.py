import pytest
import logging
from opencontext_py.apps.searcher.new_solrsearcher.sorting import SortingOptions

logger = logging.getLogger("tests-unit-logger")


TESTS_REQUEST_TO_SOLR = [
    # Tuples of test cases, with input dicts and expected output strings:
    #
    # (request_dict, sort value for solr),
    #
    ({}, SortingOptions.DEFAULT_SOLR_SORT,),
    ({'sort':[]}, SortingOptions.DEFAULT_SOLR_SORT,),
    ({'sort':False}, SortingOptions.DEFAULT_SOLR_SORT,),
    
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
]


def test_make_solr_sort_param_from_request_dict():
    """Tests translation of client request to sorting for solr query."""
    sort_opts = SortingOptions()
    for input_request_dict, output_expected_solr in TESTS_REQUEST_TO_SOLR:
        output = sort_opts.make_solr_sort_param_from_request_dict(
            input_request_dict
        )
        assert output == output_expected_solr