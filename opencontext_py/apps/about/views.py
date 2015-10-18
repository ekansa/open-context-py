import json
from django.conf import settings
from django.http import HttpResponse, Http404
from django.template import RequestContext, loader
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.about.estimator import CostEstimator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


@cache_control(no_cache=True)
@never_cache
def index_view(request):
    """ Get the search context JSON-LD """
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        template = loader.get_template('about/index.html')
        context = RequestContext(request,
                                 {'base_url': base_url,
                                  'page_title': 'Open Context: About',
                                  'act_nav': 'about',
                                  'nav_items': settings.NAV_ITEMS})
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


def uses_view(request):
    """ Get the search context JSON-LD """
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        template = loader.get_template('about/temp.html')
        context = RequestContext(request,
                                 {'base_url': base_url,
                                  'page_title': 'Open Context: About - Uses',
                                  'act_nav': 'about',
                                  'nav_items': settings.NAV_ITEMS})
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


def pub_view(request):
    """ Get the search context JSON-LD """
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        template = loader.get_template('about/temp.html')
        context = RequestContext(request,
                                 {'base_url': base_url,
                                  'page_title': 'Open Context: About - Publishing',
                                  'act_nav': 'about',
                                  'nav_items': settings.NAV_ITEMS})
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


@ensure_csrf_cookie
# @cache_control(no_cache=True)
# @never_cache
def estimate_view(request):
    """ Get the search context JSON-LD """
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        template = loader.get_template('about/estimate.html')
        context = RequestContext(request,
                                 {'base_url': base_url,
                                  'page_title': 'Open Context: About - Cost Estimate',
                                  'act_nav': 'about',
                                  'nav_items': settings.NAV_ITEMS})
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


@cache_control(no_cache=True)
@never_cache
def process_estimate(request):
    """ Finalizes an import """
    if request.method == 'POST':
        cost = CostEstimator()
        output = cost.process_estimate(request.POST)
        json_output = json.dumps(output,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        return HttpResponseForbidden


def concepts_view(request):
    """ Get the search context JSON-LD """
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        template = loader.get_template('about/temp.html')
        context = RequestContext(request,
                                 {'base_url': base_url,
                                  'page_title': 'Open Context: About - Concepts',
                                  'act_nav': 'about',
                                  'nav_items': settings.NAV_ITEMS})
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


def tech_view(request):
    """ Get the search context JSON-LD """
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        template = loader.get_template('about/temp.html')
        context = RequestContext(request,
                                 {'base_url': base_url,
                                  'page_title': 'Open Context: About - Technology',
                                  'act_nav': 'about',
                                  'nav_items': settings.NAV_ITEMS})
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


def services_view(request):
    """ Get the search context JSON-LD """
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        template = loader.get_template('about/services.html')
        context = RequestContext(request,
                                 {'base_url': base_url,
                                  'page_title': 'Open Context: About - Web Services and APIs',
                                  'act_nav': 'about',
                                  'nav_items': settings.NAV_ITEMS})
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


def recipes_view(request):
    """ Get the search context JSON-LD """
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        template = loader.get_template('about/recipes.html')
        context = RequestContext(request,
                                 {'base_url': base_url,
                                  'page_title': 'Open Context: About - API Cookbook',
                                  'act_nav': 'about',
                                  'nav_items': settings.NAV_ITEMS})
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)

@cache_control(no_cache=True)
@never_cache
def bibliography_view(request):
    """ Get the search context JSON-LD """
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        template = loader.get_template('about/bibliography.html')
        context = RequestContext(request,
                                 {'base_url': base_url,
                                  'page_title': 'Open Context: About - API Cookbook',
                                  'act_nav': 'about',
                                  'nav_items': settings.NAV_ITEMS})
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)

