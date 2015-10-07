import json
from django.http import HttpResponse, Http404
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from django.template import RequestContext, loader
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.searcher.solrsearcher.models import SolrSearch
from opencontext_py.apps.searcher.solrsearcher.makejsonld import MakeJsonLd
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks
from opencontext_py.apps.searcher.solrsearcher.templating import SearchTemplate
from opencontext_py.apps.searcher.solrsearcher.requestdict import RequestDict
from opencontext_py.apps.searcher.solrsearcher.projtemplating import ProjectAugment
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


# Returns a search interface to browse projects
def index(request):
    spatial_context=None
    rp = RootPath()
    base_url = rp.get_baseurl()
    rd = RequestDict()
    request_dict_json = rd.make_request_dict_json(request,
                                                  spatial_context)
    url = request.get_full_path()
    if 'http://' not in url \
       and 'https://' not in url:
        url = base_url + url
    if '?' in url:
        json_url = url.replace('?', '.json?')
    else:
        json_url = url + '.json'
    # json_url = json_url.replace('/projects', '/sets')  # get more project data
    solr_s = SolrSearch()
    solr_s.do_context_paths = False
    solr_s.item_type_limit = 'projects'
    if solr_s.solr is not False:
        response = solr_s.search_solr(request_dict_json)
        m_json_ld = MakeJsonLd(request_dict_json)
        m_json_ld.base_search_link = '/projects/'
        # share entities already looked up. Saves database queries
        m_json_ld.entities = solr_s.entities
        m_json_ld.request_full_path = request.get_full_path()
        m_json_ld.spatial_context = spatial_context
        json_ld = m_json_ld.convert_solr_json(response.raw_content)
        req_neg = RequestNegotiation('text/html')
        req_neg.supported_types = ['application/json',
                                   'application/ld+json']
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if 'json' in req_neg.use_response_type:
            # content negotiation requested JSON or JSON-LD
            return HttpResponse(json.dumps(json_ld,
                                ensure_ascii=False, indent=4),
                                content_type=req_neg.use_response_type + "; charset=utf8")
        else:
            # now make the JSON-LD into an object suitable for HTML templating
            st = SearchTemplate(json_ld)
            st.process_json_ld()
            p_aug = ProjectAugment(json_ld)
            p_aug.process_json_ld()
            template = loader.get_template('projects/index.html')
            context = RequestContext(request,
                                     {'st': st,
                                      'p_aug': p_aug,
                                      'url': url,
                                      'json_url': json_url,
                                      'base_url': base_url})
            if req_neg.supported:
                return HttpResponse(template.render(context))
            else:
                # client wanted a mimetype we don't support
                return HttpResponse(req_neg.error_message,
                                    content_type=req_neg.use_response_type + "; charset=utf8",
                                    status=415)
    else:
        template = loader.get_template('500.html')
        context = RequestContext(request,
                                 {'error': 'Solr Connection Problem'})
        return HttpResponse(template.render(context), status=503)


# Returns a search interface to browse projects
def index_json(request):
    spatial_context=None
    rp = RootPath()
    base_url = rp.get_baseurl()
    rd = RequestDict()
    request_dict_json = rd.make_request_dict_json(request,
                                                  spatial_context)
    url = request.get_full_path()
    if 'http://' not in url \
       and 'https://' not in url:
        url = base_url + url
    if '?' in url:
        json_url = url.replace('?', '.json?')
    else:
        json_url = url + '.json'
    json_url = json_url.replace('/projects/.json', '')
    solr_s = SolrSearch()
    solr_s.do_context_paths = False
    solr_s.item_type_limit = 'projects'
    if solr_s.solr is not False:
        response = solr_s.search_solr(request_dict_json)
        m_json_ld = MakeJsonLd(request_dict_json)
        m_json_ld.base_search_link = '/projects/'
        # share entities already looked up. Saves database queries
        m_json_ld.entities = solr_s.entities
        m_json_ld.request_full_path = request.get_full_path()
        m_json_ld.spatial_context = spatial_context
        json_ld = m_json_ld.convert_solr_json(response.raw_content)
        req_neg = RequestNegotiation('application/json')
        req_neg.supported_types = ['application/ld+json']
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            # requester wanted a mimetype we DO support
            return HttpResponse(json.dumps(json_ld,
                                ensure_ascii=False, indent=4),
                                content_type=req_neg.use_response_type + "; charset=utf8")
        else:
            # client wanted a mimetype we don't support
            return HttpResponse(req_neg.error_message,
                                status=415)
    else:
        template = loader.get_template('500.html')
        context = RequestContext(request,
                                 {'error': 'Solr Connection Problem'})
        return HttpResponse(template.render(context), status=503)


@cache_control(no_cache=True)
@never_cache
def html_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid, True)
    if(ocitem.manifest is not False):
        rp = RootPath()
        base_url = rp.get_baseurl()
        temp_item = TemplateItem()
        temp_item.read_jsonld_dict(ocitem.json_ld)
        template = loader.get_template('projects/view.html')
        req_neg = RequestNegotiation('text/html')
        req_neg.supported_types = ['application/json',
                                   'application/ld+json']
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            if 'json' in req_neg.use_response_type:
                # content negotiation requested JSON or JSON-LD
                return HttpResponse(json.dumps(ocitem.json_ld,
                                    ensure_ascii=False, indent=4),
                                    content_type=req_neg.use_response_type + "; charset=utf8")
            else:
                context = RequestContext(request,
                                         {'item': temp_item,
                                          'base_url': base_url})
                return HttpResponse(template.render(context))
        else:
                # client wanted a mimetype we don't support
                return HttpResponse(req_neg.error_message,
                                    content_type=req_neg.use_response_type + "; charset=utf8",
                                    status=415)
    else:
        raise Http404


def json_view(request, uuid):
    ocitem = OCitem()
    if 'hashes' in request.GET:
        ocitem.assertion_hashes = True
    ocitem.get_item(uuid, True)
    if(ocitem.manifest is not False):
        req_neg = RequestNegotiation('application/json')
        req_neg.supported_types = ['application/ld+json']
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            json_output = json.dumps(ocitem.json_ld,
                                     indent=4,
                                     ensure_ascii=False)
            return HttpResponse(json_output,
                                content_type=req_neg.use_response_type + "; charset=utf8",)
        else:
            # client wanted a mimetype we don't support
            return HttpResponse(req_neg.error_message,
                                content_type=req_neg.use_response_type + "; charset=utf8",
                                status=415)
    else:
        raise Http404
