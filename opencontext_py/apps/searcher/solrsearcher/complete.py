import json
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.apps.searcher.solrsearcher.models import SolrSearch
from opencontext_py.apps.searcher.solrsearcher.makejsonld import MakeJsonLd
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks
from opencontext_py.apps.searcher.solrsearcher.templating import SearchTemplate
from opencontext_py.apps.searcher.solrsearcher.requestdict import RequestDict
from opencontext_py.apps.searcher.solrsearcher.reconciliation import Reconciliation
from opencontext_py.apps.searcher.solrsearcher.projtemplating import ProjectAugment
from django.views.decorators.cache import cache_control


class CompleteQuery():
    """ Complete Query that to avoid using Requests to
        make a search query
    """
    def __init__(self):
        self.m_cache = MemoryCache()
        self.request_full_path = ''

    def get_json_query(self, request, spatial_context=None):
        """ makes a json query """
        json_ld = False
        request_dict = self.make_request_dict(request,
                                              spatial_context)
        request_dict_json = json.dumps(request_dict,
                                       ensure_ascii=False, indent=4)
        solr_s = SolrSearch()
        if solr_s.solr is not False:
            response = solr_s.search_solr(request_dict_json)
            m_json_ld = MakeJsonLd(request_dict_json)
            m_json_ld.base_search_link = '/search/'
            # share entities already looked up. Saves database queries
            m_json_ld.request_full_path = self.request_full_path
            m_json_ld.spatial_context = spatial_context
            json_ld = m_json_ld.convert_solr_json(response.raw_content)
        return json_ld

    def make_request_dict(self, request, spatial_context=None):
        """ makes a request dict as similar to that
            used by the Search View
        """
        new_request = {}
        if spatial_context is not None:
            new_request['path'] = spatial_context
        for key, key_val in request.items():
            if isinstance(key_val, list):
                new_request[key] = key_val
            else:
                new_request[key] = [str(key_val)]
        return new_request
