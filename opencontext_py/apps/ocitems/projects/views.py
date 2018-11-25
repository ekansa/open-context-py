import json
from django.http import HttpResponse, Http404
from django.shortcuts import redirect

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.entities.redirects.manage import RedirectURL
from opencontext_py.apps.ocitems.ocitem.generation import OCitem as OCitemNew
from opencontext_py.apps.ocitems.ocitem.htmltemplating import HTMLtemplate
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from opencontext_py.apps.ocitems.projects.content import ProjectContent
from opencontext_py.apps.ocitems.projects.layers import ProjectLayers
from opencontext_py.apps.ocitems.ocitem.views import items_graph

from django.template import RequestContext, loader
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.utils.cache import patch_vary_headers

ITEM_TYPE = 'projects'

# Returns a search interface to browse projects
def index(request):
    """ redirects requests from the projects index
        to the project-search view
    """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    new_url =  base_url + '/projects-search/'
    return redirect(new_url, permanent=True)


@cache_control(no_cache=True)
@never_cache
def html_view_new(request, uuid):
    request = RequestNegotiation().anonymize_request(request)
    # Handle some content negotiation for the item.    
    req_neg = RequestNegotiation('text/html')
    req_neg.supported_types = []
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if not req_neg.supported:
        # The client may be wanting a non-HTML representation, so
        # use the following function to get it.
        return items_graph(request, uuid, item_type=ITEM_TYPE)
    # Proceed with constructing the HTML item
    ocitem = OCitemNew()
    if 'hashes' in request.GET:
        ocitem.assertion_hashes = True
    exists = ocitem.check_exists(uuid)
    if not exists:
        # Did not find a record for the table, check for redirects
        r_url = RedirectURL()
        r_ok = r_url.get_direct_by_type_id(ITEM_TYPE, uuid)
        if r_ok:
            # found a redirect!!
            return redirect(r_url.redirect, permanent=r_url.permanent)
        # raise Http404
        raise Http404
    # Construnct item the JSON-LD 
    ocitem.generate_json_ld()
    rp = RootPath()
    base_url = rp.get_baseurl()
    proj_content = ProjectContent(ocitem.manifest.uuid,
                                  ocitem.manifest.slug,
                                  ocitem.json_ld)
    html_temp = HTMLtemplate()
    html_temp.proj_context_json_ld = ocitem.proj_context_json_ld
    html_temp.proj_content = proj_content.get_project_content()
    html_temp.read_jsonld_dict(ocitem.json_ld)
    template = loader.get_template('projects/view.html')
    context = {
        'item': html_temp,
        'base_url': base_url,
        'user': request.user
    }
    response = HttpResponse(template.render(context, request))
    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
    return response

def html_view(request, uuid):
    request = RequestNegotiation().anonymize_request(request)
    # Handle some content negotiation for the item.    
    req_neg = RequestNegotiation('text/html')
    req_neg.supported_types = []
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if not req_neg.supported:
        # The client may be wanting a non-HTML representation, so
        # use the following function to get it.
        return items_graph(request, uuid, item_type=ITEM_TYPE)
    if request.GET.get('new') is not None:
        return html_view_new(request, uuid)
    ocitem = OCitem()
    ocitem.get_item(uuid, True)
    if not ocitem.manifest:
        # Did not find a record for the table, check for redirects
        r_url = RedirectURL()
        r_ok = r_url.get_direct_by_type_id(ITEM_TYPE, uuid)
        if r_ok:
            # found a redirect!!
            return redirect(r_url.redirect, permanent=r_url.permanent)
        # raise Http404
        raise Http404
    # Construnct item the JSON-LD    
    request.uuid = ocitem.manifest.uuid
    request.project_uuid = ocitem.manifest.project_uuid
    request.item_type = ocitem.manifest.item_type
    rp = RootPath()
    base_url = rp.get_baseurl()
    proj_content = ProjectContent(ocitem.manifest.uuid,
                                  ocitem.manifest.slug,
                                  ocitem.json_ld)
    temp_item = TemplateItem()
    temp_item.proj_content = proj_content.get_project_content()
    temp_item.read_jsonld_dict(ocitem.json_ld)
    template = loader.get_template('projects/view.html')
    context = {
        'item': temp_item,
        'base_url': base_url,
        'user': request.user
    }
    response = HttpResponse(template.render(context, request))
    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
    return response


def layers_view(request, uuid):
    """View geospatial layers associated with a project. """
    ocitem = OCitem()
    ocitem.get_item(uuid, True)
    if not ocitem.manifest:
        raise Http404
    proj_layers = ProjectLayers(ocitem.manifest.uuid)
    proj_layers.get_geo_overlays()
    json_output = proj_layers.json_geo_overlay()
    if 'callback' in request.GET:
        funct = request.GET['callback']
        return HttpResponse(funct + '(' + json_output + ');',
                            content_type='application/javascript' + "; charset=utf8")
    return HttpResponse(json_output,
                        content_type="application/json; charset=utf8")

def json_view(request, uuid):
    """Returns a JSON media response for an item"""
    return items_graph(
        request, uuid, return_media='application/json', item_type=ITEM_TYPE)

def geojson_view(request, uuid):
    """Returns a GeoJSON media response for an item"""
    return items_graph(
        request, uuid, return_media='application/vnd.geo+json', item_type=ITEM_TYPE)

def jsonld_view(request, uuid):
    """Returns a JSON-LD media response for an item"""
    return items_graph(
        request, uuid, return_media='application/ld+json', item_type=ITEM_TYPE)

def nquads_view(request, uuid):
    """Returns a N-Quads media response for an item"""
    return items_graph(
        request, uuid, return_media='application/n-quads', item_type=ITEM_TYPE)

def ntrpls_view(request, uuid):
    """Returns a N-Triples media response for an item"""
    return items_graph(
        request, uuid, return_media='application/n-triples', item_type=ITEM_TYPE)

def rdf_view(request, uuid):
    """Returns a RDF/XML media response for an item"""
    return items_graph(
        request, uuid, return_media='application/rdf+xml', item_type=ITEM_TYPE)

def turtle_view(request, uuid):
    """Returns a Turtle media response for an item"""
    return items_graph(
        request, uuid, return_media='text/turtle', item_type=ITEM_TYPE)