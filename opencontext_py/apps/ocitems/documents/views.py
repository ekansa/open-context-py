from django.http import HttpResponse
from opencontext_py.apps.ocitems.ocitem.models import OCitem
import json


# A document item is a text document (usually HTML/XHTML)
# item where the content is structured text, not a binary file
# which would be a media resource item
def index(request):
    return HttpResponse("Hello, world. You're at the documnents index.")


def html_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid)
    if(ocitem.manifest is not False):
        return HttpResponse("Hello, world. You're at the document htmlView of " + str(uuid))
    else:
        raise Http404


def json_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid)
    if(ocitem.manifest is not False):
        json_output = json.dumps(ocitem.json_ld,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404
