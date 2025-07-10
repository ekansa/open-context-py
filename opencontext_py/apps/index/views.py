from django.http import HttpResponse
from django.conf import settings
from django.template import loader
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.libs.utilities.git_history import get_template_file_git_updated_datetime_str

def index(request):
    """ Get home page """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    old_view = False
    open_graph = {
        'twitter_site': settings.TWITTER_SITE,
        'type': 'website',
        'url': base_url,
        'site_name': settings.CANONICAL_SITENAME,
        'description': 'Home page for Open Context, an open access service for publishing, '\
                       'preserving, exploring and analyzing archaeological '\
                       'research data',
        'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
        'video': False
    }
    # template = loader.get_template('index/view.html')
    template = loader.get_template('bootstrap_vue/index/index.html')
    context = {
        'BASE_URL': base_url,
        'load_index_static': True,
        'old_view': old_view,
        'PAGE_TITLE': 'Open Context: Publisher of Research Data',
        'og': open_graph,
        'act_nav': 'home',
        'NAV_ITEMS': settings.NAV_ITEMS,
        'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
            'bootstrap_vue/index/index.html'
        ),
    }
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        return HttpResponse(template.render(context, request))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(template.render(context, request),
                            status=415)


def robots(request):
    """ view for the robots.txt file """
    template = loader.get_template('index/robots.txt')
    context = {}
    return HttpResponse(template.render(context, request),
                        content_type="text/plain; charset=utf8")

def bing_index_now(request):
    """ view for the Bing index now file """
    template = loader.get_template('index/4db754ce144f4ae0b8bbd0fac5e39b3c.txt')
    context = {}
    return HttpResponse(template.render(context, request),
                        content_type="text/plain; charset=utf8")

