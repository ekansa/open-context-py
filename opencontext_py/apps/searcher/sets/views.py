import json
from django.conf import settings
from django.http import HttpResponse
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.searcher.solrsearcher.models import SolrSearch
from opencontext_py.apps.searcher.solrsearcher.makejsonld import MakeJsonLd
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks


def index(request, spatial_context=None):
    return HttpResponse("Hello, world. You're at the sets index.")


def html_view(request, spatial_context=None):
    return HttpResponse("Hello, world. You are trying to browse sets.")


def json_view(request, spatial_context=None):
    """ API for searching Open Context """
    new_request = LastUpdatedOrderedDict()
    solr_s = SolrSearch()
    request_dict = solr_s.make_request_obj_dict(request,
                                                spatial_context)
    response = solr_s.search_solr(request_dict)
    m_json_ld = MakeJsonLd(request_dict)
    # share entities already looked up. Saves database queries
    m_json_ld.entities = solr_s.entities
    m_json_ld.request_full_path = request.get_full_path()
    m_json_ld.spatial_context = spatial_context
    json_ld = m_json_ld.convert_solr_json(response.raw_content)
    return HttpResponse(json.dumps(json_ld,
                        ensure_ascii=False, indent=4),
                        content_type="application/json; charset=utf8")

