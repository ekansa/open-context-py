import pytest
import logging
from opencontext_py.apps.searcher.new_solrsearcher import utilities

logger = logging.getLogger("tests-unit-logger")


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


def test_prep_string_search_term_list():
    """Tests translation of client request to sorting for solr query."""
    for raw_search_text, expected_solr_list in TESTS_FULLTEXT_TO_SOLR:
        solr_list = utilities.prep_string_search_term_list(
            raw_search_text
        )
        assert solr_list == expected_solr_list