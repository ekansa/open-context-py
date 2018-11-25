import json
from django.http import HttpResponse, Http404
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from opencontext_py.apps.entities.redirects.manage import RedirectURL
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from opencontext_py.apps.ocitems.ocitem.views import items_graph
from django.template import RequestContext, loader
from django.utils.cache import patch_vary_headers


# A person resource describes metadata about a person or organization
# that played some role in creating, describing, or managing data in Open Context
# These are basically foaf:Agent items
ITEM_TYPE = 'persons'

def index(request):
    request = RequestNegotiation().anonymize_request(request)
    rp = RootPath()
    base_url = rp.get_baseurl()
    new_url = base_url + '/search/?type=persons'
    return redirect(new_url, permanent=True)


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
    # Proceed with constructing the HTML item
    ocitem = OCitem()
    if 'hashes' in request.GET:
        ocitem.assertion_hashes = True
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
    temp_item = TemplateItem(request)
    temp_item.read_jsonld_dict(ocitem.json_ld)
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
    template = loader.get_template('persons/view.html')
    context = {
        'item': temp_item,
        'base_url': base_url,
        'user': request.user
    }
    response = HttpResponse(template.render(context, request))
    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
    return response

def json_view(request, uuid):
    """Returns a JSON media response for an item"""
    return items_graph(
        request, uuid, return_media='application/json', item_type=ITEM_TYPE)

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