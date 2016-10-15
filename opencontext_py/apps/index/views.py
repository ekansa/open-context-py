from django.http import HttpResponse, Http404
from django.conf import settings
from django.template import RequestContext, loader
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation


def index(request):
    """ Get home page """
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    old_view = False
    open_graph = {
        'twitter_site': settings.TWITTER_SITE,
        'type': 'website',
        'url': base_url,
        'site_name': settings.CANONICAL_SITENAME,
        'description': 'Home page for Open Context, an open access service for publishign, '\
                       'preserving, exploring and analyzing archaeological '\
                       'research data',
        'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
        'video': False
    }
    template = loader.get_template('index/view.html')
    context = RequestContext(request,
                             {'base_url': base_url,
                              'old_view': old_view,
                              'page_title': 'Open Context: Publisher of Research Data',
                              'og': open_graph,
                              'act_nav': 'home',
                              'nav_items': settings.NAV_ITEMS})
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(template.render(context),
                            status=415)


def robots(request):
    """ view for the robots.txt file """
    template = loader.get_template('index/robots.txt')
    context = RequestContext(request)
    return HttpResponse(template.render(context),
                        content_type="text/plain; charset=utf8")
