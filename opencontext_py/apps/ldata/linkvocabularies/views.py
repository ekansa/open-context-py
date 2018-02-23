import json
from django.conf import settings
from django.http import HttpResponse, Http404
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from django.template import RequestContext, loader
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ldata.linkvocabularies.templating import TemplateVocab
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


# An vocabulary item displays entities in a SKOS controlled vocabulary
# or OWL ontology
# this is still largely "to do" and has a short term kludge
# to show DINAA
@cache_control(no_cache=True)
@never_cache
def index_view(request):
    """ Get the search context JSON-LD """
    rp = RootPath()
    base_url = rp.get_baseurl()
    req_neg = RequestNegotiation('text/html')
    if 'HTTP_ACCEPT' in request.META:
        req_neg.check_request_support(request.META['HTTP_ACCEPT'])
    if req_neg.supported:
        # requester wanted a mimetype we DO support
        template = loader.get_template('vocabularies/index.html')
        context =  {
            'base_url': base_url,
            'page_title': 'Open Context: Vocabularies + Ontologies',
            'act_nav': 'vocabularies',
            'nav_items': settings.NAV_ITEMS
        }
        return HttpResponse(template.render(context, request))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


# @cache_control(no_cache=True)
# @never_cache
def html_view(request, identifier):
    rp = RootPath()
    base_url = rp.get_baseurl()
    uri = 'http://opencontext.org/vocabularies/' + str(identifier)
    lequiv = LinkEquivalence()
    id_list = lequiv.get_identifier_list_variants(uri)
    lequiv = LinkEquivalence()
    id_s_list = lequiv.get_identifier_list_variants(uri + '/')
    for id_s in id_s_list:
        if id_s not in id_list:
            # add the slashed version to the list
            id_list.append(id_s)
    entity = False
    for test_id in id_list:
        ent = Entity()
        found = ent.dereference(test_id)
        if found is False:
            found = ent.dereference(test_id, test_id)
        if found:
            entity = ent
            break
    if entity is not False:
        t_vocab = TemplateVocab()
        t_vocab.create_template_for_entity(entity)
        t_vocab.make_json_for_html()
        req_neg = RequestNegotiation('text/html')
        req_neg.supported_types = ['application/ld+json',
                                   'application/json']
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            if 'json' in req_neg.use_response_type:
                # content negotiation requested JSON or JSON-LD
                json_obj = t_vocab.make_json_obj()
                return HttpResponse(json.dumps(json_obj,
                                    ensure_ascii=False, indent=4),
                                    content_type=req_neg.use_response_type + "; charset=utf8")
            else:
                template = loader.get_template('vocabularies/view.html')
                context = {
                    'item': t_vocab,
                    'base_url': base_url,
                    'page_title': 'Open Context: Vocabularies + Ontologies',
                    'act_nav': 'vocabularies',
                    'nav_items': settings.NAV_ITEMS
                }
                return HttpResponse(template.render(context, request))
        else:
             # client wanted a mimetype we don't support
            return HttpResponse(req_neg.error_message,
                                content_type="text/plain; charset=utf8",
                                status=415)
    else:
        raise Http404


# @cache_control(no_cache=True)
# @never_cache
def json_view(request, identifier):
    rp = RootPath()
    base_url = rp.get_baseurl()
    uri = 'http://opencontext.org/vocabularies/' + str(identifier)
    lequiv = LinkEquivalence()
    id_list = lequiv.get_identifier_list_variants(uri)
    lequiv = LinkEquivalence()
    id_s_list = lequiv.get_identifier_list_variants(uri + '/')
    for id_s in id_s_list:
        if id_s not in id_list:
            # add the slashed version to the list
            id_list.append(id_s)
    entity = False
    for test_id in id_list:
        ent = Entity()
        found = ent.dereference(test_id)
        if found is False:
            found = ent.dereference(test_id, test_id)
        if found:
            entity = ent
            break
    if entity is not False:
        t_vocab = TemplateVocab()
        t_vocab.create_template_for_entity(entity)
        json_obj = t_vocab.make_json_obj()
        req_neg = RequestNegotiation('application/ld+json')
        req_neg.supported_types = ['application/json']
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            return HttpResponse(json.dumps(json_obj,
                                ensure_ascii=False, indent=4),
                                content_type=req_neg.use_response_type + "; charset=utf8")
        else:
             # client wanted a mimetype we don't support
            return HttpResponse(req_neg.error_message,
                                content_type="text/plain; charset=utf8",
                                status=415)
    else:
        raise Http404