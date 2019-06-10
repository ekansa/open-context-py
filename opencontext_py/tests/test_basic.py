import pytest
import json

from django.db import connection
from django.test.utils import setup_test_environment
from django.test.client import Client

from opencontext_py.apps.ocitems.octypes import models
from opencontext_py.apps.searcher.solrsearcher.models import SolrSearch
from opencontext_py.apps.searcher.solrsearcher.makejsonld import MakeJsonLd

def test_hello():
    assert True

def test_main_page():

    client = Client()

    response = client.get('/')
    assert response.status_code == 200

def test_other_pages():

    pages_to_test = [
        '/about',
        '/projects-search/',
        '/subjects-search/#1/-10/13/6/any/Google-Satellite',
        '/search/#2/45.0/0.0/6/any/Google-Satellite',
        '/projects/416A274C-CF88-4471-3E31-93DB825E9E4A'
    ]

    client = Client()

    bad_status_codes = {}

    for page in pages_to_test:
        response = client.get(page)
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
        assert json_ld['totalResults'] == 108



def my_custom_sql():

    query = """
-- mediafiles associated with San Diego project?
-- now I can get 251
SELECT *
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
    print(row)
    assert False


