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
           'fq':['root___context_id:united_states___*'],
           'facet.field':['united_states___context_id'],
        },
    ),
    (
        'United States',
        {
           'fq':['root___context_id:united_states___*'],
           'facet.field':['united_states___context_id'],
        },
    ),
    (
        'United States/',
        {
           'fq':['root___context_id:united_states___*'],
           'facet.field':['united_states___context_id'],
        },
    ),
    (
        '/United States',
        {
           'fq':['root___context_id:united_states___*'],
           'facet.field':['united_states___context_id'],
        },
    ),
    (
        '/United States||',
        {
           'fq':['root___context_id:united_states___*'],
           'facet.field':['united_states___context_id'],
        },
    ),
    (
        'United States/California',
        {
           'fq':['united_states___context_id:california___*'],
           'facet.field':['california___context_id'],
        },
    ),
    
    # Test case where Foo Bar are parts of context paths that do
    # not exist
    (
        'United States/California||Foo Bar',
        {
           'fq':['united_states___context_id:california___*'],
           'facet.field':['california___context_id'],
        },
    ),
    
    # Test case where Foo and Bar are parts of context paths that do
    # not exist
    (
        'United States||Foo-Bar/California||Foo Bar',
        {
           'fq':['united_states___context_id:california___*'],
           'facet.field':['california___context_id'],
        },
    ),
    (
        'United States/California||Florida',
        {
           'fq':['((united_states___context_id:california___*) OR (united_states___context_id:florida___*))'],
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
           'fq':['24_poggio_civitate___context_id:24_civitate_a___*'],
           'facet.field':['24_civitate_a___context_id',],
        },
    ),
]

TESTS_NULLS = [
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
        'Foo||Bar',
        None,
    ),
]

TESTS_PROJECTS = TESTS_NULLS + [
    (
        '24-murlo',
        {
            'fq': ['((root___project_id:24_murlo___*) AND (obj_all___project_id:24_murlo___*))',],
            'facet.field':['24_murlo___project_id',],
        }
    ),
    (
        '24-murlo||foo',
        {
            'fq': ['((root___project_id:24_murlo___*) AND (obj_all___project_id:24_murlo___*))',],
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
            'fq': ['((root___project_id:52_digital_index_of_north_american_archaeology_dinaa___*) AND (obj_all___project_id:52_digital_index_of_north_american_archaeology_dinaa___*))',],
            'facet.field':['52_digital_index_of_north_american_archaeology_dinaa___project_id',],
        }
    ),
    # Example of a sub-project
    (
        '52-digital-index-of-north-american-archaeology-linking-si',
        {
            'fq': ['((52_digital_index_of_north_american_archaeology_dinaa___project_id:52_digital_index_of_north_american_archaeology_linking_si___*) AND (obj_all___project_id:52_digital_index_of_north_american_archaeology_linking_si___*))',],
            'facet.field':['52_digital_index_of_north_american_archaeology_linking_si___project_id',],
        }
    ),
    (
        '52-digital-index-of-north-american-archaeology-dinaa---52-digital-index-of-north-american-archaeology-linking-si',
        {
            'fq': ['((root___project_id:52_digital_index_of_north_american_archaeology_dinaa___*) AND (obj_all___project_id:52_digital_index_of_north_american_archaeology_dinaa___*) AND (52_digital_index_of_north_american_archaeology_dinaa___project_id:52_digital_index_of_north_american_archaeology_linking_si___*) AND (obj_all___project_id:52_digital_index_of_north_american_archaeology_linking_si___*))'],
            'facet.field':['52_digital_index_of_north_american_archaeology_linking_si___project_id',],
        }
    ),
]


