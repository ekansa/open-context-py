import pytest
import logging
from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.querymaker import (
    get_identifier_query_dict,
    get_object_uri_query_dict,
)

logger = logging.getLogger("tests-unit-logger")


TESTS_IDS = [
    # Tuples of test cases, with input raw_identifiers and expected
    # output query_dict:
    #
    # (raw_identifier, expected_query_dict),
    #
    (None, None,),
    (
        'ark:/28722/k2g44m01s',
        {
            'fq': [
                "((persistent_uri:ark\\:/28722/k2g44m01s) "
                + "OR (persistent_uri:http\\://n2t.net/ark\\:/28722/k2g44m01s) "
                + "OR (persistent_uri:https\\://n2t.net/ark\\:/28722/k2g44m01s))",
            ],
        }
    ),
    (
        'ark:/28722/foo||ark:/28722/bar',
        {
            'fq': [
                "((persistent_uri:ark\\:/28722/foo) " 
                + "OR (persistent_uri:ark\\:/28722/bar) " 
                + "OR (persistent_uri:http\\://n2t.net/ark\\:/28722/foo) "
                + "OR (persistent_uri:http\\://n2t.net/ark\\:/28722/bar) "
                + "OR (persistent_uri:https\\://n2t.net/ark\\:/28722/foo) "
                + "OR (persistent_uri:https\\://n2t.net/ark\\:/28722/bar))",
            ],
        }
    ),
    (
        'slug-foo',
        {
            'fq': [
                "((persistent_uri:slug\\-foo) " 
                + "OR (uuid:slug-foo) " 
                + "OR (slug_type_uri_label:slug_foo___*) " 
                + "OR (persistent_uri:http\\://orcid.org/slug\\-foo) "
                + "OR (persistent_uri:https\\://orcid.org/slug\\-foo) "
                + "OR (persistent_uri:http\\://doi.org/slug\\-foo) "
                + "OR (persistent_uri:https\\://doi.org/slug\\-foo) "
                + "OR (persistent_uri:http\\://dx.doi.org/slug\\-foo) "
                + "OR (persistent_uri:https\\://dx.doi.org/slug\\-foo))",
            ],
        }
    ),
    (
        'http://opencontext.org/persons/foo',
        {
            'fq': [
                "((uuid:foo) "
                + "OR (persistent_uri:http\\://opencontext.org/persons/foo) "
                + "OR (persistent_uri:https\\://opencontext.org/persons/foo) " 
                + "OR (persistent_uri:http\\://opencontext.org/persons/foo/) "
                + "OR (persistent_uri:https\\://opencontext.org/persons/foo/))",
            ],
        }
    ),
]


def get_terms_set_in_filter_query(solr_fq, term=" OR "):
    """Splits a solr filter query on a term"""
    solr_fqs = solr_fq.replace(
        '(', ''
    ).replace(
        ')', ''
    ).split(term)
    return set(solr_fqs)
     

def test_get_identifier_query_dict():
    """Tests making a query dict for document identifiers."""
    for raw_identifier, expected_query_dict in TESTS_IDS:
        query_dict = get_identifier_query_dict(raw_identifier)
        if query_dict is None:
            assert query_dict == expected_query_dict
            continue
        assert get_terms_set_in_filter_query(
            query_dict['fq'][0]
        ) == get_terms_set_in_filter_query(
             expected_query_dict['fq'][0]
        )