import json
from django.conf import settings
from django.http import HttpResponse, Http404
from django.template import RequestContext, loader
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.oai.models import OAIpmh

def index(request):
    return HttpResponse("Hello, world. You're at the OAI index.")


def oai_view(request):
    """ Get the item context JSON-LD """
    oai_obj = OAIpmh()
    req_neg = RequestNegotiation('application/xml')
    req_neg.supported_types = ['application/xml']
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        xml = oai_obj.process_verb(request)
        return HttpResponse(json.dumps(json_ld,
                            ensure_ascii=False, indent=4),
                            content_type=req_neg.use_response_type + "; charset=utf8")
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)
