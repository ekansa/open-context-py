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


# @cache_control(no_cache=True)
# @never_cache
def index_view(request):
    """ Get the search context JSON-LD """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        open_graph = {
            'twitter_site': settings.TWITTER_SITE,
            'type': 'website',
            'url': base_url + '/about/',
            'site_name': settings.CANONICAL_SITENAME,
            'description': 'Video and introduction to Open Context, an open-access '
                           'data publication service for archaeology ',
            'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
            'video': 'https://opencontext.wistia.com/medias/s0g0fsyqkz'
        }
        template = loader.get_template('about/index.html')
        context = {
            'base_url': base_url,
            'page_title': 'Open Context: About',
            'act_nav': 'about',
            'og': open_graph,
            'nav_items': settings.NAV_ITEMS
        }
        return HttpResponse(template.render(context, request))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)

@cache_control(no_cache=True)
@never_cache
def uses_view(request):
    """ Get uses page """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        template = loader.get_template('about/uses.html')
        open_graph = {
            'twitter_site': settings.TWITTER_SITE,
            'type': 'website',
            'url': base_url + '/about/uses',
            'site_name': settings.CANONICAL_SITENAME,
            'description': 'Summary of how to use Open Context for sharing, '\
                           'preserving, exploring and analyzing archaeological '\
                           'research data',
            'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
            'video': False
        }
        context = {
            'base_url': base_url,
            'page_title': 'Open Context: About - Uses',
            'og': open_graph,
            'act_nav': 'about',
            'nav_items': settings.NAV_ITEMS
        }
        return HttpResponse(template.render(context, request))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


@cache_control(no_cache=True)
@never_cache
def pub_view(request):
    """ Get publishing overview page """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        open_graph = {
            'twitter_site': settings.TWITTER_SITE,
            'type': 'website',
            'url': base_url + '/about/publishing',
            'site_name': settings.CANONICAL_SITENAME,
            'description': 'How to publish archaeological research data '\
                           'with Open Context',
            'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
            'video': False
        }
        template = loader.get_template('about/publishing.html')
        context = {
            'base_url': base_url,
            'page_title': 'Open Context: About - Publishing',
            'act_nav': 'about',
            'og': open_graph,
            'nav_items': settings.NAV_ITEMS
        }
        return HttpResponse(template.render(context, request))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


# @cache_control(no_cache=True)
# @never_cache
def people_view(request):
    """ Get people page """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        open_graph = {
            'twitter_site': settings.TWITTER_SITE,
            'type': 'website',
            'url': base_url + '/about/people',
            'site_name': settings.CANONICAL_SITENAME,
            'description': 'Data editors, software developers, designers '\
                           'and alumni with Open Context research data '\
                           'publishing services',
            'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
            'video': False
        }
        template = loader.get_template('about/people.html')
        context = {
            'base_url': base_url,
            'page_title': 'Open Context: About - People',
            'og': open_graph,
            'act_nav': 'about',
            'nav_items': settings.NAV_ITEMS
        }
        return HttpResponse(template.render(context, request))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


@ensure_csrf_cookie
# @cache_control(no_cache=True)
# @never_cache
def estimate_view(request):
    """ Get page with publication project cost estimation """
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        open_graph = {
            'twitter_site': settings.TWITTER_SITE,
            'type': 'website',
            'url': base_url + '/about/estimate',
            'site_name': settings.CANONICAL_SITENAME,
            'description': 'Estimate data publication and archiving '\
                           'costs with Open Context to help budget for '\
                           'grant data management plans',
            'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
            'video': False
        }
        template = loader.get_template('about/estimate.html')
        context = {
            'base_url': base_url,
            'page_title': 'Open Context: About - Cost Estimate',
            'og': open_graph,
            'act_nav': 'about',
            'nav_items': settings.NAV_ITEMS
        }
        return HttpResponse(template.render(context, request))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


