import json
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponse, Http404
from django.template import RequestContext, loader
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.solrconnection import SolrConnection
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.libs.memorycache import MemoryCache
from opencontext_py.libs.databasecache import DatabaseCache
from opencontext_py.libs.filecache import FileCacheJSON
from opencontext_py.apps.searcher.solrsearcher.models import SolrSearch
from opencontext_py.apps.searcher.solrsearcher.makejsonld import MakeJsonLd
from opencontext_py.apps.searcher.solrsearcher.filterlinks import FilterLinks
from opencontext_py.apps.searcher.solrsearcher.templating import SearchTemplate
from opencontext_py.apps.searcher.solrsearcher.requestdict import RequestDict
from opencontext_py.apps.searcher.solrsearcher.reconciliation import Reconciliation
from opencontext_py.apps.searcher.solrsearcher.projtemplating import ProjectAugment
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.views.decorators.cache import cache_page
from django.utils.cache import patch_vary_headers


def index(request, spatial_context=None):
    request = RequestNegotiation().anonymize_request(request)
    return HttpResponse("Hello, world. You're at the search index.")


def sets_view(request, spatial_context=''):
    """ redirects requests from the legacy site 'sets'
        to the subjects-search view

        We can add URL parameter mappings to this later
        so that old url parameters can be mapped to the
        current parameters
    """
    request = RequestNegotiation().anonymize_request(request)
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
    request = RequestNegotiation().anonymize_request(request)
    url = request.get_full_path()
    new_url = url.replace('/lightbox/', '/media-search/')
    param_suffix = ''
    if '?' in url:
        url_ex = url.split('?')
        param_suffix = '?' + url_ex[1]
    return redirect(new_url, permanent=True)

