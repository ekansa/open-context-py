import json
from django.http import HttpResponse, Http404
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.entities.entity.templating import EntityTemplate


# These views display an HTML form for classifying import fields,
# and handles AJAX requests / responses to change classifications
def index(request):
    return HttpResponse("Hello, world. You're at the entities index.")


def hierarchy_children(request, identifier):
    """ JSON data for an identifier in its hierarchy """
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