# Tests for descriptive predicates
TESTS_PREDICATES = TESTS_NULLS + [
    (
        '93-element',
        {
            'fq': ['root___pred_id:93_element___*',],
            'facet.field':['93_element___pred_id',],
        }
    ),
    (
        '24-object-type',
        {
            'fq': ['root___pred_id:24_object_type___*',],
            'facet.field':['24_object_type___pred_id',],
        }
    ),
    (
        # NOTE: '24-textile-related' is a hierarchic type (parent level)
        '24-object-type---24-textile-related',
        {
            'fq': ['((root___pred_id:24_object_type___*) AND (24_object_type___pred_id:24_textile_related___*) AND (obj_all___24_object_type___pred_id:24_textile_related___*))',],
            'facet.field':['24_textile_related___24_object_type___pred_id',],
        }
    ),
    (
        # NOTE: '24-textile-relatedrocchetto' is a hierarchic type 
        # (child level)
        '24-object-type---24-textile-related---24-textile-relatedrocchetto',
        {
            'fq': ['((root___pred_id:24_object_type___*) AND (24_object_type___pred_id:24_textile_related___*) AND (obj_all___24_object_type___pred_id:24_textile_related___*) AND (24_textile_related___24_object_type___pred_id:24_textile_relatedrocchetto___*) AND (obj_all___24_object_type___pred_id:24_textile_relatedrocchetto___*))',],
            'facet.field':['24_textile_relatedrocchetto___24_object_type___pred_id',],
        }
    ),
    (
        # NOTE: '24-textile-relatedspindle-whorl' is a hierarchic type 
        # (child level), but the parent is not in the path.
        '24-object-type---24-textile-relatedspindle-whorl',
        {
            'fq': ['((root___pred_id:24_object_type___*) AND (24_textile_related___24_object_type___pred_id:24_textile_relatedspindle_whorl___*) AND (obj_all___24_object_type___pred_id:24_textile_relatedspindle_whorl___*))',],
            'facet.field':['24_textile_relatedspindle_whorl___24_object_type___pred_id',],
        }
    ),
    (
        '93-m1-length',
        {
            'fq': ['root___pred_id:93_m1_length___*',],
            # NOTE: We don't expect a facet field for 93-m1-length,
            # as it is for literal (double, float) values.
            'facet.field':[],
        }
    ),
    (
        '93-m1-length---[0 TO 100]',
        {
            'fq': ['((root___pred_id:93_m1_length___*) AND (93_m1_length___pred_double:[0 TO 100]))',],
            'facet.field':[],
        }
    ),
    (
        '93-element||93-m1-length',
        {
            'fq': ['((root___pred_id:93_element___*) OR (root___pred_id:93_m1_length___*))',],
            # NOTE: We don't expect a facet field for 93-m1-length,
            # as it is for literal (double, float) values.
            'facet.field':['93_element___pred_id',],
        }
    ),
    (
        '35-sd---35-glcstandard-measurement',
        {
            'fq': ['((root___pred_id:35_sd___*) '
                   + 'AND (35_glc___pred_id:35_glcstandard_measurement___*))',
            ],
            # NOTE: We don't expect a facet field for 35-glcstandard-measurement,
            # as it is for literal (double, float) values.
            'facet.field':[],
        }
    ),
    (
        '35-sd---35-glcstandard-measurement',
        {
            'fq': ['((root___pred_id:35_sd___*) ' 
                   + 'AND (35_glc___pred_id:35_glcstandard_measurement___*))',
            ],
            # NOTE: We don't expect a facet field for 35-glcstandard-measurement,
            # as it is for literal (double, float) values.
            'facet.field':[],
        }
    ),
    (
        '35-sd---35-glcstandard-measurement---[0 TO 100]',
        {
            'fq': ['((root___pred_id:35_sd___*) '
                   + 'AND (35_glc___pred_id:35_glcstandard_measurement___*) '
                   + 'AND (35_glcstandard_measurement___pred_double:[0 TO 100]))',
            ],
            # NOTE: We don't expect a facet field for 35-glcstandard-measurement,
            # as it is for literal (double, float) values.
            'facet.field':[],
        }
    ),
    (
        '93-reference',
        {
            'fq': ['root___pred_id:93_reference___*',],
            # NOTE: We don't expect a facet field for 93-reference,
            # as it is for literal (string) values.
            'facet.field':[],
        }
    ),
    (
        '93-reference---dog',
        {
            'fq': ['((root___pred_id:93_reference___*) '
                   + 'AND (93_reference___pred_string:\"dog\"))',
            ],
            # NOTE: We don't expect a facet field for 93-reference,
            # as it is for literal (string) values.
            'facet.field':[],
        }
    ),
    (
        'biol-term-hastaxonomy',
        {
            # NOTE: This is a linked-data predicate, so the root
            # solr field is ld___pred_id.
            'fq': ['ld___pred_id:biol_term_hastaxonomy___*',],
            'facet.field':['biol_term_hastaxonomy___pred_id'],
        }
    ),
    (
        'biol-term-hastaxonomy---eol-p-7687',
        {
            # NOTE: This is a linked-data predicate, with the entity 
            # eol-p-7687 as a child of entity eol-p-7678
            'fq': ['((ld___pred_id:biol_term_hastaxonomy___*) ' 
                   + 'AND (eol_p_7678___biol_term_hastaxonomy___pred_id:eol_p_7687___*) '
                   + 'AND (obj_all___biol_term_hastaxonomy___pred_id:eol_p_7687___*))',
            ],
            'facet.field':['eol_p_7687___biol_term_hastaxonomy___pred_id'],
        }
    ),
    (
        'oc-zoo-has-anat-id',
        {
            # NOTE: This is a linked-data predicate, so the root
            # solr field is ld___pred_id.
            'fq': ['ld___pred_id:oc_zoo_has_anat_id___*',],
            'facet.field':['oc_zoo_has_anat_id___pred_id'],
        }
    ),
    (
        'oc-zoo-has-anat-id---obo-uberon-0001684',
        {
            # NOTE: This is a linked-data predicate, so the root
            # solr field is ld___pred_id.
            'fq': ['((ld___pred_id:oc_zoo_has_anat_id___*) '
                    + 'AND (oc_zoo_has_anat_id___pred_id:obo_uberon_0001684___*) '
                    + 'AND (obj_all___oc_zoo_has_anat_id___pred_id:obo_uberon_0001684___*))',
            ],
            'facet.field':['obo_uberon_0001684___oc_zoo_has_anat_id___pred_id'],
        }
    ),
]


