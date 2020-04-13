import copy
import pytest
import logging
from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher.searchlinks import SearchLinks

logger = logging.getLogger("tests-unit-logger")

TEST_BASE_URL = '/tests/'

TESTS_MAKE_URL = [
    # Tuples of test cases, with input dicts and expected output strings:
    #
    # (request_dict, expected_html_url),
    #
    ({}, TEST_BASE_URL,),
    (
        {'path': 'foo'}, 
        TEST_BASE_URL + 'foo',
    ),
    (
        {'path': 'foo/bar'}, 
        TEST_BASE_URL + 'foo/bar',
    ),
    (
        # parameters are ordered predictably
        {
            'path': 'foo/bar',
            'start': 0,
            'rows': 20,
        }, 
        TEST_BASE_URL + 'foo/bar?rows=20&start=0',
    ),
    (
        # parameters are ordered predictably
        {
            'path': 'foo/bar',
            'start': 0,
            'rows': 20,
            'prop': ['foo---bar', 'ipsum---lorum',],
        }, 
        TEST_BASE_URL + 'foo/bar?prop=foo---bar&prop=ipsum---lorum&rows=20&start=0',
    ),
]


TESTS_REPLACE_PARAM_VALUE = [
    (   
        {}, 
        'foo', 
        'bar', 
        None, 
        TEST_BASE_URL,
    ),
    (   
        {'path': 'Italy'}, 
        'foo', 
        'bar', 
        None, 
        (TEST_BASE_URL + 'Italy'),
    ),
    (   
        {'path': 'Italy'}, 
        'path', 
        'Italy', 
        None, 
        (TEST_BASE_URL),
    ),
    (   
        {'path': 'Italy'}, 
        'path', 
        None, 
        None, 
        (TEST_BASE_URL),
    ),
    # Case to remove the path, but keep the props.
    (   
        {
            'path': 'Italy',
            'prop': ['foo---bar', 'ipsum---lorum',]
        }, 
        'path', 
        None, 
        None, 
        (TEST_BASE_URL + '?prop=foo---bar&prop=ipsum---lorum'),
    ),
    # Case to replace all the props.
    (   
        {
            'path': 'Italy',
            'prop': ['foo---bar', 'ipsum---lorum',]
        }, 
        'prop', 
        None, 
        'replacing-all-props', 
        (TEST_BASE_URL + 'Italy?prop=replacing-all-props'),
    ),
    # Case to remove the last ---bar item from a prop 
    # hierarchy.
    (   
        {
            'path': 'Italy',
            'prop': ['foo---bar', 'ipsum---lorum',]
        }, 
        'prop', 
        'bar', 
        None, 
        (TEST_BASE_URL + 'Italy?prop=foo&prop=ipsum---lorum'),
    ),
    # Case to replace the last ---bar item from a prop
    # hierarchy with a ---blubbie.
    (   
        {
            'path': 'Italy',
            'prop': ['foo---bar', 'ipsum---lorum',]
        }, 
        'prop', 
        'bar', 
        'blubbie', 
        (TEST_BASE_URL + 'Italy?prop=foo---blubbie&prop=ipsum---lorum'),
    ),
]

def test_make_url_from_request_dict():
    """Tests making URLs from a request dictionary object."""
    for request_dict, expected_html_url in TESTS_MAKE_URL:
        sl = SearchLinks(
            request_dict=copy.deepcopy(request_dict),
            base_search_url=TEST_BASE_URL
        )
        urls = sl.make_urls_from_request_dict(
            base_request_url=TEST_BASE_URL
        )
        assert urls['html'] == expected_html_url


def test_replace_param_value():
    """Tests making replacements on a request dictionary object."""
    for (
            request_dict,
            param,
            match_old_value,
            new_value, 
            expected_html_url
        ) in TESTS_REPLACE_PARAM_VALUE:
        sl = SearchLinks(
            request_dict=copy.deepcopy(request_dict),
            base_search_url=TEST_BASE_URL
        )
        sl.replace_param_value(
            param,
            match_old_value=match_old_value,
            new_value=new_value
        )
        urls = sl.make_urls_from_request_dict(
            base_request_url=TEST_BASE_URL
        )
        assert urls['html'] == expected_html_url