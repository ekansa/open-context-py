import json
from django.http import HttpResponse, Http404
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from opencontext_py.apps.imports.sources.projects import ImportProjects
from opencontext_py.apps.edit.items.itembasic import ItemBasicEdit
from opencontext_py.apps.edit.projects.overview import ProjectOverview
from django.template import RequestContext, loader
from django.views.decorators.csrf import ensure_csrf_cookie


# These views provide forms for editing items
@ensure_csrf_cookie
def index(request):
    """ Index of a list of projects that can be edited
        or where data can be imported
    """
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)
    else:
        ipr = ImportProjects()
        projs = ipr.get_all_projects()
        rp = RootPath()
        base_url = rp.get_baseurl()
        template = loader.get_template('edit/index.html')
        context = {
            'projs': projs,
            'super_user': request.user.is_superuser,
            'icons': ItemBasicEdit.UI_ICONS,
            'base_url': base_url,
            'user': request.user
        }
        return HttpResponse(template.render(context, request))


@ensure_csrf_cookie
def status(request, project_uuid):
    """ View of the project status """
    ocitem = OCitem()
    ocitem.get_item(project_uuid)
    ok_view = False
    if ocitem.manifest is not False:
        if ocitem.manifest.item_type == 'projects':
            ok_view = True
    if ok_view:
        rp = RootPath()
        base_url = rp.get_baseurl()
        temp_item = TemplateItem(request)
        temp_item.check_edit_permitted = True
        temp_item.read_jsonld_dict(ocitem.json_ld)
        if temp_item.edit_permitted:
            p_o = ProjectOverview(project_uuid)
            p_o.get_manifest_summary()
            p_o.get_person_list()
            # p_o. get_data_type_summary()
            template = loader.get_template('edit/project-status.html')
            context = {
                'item': temp_item,
                'super_user': request.user.is_superuser,
                'icons': ItemBasicEdit.UI_ICONS,
                'status': p_o,
                'base_url': base_url,
                'user': request.user
            }
            return HttpResponse(template.render(context, request))
        else:
            template = loader.get_template('edit/view401.html')
            context = {
                'item': temp_item,
                'base_url': base_url
            }
            return HttpResponse(template.render(context, request), status=401)
    else:
        raise Http404

