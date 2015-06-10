import json
from django.http import HttpResponse, Http404
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.entities.entity.templating import EntityTemplate
from opencontext_py.apps.ldata.linkannotations.models import LinkAnnotation
from opencontext_py.apps.ocitems.identifiers.models import StableIdentifer
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence

# These views display an HTML form for classifying import fields,
# and handles AJAX requests / responses to change classifications
def index(request):
    return HttpResponse("Hello, world. You're at the entities index.")


def hierarchy_children(request, identifier):
    """ Returns JSON data for an identifier in its hierarchy """
    et = EntityTemplate()
    children = et.get_children(identifier)
    if children is not False:
        json_output = json.dumps(children,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404


def look_up(request, item_type):
    """ Returns JSON data for entities
        limited by certain criteria
    """
    ent = Entity()
    qstring = ''
    class_uri = False
    project_uuid = False
    vocab_uri = False
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
    entity_list = ent.search(qstring,
                             item_type,
                             class_uri,
                             project_uuid,
                             vocab_uri)
    json_output = json.dumps(entity_list,
                             indent=4,
                             ensure_ascii=False)
    return HttpResponse(json_output,
                        content_type='application/json; charset=utf8')

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
        result = LastUpdatedOrderedDict()
        result['list'] = []
        result['pred-key-objs'] = []
        result['stable-ids'] = []
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
            o_ent = Entity()
            o_found = o_ent.dereference(la.object_uri)
            if o_found:
                item['object_label'] = o_ent.label
                obj_item['label'] = o_ent.label
            else:
                item['object_label'] = False
                obj_item['label'] = False
            pred_key_found = False
            for pred_list in result['pred-key-objs']:
                if pred_list['id'] == la.predicate_uri:
                    pred_list['objects'].append(obj_item)
                    pred_key_found = True
            if pred_key_found is False:
                pred_obj = LastUpdatedOrderedDict()
                pred_obj['id'] = item['predicate_uri']
                pred_obj['label'] = item['predicate_label']
                pred_obj['objects'] = [obj_item]
                result['pred-key-objs'].append(pred_obj)
            result['list'].append(item)
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
            result['stable-ids'].append(stable_id)
        json_output = json.dumps(result,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404