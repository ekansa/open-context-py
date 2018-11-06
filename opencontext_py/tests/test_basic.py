import pytest
import json

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
