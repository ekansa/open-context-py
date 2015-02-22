import json
from django.http import HttpResponse, Http404
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.ocitems.ocitem.models import OCitem


# A person resource describes metadata about a person or organization
# that played some role in creating, describing, or managing data in Open Context
# These are basically foaf:Agent items
def index(request):
    return HttpResponse("Hello, world. You're at the persons index.")


def html_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid)
    if(ocitem.manifest is not False):
        rp = RootPath()
        base_url = rp.get_baseurl()
        return HttpResponse("Hello, world. You're at the person htmlView of " + str(uuid))
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
