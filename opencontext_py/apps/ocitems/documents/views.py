import json
from django.http import HttpResponse, Http404
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from django.template import RequestContext, loader


# A document item is a text document (usually HTML/XHTML)
# item where the content is structured text, not a binary file
# which would be a media resource item
def index(request):
    return HttpResponse("Hello, world. You're at the documnents index.")


def html_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid)
    if(ocitem.manifest is not False):
        rp = RootPath()
        base_url = rp.get_baseurl()
        temp_item = TemplateItem(request)
        if temp_item.view_permitted:
            temp_item.read_jsonld_dict(ocitem.json_ld)
            template = loader.get_template('documents/view.html')
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
        json_output = json.dumps(ocitem.json_ld,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404