# @cache_control(no_cache=True)
# @never_cache
# @vary_on_headers('Accept', 'accept', 'content-type')
@cache_page(settings.FILE_CACHE_TIMEOUT, cache='file')
def html_view(request, spatial_context=None):
    request = RequestNegotiation().anonymize_request(request)
    item_type_limited = False
    rp = RootPath()
    base_url = rp.get_baseurl()
    rd = RequestDict()
    chart = False # provide a chart, now only experimental
    if request.GET.get('chart') is not None:
        chart = True
    request_dict_json = rd.make_request_dict_json(request,
                                                  spatial_context)
    # toggle if Human-Remains are OK to show in search results
    # defaults to FALSE, requires user interface action to allow
    if request.GET.get('human-remains') is not None:
        human_remains_ok = True
    else:
        human_remains_ok = False
        human_remains_opt_in = request.session.get('human_remains_ok')
        if human_remains_opt_in:
            # opt-in OK for this user in this session
            human_remains_ok = True
    if rd.security_ok is False:
        # looks like an abusive SQL injection request
        template = loader.get_template('400.html')
        context = RequestContext(request,
                                 {'abusive': True})
        return HttpResponse(template.render(context), status=400)
    elif rd.do_bot_limit:
        # redirect bot requests away from faceted search where
        # they can negatively impact performance
        cache_control(no_cache=True)
        return redirect('/search/', permanent=False)
    else:
        # url and json_url neeed for view templating
        url = request.get_full_path()
        if 'http://' not in url \
           and 'https://' not in url:
            url = base_url + url
        if '?' in url:
            json_url = url.replace('?', '.json?')
        else:
            json_url = url + '.json'
        # see if search results are cached. this is not done
        # with a view decorator, because we want to handle bots differently
        db_cache = DatabaseCache()
        cache_key = db_cache.make_cache_key('search',
                                            request_dict_json)
        # print('Cache key: ' + cache_key)
        geo_proj = False
        json_ld = None
        if rd.refresh_cache:
            # the request wanted to refresh the cache
            db_cache.remove_cache_object(cache_key)
        if 'response' in request.GET:
            if 'geo-project' in request.GET['response']:
                geo_proj = True
        # get the search result JSON-LD, if it exists in cache
        json_ld = db_cache.get_cache_object(cache_key)
        if json_ld is None:
            # cached result is not found, so make it with a new search
            solr_s = SolrSearch()
            solr_s.is_bot = rd.is_bot  # True if bot detected
            solr_s.do_bot_limit = rd.do_bot_limit  # Toggle limits on facets for bots
            if solr_s.solr is not False:
                response = solr_s.search_solr(request_dict_json)                
                # are we filtering for item_types?
                item_type_limited = solr_s.item_type_limited
                m_json_ld = MakeJsonLd(request_dict_json)
                m_json_ld.base_search_link = '/search/'
                m_json_ld.request_full_path = request.get_full_path()
                m_json_ld.spatial_context = spatial_context
                json_ld = m_json_ld.convert_solr_json(response.raw_content)
                # now cache the resulting JSON-LD
                db_cache.save_cache_object(cache_key, json_ld)
        if json_ld is not None:
            req_neg = RequestNegotiation('text/html')
            req_neg.supported_types = ['application/json',
                                       'application/ld+json',
                                       'application/vnd.geo+json']
            if 'HTTP_ACCEPT' in request.META:
                req_neg.check_request_support(request.META['HTTP_ACCEPT'])
            if 'json' in req_neg.use_response_type:
                # content negotiation requested JSON or JSON-LD
                recon_obj = Reconciliation()
                json_ld = recon_obj.process(request.GET,
                                            json_ld)
                request.content_type = req_neg.use_response_type
                response = HttpResponse(json.dumps(json_ld,
                                        ensure_ascii=False, indent=4),
                                        content_type=req_neg.use_response_type + "; charset=utf8")
                patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
                return response
            else:
                # now make the JSON-LD into an object suitable for HTML templating
                st = SearchTemplate(json_ld)
                st.item_type_limited = item_type_limited
                st.human_remains_ok = human_remains_ok
                st.process_json_ld()
                props = []
                if 'prop' in request.GET:
                    props = request.GET.getlist('prop')
                # check to make sure chrono chart will be ok
                if 'proj' in request.GET \
                   or len(props) > 1 \
                   or 'q' in request.GET \
                   or spatial_context is not None:
                    if 'oc-api:has-form-use-life-ranges' in json_ld:
                        if len(json_ld['oc-api:has-form-use-life-ranges']) > 0 and st.total_count > 0:
                            chart = True
                template = loader.get_template('search/view.html')
                context = {
                    'st': st,
                    'item_type': '*',
                    'chart': chart,
                    'human_remains_ok': human_remains_ok,
                    'base_search_link': m_json_ld.base_search_link,
                    'url': url,
                    'json_url': json_url,
                    'base_url': base_url
                }
                if req_neg.supported:
                    response = HttpResponse(template.render(context, request))
                    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
                    return response
                else:
                    # client wanted a mimetype we don't support
                    return HttpResponse(req_neg.error_message,
                                        content_type=req_neg.use_response_type + "; charset=utf8",
                                        status=415)
        else:
            cache_control(no_cache=True)
            template = loader.get_template('500.html')
            context = RequestContext(request,
                                     {'error': 'Solr Connection Problem'})
            return HttpResponse(template.render(context), status=503)


