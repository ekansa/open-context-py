from django.http import HttpResponse
from opencontext_py.apps.ocitems.ocitem.models import OCitem
import json


# A media resource describes metadata about a binary file (usually an image)
# A media resource will have links to different versions of the binary file
# so that thumbnail, preview, and other versions can be discovered. However
# these other versions are "part" of an abstract media resource
def index(request):
    return HttpResponse("Hello, world. You're at the media index.")


def html_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid)
    if(ocitem.manifest is not False):
        return HttpResponse("Hello, world. You're at the media htmlView of " + str(uuid))
    else:
        raise Http404


def json_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid)
    if(ocitem.manifest is not False):
        json_output = json.dumps(ocitem.json_ld,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output, mimetype='application/json; charset=utf8')
    else:
        raise Http404
