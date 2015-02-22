import json
from django.http import HttpResponse, Http404
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from django.template import RequestContext, loader


# A project resource represents a work of research data
# and media contributed to Open Context
def index(request):
    return HttpResponse("Hello, world. You're at the projects index.")


def html_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid, True)
    if(ocitem.manifest is not False):
        rp = RootPath()
        base_url = rp.get_baseurl()
        temp_item = TemplateItem()
        temp_item.read_jsonld_dict(ocitem.json_ld)
        template = loader.get_template('projects/view.html')
        context = RequestContext(request,
                                 {'item': temp_item,
                                  'base_url': base_url})
        return HttpResponse(template.render(context))
    else:
        raise Http404


def json_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid, True)
    if(ocitem.manifest is not False):
        json_output = json.dumps(ocitem.json_ld,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404
