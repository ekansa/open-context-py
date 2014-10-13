import json
from django.http import HttpResponse, Http404
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.entities.entity.templating import EntityTemplate


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