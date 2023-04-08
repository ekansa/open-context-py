import json
from django.conf import settings
from django.http import HttpResponse
from django.template import loader
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.libs.utilities.git_history import get_template_file_git_updated_datetime_str

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
        template = loader.get_template('bootstrap_vue/about/index.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: About',
            'act_nav': 'about',
            'NAV_ITEMS': settings.NAV_ITEMS,
            'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
                'bootstrap_vue/about/index.html'
            ),
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
        template = loader.get_template('bootstrap_vue/about/uses.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: About - Uses',
            'act_nav': 'about',
            'NAV_ITEMS': settings.NAV_ITEMS,
            'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
                'bootstrap_vue/about/uses.html'
            ),
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
        template = loader.get_template('bootstrap_vue/about/publishing.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: About - Publishing',
            'act_nav': 'about',
            'NAV_ITEMS': settings.NAV_ITEMS,
            'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
                'bootstrap_vue/about/publishing.html'
            ),
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
        template = loader.get_template('bootstrap_vue/about/people.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: About - People',
            'act_nav': 'about',
            'NAV_ITEMS': settings.NAV_ITEMS,
            'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
                'bootstrap_vue/about/people.html'
            ),
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
        template = loader.get_template('bootstrap_vue/about/estimate.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: About - Cost Estimate',
            'act_nav': 'about',
            'NAV_ITEMS': settings.NAV_ITEMS,
            'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
                'bootstrap_vue/about/estimate.html'
            ),
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
        template = loader.get_template('bootstrap_vue/about/temp.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: About - Concepts',
            'act_nav': 'about',
            'NAV_ITEMS': settings.NAV_ITEMS,

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
        template = loader.get_template('bootstrap_vue/about/technology.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: About - Technology',
            'act_nav': 'about',
            'NAV_ITEMS': settings.NAV_ITEMS,
            'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
                'bootstrap_vue/about/technology.html'
            ),
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
        template = loader.get_template('bootstrap_vue/about/services.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: About - Web Services and APIs',
            'act_nav': 'about',
            'NAV_ITEMS': settings.NAV_ITEMS,
            'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
                'bootstrap_vue/about/services.html'
            ),
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
        template = loader.get_template('bootstrap_vue/about/recipes.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: About - API Cookbook',
            'act_nav': 'about',
            'NAV_ITEMS': settings.NAV_ITEMS,
            'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
                'bootstrap_vue/about/recipes.html'
            ),
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
        template = loader.get_template('bootstrap_vue/about/bibliography.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: About - Bibliography',
            'act_nav': 'about',
            'NAV_ITEMS': settings.NAV_ITEMS,
            'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
                'bootstrap_vue/about/bibliography.html'
            ),
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
        template = loader.get_template('bootstrap_vue/about/intellectual-property.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: About - Intellectual Property',
            'act_nav': 'about',
            'NAV_ITEMS': settings.NAV_ITEMS,
            'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
                'bootstrap_vue/about/intellectual-property.html'
            ),
        }
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


@cache_control(no_cache=True)
@never_cache
def fair_care_view(request):
    """ Get page about FAIR+CARE policies """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        template = loader.get_template('bootstrap_vue/about/fair-care.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: About - FAIR and CARE Data Principles',
            'act_nav': 'about',
            'NAV_ITEMS': settings.NAV_ITEMS,
            'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
                'bootstrap_vue/about/intellectual-property.html'
            ),
        }
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(
            req_neg.error_message,
            status=415
        )


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
        template = loader.get_template('bootstrap_vue/about/sponsors.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: About - Sponsors and Support',
            'act_nav': 'about',
            'NAV_ITEMS': settings.NAV_ITEMS,
            'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
                'bootstrap_vue/about/sponsors.html'
            ),
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
        template = loader.get_template('bootstrap_vue/about/terms.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: About - Terms of Use and Privacy Policies',
            'act_nav': 'about',
            'NAV_ITEMS': settings.NAV_ITEMS,
            'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
                'bootstrap_vue/about/terms.html'
            ),
        }
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)