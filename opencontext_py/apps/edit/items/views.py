import json
from django.http import HttpResponse, Http404
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from opencontext_py.apps.edit.items.model import ItemEdit
from django.template import RequestContext, loader
from django.views.decorators.csrf import ensure_csrf_cookie


# These views provide forms for editing items
def index(request):
    return HttpResponse("Hello, world. You're at the edit index.")


@ensure_csrf_cookie
def html_view(request, uuid):
    """ Displays the HTML item editing interface """
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


def update_item(request, uuid):
    """ Handles POST requests to update an item """
    item_edit = ItemEdit(uuid, request)
    if item_edit.manifest is not False:
        if request.method == 'POST':
            if item_edit.edit_permitted:
                result = {}
                if 'label' in request.POST:
                    result = item_edit.update_label(request.POST['label'])
                if 'class_uri' in request.POST:
                    result = item_edit.update_class_uri(request.POST['class_uri'])
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                return HttpResponse(json_output,
                                    content_type='application/json; charset=utf8')
            else:
                json_output = json.dumps({'error': 'edit permission required'},
                                         indent=4,
                                         ensure_ascii=False)
                return HttpResponse(json_output,
                                    content_type='application/json; charset=utf8',
                                    status=401)
        else:
            return HttpResponseForbidden
    else:
        raise Http404

