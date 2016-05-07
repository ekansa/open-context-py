import json
from django.conf import settings
from django.http import HttpResponse, Http404
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.requestnegotiation import RequestNegotiation
from django.template import RequestContext, loader
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
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
        context = RequestContext(request,
                                 {'base_url': base_url,
                                  'page_title': 'Open Context: Vocabularies + Ontologies',
                                  'act_nav': 'vocabularies',
                                  'nav_items': settings.NAV_ITEMS})
        return HttpResponse(template.render(context))
    else:
        # client wanted a mimetype we don't support
        return HttpResponse(req_neg.error_message,
                            status=415)


@cache_control(no_cache=True)
@never_cache
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
    entity_obj = False
    for test_id in id_list:
        ent = Entity()
        found = ent.dereference(test_id)
        if found:
            entity_obj = LastUpdatedOrderedDict()
            entity_obj['id'] = ent.uri
            entity_obj['label'] = ent.label
            entity_obj['uuid'] = ent.uuid
            entity_obj['slug'] = ent.slug
            entity_obj['item_type'] = ent.item_type
            entity_obj['class_uri'] = ent.class_uri
            entity_obj['data_type'] = ent.data_type
            entity_obj['vocab_uri'] = ent.vocab_uri
            ent_voc = Entity()
            vocab_found = ent_voc.dereference(ent.vocab_uri)
            if vocab_found:
                entity_obj['vocab_label'] = ent_voc.label
            else:
                entity_obj['vocab_label'] = ent.vocab_uri
            entity_obj['project_uuid'] = ent.project_uuid
            if 'dinaa' in ent.vocab_uri:
                entity_obj['github'] = 'https://github.com/ekansa/oc-ontologies/blob/master/vocabularies/dinaa-alt.owl'
            elif 'oc-general' in ent.vocab_uri:
                entity_obj['github'] = 'https://github.com/ekansa/oc-ontologies/blob/master/vocabularies/oc-general.owl'
            else:
                entity_obj['github'] = False
            break
    if entity_obj is not False:
        template = loader.get_template('vocabularies/temp.html')
        context = RequestContext(request,
                                 {'item': entity_obj,
                                  'base_url': base_url,
                                  'page_title': 'Open Context: Vocabularies + Ontologies',
                                  'act_nav': 'vocabularies',
                                  'nav_items': settings.NAV_ITEMS})
        return HttpResponse(template.render(context))
    else:
        raise Http404
