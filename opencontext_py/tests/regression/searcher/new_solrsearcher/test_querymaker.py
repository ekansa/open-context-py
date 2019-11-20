import pytest
import logging
import random

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

from opencontext_py.apps.searcher.new_solrsearcher import querymaker

logger = logging.getLogger("tests-regression-logger")


TESTS_SPATIAL_CONTEXTS = [
    # Tuples of test cases, with input spatial context path
    # and expected output dicts:
    #
    # (spatial_context, expected_query_dict),
    #
    (
        None,
        {
           'fq':[],
           'facet.field':[SolrDocument.ROOT_CONTEXT_SOLR],
        },
    ),
    (
        'United+States',
        {
           'fq':['root___context_id{a}:united-states{b}'],
           'facet.field':['united_states___context_id'],
        },
    ),
    (
        'United States',
        {
           'fq':['root___context_id{a}:united-states{b}'],
           'facet.field':['united_states___context_id'],
        },
    ),
    (
        'United States/',
        {
           'fq':['root___context_id{a}:united-states{b}'],
           'facet.field':['united_states___context_id'],
        },
    ),
    (
        '/United States',
        {
           'fq':['root___context_id{a}:united-states{b}'],
           'facet.field':['united_states___context_id'],
        },
    ),
    (
        '/United States||',
        {
           'fq':['root___context_id{a}:united-states{b}'],
           'facet.field':['united_states___context_id'],
        },
    ),
    (
        'United States/California',
        {
           'fq':['united_states___context_id{a}:california{b}'],
           'facet.field':['california___context_id'],
        },
    ),
    
    # Test case where Foo Bar are parts of context paths that do
    # not exist
    (
        'United States/California||Foo Bar',
        {
           'fq':['united_states___context_id{a}:california{b}'],
           'facet.field':['california___context_id'],
        },
    ),
    
    # Test case where Foo and Bar are parts of context paths that do
    # not exist
    (
        'United States||Foo-Bar/California||Foo Bar',
        {
           'fq':['united_states___context_id{a}:california{b}'],
           'facet.field':['california___context_id'],
        },
    ),
    (
        'United States/California||Florida',
        {
           'fq':['((united_states___context_id{a}:california{b}) OR (united_states___context_id{a}:florida{b}))'],
           'facet.field':['california___context_id', 'florida___context_id',],
        },
    ),
    
    # The following test case highlights how the solr query uses slugs
    # like "24-poggio-civitate" and "24-civitate-a" as identifiers.
    # Translanding a context path string into a solr query requires
    # use of the database to look up the corresponding slugs assigned
    # to the spatial context (subjects) entities being queried. 
    (
        'Italy/Poggio+Civitate/Civitate+A',
        {
           'fq':['24_poggio_civitate___context_id{a}:24-civitate-a{b}'],
           'facet.field':['24_civitate_a___context_id',],
        },
    ),
]


TESTS_PROJECTS = [
    
    (
        None,
        None,
    ),
    (
        '',
        None,
    ),
    (
        'Foo',
        None,
    ),
    (
        'Murlo||Foo',
        None,
    ),
    (
        '24-murlo',
        {
            'fq': ['((root___project_id{a}:24-murlo{b}) AND (obj_all___project_id{a}:24-murlo{b}))',],
            'facet.field':['24_murlo___project_id',],
        }
    ),
    (
        '24-murlo||foo',
        {
            'fq': ['((root___project_id{a}:24-murlo{b}) AND (obj_all___project_id{a}:24-murlo{b}))',],
            'facet.field':['24_murlo___project_id',],
        }
    ),
    (
        '24-murlo---foo',
        None,
    ),
    (
        'foo---24-murlo',
        None,
    ),
    (
        '52-digital-index-of-north-american-archaeology-dinaa',
        {
            'fq': ['((root___project_id{a}:52-digital-index-of-north-american-archaeology-dinaa{b}) AND (obj_all___project_id{a}:52-digital-index-of-north-american-archaeology-dinaa{b}))',],
            'facet.field':['52_digital_index_of_north_american_archaeology_dinaa___project_id',],
        }
    ),
    # Example of a sub-project
    (
        '52-digital-index-of-north-american-archaeology-linking-si',
        {
            'fq': ['((52_digital_index_of_north_american_archaeology_dinaa___project_id{a}:52-digital-index-of-north-american-archaeology-linking-si{b}) AND (obj_all___project_id{a}:52-digital-index-of-north-american-archaeology-linking-si{b}))',],
            'facet.field':['52_digital_index_of_north_american_archaeology_linking_si___project_id',],
        }
    ),
    (
        '52-digital-index-of-north-american-archaeology-dinaa---52-digital-index-of-north-american-archaeology-linking-si',
        {
            'fq': ['((root___project_id{a}:52-digital-index-of-north-american-archaeology-dinaa{b}) AND (obj_all___project_id{a}:52-digital-index-of-north-american-archaeology-dinaa{b}) AND (52_digital_index_of_north_american_archaeology_dinaa___project_id{a}:52-digital-index-of-north-american-archaeology-linking-si{b}) AND (obj_all___project_id{a}:52-digital-index-of-north-american-archaeology-linking-si{b}))'],
            'facet.field':['52_digital_index_of_north_american_archaeology_linking_si___project_id',],
        }
    ),
]

def set_fq_field_formating():
    if SolrDocument.DO_LEGACY_FQ:
        a = '_fq'
        b = ''
    else:
        a = ''
        b = SolrDocument.SOLR_VALUE_DELIM + '*'
    return a, b

@pytest.mark.django_db
def test_get_spatial_context_query_dict():
    """Tests get_spatial_context_query_dict on a variety of inputs."""
    a, b = set_fq_field_formating()
    
    for spatial_context, exp_dict in TESTS_SPATIAL_CONTEXTS:
        query_dict = querymaker.get_spatial_context_query_dict(
            spatial_context
        )
        assert query_dict['fq'] == [fq.format(a=a, b=b) for fq in exp_dict['fq']]
        assert query_dict['facet.field'] == exp_dict['facet.field']


@pytest.mark.django_db
def test_get_projects_query_dict():
    """Tests get_spatial_context_query_dict on a variety of inputs."""
    # NOTE: This uses the function:
    # querymaker.get_general_hierarchic_paths_query_dict
    # to test queries relating to Open Context projects.
    #
    # TODO: Make more tests for a wider variety of metadata queries.
    #
    a, b = set_fq_field_formating()
    for raw_projects_path, exp_dict in TESTS_PROJECTS:
        query_dict = querymaker.get_general_hierarchic_paths_query_dict(
            raw_projects_path,
            root_field=SolrDocument.ROOT_PROJECT_SOLR,
            field_suffix=SolrDocument.FIELD_SUFFIX_PROJECT,
        )
        if query_dict is None:
            # Case where we don't have a dict response.
            assert query_dict == exp_dict
            continue
        assert query_dict['fq'] == [fq.format(a=a, b=b) for fq in exp_dict['fq']]
        assert query_dict['facet.field'] == exp_dict['facet.field']
