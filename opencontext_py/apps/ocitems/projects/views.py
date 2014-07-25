from django.http import HttpResponse, Http404
from opencontext_py.apps.ocitems.ocitem.models import OCitem
import json


# A project resource represents a work of research data
# and media contributed to Open Context
def index(request):
    return HttpResponse("Hello, world. You're at the projects index.")


def html_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid, True)
    if(ocitem.manifest is not False):
        return HttpResponse("Hello, world. You're at the project htmlView of " + str(uuid))
    else:
        raise Http404


def json_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid, True)
    if(ocitem.manifest is not False):
        json_output = json.dumps(ocitem.json_ld,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output, mimetype='application/json; charset=utf8')
    else:
        raise Http404
