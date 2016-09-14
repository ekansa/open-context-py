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
        if found is False:
            found = ent.dereference(test_id, test_id)
        if found:
            entity_obj = LastUpdatedOrderedDict()
            entity_obj['id'] = ent.uri
            entity_obj['label'] = ent.label
            entity_obj['uuid'] = ent.uuid
            entity_obj['slug'] = ent.slug
            entity_obj['entity_type'] = ent.entity_type
            entity_obj['vocab_uri'] = ent.vocab_uri
            if ent.uri == ent.vocab_uri:
                # request of a vocabulary, not a specific entity
                t_vocab = TemplateVocab()
                t_vocab.uri = ent.uri
                t_vocab.vocab_uri = ent.vocab_uri
                t_vocab.get_comments()
                t_vocab.get_top_entities()
                entity_obj['comment'] = t_vocab.default_comment
                entity_obj['rdfs:comment'] = t_vocab.comment
                entity_obj['top_classes'] = t_vocab.top_classes
                entity_obj['top_properties'] = t_vocab.top_properties
            else:
                # request an entity in a vocabulary
                t_vocab = TemplateVocab()
                t_vocab.vocab_uri = ent.vocab_uri
                t_vocab.uri = ent.uri
                t_vocab.get_comments()
                t_vocab.get_entity_parents()
                t_vocab.get_entity_children()
                entity_obj['comment'] = t_vocab.default_comment
                entity_obj['rdfs:comment'] = t_vocab.comment
                entity_obj['parents'] = t_vocab.parents
                entity_obj['children'] = t_vocab.children
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
        req_neg = RequestNegotiation('text/html')
        req_neg.supported_types = ['application/ld+json',
                                   'application/json']
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            if 'json' in req_neg.use_response_type:
                # content negotiation requested JSON or JSON-LD
                return HttpResponse(json.dumps(entity_obj,
                                    ensure_ascii=False, indent=4),
                                    content_type=req_neg.use_response_type + "; charset=utf8")
            else:
                template = loader.get_template('vocabularies/temp.html')
                context = RequestContext(request,
                                         {'item': entity_obj,
                                          'base_url': base_url,
                                          'page_title': 'Open Context: Vocabularies + Ontologies',
                                          'act_nav': 'vocabularies',
                                          'nav_items': settings.NAV_ITEMS})
                return HttpResponse(template.render(context))
        else:
             # client wanted a mimetype we don't support
            return HttpResponse(req_neg.error_message,
                                content_type="text/plain; charset=utf8",
                                status=415)
    else:
        raise Http404


@cache_control(no_cache=True)
@never_cache
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
    entity_obj = False
    for test_id in id_list:
        ent = Entity()
        found = ent.dereference(test_id)
        if found is False:
            found = ent.dereference(test_id, test_id)
        if found:
            entity_obj = LastUpdatedOrderedDict()
            entity_obj['id'] = ent.uri
            entity_obj['label'] = ent.label
            entity_obj['uuid'] = ent.uuid
            entity_obj['slug'] = ent.slug
            entity_obj['entity_type'] = ent.entity_type
            entity_obj['vocab_uri'] = ent.vocab_uri
            ent_voc = Entity()
            vocab_found = ent_voc.dereference(ent.vocab_uri)
            if ent.uri == ent.vocab_uri:
                # request of a vocabulary, not a specific entity
                t_vocab = TemplateVocab()
                t_vocab.uri = ent.uri
                t_vocab.vocab_uri = ent.vocab_uri
                t_vocab.get_comments()
                t_vocab.get_top_entities()
                entity_obj['rdfs:comment'] = t_vocab.comment
                entity_obj['top_classes'] = t_vocab.top_classes
                entity_obj['top_properties'] = t_vocab.top_properties
            else:
                # request an entity in a vocabulary
                t_vocab = TemplateVocab()
                t_vocab.vocab_uri = ent.vocab_uri
                t_vocab.uri = ent.uri
                t_vocab.get_comments()
                t_vocab.get_entity_parents()
                t_vocab.get_entity_children()
                entity_obj['rdfs:comment'] = t_vocab.comment
                entity_obj['parents'] = t_vocab.parents
                entity_obj['children'] = t_vocab.children
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
        req_neg = RequestNegotiation('application/ld+json')
        req_neg.supported_types = ['application/json']
        if 'HTTP_ACCEPT' in request.META:
            req_neg.check_request_support(request.META['HTTP_ACCEPT'])
        if req_neg.supported:
            return HttpResponse(json.dumps(entity_obj,
                                ensure_ascii=False, indent=4),
                                content_type=req_neg.use_response_type + "; charset=utf8")
        else:
             # client wanted a mimetype we don't support
            return HttpResponse(req_neg.error_message,
                                content_type="text/plain; charset=utf8",
                                status=415)
    else:
        raise Http404