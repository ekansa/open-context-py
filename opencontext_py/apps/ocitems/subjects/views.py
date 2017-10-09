import json
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from opencontext_py.apps.ocitems.subjects.supplement import SubjectSupplement
from django.template import RequestContext, loader
from django.utils.cache import patch_vary_headers


# A subject is a generic item that is the subbject of observations
# A subject is the main type of record in open context for analytic data
# The main dependency for this app is for OCitems, which are used to generate
# Every type of item in Open Context, including subjects
def index(request):
    """ redirects requests from the subjects index
        to the subjects-search view
    """
    rp = RootPath()
    base_url = rp.get_baseurl()
    new_url = base_url + '/subjects-search/'
    return redirect(new_url, permanent=True)


def old_redirect_view(request):
    """ Redirects from the original PHP version of
        Open Context when ".php" was in URLs
    """
    rp = RootPath()
    base_url = rp.get_baseurl()
    new_url = base_url + '/subjects-search/'
    if 'item' in request.GET:
        uuid = request.GET['item']
        new_url = base_url + '/subjects/' + uuid
    return redirect(new_url, permanent=True)


def html_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid)
    if ocitem.manifest is not False:
        # check to see if there's related data via API calls. Add if so.
        request.uuid = ocitem.manifest.uuid
        request.project_uuid = ocitem.manifest.project_uuid
        request.item_type = ocitem.manifest.item_type
        subj_s = SubjectSupplement(ocitem.json_ld)
        ocitem.json_ld = subj_s.get_catal_related()
        rp = RootPath()
        base_url = rp.get_baseurl()
        temp_item = TemplateItem(request)
        temp_item.read_jsonld_dict(ocitem.json_ld)
        template = loader.get_template('subjects/view.html')
        if temp_item.view_permitted:
            req_neg = RequestNegotiation('text/html')
            req_neg.supported_types = ['application/json',
                                       'application/ld+json',
                                       'application/vnd.geo+json']
            if 'HTTP_ACCEPT' in request.META:
                req_neg.check_request_support(request.META['HTTP_ACCEPT'])
            if req_neg.supported:
                if 'json' in req_neg.use_response_type:
                    # content negotiation requested JSON or JSON-LD
                    request.content_type = req_neg.use_response_type
                    response = HttpResponse(json.dumps(ocitem.json_ld,
                                            ensure_ascii=False, indent=4),
                                            content_type=req_neg.use_response_type + "; charset=utf8")
                    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
                    return response
                else:
                    context = {
                        'item': temp_item,
                        'base_url': base_url,
                        'user': request.user
                    }
                    response = HttpResponse(template.render(context, request))
                    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
                    return response
            else:
                # client wanted a mimetype we don't support
                return HttpResponse(req_neg.error_message,
                                    content_type=req_neg.use_response_type + "; charset=utf8",
                                    status=415)
        else:
            template = loader.get_template('items/view401.html')
            context = {
                'item': temp_item,
                'base_url': base_url,
                'user': request.user
            }
            return HttpResponse(template.render(context, request), status=401)
    else:
        raise Http404


def json_view(request, uuid):
    """ returns a json representation """
    ocitem = OCitem()
    if 'hashes' in request.GET:
        ocitem.assertion_hashes = True
    ocitem.get_item(uuid)
    if ocitem.manifest is not False:
        request.uuid = ocitem.manifest.uuid
        request.project_uuid = ocitem.manifest.project_uuid
        request.item_type = ocitem.manifest.item_type
        req_neg = RequestNegotiation('application/json')
        req_neg.supported_types = ['application/ld+json',
                                   'application/vnd.geo+json']
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            request.content_type = req_neg.use_response_type
            json_output = json.dumps(ocitem.json_ld,
                                     indent=4,
                                     ensure_ascii=False)
            if 'callback' in request.GET:
                funct = request.GET['callback']
                return HttpResponse(funct + '(' + json_output + ');',
                                    content_type='application/javascript' + "; charset=utf8")
            else:
                return HttpResponse(json_output,
                                    content_type=req_neg.use_response_type + "; charset=utf8")
        else:
            # client wanted a mimetype we don't support
            return HttpResponse(req_neg.error_message,
                                content_type=req_neg.use_response_type + "; charset=utf8",
                                status=415)
    else:
        raise Http404
