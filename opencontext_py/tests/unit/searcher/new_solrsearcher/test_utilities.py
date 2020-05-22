import pytest
import logging

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities


logger = logging.getLogger("tests-unit-logger")


TESTS_MULTIPLE_OR_PATHS = [
    # Tuples of test cases, with input strings and expected output lists:
    #
    # (raw_path, expected_paths_list, hiearchy_delim, or_delim,),
    #
    (
        'United States/California',
        ['United States/California'],
        '/',
        '||',
    ),
    (
        'Turkey/Domuztepe/I||II||Stray',
        ['Turkey/Domuztepe/I', 'Turkey/Domuztepe/II', 'Turkey/Domuztepe/Stray'],
        '/',
        '||',
    ),
    (
        'foo---bar',
        ['foo---bar'],
        '---',
        '||',
    ),
    (
        'foo---bar||bar',
        ['foo---bar'],
        '---',
        '||',
    ),
    (
        'foo||foo---bar||bar',
        ['foo---bar'],
        '---',
        '||',
    ),
    (
        'foo---bar||bad',
        ['foo---bar', 'foo---bad'],
        '---',
        '||',
    ),
    (
        'foo---bar||bad---super',
        ['foo---bar---super', 'foo---bad---super'],
        '---',
        '||',
    ),
    (
        '---foo---bar||bad---super',
        ['foo---bar---super', 'foo---bad---super'],
        '---',
        '||',
    ),
    (
        '---foo---bar||bad---super---',
        ['foo---bar---super', 'foo---bad---super'],
        '---',
        '||',
    ),
    (
        '---foo---bar||bad---super||',
        ['foo---bar---super', 'foo---bad---super'],
        '---',
        '||',
    ),
]


TESTS_FULLTEXT_TO_SOLR = [
    # Tuples of test cases, with input strings and expected output lists:
    #
    # (raw_search_string, solr_escaped_quoted_search_terms_list),
    #
    ('foo bar', ['"foo"', '"bar"',]),
    ('"foo bar"', ['"foo\\ bar"',]),
    ('"foo bar" foo', ['"foo\\ bar"', '"foo"',]),
    ('"foo bar" foo bar', ['"foo\\ bar"', '"foo"', '"bar"',]),
    ('"foo bar" "foo bar"', ['"foo\\ bar"', '"foo\\ bar"',]),
    ('"foo bar" "sheep-goat"', ['"foo\\ bar"', '"sheep\\-goat"',]),
    ('"foo bar" "sheep/goat"', ['"foo\\ bar"', '"sheep/goat"',]),
]


TESTS_URL_OPTIONS = [
    # Tuples of test cases, with input strings and expected output lists:
    #
    # (raw_term, list_of_url_equivalences),
    (None, None,),
    (1, None,),
    (
        'http://ocls.org', 
        [
            'http://ocls.org',
            'http://ocls.org/', 
            'https://ocls.org',
            'https://ocls.org/',
        ],
    ),
    (
        'https://ocls.org', 
        [
            'http://ocls.org',
            'http://ocls.org/', 
            'https://ocls.org',
            'https://ocls.org/',
        ],
    ),
    (
        'dc-terms:title', 
        [
            'dc-terms:title',
            'http://purl.org/dc/terms/title',
            'http://purl.org/dc/terms/title/',
            'https://purl.org/dc/terms/title',
            'https://purl.org/dc/terms/title/',  
        ],
    ),
    (
        'https://purl.org/dc/terms/temporal', 
        [
            'dc-terms:temporal',
            'http://purl.org/dc/terms/temporal',
            'http://purl.org/dc/terms/temporal/',
            'https://purl.org/dc/terms/temporal',
            'https://purl.org/dc/terms/temporal/',  
        ],
    ),
    (
        'https://purl.org/dc/terms/temporal', 
        [
            'dc-terms:temporal',
            'http://purl.org/dc/terms/temporal',
            'http://purl.org/dc/terms/temporal/',
            'https://purl.org/dc/terms/temporal',
            'https://purl.org/dc/terms/temporal/',  
        ],
    ),
]

