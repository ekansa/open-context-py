import json
from django.http import HttpResponse, Http404
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.ocitems.octypes.supplement import TypeSupplement
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from django.template import RequestContext, loader


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
        rp = RootPath()
        base_url = rp.get_baseurl()
        ts = TypeSupplement(ocitem.json_ld)
        ocitem.json_ld = ts.get_arachne_comparanda()
        temp_item = TemplateItem(request)
        temp_item.read_jsonld_dict(ocitem.json_ld)
        if temp_item.view_permitted:
            template = loader.get_template('types/view.html')
            context = RequestContext(request,
                                     {'item': temp_item,
                                      'base_url': base_url})
            return HttpResponse(template.render(context))
        else:
            template = loader.get_template('items/view401.html')
            context = RequestContext(request,
                                     {'item': temp_item,
                                      'base_url': base_url})
            return HttpResponse(template.render(context), status=401)
    else:
        raise Http404


def json_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid)
    if(ocitem.manifest is not False):
        ts = TypeSupplement(ocitem.json_ld)
        ocitem.json_ld = ts.get_arachne_comparanda()
        json_output = json.dumps(ocitem.json_ld,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output, content_type='application/json; charset=utf8')
    else:
        raise Http404