# @cache_control(no_cache=True)
@cache_page(settings.FILE_CACHE_TIMEOUT, cache='file')
def json_view(request, spatial_context=None):
    """ API for searching Open Context """
    
    
    rd = RequestDict()
    request_dict_json = rd.make_request_dict_json(request,
                                                  spatial_context)
    if rd.security_ok is False:
        template = loader.get_template('400.html')
        context = RequestContext(request,
                                 {'abusive': True})
        return HttpResponse(template.render(context), status=400)
    elif rd.do_bot_limit:
        # redirect bot requests away from faceted search where
        # they can negatively impact performance
        cache_control(no_cache=True)
        return redirect('/search/.json', permanent=False)
    else:
        # see if search results are cached. this is not done
        # with a view decorator, because we want to handle bots differently
        db_cache = DatabaseCache()
        cache_key = db_cache.make_cache_key('search',
                                            request_dict_json)
        if rd.refresh_cache:
            # the request wanted to refresh the cache
            db_cache.remove_cache_object(cache_key)
        # get the search result JSON-LD, if it exists in cache
        json_ld = db_cache.get_cache_object(cache_key)
        if json_ld is None:
            # cached result is not found, so make it with a new search
            solr_s = SolrSearch()
            solr_s.is_bot = rd.is_bot  # True if bot detected
            solr_s.do_bot_limit = rd.do_bot_limit  # Toggle limits on facets for bots
            
            if solr_s.solr is not False:
                response = solr_s.search_solr(request_dict_json)
                
                m_json_ld = MakeJsonLd(request_dict_json)
                m_json_ld.base_search_link = '/search/'
                m_json_ld.request_full_path = request.get_full_path()
                m_json_ld.spatial_context = spatial_context
                json_ld = m_json_ld.convert_solr_json(response.raw_content)
                # now cache the resulting JSON-LD
                db_cache.save_cache_object(cache_key, json_ld)
        if json_ld is not None:
            req_neg = RequestNegotiation('application/json')
            req_neg.supported_types = ['application/ld+json',
                                       'application/vnd.geo+json']
            recon_obj = Reconciliation()
            json_ld = recon_obj.process(request.GET,
                                        json_ld)
            if 'HTTP_ACCEPT' in request.META:
                req_neg.check_request_support(request.META['HTTP_ACCEPT'])
            if req_neg.supported:
                # requester wanted a mimetype we DO support
                request.content_type = req_neg.use_response_type
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
            cache_control(no_cache=True)
            template = loader.get_template('500.html')
            context = RequestContext(request,
                                     {'error': 'Solr Connection Problem'})
            return HttpResponse(template.render(context), status=503)


# @cache_control(no_cache=True)
@cache_page(settings.FILE_CACHE_TIMEOUT, cache='file')
def subjects_html_view(request, spatial_context=None):
    """ returns HTML representation of subjects search
    """
    request = RequestNegotiation().anonymize_request(request)
    item_type_limited = True
    csv_downloader = False  # provide CSV downloader interface
    if request.GET.get('csv') is not None:
        csv_downloader = True
    chart = False # provide a chart, now only experimental
    if request.GET.get('chart') is not None:
        chart = True
    # toggle if Human-Remains are OK to show in search results
    # defaults to FALSE, requires user interface action to allow
    if request.GET.get('human-remains') is not None:
        human_remains_ok = True
    else:
        human_remains_ok = False
        human_remains_opt_in = request.session.get('human_remains_ok')
        if human_remains_opt_in:
            # opt-in OK for this user in this session
            human_remains_ok = True
    rp = RootPath()
    base_url = rp.get_baseurl()
    rd = RequestDict()
    request_dict_json = rd.make_request_dict_json(request,
                                                  spatial_context)
    if rd.security_ok is False:
        template = loader.get_template('400.html')
        context = RequestContext(request,
                                 {'abusive': True})
        return HttpResponse(template.render(context), status=400)
    elif rd.do_bot_limit:
        cache_control(no_cache=True)
        # redirect bot requests away from faceted search where
        # they can negatively impact performance
        return redirect('/subjects-search/', permanent=False)
    else:
        # url and json_url neeed for view templating
        url = request.get_full_path()
        if 'http://' not in url \
           and 'https://' not in url:
            url = base_url + url
        if '?' in url:
            json_url = url.replace('?', '.json?')
        else:
            json_url = url + '.json'
        # see if search results are cached. this is not done
        # with a view decorator, because we want to handle bots differently
        db_cache = DatabaseCache()
        cache_key = db_cache.make_cache_key('subjects-search',
                                            request_dict_json)
        if rd.refresh_cache:
            # the request wanted to refresh the cache
            db_cache.remove_cache_object(cache_key)
        # get the search result JSON-LD, if it exists in cache
        json_ld = db_cache.get_cache_object(cache_key)
        if json_ld is None:
            # cached result is not found, so make it with a new search
            solr_s = SolrSearch()
            solr_s.is_bot = rd.is_bot  # True if bot detected
            solr_s.do_bot_limit = rd.do_bot_limit  # Toggle limits on facets for bots
            
            solr_s.item_type_limit = 'subjects'
            if solr_s.solr is not False:
                response = solr_s.search_solr(request_dict_json)
                
                m_json_ld = MakeJsonLd(request_dict_json)
                m_json_ld.base_search_link = '/subjects-search/'
                m_json_ld.request_full_path = request.get_full_path()
                m_json_ld.spatial_context = spatial_context
                json_ld = m_json_ld.convert_solr_json(response.raw_content)
                # now cache the resulting JSON-LD
                db_cache.save_cache_object(cache_key, json_ld)
        if json_ld is not None:
            req_neg = RequestNegotiation('text/html')
            req_neg.supported_types = ['application/json',
                                       'application/ld+json',
                                       'application/vnd.geo+json']
            if 'HTTP_ACCEPT' in request.META:
                req_neg.check_request_support(request.META['HTTP_ACCEPT'])
            if 'json' in req_neg.use_response_type:
                # content negotiation requested JSON or JSON-LD
                recon_obj = Reconciliation()
                json_ld = recon_obj.process(request.GET,
                                            json_ld)
                request.content_type = req_neg.use_response_type
                response = HttpResponse(json.dumps(json_ld,
                                        ensure_ascii=False, indent=4),
                                        content_type=req_neg.use_response_type + "; charset=utf8")
                patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
                return response
            else:
                # now make the JSON-LD into an object suitable for HTML templating
                st = SearchTemplate(json_ld)
                st.item_type_limited = item_type_limited
                st.human_remains_ok = human_remains_ok
                st.process_json_ld()
                template = loader.get_template('search/view.html')
                props = []
                if 'prop' in request.GET:
                    props = request.GET.getlist('prop')
                # check to make sure chrono chart will be ok
                if 'proj' in request.GET \
                   or len(props) > 1 \
                   or 'q' in request.GET \
                   or spatial_context is not None:
                    if 'oc-api:has-form-use-life-ranges' in json_ld:
                        if len(json_ld['oc-api:has-form-use-life-ranges']) > 0 and st.total_count > 0:
                            chart = True
                if len(props) > 1 or st.total_count <= 25000 \
                   or ('proj' in request.GET and spatial_context is not None):
                    # allow downloads, multiple props selected
                    # or relatively few records
                    csv_downloader = True
                context = {
                    'st': st,
                    'csv_downloader': csv_downloader,
                    'chart': chart,
                    'human_remains_ok': human_remains_ok,
                    'item_type': 'subjects',
                    'base_search_link': m_json_ld.base_search_link,
                    'url': url,
                    'json_url': json_url,
                    'base_url': base_url
                }
                if req_neg.supported:
                    response = HttpResponse(template.render(context, request))
                    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
                    return response
                else:
                    # client wanted a mimetype we don't support
                    return HttpResponse(req_neg.error_message,
                                        content_type=req_neg.use_response_type + "; charset=utf8",
                                        status=415)
        else:
            cache_control(no_cache=True)
            template = loader.get_template('500.html')
            context = RequestContext(request,
                                     {'error': 'Solr Connection Problem'})
            return HttpResponse(template.render(context), status=503)


