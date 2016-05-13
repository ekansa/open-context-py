import json
import mimetypes
import requests
import logging
from django.http import HttpResponse, Http404
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.generalapi import GeneralAPI
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.entities.entity.templating import EntityTemplate
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


# These views display an HTML form for classifying import fields,
# and handles AJAX requests / responses to change classifications
def index(request):
    return HttpResponse("Hello, world. You're at the entities index.")


@cache_control(no_cache=True)
@never_cache
def hierarchy_children(request, identifier):
    """ Returns JSON data for an identifier in its hierarchy """
    et = EntityTemplate()
    children = et.get_described_children(identifier)
    if children is not False:
        json_output = json.dumps(children,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404


@cache_control(no_cache=True)
@never_cache
def look_up(request, item_type):
    """ Returns JSON data for entities
        limited by certain criteria
    """
    ent = Entity()
    qstring = ''
    class_uri = False
    project_uuid = False
    vocab_uri = False
    ent_type = False
    context_uuid = False
    data_type = False
    if len(item_type) < 2:
        item_type = False
    if 'q' in request.GET:
        qstring = request.GET['q']
    if 'class_uri' in request.GET:
        class_uri = request.GET['class_uri']
    if 'project_uuid' in request.GET:
        project_uuid = request.GET['project_uuid']
    if 'vocab_uri' in request.GET:
        vocab_uri = request.GET['vocab_uri']
    if 'ent_type' in request.GET:
        ent_type = request.GET['ent_type']
    if 'context_uuid' in request.GET:
        context_uuid = request.GET['context_uuid']
    if 'data_type' in request.GET:
        data_type = request.GET['data_type']
    entity_list = ent.search(qstring,
                             item_type,
                             class_uri,
                             project_uuid,
                             vocab_uri,
                             ent_type,
                             context_uuid,
                             data_type)
    json_output = json.dumps(entity_list,
                             indent=4,
                             ensure_ascii=False)
    return HttpResponse(json_output,
                        content_type='application/json; charset=utf8')


@cache_control(no_cache=True)
@never_cache
def id_summary(request, identifier):
    """ Returns JSON data for entities
        limited by certain criteria
    """
    lequiv = LinkEquivalence()
    id_list = lequiv.get_identifier_list_variants(identifier)
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
            entity_obj['project_uuid'] = ent.project_uuid
            break
    if entity_obj is not False:
        json_output = json.dumps(entity_obj,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404


@cache_control(no_cache=True)
@never_cache
def entity_annotations(request, subject):
    """ Returns JSON data with
        annotations on a given subject entity
    """
    ent = Entity()
    found = ent.dereference(subject)
    if found is False:
        found = ent.dereference(subject, subject)
    if found:
        # we found the subject entity, now get linked data assertions
        # make an object for computing hrefs to local host version of OC-URIs
        rp = RootPath()
        # make a result dict
        result = LastUpdatedOrderedDict()
        result['list'] = []  # list of link data annotations
        result['preds_objs'] = [] # list of predicates, then of objects
        result['stable_ids'] = [] # list of stable_ids
        la_list = LinkAnnotation.objects\
                                .filter(subject=subject)\
                                .order_by('predicate_uri', 'sort')
        for la in la_list:
            item = LastUpdatedOrderedDict()
            obj_item = LastUpdatedOrderedDict()
            item['hash_id'] = la.hash_id
            obj_item['hash_id'] = la.hash_id
            item['subject'] = la.subject
            item['subject_type'] = la.subject_type
            item['project_uuid'] = la.project_uuid
            if la.sort is None:
                la.sort = 0
            item['sort'] = float(la.sort)
            obj_item['sort'] = float(la.sort)
            item['predicate_uri'] = la.predicate_uri
            p_ent = Entity()
            p_found = p_ent.dereference(la.predicate_uri)
            if p_found:
                item['predicate_label'] = p_ent.label
            else:
                item['predicate_label'] = False
            item['object_uri'] = la.object_uri
            obj_item['id'] = la.object_uri
            obj_item['href'] = obj_item['id'].replace(settings.CANONICAL_HOST,
                                                      rp.get_baseurl())
            o_ent = Entity()
            o_found = o_ent.dereference(la.object_uri)
            if o_found:
                item['object_label'] = o_ent.label
                obj_item['label'] = o_ent.label
            else:
                item['object_label'] = False
                obj_item['label'] = False
            pred_key_found = False
            for pred_list in result['preds_objs']:
                if pred_list['id'] == la.predicate_uri:
                    pred_list['objects'].append(obj_item)
                    pred_key_found = True
            if pred_key_found is False:
                pred_obj = LastUpdatedOrderedDict()
                pred_obj['id'] = item['predicate_uri']
                pred_obj['label'] = item['predicate_label']
                pred_obj['href'] = pred_obj['id'].replace(settings.CANONICAL_HOST,
                                                          rp.get_baseurl())
                if 'https://' not in pred_obj['href'] \
                   and 'http://' not in pred_obj['href']:
                    pred_obj['href'] = False
                pred_obj['objects'] = [obj_item]
                result['preds_objs'].append(pred_obj)
            result['list'].append(item)
        # now lets get any stable identifiers for this item
        s_ids = StableIdentifer.objects\
                               .filter(uuid=ent.uuid)
        id_type_prefixes = StableIdentifer.ID_TYPE_PREFIXES
        for s_id in s_ids:
            stable_id = LastUpdatedOrderedDict()
            stable_id['type'] = s_id.stable_type
            stable_id['stable_id'] = s_id.stable_id
            stable_id['id'] = False
            if s_id.stable_type in id_type_prefixes:
                stable_id['id'] = id_type_prefixes[s_id.stable_type]
                stable_id['id'] += s_id.stable_id
            result['stable_ids'].append(stable_id)
        json_output = json.dumps(result,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404


@cache_control(no_cache=True)
@never_cache
def contain_children(request, identifier):
    """ Returns JSON data with
        spatial containment for a given
        uuid identiffied entity
    """
    ent = Entity()
    found = ent.dereference(identifier)
    if found:
        depth = 1
        recursive = False
        if 'depth' in request.GET:
            try:
                depth = int(float(request.GET['depth']))
            except:
                depth = 1
        et = EntityTemplate()
        children = et.get_containment_children(ent,
                                               depth)
        json_output = json.dumps(children,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404


@cache_control(no_cache=True)
@never_cache
def description_hierarchy(request, identifier):
    """ Returns JSON data with
        descriptive property and type hierarchies
        for a given uuid identiffied entity
    """
    item_type = False
    class_uri = False
    if '/' in identifier:
        id_ex = identifier.split('/')
        identifier = id_ex[0]
        if len(id_ex) >= 2:
            item_type = id_ex[1]
        if len(id_ex) >= 3:
            class_uri = id_ex[2]
    ent = Entity()
    found = ent.dereference(identifier)
    if found:
        depth = 1
        recursive = False
        if 'depth' in request.GET:
            try:
                depth = int(float(request.GET['depth']))
            except:
                depth = 1
        et = EntityTemplate()
        children = et.get_description_tree(ent,
                                           depth,
                                           True,
                                           item_type,
                                           class_uri)
        json_output = json.dumps(children,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404


def proxy(request, target_url):
    """ Proxy request so as to get around CORS
        issues for displaying PDFs with javascript
        and other needs
    """
    gapi = GeneralAPI()
    if 'https:' in target_url:
        target_url = target_url.replace('https:', 'http:')
    if 'http://' not in target_url:
        target_url = target_url.replace('http:/', 'http://')
    ok = True
    status_code = 404
    print('Try to see: ' + target_url)
    try:
        r = requests.get(target_url,
                         timeout=240,
                         headers=gapi.client_headers)
        status_code = r.status_code
        r.raise_for_status()
    except:
        ok = False
        content = target_url + ' ' + str(status_code)
    if ok:
        status_code = r.status_code
        mimetype = r.headers['Content-Type']
        content = r.content
        return HttpResponse(content,
                            status=status_code,
                            content_type=mimetype)
    else:
        return HttpResponse('Fail with HTTP status: ' + str(content),
                            status=status_code,
                            content_type='text/plain')
