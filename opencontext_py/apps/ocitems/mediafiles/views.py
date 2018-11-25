import json
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.entities.redirects.manage import RedirectURL
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from opencontext_py.apps.ocitems.ocitem.views import items_graph
from django.template import RequestContext, loader
from django.utils.cache import patch_vary_headers


# A media resource describes metadata about a binary file (usually an image)
# A media resource will have links to different versions of the binary file
# so that thumbnail, preview, and other versions can be discovered. However
# these other versions are "part" of an abstract media resource

ITEM_TYPE = 'media'

def index(request):
    """ Redirects requests from the media index
        to the media-search view
    """
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    new_url =  base_url + '/media-search/'
    return redirect(new_url, permanent=True)


def html_view(request, uuid, full_view=False):
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
    # Construnct the item
    ocitem = OCitem()
    ocitem.get_item(uuid)
    if not ocitem.manifest:
        # Did not find a record for the table, check for redirects
        r_url = RedirectURL()
        r_ok = r_url.get_direct_by_type_id(ITEM_TYPE, uuid)
        if r_ok:
            # found a redirect!!
            return redirect(r_url.redirect, permanent=r_url.permanent)
        # raise Http404
        raise Http404
    request.uuid = ocitem.manifest.uuid
    request.project_uuid = ocitem.manifest.project_uuid
    request.item_type = ocitem.manifest.item_type
    rp = RootPath()
    base_url = rp.get_baseurl()
    temp_item = TemplateItem(request)
    temp_item.read_jsonld_dict(ocitem.json_ld)
    if full_view:
        template = loader.get_template('media/full.html')
    else:
        template = loader.get_template('media/view.html')
    if not temp_item.view_permitted:
        # The client is not allowed to see this.
        template = loader.get_template('items/view401.html')
        context = {
            'item': temp_item,
            'base_url': base_url,
            'user': request.user
        }
        return HttpResponse(template.render(context, request), status=401)
    # Now add templated item to the a response object
    context = {
        'item': temp_item,
        'fullview': full_view,
        'base_url': base_url,
        'user': request.user
    }
    response = HttpResponse(template.render(context, request))
    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
    return response
            


# render the full version of the image (if an image)
def html_full(request, uuid):
    # Same thing as HTML, just with a full view argument.
    return html_view(request, uuid, full_view=True)

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

