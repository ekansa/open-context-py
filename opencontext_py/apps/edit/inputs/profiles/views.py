import json
from django.http import HttpResponse, Http404
from opencontext_py.libs.rootpath import RootPath
from django.template import RequestContext, loader
from django.views.decorators.csrf import ensure_csrf_cookie
from opencontext_py.apps.edit.items.itembasic import ItemBasicEdit
from opencontext_py.apps.edit.inputs.projectinputs import ProjectInputs
from opencontext_py.apps.edit.inputs.profiles.models import InputProfile
from opencontext_py.apps.edit.inputs.profiles.manage import ManageInputProfile
from opencontext_py.apps.edit.inputs.profiles.templating import InputProfileTemplating


@ensure_csrf_cookie
def profile_edit(request, profile_uuid):
    """ Handles JSON requests for a profile
    """
    ipt = InputProfileTemplating()
    exists = ipt.check_exists(profile_uuid)
    if exists:
        # now check to see if the we have edit permissions
        proj_inp = ProjectInputs(ipt.project_uuid, request)
        if proj_inp.edit_permitted or request.user.is_superuser:
            rp = RootPath()
            base_url = rp.get_baseurl()
            temp_item = {'uuid': ipt.uuid,
                         'label': ipt.inp_prof.label,
                         'project_uuid': ipt.project_uuid,
                         'project': ipt.project,
                         'context': False,
                         'act_nav': 'profiles'}
            template = loader.get_template('edit/profiles/profile-edit.html')
            context = RequestContext(request,
                                     {'item': temp_item,
                                      'super_user': request.user.is_superuser,
                                      'icons': ItemBasicEdit.UI_ICONS,
                                      'base_url': base_url})
            return HttpResponse(template.render(context))
        else:
            json_output = json.dumps({'error': 'edit permission required'},
                                     indent=4,
                                     ensure_ascii=False)
            return HttpResponse(json_output,
                                content_type='application/json; charset=utf8',
                                status=401)
    else:
        raise Http404


def json_view(request, profile_uuid):
    """ Handles JSON requests for a profile
    """
    ipt = InputProfileTemplating()
    exists = ipt.check_exists(profile_uuid)
    if exists:
        # now check to see if the we have edit permissions
        proj_inp = ProjectInputs(ipt.project_uuid, request)
        if proj_inp.edit_permitted or request.user.is_superuser:
            result = ipt.make_json(profile_uuid)
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
        raise Http404


def create(request, project_uuid):
    """ Handles POST requests to create a new input profile """
    proj_inp = ProjectInputs(project_uuid, request)
    if proj_inp.manifest is not False:
        if request.method == 'POST':
            if proj_inp.edit_permitted or request.user.is_superuser:
                m_inp_prof = ManageInputProfile()
                m_inp_prof.creator_uuid = str(request.user.id)
                m_inp_prof.project_uuid = project_uuid
                result = m_inp_prof.create_update_from_post(request.POST)
                result['errors'] = m_inp_prof.errors
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


def update(request, profile_uuid):
    """ Handles POST requests to update an existing profile """
    try:
        inp_prof = InputProfile.objects.get(uuid=profile_uuid)
        project_uuid = inp_prof.project_uuid
    except InputProfile.DoesNotExist:
        inp_prof = False
        project_uuid = False
        raise Http404
    proj_inp = ProjectInputs(project_uuid, request)
    if proj_inp.manifest is not False:
        if request.method == 'POST':
            if proj_inp.edit_permitted or request.user.is_superuser:
                m_inp_prof = ManageInputProfile()
                m_inp_prof.creator_uuid = str(request.user.id)
                m_inp_prof.project_uuid = project_uuid
                result = m_inp_prof.create_update_from_post(request.POST, profile_uuid)
                result['errors'] = m_inp_prof.errors
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


def delete(request, profile_uuid):
    """ Handles POST requests to delete an existing profile """
    try:
        inp_prof = InputProfile.objects.get(uuid=profile_uuid)
        project_uuid = inp_prof.project_uuid
    except InputProfile.DoesNotExist:
        inp_prof = False
        project_uuid = False
        raise Http404
    proj_inp = ProjectInputs(project_uuid, request)
    if proj_inp.manifest is not False:
        if request.method == 'POST':
            if proj_inp.edit_permitted or request.user.is_superuser:
                m_inp_prof = ManageInputProfile()
                m_inp_prof.creator_uuid = str(request.user.id)
                m_inp_prof.project_uuid = project_uuid
                result = m_inp_prof.delete(profile_uuid)
                result['errors'] = m_inp_prof.errors
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


def duplicate(request, profile_uuid):
    """ Handles POST requests to duplicate an existing profile """
    try:
        inp_prof = InputProfile.objects.get(uuid=profile_uuid)
        project_uuid = inp_prof.project_uuid
    except InputProfile.DoesNotExist:
        inp_prof = False
        project_uuid = False
        raise Http404
    proj_inp = ProjectInputs(project_uuid, request)
    if proj_inp.manifest is not False:
        if request.method == 'POST':
            if proj_inp.edit_permitted or request.user.is_superuser:
                m_inp_prof = ManageInputProfile()
                m_inp_prof.creator_uuid = str(request.user.id)
                m_inp_prof.project_uuid = project_uuid
                result = m_inp_prof.duplicate(request.POST,
                                              profile_uuid)
                result['errors'] = m_inp_prof.errors
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