# @cache_control(no_cache=True)
@cache_page(settings.FILE_CACHE_TIMEOUT, cache='file')
def subjects_json_view(request, spatial_context=None):
    """ API for searching Open Context, subjects only """
    
    
    rd = RequestDict()
    request_dict_json = rd.make_request_dict_json(request,
                                                  spatial_context)
    if rd.security_ok is False:
        template = loader.get_template('400.html')
        context = RequestContext(request,
                                 {'abusive': True})
        return HttpResponse(template.render(context), status=400)
    elif rd.do_bot_limit:
        # redirect bot requests away from faceted search where
        # they can negatively impact performance
        cache_control(no_cache=True)
        return redirect('/subjects-search/.json', permanent=False)
    else:
        # see if search results are cached. this is not done
        # with a view decorator, because we want to handle bots differently
        db_cache = DatabaseCache()
        filecache = FileCacheJSON()
        file_cache_key = False
        cache_key = db_cache.make_cache_key('subjects-search',
                                            request_dict_json)
        if rd.refresh_cache:
            # the request wanted to refresh the cache
            db_cache.remove_cache_object(cache_key)
        # get the search result JSON-LD, if it exists in cache
        json_ld = db_cache.get_cache_object(cache_key)
        # print(request.get_full_path())
        if request.get_full_path() == '/subjects-search/.json?response=geo-project':
            file_cache_key = 'geo-project'
            if json_ld is None:
                json_ld = filecache.get_dict_from_file(file_cache_key)
        if json_ld is None:
            # cached result is not found, so make it with a new search
            solr_s = SolrSearch()
            solr_s.is_bot = rd.is_bot  # True if bot detected
            solr_s.do_bot_limit = rd.do_bot_limit  # Toggle limits on facets for bots
            
            solr_s.item_type_limit = 'subjects'
            if solr_s.solr is not False:
                response = solr_s.search_solr(request_dict_json)
                
                m_json_ld = MakeJsonLd(request_dict_json)
                m_json_ld.base_search_link = '/subjects-search/'
                m_json_ld.request_full_path = request.get_full_path()
                m_json_ld.spatial_context = spatial_context
                json_ld = m_json_ld.convert_solr_json(response.raw_content)
                # now cache the resulting JSON-LD
                db_cache.save_cache_object(cache_key, json_ld)
                if isinstance(file_cache_key, str):
                    # cache a file for the project home screen
                    filecache.save_serialized_json(file_cache_key, json_ld)
        if json_ld is not None:
            req_neg = RequestNegotiation('application/json')
            req_neg.supported_types = ['application/ld+json',
                                       'application/vnd.geo+json']
            recon_obj = Reconciliation()
            json_ld = recon_obj.process(request.GET,
                                        json_ld)
            if 'HTTP_ACCEPT' in request.META:
                req_neg.check_request_support(request.META['HTTP_ACCEPT'])
            if req_neg.supported:
                # requester wanted a mimetype we DO support
                request.content_type = req_neg.use_response_type
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
            cache_control(no_cache=True)
            template = loader.get_template('500.html')
            context = RequestContext(request,
                                     {'error': 'Solr Connection Problem'})
            return HttpResponse(template.render(context), status=503)


