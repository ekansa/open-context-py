import json
from django.utils.http import urlencode
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponse, Http404
from django.template import RequestContext, loader
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.ocitems.manifest.feed import ManifestFeed
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


@cache_control(no_cache=True)
@never_cache
def index(request):
    """ Get the search context JSON-LD """
    rp = RootPath()
    base_url = rp.get_baseurl()
    return HttpResponse("Hello, world. You're at the manifest index: " + str(request.GET))


@cache_control(no_cache=True)
@never_cache
def index_atom(request):
    """ Get the search context JSON-LD """
    mf = ManifestFeed()
    xml_string = mf.make_feed(request.GET)
    if xml_string is not False:
        req_neg = RequestNegotiation('application/atom+xml')
        req_neg.supported_types = ['application/atom+xml']
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            if 'atom' in req_neg.use_response_type:
                # content negotiation requested Atom
                return HttpResponse(xml_string,
                                    content_type=req_neg.use_response_type + "; charset=utf8")
            else:
                # give atom anyway
                return HttpResponse(xml_string,
                                    content_type='application/atom+xml' + "; charset=utf8")
        else:
            # client wanted a mimetype we don't support
            return HttpResponse(req_neg.error_message,
                                content_type='text/html' + "; charset=utf8",
                                status=415)
    else:
        # no feed of this page or type
        raise Http404


@cache_control(no_cache=True)
@never_cache
def all_atom(request):
    """ Redirects requests from legacy '/all'/.atom' to
        the manifest list above
    """
    url = request.get_full_path()
    new_url = '/manifest/.atom'
    if '?' in url:
        url_ex = url.split('?')
        new_url += '?' + url_ex[1]
    return redirect(new_url, permanent=True)
