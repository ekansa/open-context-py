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

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.icons.configs import DEFAULT_ITEM_TYPE_ICONS


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
            'url': base_url + '/highlights',
            'site_name': settings.CANONICAL_SITENAME,
            'description': (
                'Highlights of open access archaeological collections, data, media and '
                'documentation published by Open Context'
            ),
            'image': base_url + '/static/oc/images/index/oc-blue-square-logo.png',
        }
        template = loader.get_template('bootstrap_vue/highlights/highlights.html')
        context = {
            'BASE_URL': base_url,
            'PAGE_TITLE': 'Open Context: Highlights',
            'act_nav': 'highlights',
            'og': open_graph,
            'NAV_ITEMS': settings.NAV_ITEMS,
            'GOOGLE_MAPS': 'hide',
            'PAGE_MODIFIED': get_template_file_git_updated_datetime_str(
                'bootstrap_vue/highlights/highlights.html'
            ),
            'DEFAULT_ITEM_TYPE_ICONS': DEFAULT_ITEM_TYPE_ICONS,
        }
        return HttpResponse(template.render(context, request))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(
            req_neg.error_message,
            status=415
        )
