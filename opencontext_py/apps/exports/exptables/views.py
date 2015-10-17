import json
from django.http import HttpResponse, Http404
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.exports.exptables.models import ExpTable
from opencontext_py.apps.exports.exptables.templating import ExpTableTemplating
from django.template import RequestContext, loader


# An octype item is a concept from a controlled vocabulary that originates from
# an Open Context contributor
# The main dependency for this app is for OCitems, which are used to generate
# Every type of item in Open Context, including subjects
def index(request):
    return HttpResponse("Hello, world. You're at the types index.")


def html_view(request, table_id):
    exp_tt = ExpTableTemplating(table_id)
    if exp_tt.exp_tab is not False:
        rp = RootPath()
        base_url = rp.get_baseurl()
        template = loader.get_template('types/view.html')
        if temp_item.view_permitted:
            req_neg = RequestNegotiation('text/html')
            req_neg.supported_types = ['application/json',
                                       'application/ld+json']
            if 'HTTP_ACCEPT' in request.META:
                req_neg.check_request_support(request.META['HTTP_ACCEPT'])
            if req_neg.supported:
                if 'json' in req_neg.use_response_type:
                    # content negotiation requested JSON or JSON-LD
                    return HttpResponse(json.dumps(ocitem.json_ld,
                                        ensure_ascii=False, indent=4),
                                        content_type=req_neg.use_response_type + "; charset=utf8")
                else:
                    context = RequestContext(request,
                                             {'item': temp_item,
                                              'base_url': base_url})
                    return HttpResponse(template.render(context))
            else:
                # client wanted a mimetype we don't support
                return HttpResponse(req_neg.error_message,
                                    content_type=req_neg.use_response_type + "; charset=utf8",
                                    status=415)
        else:
            template = loader.get_template('items/view401.html')
            context = RequestContext(request,
                                     {'item': temp_item,
                                      'base_url': base_url})
            return HttpResponse(template.render(context), status=401)
    else:
        raise Http404


def json_view(request, table_id):
    exp_tt = ExpTableTemplating(table_id)
    if exp_tt.exp_tab is not False:
        json_ld = exp_tt.make_json_ld()
        req_neg = RequestNegotiation('application/json')
        req_neg.supported_types = ['application/ld+json']
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            json_output = json.dumps(json_ld,
                                     indent=4,
                                     ensure_ascii=False)
            return HttpResponse(json_output,
                                content_type=req_neg.use_response_type + "; charset=utf8")
        else:
            # client wanted a mimetype we don't support
            return HttpResponse(req_neg.error_message,
                                content_type=req_neg.use_response_type + "; charset=utf8",
                                status=415)
    else:
        raise Http404