TESTS_DC_SUBJECTS = TESTS_NULLS + [
    (
        'loc-sh-sh92003545',
        {
            # NOTE: This is a dublin core subjects metadata query for
            # the metadata entity loc-sh-sh92003545. Currently, we do not
            # do much hierarchy modeling of LOC subjects headings, so
            # this test is a bit less interesting.
            'fq': ['dc_terms_subject___pred_id:loc_sh_sh92003545___*',],
            'facet.field':['loc_sh_sh92003545___dc_terms_subject___pred_id'],
        }
    ),
]

@pytest.mark.django_db
def test_get_spatial_context_query_dict():
    """Tests get_spatial_context_query_dict on a variety of inputs."""
    for spatial_context, exp_dict in TESTS_SPATIAL_CONTEXTS:
        query_dict = querymaker.get_spatial_context_query_dict(
            spatial_context
        )
        assert query_dict['fq'] == [fq for fq in exp_dict['fq']]
        assert query_dict['facet.field'] == exp_dict['facet.field']


@pytest.mark.django_db
def test_get_projects_query_dict():
    """Tests get_general_hierarchic_paths_query_dict on project inputs."""
    # NOTE: This uses the function:
    # querymaker.get_general_hierarchic_paths_query_dict
    # to test queries relating to Open Context projects.
    #
    # TODO: Make more tests for a wider variety of metadata queries.
    #
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
        assert query_dict['fq'] == [fq for fq in exp_dict['fq']]
        assert query_dict['facet.field'] == exp_dict['facet.field']


@pytest.mark.django_db
def test_get_predicates_query_dict():
    """Tests get_general_hierarchic_paths_query_dict on predicate
    (attributes, property) inputs."""
    # NOTE: This uses the function:
    # querymaker.get_general_hierarchic_paths_query_dict
    # to test queries relating to Open Context projects.
    #
    for raw_prop_path, exp_dict in TESTS_PREDICATES:
        query_dict = querymaker.get_general_hierarchic_paths_query_dict(
            raw_prop_path,
            root_field=SolrDocument.ROOT_PREDICATE_SOLR,
            field_suffix=SolrDocument.FIELD_SUFFIX_PREDICATE
        )
        if query_dict is None:
            # Case where we don't have a dict response.
            assert query_dict == exp_dict
            continue
        assert query_dict['fq'] == [fq for fq in exp_dict['fq']]
        assert query_dict['facet.field'] == exp_dict['facet.field']


@pytest.mark.django_db
def test_get_dc_subjects_query_dict():
    """Tests get_general_hierarchic_paths_query_dict on dc-subjects
    (metadata entities) inputs."""
    # NOTE: This uses the function:
    # querymaker.get_general_hierarchic_paths_query_dict
    # to test queries relating to Open Context projects.
    #
    for raw_dc_path, exp_dict in TESTS_DC_SUBJECTS:
        query_dict = querymaker.get_general_hierarchic_paths_query_dict(
            raw_dc_path,
            root_field='dc_terms_subject___pred_id',
            obj_all_slug='dc-terms-subject',
            field_suffix=SolrDocument.FIELD_SUFFIX_PREDICATE,
            attribute_field_part='dc_terms_subject___',
        )
        if query_dict is None:
            # Case where we don't have a dict response.
            assert query_dict == exp_dict
            continue
        assert query_dict['fq'] == [fq for fq in exp_dict['fq']]
        assert query_dict['facet.field'] == exp_dict['facet.field']