import json
from django.http import HttpResponse, Http404
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from django.template import RequestContext, loader


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
        temp_item = TemplateItem(request)
        temp_item.read_jsonld_dict(ocitem.json_ld)
        if temp_item.view_permitted:
            template = loader.get_template('media/view.html')
            context = RequestContext(request,
                                     {'item': temp_item})
            return HttpResponse(template.render(context))
        else:
            template = loader.get_template('items/view401.html')
            context = RequestContext(request,
                                     {'item': temp_item})
            return HttpResponse(template.render(context), status=401)
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
