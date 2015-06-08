import json
from django.http import HttpResponse, Http404
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from opencontext_py.apps.edit.items.itembasic import ItemBasicEdit
from opencontext_py.apps.edit.items.itemannotation import ItemAnnotation
from opencontext_py.apps.edit.items.itemcreate import ItemCreate
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
        rp = RootPath()
        base_url = rp.get_baseurl()
        temp_item = TemplateItem(request)
        temp_item.check_edit_permitted = True
        temp_item.read_jsonld_dict(ocitem.json_ld)
        if temp_item.edit_permitted:
            template = loader.get_template('edit/view.html')
            context = RequestContext(request,
                                     {'item': temp_item,
                                      'base_url': base_url})
            return HttpResponse(template.render(context))
        else:
            template = loader.get_template('edit/view401.html')
            context = RequestContext(request,
                                     {'item': temp_item,
                                      'base_url': base_url})
            return HttpResponse(template.render(context), status=401)
    else:
        raise Http404


def update_item_basics(request, uuid):
    """ Handles POST requests to update an item """
    item_edit = ItemBasicEdit(uuid, request)
    if item_edit.manifest is not False:
        if request.method == 'POST':
            if item_edit.edit_permitted or request.user.is_superuser:
                result = {}
                if 'label' in request.POST:
                    result = item_edit.update_label(request.POST['label'],
                                                    request.POST)
                elif 'class_uri' in request.POST:
                    result = item_edit.update_class_uri(request.POST['class_uri'])
                elif 'content' in request.POST \
                    and 'content_type' in request.POST:
                    result = item_edit.update_string_content(request.POST['content'],
                                                             request.POST['content_type'])
                result['errors'] = item_edit.errors
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


def add_item_annotation(request, uuid):
    """ Handles POST requests to add an annotation to an item """
    item_anno = ItemAnnotation(uuid, request)
    if item_anno.manifest is not False:
        if request.method == 'POST':
            if item_anno.edit_permitted or request.user.is_superuser:
                item_anno.creator_uuid = str(request.user.id)
                result = item_anno.add_item_annotation(request.POST)
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


def add_item_stable_id(request, uuid):
    """ Handles POST requests to add an annotation to an item """
    item_anno = ItemAnnotation(uuid, request)
    if item_anno.manifest is not False:
        if request.method == 'POST':
            orcid_ok = item_anno.check_orcid_ok(request.POST)
            if (item_anno.edit_permitted and orcid_ok)\
               or request.user.is_superuser:
                item_anno.creator_uuid = str(request.user.id)
                result = item_anno.add_item_stable_id(request.POST)
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



def create_item_into(request, project_uuid):
    """ Handles POST requests to create an item """
    item_create = ItemCreate(project_uuid, request)
    if item_create.proj_manifest_obj is not False \
       or item_create.oc_root_project:
        if request.method == 'POST':
            if item_create.edit_permitted or request.user.is_superuser:
                item_type_fail = True
                if 'item_type' in request.POST:
                    result = {}
                    if request.POST['item_type'] == 'persons':
                        item_type_fail = False
                        result = item_create.create_person(request.POST)
                    else:
                        item_type_fail = True
                    result['errors'] = item_create.errors
                    json_output = json.dumps(result,
                                             indent=4,
                                             ensure_ascii=False)
                    return HttpResponse(json_output,
                                        content_type='application/json; charset=utf8')
                if item_type_fail:
                    json_output = json.dumps({'error': 'item_type failure'},
                                         indent=4,
                                         ensure_ascii=False)
                    return HttpResponse(json_output,
                                        content_type='application/json; charset=utf8',
                                        status=400)
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