@cache_control(no_cache=True)
@never_cache
def process_estimate(request):
    """ process an estimate """
    if request.method == 'POST':
        cost = CostEstimator()
        output = cost.process_estimate(request.POST)
        json_output = json.dumps(output,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    elif request.method == 'GET':
        cost = CostEstimator()
        output = cost.process_estimate(request.GET)
        json_output = json.dumps(output,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        return HttpResponseForbidden


def concepts_view(request):
    """ Get concepts overview """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        template = loader.get_template('about/temp.html')
        context = {
            'base_url': base_url,
            'page_title': 'Open Context: About - Concepts',
            'act_nav': 'about',
            'nav_items': settings.NAV_ITEMS
        }
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)

@cache_control(no_cache=True)
@never_cache
def tech_view(request):
    """ Show technology page """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        open_graph = {
            'twitter_site': settings.TWITTER_SITE,
            'type': 'website',
            'url': base_url + '/about/technology',
            'site_name': settings.CANONICAL_SITENAME,
            'description': 'Overview of the open-source software technologies '\
                           'created and used by Open Context to publish '\
                           'archaeological data on the Web',
            'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
            'video': False
        }
        template = loader.get_template('about/technology.html')
        context = {
            'base_url': base_url,
            'page_title': 'Open Context: About - Technology',
            'act_nav': 'about',
            'og': open_graph,
            'nav_items': settings.NAV_ITEMS
        }
        return HttpResponse(template.render(context, request))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


def services_view(request):
    """ Get page documenting the API """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        open_graph = {
            'twitter_site': settings.TWITTER_SITE,
            'type': 'website',
            'url': base_url + '/about/technology',
            'site_name': settings.CANONICAL_SITENAME,
            'description': 'Overview of the APIs (machine-readable data) '\
                           'offered by Open Context to promote '\
                           'interoperability and new uses of data',
            'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
            'video': False
        }
        template = loader.get_template('about/services.html')
        context = {
            'base_url': base_url,
            'page_title': 'Open Context: About - Web Services and APIs',
            'og': open_graph,
            'act_nav': 'about',
            'nav_items': settings.NAV_ITEMS
        }
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


def recipes_view(request):
    """ Get page about recipes using the API """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        open_graph = {
            'twitter_site': settings.TWITTER_SITE,
            'type': 'website',
            'url': base_url + '/about/recipes',
            'site_name': settings.CANONICAL_SITENAME,
            'description': 'Specific guidance on the use of Open Context APIs '\
                           '(machine-readable data) to meet certain data '\
                           'management needs',
            'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
            'video': False
        }
        template = loader.get_template('about/recipes.html')
        context = {
            'base_url': base_url,
            'page_title': 'Open Context: About - API Cookbook',
            'og': open_graph,
            'act_nav': 'about',
            'nav_items': settings.NAV_ITEMS
        }
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)

@cache_control(no_cache=True)
@never_cache
def bibliography_view(request):
    """ Get page about bibliography / publications """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        open_graph = {
            'twitter_site': settings.TWITTER_SITE,
            'type': 'website',
            'url': base_url + '/about/bibliography',
            'site_name': settings.CANONICAL_SITENAME,
            'description': 'Publications related to Open Context and its '\
                           'contributions to research data management, '\
                           'archaeological ethics, scholarly communications, and '\
                           'professional practice',
            'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
            'video': False
        }
        template = loader.get_template('about/bibliography.html')
        context = {
            'base_url': base_url,
            'page_title': 'Open Context: About - Bibliography',
            'og': open_graph,
            'act_nav': 'about',
            'nav_items': settings.NAV_ITEMS
        }
        return HttpResponse(template.render(context, request))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)

@cache_control(no_cache=True)
@never_cache
def ip_view(request):
    """ Get page about IP policies """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        open_graph = {
            'twitter_site': settings.TWITTER_SITE,
            'type': 'website',
            'url': base_url + '/about/intellectual-property',
            'site_name': settings.CANONICAL_SITENAME,
            'description': 'Intellectual property policies for Open Context and '\
                           'ethical guidance for contributors and users of '\
                           'archaeological research data',
            'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
            'video': False
        }
        template = loader.get_template('about/intellectual-property.html')
        context = {
            'base_url': base_url,
            'page_title': 'Open Context: About - Intellectual Property',
            'og': open_graph,
            'act_nav': 'about',
            'nav_items': settings.NAV_ITEMS
        }
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


@cache_control(no_cache=True)
@never_cache
def sponsors_view(request):
    """ Get the page about sponsors """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        open_graph = {
            'twitter_site': settings.TWITTER_SITE,
            'type': 'website',
            'url': base_url + '/about/sponsors',
            'site_name': settings.CANONICAL_SITENAME,
            'description': 'Sources of financial support for '\
                           'Open Context and collaborative institutions providing '\
                           'complementary services',
            'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
            'video': False
        }
        template = loader.get_template('about/sponsors.html')
        context = {
            'base_url': base_url,
            'page_title': 'Open Context: About - Intellectual Property',
            'og': open_graph,
            'act_nav': 'about',
            'nav_items': settings.NAV_ITEMS
        }
        return HttpResponse(template.render(context, request))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


# @cache_control(no_cache=True)
# @never_cache
def terms_view(request):
    """ Get the page about Terms """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        open_graph = {
            'twitter_site': settings.TWITTER_SITE,
            'type': 'website',
            'url': base_url + '/about/terms',
            'site_name': settings.CANONICAL_SITENAME,
            'description': 'Terms and Conditions of Use, and '\
                           'Privacy Policies for Open Context',
            'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
            'video': False
        }
        template = loader.get_template('about/terms.html')
        context = {
            'base_url': base_url,
            'page_title': 'Open Context: About - Terms of Use and Privacy Policies',
            'og': open_graph,
            'act_nav': 'about',
            'nav_items': settings.NAV_ITEMS
        }
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)