TESTS_ITEM_TYPE_KEYS = [
    # Tuple is as follows:
    # (input_key, expected_output,)
    (
        None, None,
    ),
    (
        'foo', None,
    ),
    (
        'subjects', configs.ITEM_TYPE_MAPPINGS['subjects'],
    ),
    (
        'oc-gen-media', configs.ITEM_TYPE_MAPPINGS['media'],
    ),
    (
        'oc-gen:media', configs.ITEM_TYPE_MAPPINGS['media'],
    ),
    (
        'https://opencontext.org/vocabularies/oc-general/media', 
        configs.ITEM_TYPE_MAPPINGS['media'],
    ),
    (
        'http://opencontext.org/vocabularies/oc-general/media', 
        configs.ITEM_TYPE_MAPPINGS['media'],
    ),
    (
        'http://opencontext.org/vocabularies/oc-general/persons/', 
        configs.ITEM_TYPE_MAPPINGS['persons'],
    ),
    (
        'https://opencontext.org/vocabularies/oc-general/persons/', 
        configs.ITEM_TYPE_MAPPINGS['persons'],
    ),
]


# List of tests for to look at the aggregation depth needed to return
# the number of max_groups or less of a list of hierarchic encoded
# string values.
TESTS_AGG_DEPTHS = [
    ( 
        8,  # max_groups
        [
            '01000',
            '01001',
            '01002',
            '01003',
            '01010',
            '01011',
            '01012',
            '01013',
        ],  # list of path strings
        5,  # expected aggregation depth returned
    ),
    ( 
        6, 
        [
            '01000',
            '01001',
            '01002',
            '01003',
            '01010',
            '01011',
            '01012',
            '01013',
        ],
        4,
    ),
    ( 
        2, 
        [
            '01000',
            '01001',
            '01002',
            '01003',
            '01010',
            '01011',
            '01012',
            '01013',
        ],
        4,
    ),
    ( 
        2, 
        [
            '01000',
            '01001',
            '01002',
            '01003',
            '01010',
            '01011',
            '01012',
            '01013',
            '01020',
        ],
        3,
    ),

]

def test_infer_multiple_or_hierarchy_paths():
    """Tests creation of multiple hierarchy paths inferred from OR operators"""
    for raw_path, exp_paths, hierarchy_delim, or_delim in TESTS_MULTIPLE_OR_PATHS:
        paths_list = utilities.infer_multiple_or_hierarchy_paths(
            raw_path,
            hierarchy_delim=hierarchy_delim,
            or_delim=or_delim,
        )
        assert paths_list == exp_paths


def test_prep_string_search_term_list():
    """Tests translation of client request to sorting for solr query."""
    for raw_search_text, expected_solr_list in TESTS_FULLTEXT_TO_SOLR:
        solr_list = utilities.prep_string_search_term_list(
            raw_search_text
        )
        assert solr_list == expected_solr_list


def test_make_uri_equivalence_list():
    """Tests make_uri_equivalence_list function"""
    for raw_term, expected_list in TESTS_URL_OPTIONS:
        uri_list = utilities.make_uri_equivalence_list(
            raw_term
        )
        # The order of the list is not important, 
        # just the contents. So test as equivalent sets.
        if expected_list is None:
            assert uri_list is None
            continue
        assert set(uri_list) == set(expected_list)


def test_get_item_type_dict():
    """Tests get_item_type_dict function"""
    for test_key, expected in TESTS_ITEM_TYPE_KEYS:
        test_result = utilities.get_item_type_dict(
            test_key
        )
        assert test_result == expected


def test_get_aggregation_depth_to_group_paths():
    """Tests get_aggregation_depth_to_group_paths function"""
    for max_groups, paths, expected_depth in TESTS_AGG_DEPTHS:
        test_depth = utilities.get_aggregation_depth_to_group_paths(
            max_groups,
            paths,
        )
        assert test_depth == expected_depth

