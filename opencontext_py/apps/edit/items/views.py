import json
from django.http import HttpResponse, Http404
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from django.template import RequestContext, loader


# These views provide forms for editing items
def index(request):
    return HttpResponse("Hello, world. You're at the edit index.")


def html_view(request, uuid):
    ocitem = OCitem()
    ocitem.get_item(uuid)
    if(ocitem.manifest is not False):
        temp_item = TemplateItem(request)
        temp_item.check_edit_permitted = True
        temp_item.read_jsonld_dict(ocitem.json_ld)
        if temp_item.edit_permitted:
            template = loader.get_template('edit/view.html')
            context = RequestContext(request,
                                     {'item': temp_item})
            return HttpResponse(template.render(context))
        else:
            template = loader.get_template('edit/view401.html')
            context = RequestContext(request,
                                     {'item': temp_item})
            return HttpResponse(template.render(context), status=401)
    else:
        raise Http404
