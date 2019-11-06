import pytest
import json

from django.db import connection
from django.test.utils import setup_test_environment
from django.test.client import (Client, RequestFactory)
from django.conf import settings

from opencontext_py.apps.ocitems.octypes import models
from opencontext_py.apps.searcher.solrsearcher.models import (SolrSearch,  KludgeSolrResponse)
from opencontext_py.apps.searcher.solrsearcher.makejsonld import MakeJsonLd
from opencontext_py.apps.searcher.solrsearcher.requestdict import RequestDict

from mysolr.compat import (urljoin, parse_response)


settings.ALLOWED_HOSTS += ['testserver']

def test_hello():
    """
    a hello world test -- will get rid of once I'm more confident of understanding all these pieces
    """
    assert True

def test_main_page():
    """
    load up the homepage
    """

    client = Client()

    response = client.get('/', follow=True)
    assert response.status_code == 200

def test_solr_output():

    client = Client()

    response = client.get('/search/.json?q=gold&response=solr', follow=True)
    assert response.status_code == 200

def test_q_solr():

    request_dict_json = json.dumps({
      "path": False,
        "q": [
          "gold"
         ],
       "response": [
         "solr"
       ]
     })

    solr_s = SolrSearch()
    solr_s.is_bot = False  # True if bot detected
    solr_s.do_bot_limit = False  # Toggle limits on facets for bots
    solr_s.do_context_paths = True
    solr_s.item_type_limit = False

    if solr_s.solr is not False:
        response = solr_s.search_solr(request_dict_json)
        m_json_ld = MakeJsonLd(request_dict_json)
        m_json_ld.base_search_link = '/search/'
        m_json_ld.request_full_path = '/search/.json?q=gold&response=solr'
        m_json_ld.spatial_context = None
        json_ld = m_json_ld.convert_solr_json(response.raw_content)
        assert json_ld['responseHeader']['QTime'] > 0


def test_compose_query():
    request_dict = {
      "path": False,
        "q": [
          "gold"
         ],
       "response": [
         "solr"
       ]
     }

    solr_s = SolrSearch()
    query = solr_s.compose_query(request_dict)

def test_compose_query_2():

    request_path = '/search/.json?q=gold&response=solr'
    spatial_context = None

    print(solr_call(request_path, spatial_context))
    assert False


def test_ssearch():

    client = Client()

    response = client.get('/subjects-search/.json?response=geo-project', follow=True)
    assert response.status_code == 200

def test_project_context():

    client = Client()
    response = client.get('/contexts/projects/3FAAA477-5572-4B05-8DC1-CA264FE1FC10.json', follow=True)
    assert response.status_code == 200

def test_index_solr_doc():

    from opencontext_py.apps.ocitems.manifest.models import Manifest
    from opencontext_py.apps.indexer.reindex import SolrReIndex
    uuids = ['3FAAA477-5572-4B05-8DC1-CA264FE1FC10']
    sri = SolrReIndex()
    sri.reindex_uuids(uuids)


def test_other_pages():
    """
    a basic way to test functionality of the overall system by loading various pages
    """

    pages_to_test = [
        '/about',
        '/projects-search/',
        '/subjects-search/#1/-10/13/6/any/Google-Satellite',
        '/search/#2/45.0/0.0/6/any/Google-Satellite',
        '/projects/3FAAA477-5572-4B05-8DC1-CA264FE1FC10'
    ]

    client = Client()

    bad_status_codes = {}

    for page in pages_to_test:
        response = client.get(page,follow=True)
        if response.status_code >= 400:
            bad_status_codes[page] = response.status_code

    if bad_status_codes:
        print (bad_status_codes)
        assert False
    else:
        assert True


def test_num_octypes():
    assert models.OCtype.objects.count() > 0

def test_json_feed():
    spatial_context = 'dc-coverage=loc-sh-sh85025408'
    request_dict_json = json.dumps({'dc-coverage': ['loc-sh-sh85025408'],
       'path': False})

    solr_s = SolrSearch()
    solr_s.is_bot = False  # True if bot detected
    solr_s.do_bot_limit = False  # Toggle limits on facets for bots
    solr_s.do_context_paths = False
    solr_s.item_type_limit = 'projects'

    if solr_s.solr is not False:
        response = solr_s.search_solr(request_dict_json)
        m_json_ld = MakeJsonLd(request_dict_json)
        m_json_ld.base_search_link = '/projects-search/'
        m_json_ld.request_full_path = 'http://octest.raymondyee.net/projects-search.json'
        m_json_ld.spatial_context = spatial_context
        json_ld = m_json_ld.convert_solr_json(response.raw_content)
        print (json.dumps(json_ld, indent=4))



def test_projects_feed():
    spatial_context = None
    request_dict_json = json.dumps({'path': False, 'a': ['c']})

    solr_s = SolrSearch()
    solr_s.is_bot = False  # True if bot detected
    solr_s.do_bot_limit = False  # Toggle limits on facets for bots
    solr_s.do_context_paths = False
    solr_s.item_type_limit = 'projects'

    if solr_s.solr is not False:
        response = solr_s.search_solr(request_dict_json)
        m_json_ld = MakeJsonLd(request_dict_json)
        m_json_ld.base_search_link = '/projects-search/'
        m_json_ld.request_full_path = '/projects-search/'
        m_json_ld.spatial_context = spatial_context
        json_ld = m_json_ld.convert_solr_json(response.raw_content)
        assert json_ld['totalResults'] > 0



def my_custom_sql():

    """
    example of a custom sql query to run for testing
    """

    query = """
-- mediafiles associated with San Diego project?
-- now I can get 251
SELECT COUNT(*)
FROM oc_mediafiles AS media
WHERE
  media.project_uuid = '3FAAA477-5572-4B05-8DC1-CA264FE1FC10' AND 
  media.file_type = 'oc-gen:fullfile';
"""
    with connection.cursor() as cursor:
        cursor.execute(query)
        row = cursor.fetchone()

    return row

def test_custom_sql():
    row = my_custom_sql()
    assert row[0] == 251

# model: https://github.com/ekansa/open-context-py/blob/45317e3f236c8657657d5ade4764364becba4411/opencontext_py/apps/searcher/solrsearcher/models.py#

def solr_call(request_path, spatial_context=None):


    rf = RequestFactory()
    request = rf.get(request_path)

    rd = RequestDict()
    request_dict = json.loads(rd.make_request_dict_json(request,
                                                  spatial_context))

    solr_s = SolrSearch()
    query = solr_s.compose_query(request_dict)

    if 'fq' in query:
        if isinstance(query['fq'], list):
            new_fq = []
            for old_fq in query['fq']:
                if isinstance(old_fq, str):
                    new_fq.append(old_fq.replace('(())', ' '))
            query['fq'] = new_fq
    if solr_s.do_bot_limit:
        query['facet.field'] = []
        query['stats.field'] = []

    response = KludgeSolrResponse()
    squery = response.build_request(query)
    url = urljoin(solr_s.solr.base_url, 'select')
    try:
        http_response = solr_s.solr.make_request.post(url,
                                                    data=squery,
                                                    timeout=240)
        response.raw_content = parse_response(http_response.content)
    except Exception as error:
        raise error
    else:
        return {
          'response': response,
          'squery': squery,
          'query': query,
          'url': url
        }

