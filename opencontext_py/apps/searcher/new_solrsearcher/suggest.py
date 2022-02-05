import re

from opencontext_py.apps.indexer import solrdocument_new_schema as SolrDoc
from opencontext_py.apps.indexer import solr_utils

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities

from opencontext_py.libs.solrclient import SolrClient

# ---------------------------------------------------------------------
# This module contains functions for full-text term suggestion
# ---------------------------------------------------------------------

SOLR_REQUEST_SUGGEST_COUNT = 20
SOLR_SUGGEST_MAX = 10


def get_solr_suggest_connection():
    """ Connects to solr """
    args = {
        'search_handler': '/suggest',
    }
    if configs.USE_TEST_SOLR_CONNECTION:
        args['use_test_solr'] = True
    solr_sug = SolrClient(**args).solr
    return solr_sug


def get_raw_solr_suggest(q_term, project_slugs=None):
    """Gets a raw solr suggest response for a q_term
    
    :param str q_term: A search string
    :param list project_slugs: An optional list of slugs
        to use as a context filter on the suggestion
    """
    solr_sug = get_solr_suggest_connection()
    params = {'suggest.count': SOLR_REQUEST_SUGGEST_COUNT}
    if isinstance(project_slugs, list):
        solr_slugs = [(s.replace('-', '_') + '*') for s in project_slugs]
        params['suggest.cfq'] = ' OR '.join(solr_slugs)
    result = solr_sug.search(q_term, **params)
    return result.raw_response


def get_solr_suggests(q_term, project_slugs=None, project_slugs_str=None, highlight=False, limit_count=SOLR_SUGGEST_MAX):
    """Gets a raw solr suggest response for a q_term
    
    :param str q_term: A search string
    :param list project_slugs: An optional list of slugs
        to use as a context filter on the suggestion
    :param str project_slugs_str: An optional string of project slugs
        delimited by the standard OR delimiter.
    :param bool highlight: Make sure suggestions highlight the q_term with a
        <b>...</b> HTML tag highlight
    :param int limit_count: Limit the number of results returned.
    """
    if project_slugs_str:
        project_slugs = project_slugs_str.split(configs.REQUEST_OR_OPERATOR)
    result_json = None
    try:
        result_json = get_raw_solr_suggest(q_term, project_slugs=project_slugs)
    except:
        return None
    if not result_json:
        return None
    path_keys = ['suggest', 'ocsuggester',]
    main_sug_dict = utilities.get_dict_path_value(path_keys, result_json)
    if not main_sug_dict:
        return None
    
    suggestion_list = []
    for _, sug_dict in main_sug_dict.items():
        for term_dict in sug_dict.get('suggestions', []):
            term = term_dict.get('term')
            if not term :
                continue
            if highlight and '<b>' not in term:
                # Make sure our suggest has highlighting.
                # Get the case insensitive match.
                found_q_terms = re.findall(q_term, term, re.IGNORECASE)
                if found_q_terms:      
                    term = re.sub(found_q_terms[0], f'<b>{found_q_terms[0]}</b>', term)
            if term  in suggestion_list:
                continue
            suggestion_list.append(term)
    
    if limit_count is None:
        return suggestion_list
    return suggestion_list[:limit_count]



def get_rebuild_solr_suggest():
    """Gets a raw solr suggest response for a q_term
    
    :param str q_term: A search string
    :param list project_slugs: An optional list of slugs
        to use as a context filter on the suggestion
    """
    solr_sug = get_solr_suggest_connection()
    params = {'suggest.build': 'true'}
    result = solr_sug.search('', **params)
    return result.raw_response