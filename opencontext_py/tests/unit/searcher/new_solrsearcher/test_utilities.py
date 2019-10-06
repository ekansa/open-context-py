import pytest
import logging
from opencontext_py.apps.searcher.new_solrsearcher import utilities

logger = logging.getLogger("tests-unit-logger")


TESTS_MUTIPLE_OR_PATHS = [
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


def test_infer_multiple_or_hierarchy_paths():
    """Tests creation of multiple hierarchy paths inferred from OR operators"""
    for raw_path, exp_paths, hierarchy_delim, or_delim in TESTS_MUTIPLE_OR_PATHS:
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
    