# @cache_control(no_cache=True)
# @never_cache
@cache_page(settings.FILE_CACHE_TIMEOUT, cache='file')
def media_html_view(request, spatial_context=None):
    """ returns HTML representation of media search
    """
    request = RequestNegotiation().anonymize_request(request)
    item_type_limited = True
    
    
    rp = RootPath()
    base_url = rp.get_baseurl()
    rd = RequestDict()
    request_dict_json = rd.make_request_dict_json(request,
                                                  spatial_context)
    chart = False # provide a chart, now only experimental
    if request.GET.get('chart') is not None:
        chart = True
    if spatial_context is not None:
        chart = True
    # toggle if Human-Remains are OK to show in search results
    # defaults to FALSE, requires user interface action to allow
    if request.GET.get('human-remains') is not None:
        human_remains_ok = True
    else:
        human_remains_ok = False
        human_remains_opt_in = request.session.get('human_remains_ok')
        if human_remains_opt_in:
            # opt-in OK for this user in this session
            human_remains_ok = True
    if rd.security_ok is False:
        template = loader.get_template('400.html')
        context = RequestContext(request,
                                 {'abusive': True})
        return HttpResponse(template.render(context), status=400)
    elif rd.do_bot_limit:
        # redirect bot requests away from faceted search where
        # they can negatively impact performance
        cache_control(no_cache=True)
        return redirect('/media-search/', permanent=False)
    else:
        # url and json_url neeed for view templating
        url = request.get_full_path()
        if 'http://' not in url \
           and 'https://' not in url:
            url = base_url + url
        if '?' in url:
            json_url = url.replace('?', '.json?')
        else:
            json_url = url + '.json'
        # see if search results are cached. this is not done
        # with a view decorator, because we want to handle bots differently
        db_cache = DatabaseCache()
        cache_key = db_cache.make_cache_key('media-search',
                                            request_dict_json)
        if rd.refresh_cache:
            # the request wanted to refresh the cache
            db_cache.remove_cache_object(cache_key)
        # get the search result JSON-LD, if it exists in cache
        json_ld = db_cache.get_cache_object(cache_key)
        if json_ld is None:
            # cached result is not found, so make it with a new search
            solr_s = SolrSearch()
            solr_s.is_bot = rd.is_bot  # True if bot detected
            
            solr_s.item_type_limit = 'media'
            # add category facet fields for related items
            solr_s.facet_fields += SolrSearch.REL_CAT_FACET_FIELDS
            solr_s.stats_fields += SolrSearch.MEDIA_STATS_FIELDS
            if solr_s.solr is not False:
                response = solr_s.search_solr(request_dict_json)
                
                m_json_ld = MakeJsonLd(request_dict_json)
                m_json_ld.base_search_link = '/media-search/'
                m_json_ld.request_full_path = request.get_full_path()
                m_json_ld.spatial_context = spatial_context
                m_json_ld.get_all_media = True  # get links to all media files for an item
                json_ld = m_json_ld.convert_solr_json(response.raw_content)
                # now cache the resulting JSON-LD
                db_cache.save_cache_object(cache_key, json_ld)
        if json_ld is not None:
            req_neg = RequestNegotiation('text/html')
            req_neg.supported_types = ['application/json',
                                       'application/ld+json',
                                       'application/vnd.geo+json']
            if 'HTTP_ACCEPT' in request.META:
                req_neg.check_request_support(request.META['HTTP_ACCEPT'])
            if 'json' in req_neg.use_response_type:
                # content negotiation requested JSON or JSON-LD
                request.content_type = req_neg.use_response_type
                recon_obj = Reconciliation()
                json_ld = recon_obj.process(request.GET,
                                            json_ld)
                response = HttpResponse(json.dumps(json_ld,
                                        ensure_ascii=False, indent=4),
                                        content_type=req_neg.use_response_type + "; charset=utf8")
                patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
                return response
            else:
                # now make the JSON-LD into an object suitable for HTML templating
                st = SearchTemplate(json_ld)
                st.item_type_limited = item_type_limited
                st.human_remains_ok = human_remains_ok
                st.process_json_ld()
                props = []
                if 'prop' in request.GET:
                    props = request.GET.getlist('prop')
                # check to make sure chrono chart will be ok
                if 'proj' in request.GET \
                   or len(props) > 1 \
                   or 'q' in request.GET \
                   or spatial_context is not None:
                    if 'oc-api:has-form-use-life-ranges' in json_ld:
                        if len(json_ld['oc-api:has-form-use-life-ranges']) > 0 and st.total_count > 0:
                            chart = True
                template = loader.get_template('search/view.html')
                context = {
                    'st': st,
                    'item_type': 'media',
                    'chart': chart,
                    'human_remains_ok': human_remains_ok,
                    'base_search_link': m_json_ld.base_search_link,
                    'url': url,
                    'json_url': json_url,
                    'base_url': base_url
                }
                if req_neg.supported:
                    response = HttpResponse(template.render(context, request))
                    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
                    return response
                else:
                    # client wanted a mimetype we don't support
                    return HttpResponse(req_neg.error_message,
                                        content_type=req_neg.use_response_type + "; charset=utf8",
                                        status=415)
        else:
            cache_control(no_cache=True)
            template = loader.get_template('500.html')
            context = RequestContext(request,
                                     {'error': 'Solr Connection Problem'})
            return HttpResponse(template.render(context), status=503)


