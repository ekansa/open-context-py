import json
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponse, Http404
from django.template import RequestContext, loader
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.searcher.solrsearcher.models import SolrSearch
from opencontext_py.apps.searcher.solrsearcher.makejsonld import MakeJsonLd
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks
from opencontext_py.apps.searcher.solrsearcher.templating import SearchTemplate
from opencontext_py.apps.searcher.solrsearcher.requestdict import RequestDict
from opencontext_py.apps.searcher.solrsearcher.reconciliation import Reconciliation
from opencontext_py.apps.searcher.solrsearcher.projtemplating import ProjectAugment
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


def index(request, spatial_context=None):
    return HttpResponse("Hello, world. You're at the search index.")


def sets_view(request, spatial_context=''):
    """ redirects requests from the legacy site 'sets'
        to the subjects-search view

        We can add URL parameter mappings to this later
        so that old url parameters can be mapped to the
        current parameters
    """
    url = request.get_full_path()
    new_url = url.replace('/sets/', '/subjects-search/')
    param_suffix = ''
    if '?' in url:
        url_ex = url.split('?')
        param_suffix = '?' + url_ex[1]
    return redirect(new_url, permanent=True)


def lightbox_view(request, spatial_context=''):
    """ redirects requests from the legacy site 'lightbox'
        to the media-search view

        We can add URL parameter mappings to this later
        so that old url parameters can be mapped to the
        current parameters
    """
    url = request.get_full_path()
    new_url = url.replace('/lightbox/', '/media-search/')
    param_suffix = ''
    if '?' in url:
        url_ex = url.split('?')
        param_suffix = '?' + url_ex[1]
    return redirect(new_url, permanent=True)


