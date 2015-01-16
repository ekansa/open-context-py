from django.http import HttpResponse, Http404
from opencontext_py.apps.ocitems.ocitem.models import OCitem
import json


# An octype item is a concept from a controlled vocabulary that originates from
# an Open Context contributor
# The main dependency for this app is for OCitems, which are used to generate
# Every type of item in Open Context, including subjects
def index(request):
    return HttpResponse("Hello, world. You're at the types index.")


def html_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid)
    if(ocitem.manifest is not False):
        return HttpResponse("Hello, world. You're at the type htmlView of " + str(uuid))
    else:
        raise Http404


def json_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid)
    if(ocitem.manifest is not False):
        json_output = json.dumps(ocitem.json_ld,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output, content_type='application/json; charset=utf8')
    else:
        raise Http404
