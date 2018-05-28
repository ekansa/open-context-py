import json
from django.conf import settings
from django.shortcuts import redirect
from opencontext_py.apps.entities.redirects.manage import RedirectURL
from django.http import HttpResponse, Http404
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.exports.exptables.models import ExpTable
from opencontext_py.apps.exports.exptables.templating import ExpTableTemplating
from opencontext_py.apps.exports.exprecords.dump import CSVdump
from django.template import RequestContext, loader
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


# An table item caches a list of uuids, along with record values (as string literals)
# of attributes for download as a CSV file. It does some violence to the more
# elaborately structured aspects of Open Context's data model, but is convenient
# for most researchers.
@cache_control(no_cache=True)
@never_cache
def index_view(request, table_id=None):
    """ Get the search context JSON-LD """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        template = loader.get_template('tables/index.html')
        context = {
            'base_url': base_url,
            'page_title': 'Open Context: Tables',
            'act_nav': 'tables',
            'nav_items': settings.NAV_ITEMS,
            'user': request.user
        }
        return HttpResponse(template.render(context, request))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


@cache_control(no_cache=True)
@never_cache
def html_view(request, table_id):
    request = RequestNegotiation().anonymize_request(request)
    exp_tt = ExpTableTemplating(table_id)
    rp = RootPath()
    base_url = rp.get_baseurl()
    if exp_tt.exp_tab is not False:
        exp_tt.prep_html()
        template = loader.get_template('tables/view.html')
        if exp_tt.view_permitted:
            req_neg = RequestNegotiation('text/html')
            req_neg.supported_types = ['application/json',
                                       'application/ld+json',
                                       'text/csv']
            if 'HTTP_ACCEPT' in request.META:
                req_neg.check_request_support(request.META['HTTP_ACCEPT'])
            if req_neg.supported:
                if 'json' in req_neg.use_response_type:
                    # content negotiation requested JSON or JSON-LD
                    return HttpResponse(json.dumps(ocitem.json_ld,
                                        ensure_ascii=False, indent=4),
                                        content_type=req_neg.use_response_type + "; charset=utf8")
                elif 'csv' in req_neg.use_response_type:
                    return redirect(exp_tt.csv_url, permanent=False)
                else:
                    context = {
                        'page_title': exp_tt.exp_tab.label,
                        'item': exp_tt,
                        'base_url': base_url,
                        'user': request.user
                    }
                    return HttpResponse(template.render(context, request))
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
        # did not find a record for the table, check for redirects
        r_url = RedirectURL()
        r_ok = r_url.get_direct_by_type_id('tables', exp_tt.public_table_id)
        if r_ok:
            # found a redirect!!
            return redirect(r_url.redirect, permanent=r_url.permanent)
        else:
            # raise Http404
            template = loader.get_template('tables/index.html')
            context = {
                'base_url': base_url,
                'page_title': 'Open Context: Tables',
                'act_nav': 'tables',
                'nav_items': settings.NAV_ITEMS,
                'user': request.user
            }
            return HttpResponse(template.render(context, request))


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


def csv_view(request, table_id):
    request = RequestNegotiation().anonymize_request(request)
    exp_tt = ExpTableTemplating(table_id)
    if exp_tt.exp_tab is not False:
        exp_tt.prep_csv()
        req_neg = RequestNegotiation('text/csv')
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            if isinstance(exp_tt.csv_url, str):
                return redirect(exp_tt.csv_url, permanent=False)
            else:
                dump = CSVdump()
                return dump.web_dump(exp_tt.table_id)
        else:
            # client wanted a mimetype we don't support
            return HttpResponse(req_neg.error_message,
                                content_type=req_neg.use_response_type + "; charset=utf8",
                                status=415)
    else:
        raise Http404