# @cache_control(no_cache=True)
@cache_page(settings.FILE_CACHE_TIMEOUT, cache='file')
def media_json_view(request, spatial_context=None):
    """ API for searching Open Context, media only """
    
    
    rd = RequestDict()
    request_dict_json = rd.make_request_dict_json(request,
                                                  spatial_context)
    if rd.security_ok is False:
        template = loader.get_template('400.html')
        context = RequestContext(request,
                                 {'abusive': True})
        return HttpResponse(template.render(context), status=400)
    elif rd.do_bot_limit:
        # redirect bot requests away from faceted search where
        # they can negatively impact performance
        return redirect('/media-search/.json', permanent=False)
    else:
        # see if search results are cached. this is not done
        # with a view decorator, because we want to handle bots differently
        db_cache = DatabaseCache()
        cache_key = db_cache.make_cache_key('media-search',
                                            request_dict_json)
        if rd.refresh_cache:
            # the request wanted to refresh the cache
            db_cache.remove_cache_object(cache_key)
        # get the search result JSON-LD, if it exists in cache
        json_ld = db_cache.get_cache_object(cache_key)
        if json_ld is None:
            # cached result is not found, so make it with a new search
            solr_s = SolrSearch()
            solr_s.is_bot = rd.is_bot  # True if bot detected
            solr_s.do_bot_limit = rd.do_bot_limit  # Toggle limits on facets for bots
            
            solr_s.item_type_limit = 'media'
            # add category facet fields for related items
            solr_s.facet_fields += SolrSearch.REL_CAT_FACET_FIELDS
            solr_s.stats_fields += SolrSearch.MEDIA_STATS_FIELDS
            if solr_s.solr is not False:
                response = solr_s.search_solr(request_dict_json)
                
                m_json_ld = MakeJsonLd(request_dict_json)
                m_json_ld.base_search_link = '/media-search/'
                m_json_ld.request_full_path = request.get_full_path()
                m_json_ld.spatial_context = spatial_context
                m_json_ld.get_all_media = True  # get links to all media files for an item
                json_ld = m_json_ld.convert_solr_json(response.raw_content)
                # now cache the resulting JSON-LD
                db_cache.save_cache_object(cache_key, json_ld)
        if json_ld is not None:
            req_neg = RequestNegotiation('application/json')
            req_neg.supported_types = ['application/ld+json',
                                       'application/vnd.geo+json']
            recon_obj = Reconciliation()
            json_ld = recon_obj.process(request.GET,
                                        json_ld)
            if 'HTTP_ACCEPT' in request.META:
                req_neg.check_request_support(request.META['HTTP_ACCEPT'])
            if req_neg.supported:
                # requester wanted a mimetype we DO support
                request.content_type = req_neg.use_response_type
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
            cache_control(no_cache=True)
            template = loader.get_template('500.html')
            context = RequestContext(request,
                                     {'error': 'Solr Connection Problem'})
            return HttpResponse(template.render(context), status=503)


