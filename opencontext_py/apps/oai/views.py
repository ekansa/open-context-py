import json
from django.conf import settings
from django.http import HttpResponse, Http404
from django.template import RequestContext, loader
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.oai.models import OAIpmh
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt


# @cache_control(no_cache=True)
# @never_cache
@csrf_exempt  # allow random post requests (doesn't change OC, so OK)
def index(request):
    """ Get the item context JSON-LD """
    oai_obj = OAIpmh()
    req_neg = RequestNegotiation('application/xml')
    req_neg.supported_types = ['application/xml']
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        xml = oai_obj.process_request(request)
        return HttpResponse(oai_obj.output_xml_string(),
                            content_type=req_neg.use_response_type + "; charset=utf8",
                            status=oai_obj.http_resp_code)
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)
