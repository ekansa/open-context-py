import json
from django.conf import settings
from django.http import HttpResponse
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs import viewutilities
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.searcher.solrsearcher.models import SolrSearch
from opencontext_py.apps.searcher.solrsearcher.makejsonld import MakeJsonLd


def index(request, spatial_context=None):
    return HttpResponse("Hello, world. You're at the sets index.")


def html_view(request, spatial_context=None):
    return HttpResponse("Hello, world. You are trying to browse sets.")


def json_view(request, spatial_context=None):

    solr_s = SolrSearch(request, spatial_context)
    response = solr_s.search_solr()
    m_json_ld = MakeJsonLd(request)
    json_ld = m_json_ld.convert_solr_json(response.raw_content)
    return HttpResponse(json.dumps(json_ld,
                        ensure_ascii=False, indent=4),
                        content_type="application/json; charset=utf8")