# @cache_control(no_cache=True)
@cache_page(settings.FILE_CACHE_TIMEOUT, cache='file')
def projects_html_view(request, spatial_context=None):
    """ returns HTML representation of projects search
    """
    request = RequestNegotiation().anonymize_request(request)
    item_type_limited = True
    
    
    rp = RootPath()
    base_url = rp.get_baseurl()
    rd = RequestDict()
    request_dict_json = rd.make_request_dict_json(request,
                                                  spatial_context)
    if rd.security_ok is False:
        template = loader.get_template('400.html')
        context = RequestContext(request,
                                 {'abusive': True})
        return HttpResponse(template.render(context), status=400)
    elif rd.do_bot_limit:
        # redirect bot requests away from faceted search where
        # they can negatively impact performance
        cache_control(no_cache=True)
        return redirect('/projects-search/', permanent=False)
    else:
        # url and json_url neeed for view templating
        url = request.get_full_path()
        if 'http://' not in url \
           and 'https://' not in url:
            url = base_url + url
        if '?' in url:
            json_url = url.replace('?', '.json?')
        else:
            json_url = url + '.json'
        # see if search results are cached. this is not done
        # with a view decorator, because we want to handle bots differently
        db_cache = DatabaseCache()
        cache_key = db_cache.make_cache_key('projects-search',
                                            request_dict_json)
        if rd.refresh_cache:
            # the request wanted to refresh the cache
            db_cache.remove_cache_object(cache_key)
        # get the search result JSON-LD, if it exists in cache
        json_ld = db_cache.get_cache_object(cache_key)
        if json_ld is None:
            # cached result is not found, so make it with a new search
            solr_s = SolrSearch()
            solr_s.is_bot = rd.is_bot  # True if bot detected
            solr_s.do_bot_limit = rd.do_bot_limit  # Toggle limits on facets for bots
            
            solr_s.do_context_paths = False
            solr_s.item_type_limit = 'projects'
            if solr_s.solr is not False:
                response = solr_s.search_solr(request_dict_json)
                
                m_json_ld = MakeJsonLd(request_dict_json)
                m_json_ld.base_search_link = '/projects-search/'
                m_json_ld.request_full_path = request.get_full_path()
                m_json_ld.spatial_context = spatial_context
                json_ld = m_json_ld.convert_solr_json(response.raw_content)
                # now cache the resulting JSON-LD
                db_cache.save_cache_object(cache_key, json_ld)
        if json_ld is not None:
            req_neg = RequestNegotiation('text/html')
            req_neg.supported_types = ['application/json',
                                       'application/ld+json',
                                       'application/vnd.geo+json']
            if 'HTTP_ACCEPT' in request.META:
                req_neg.check_request_support(request.META['HTTP_ACCEPT'])
            if 'json' in req_neg.use_response_type:
                # content negotiation requested JSON or JSON-LD
                request.content_type = req_neg.use_response_type
                recon_obj = Reconciliation()
                json_ld = recon_obj.process(request.GET,
                                            json_ld)
                response = HttpResponse(json.dumps(json_ld,
                                        ensure_ascii=False, indent=4),
                                        content_type=req_neg.use_response_type + "; charset=utf8")
                
                patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
                return response
            else:
                # now make the JSON-LD into an object suitable for HTML templating
                st = SearchTemplate(json_ld)
                st.item_type_limited = item_type_limited
                st.process_json_ld()
                p_aug = ProjectAugment(json_ld)
                p_aug.process_json_ld()
                template = loader.get_template('search/view.html')
                context = {
                    'st': st,
                    'item_type': 'projects',
                    'base_search_link': m_json_ld.base_search_link,
                    'p_aug': p_aug,
                    'url': url,
                    'json_url': json_url,
                    'base_url': base_url
                }
                if req_neg.supported:
                    response = HttpResponse(template.render(context, request))
                    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
                    return response
                else:
                    # client wanted a mimetype we don't support
                    return HttpResponse(req_neg.error_message,
                                        content_type=req_neg.use_response_type + "; charset=utf8",
                                        status=415)
        else:
            cache_control(no_cache=True)
            template = loader.get_template('500.html')
            context = RequestContext(request,
                                     {'error': 'Solr Connection Problem'})
            return HttpResponse(template.render(context), status=503)