# @cache_control(no_cache=True)
# @never_cache
def html_view(request, spatial_context=None):
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
    solr_s = SolrSearch()
    if solr_s.solr is not False:
        response = solr_s.search_solr(request_dict_json)
        m_json_ld = MakeJsonLd(request_dict_json)
        m_json_ld.base_search_link = '/search/'
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
            recon_obj = Reconciliation()
            json_ld = recon_obj.process(request.GET,
                                        json_ld)
            return HttpResponse(json.dumps(json_ld,
                                ensure_ascii=False, indent=4),
                                content_type=req_neg.use_response_type + "; charset=utf8")
        else:
            # now make the JSON-LD into an object suitable for HTML templating
            st = SearchTemplate(json_ld)
            st.process_json_ld()
            template = loader.get_template('search/view.html')
            context = RequestContext(request,
                                     {'st': st,
                                      'item_type': '*',
                                      'base_search_link': m_json_ld.base_search_link,
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


def json_view(request, spatial_context=None):
    """ API for searching Open Context """
    rd = RequestDict()
    request_dict_json = rd.make_request_dict_json(request,
                                                  spatial_context)
    solr_s = SolrSearch()
    if solr_s.solr is not False:
        response = solr_s.search_solr(request_dict_json)
        m_json_ld = MakeJsonLd(request_dict_json)
        m_json_ld.base_search_link = '/search/'
        # share entities already looked up. Saves database queries
        m_json_ld.entities = solr_s.entities
        m_json_ld.request_full_path = request.get_full_path()
        m_json_ld.spatial_context = spatial_context
        json_ld = m_json_ld.convert_solr_json(response.raw_content)
        req_neg = RequestNegotiation('application/json')
        req_neg.supported_types = ['application/ld+json']
        recon_obj = Reconciliation()
        json_ld = recon_obj.process(request.GET,
                                    json_ld)
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            # requester wanted a mimetype we DO support
            if 'callback' in request.GET:
                funct = request.GET['callback']
                json_str = json.dumps(json_ld,
                                      ensure_ascii=False,
                                      indent=4)
                return HttpResponse(funct + '(' + json_str + ');',
                                    content_type='application/javascript' + "; charset=utf8")
            else:
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


def subjects_html_view(request, spatial_context=None):
    """ returns HTML representation of subjects search
    """
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
    solr_s = SolrSearch()
    solr_s.item_type_limit = 'subjects'
    if solr_s.solr is not False:
        response = solr_s.search_solr(request_dict_json)
        m_json_ld = MakeJsonLd(request_dict_json)
        m_json_ld.base_search_link = '/subjects-search/'
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
            recon_obj = Reconciliation()
            json_ld = recon_obj.process(request.GET,
                                        json_ld)
            return HttpResponse(json.dumps(json_ld,
                                ensure_ascii=False, indent=4),
                                content_type=req_neg.use_response_type + "; charset=utf8")
        else:
            # now make the JSON-LD into an object suitable for HTML templating
            st = SearchTemplate(json_ld)
            st.process_json_ld()
            template = loader.get_template('search/view.html')
            context = RequestContext(request,
                                     {'st': st,
                                      'item_type': 'subjects',
                                      'base_search_link': m_json_ld.base_search_link,
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


def subjects_json_view(request, spatial_context=None):
    """ API for searching Open Context, subjects only """
    rd = RequestDict()
    request_dict_json = rd.make_request_dict_json(request,
                                                  spatial_context)
    solr_s = SolrSearch()
    solr_s.item_type_limit = 'subjects'
    if solr_s.solr is not False:
        response = solr_s.search_solr(request_dict_json)
        m_json_ld = MakeJsonLd(request_dict_json)
        m_json_ld.base_search_link = '/subjects-search/'
        # share entities already looked up. Saves database queries
        m_json_ld.entities = solr_s.entities
        m_json_ld.request_full_path = request.get_full_path()
        m_json_ld.spatial_context = spatial_context
        json_ld = m_json_ld.convert_solr_json(response.raw_content)
        req_neg = RequestNegotiation('application/json')
        req_neg.supported_types = ['application/ld+json']
        recon_obj = Reconciliation()
        json_ld = recon_obj.process(request.GET,
                                    json_ld)
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            # requester wanted a mimetype we DO support
            if 'callback' in request.GET:
                funct = request.GET['callback']
                json_str = json.dumps(json_ld,
                                      ensure_ascii=False,
                                      indent=4)
                return HttpResponse(funct + '(' + json_str + ');',
                                    content_type='application/javascript' + "; charset=utf8")
            else:
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


# @cache_control(no_cache=True)
# @never_cache
def media_html_view(request, spatial_context=None):
    """ returns HTML representation of media search
    """
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
    solr_s = SolrSearch()
    solr_s.item_type_limit = 'media'
    if solr_s.solr is not False:
        response = solr_s.search_solr(request_dict_json)
        m_json_ld = MakeJsonLd(request_dict_json)
        m_json_ld.base_search_link = '/media-search/'
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
            recon_obj = Reconciliation()
            json_ld = recon_obj.process(request.GET,
                                        json_ld)
            return HttpResponse(json.dumps(json_ld,
                                ensure_ascii=False, indent=4),
                                content_type=req_neg.use_response_type + "; charset=utf8")
        else:
            # now make the JSON-LD into an object suitable for HTML templating
            st = SearchTemplate(json_ld)
            st.process_json_ld()
            template = loader.get_template('search/view.html')
            context = RequestContext(request,
                                     {'st': st,
                                      'item_type': 'media',
                                      'base_search_link': m_json_ld.base_search_link,
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


def media_json_view(request, spatial_context=None):
    """ API for searching Open Context, media only """
    rd = RequestDict()
    request_dict_json = rd.make_request_dict_json(request,
                                                  spatial_context)
    solr_s = SolrSearch()
    solr_s.item_type_limit = 'media'
    if solr_s.solr is not False:
        response = solr_s.search_solr(request_dict_json)
        m_json_ld = MakeJsonLd(request_dict_json)
        m_json_ld.base_search_link = '/media-search/'
        # share entities already looked up. Saves database queries
        m_json_ld.entities = solr_s.entities
        m_json_ld.request_full_path = request.get_full_path()
        m_json_ld.spatial_context = spatial_context
        json_ld = m_json_ld.convert_solr_json(response.raw_content)
        req_neg = RequestNegotiation('application/json')
        req_neg.supported_types = ['application/ld+json']
        recon_obj = Reconciliation()
        json_ld = recon_obj.process(request.GET,
                                    json_ld)
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            # requester wanted a mimetype we DO support
            if 'callback' in request.GET:
                funct = request.GET['callback']
                json_str = json.dumps(json_ld,
                                      ensure_ascii=False,
                                      indent=4)
                return HttpResponse(funct + '(' + json_str + ');',
                                    content_type='application/javascript' + "; charset=utf8")
            else:
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


def projects_html_view(request, spatial_context=None):
    """ returns HTML representation of projects search
    """
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
    solr_s = SolrSearch()
    solr_s.do_context_paths = False
    solr_s.item_type_limit = 'projects'
    if solr_s.solr is not False:
        response = solr_s.search_solr(request_dict_json)
        m_json_ld = MakeJsonLd(request_dict_json)
        m_json_ld.base_search_link = '/projects-search/'
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
            recon_obj = Reconciliation()
            json_ld = recon_obj.process(request.GET,
                                        json_ld)
            return HttpResponse(json.dumps(json_ld,
                                ensure_ascii=False, indent=4),
                                content_type=req_neg.use_response_type + "; charset=utf8")
        else:
            # now make the JSON-LD into an object suitable for HTML templating
            st = SearchTemplate(json_ld)
            st.process_json_ld()
            p_aug = ProjectAugment(json_ld)
            p_aug.process_json_ld()
            template = loader.get_template('search/view.html')
            context = RequestContext(request,
                                     {'st': st,
                                      'item_type': 'projects',
                                      'base_search_link': m_json_ld.base_search_link,
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


def projects_json_view(request, spatial_context=None):
    """ API for searching Open Context, media only """
    rd = RequestDict()
    request_dict_json = rd.make_request_dict_json(request,
                                                  spatial_context)
    solr_s = SolrSearch()
    solr_s.do_context_paths = False
    solr_s.item_type_limit = 'projects'
    if solr_s.solr is not False:
        response = solr_s.search_solr(request_dict_json)
        m_json_ld = MakeJsonLd(request_dict_json)
        m_json_ld.base_search_link = '/projects-search/'
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
            if 'callback' in request.GET:
                funct = request.GET['callback']
                json_str = json.dumps(json_ld,
                                      ensure_ascii=False,
                                      indent=4)
                return HttpResponse(funct + '(' + json_str + ');',
                                    content_type='application/javascript' + "; charset=utf8")
            else:
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