# @cache_control(no_cache=True)
@cache_page(settings.FILE_CACHE_TIMEOUT, cache='file')
def projects_json_view(request, spatial_context=None):
    """ API for searching Open Context, media only """        
    rd = RequestDict()
    request_dict_json = rd.make_request_dict_json(request,
                                                  spatial_context)
    if rd.security_ok is False:
        template = loader.get_template('400.html')
        context = RequestContext(request,
                                 {'abusive': True})
        return HttpResponse(template.render(context), status=400)
    elif rd.do_bot_limit:
        # redirect bot requests away from faceted search where
        # they can negatively impact performance
        cache_control(no_cache=True)
        return redirect('/projects-search/', permanent=False)
    else:
        # see if search results are cached. this is not done
        # with a view decorator, because we want to handle bots differently
        db_cache = DatabaseCache()
        cache_key = db_cache.make_cache_key('projects-search',
                                            request_dict_json)
        if rd.refresh_cache:
            # the request wanted to refresh the cache
            db_cache.remove_cache_object(cache_key)
        # get the search result JSON-LD, if it exists in cache
        json_ld = db_cache.get_cache_object(cache_key)
        if json_ld is None:
            # cached result is not found, so make it with a new search
            solr_s = SolrSearch()
            solr_s.is_bot = rd.is_bot  # True if bot detected
            solr_s.do_bot_limit = rd.do_bot_limit  # Toggle limits on facets for bots
            solr_s.do_context_paths = False
            solr_s.item_type_limit = 'projects'
            if solr_s.solr is not False:
                response = solr_s.search_solr(request_dict_json)
                m_json_ld = MakeJsonLd(request_dict_json)
                m_json_ld.base_search_link = '/projects-search/'
                m_json_ld.request_full_path = request.get_full_path()
                m_json_ld.spatial_context = spatial_context
                json_ld = m_json_ld.convert_solr_json(response.raw_content)
                # now cache the resulting JSON-LD
                db_cache.save_cache_object(cache_key, json_ld)
        if json_ld is not None:
            req_neg = RequestNegotiation('application/json')
            req_neg.supported_types = ['application/ld+json',
                                       'application/vnd.geo+json']
            if 'HTTP_ACCEPT' in request.META:
                req_neg.check_request_support(request.META['HTTP_ACCEPT'])
            if req_neg.supported:
                # requester wanted a mimetype we DO support
                request.content_type = req_neg.use_response_type
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
            cache_control(no_cache=True)
            template = loader.get_template('500.html')
            context = RequestContext(request,
                                     {'error': 'Solr Connection Problem'})
            return HttpResponse(template.render(context), status=503)
