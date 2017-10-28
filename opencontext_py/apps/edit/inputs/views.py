import json
from django.views.decorators.cache import never_cache
from django.http import HttpResponse, Http404
from opencontext_py.libs.rootpath import RootPath
from django.template import RequestContext, loader
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_control
from opencontext_py.apps.entities.entity.models import Entity
from opencontext_py.apps.edit.items.itembasic import ItemBasicEdit
from opencontext_py.apps.edit.inputs.projectinputs import ProjectInputs
from opencontext_py.apps.edit.inputs.labeling import InputLabeling
from opencontext_py.apps.edit.inputs.profiles.models import InputProfile
from opencontext_py.apps.edit.inputs.profiles.manage import ManageInputProfile
from opencontext_py.apps.edit.inputs.profiles.templating import InputProfileTemplating
from opencontext_py.apps.edit.inputs.profiles.use import InputProfileUse
from opencontext_py.apps.edit.inputs.fieldgroups.models import InputFieldGroup
from opencontext_py.apps.edit.inputs.fieldgroups.manage import ManageInputFieldGroup
from opencontext_py.apps.edit.inputs.inputfields.manage import ManageInputField
from opencontext_py.apps.ocitems.manifest.models import Manifest


@ensure_csrf_cookie
@cache_control(no_cache=True)
@never_cache
def profile_use(request, profile_uuid, edit_uuid):
    """ Handle requests to use a profile to create
        or edit a record
    """
    ipt = InputProfileTemplating()
    exists = ipt.check_exists(profile_uuid)
    if exists:
        # now check to see if the we have edit permissions
        proj_inp = ProjectInputs(ipt.project_uuid, request)
        if proj_inp.edit_permitted or request.user.is_superuser:
            if edit_uuid != 'new':
                try:
                    edit_man = Manifest.objects.get(uuid=edit_uuid)
                except Manifest.DoesNotExist:
                    # trying to use this profile to edit something that
                    # does not exist
                    edit_man = False
                    raise Http404
            else:
                edit_uuid = proj_inp.mint_new_uuid()
                edit_man = False
            if 'prefix' in request.GET:
                prefix = request.GET['prefix']
            else:
                prefix = ''
            class_uri = False
            class_label = False
            if 'class_uri' in request.GET:
                class_uri = request.GET['class_uri']
                ent = Entity()
                found = ent.dereference(class_uri)
                if found:
                    class_label = ent.label
                else:
                    class_uri = False
            context_uuid = False
            context_label = False
            if 'context_uuid' in request.GET:
                context_uuid = request.GET['context_uuid']
                ent = Entity()
                found = ent.dereference(context_uuid)
                if found:
                    context_label = ent.label
                else:
                    context_uuid = ''
            if 'id_len' in request.GET:
                try:
                    id_len = int(float(request.GET['id_len']))
                except:
                    id_len = False
            else:
                id_len = False
            rp = RootPath()
            base_url = rp.get_baseurl()
            temp_item = {'uuid': ipt.uuid,
                         'label': ipt.inp_prof.label,
                         'project_uuid': ipt.project_uuid,
                         'project': ipt.project,
                         'edit_man': edit_man,
                         'edit_uuid': edit_uuid,
                         'label_prefix': prefix,
                         'label_id_len': id_len,
                         'class_uri': class_uri,
                         'class_label': class_label,
                         'context_uuid': context_uuid,
                         'context_label': context_label,
                         'context': False,
                         'act_nav': 'profiles'}
            template = loader.get_template('edit/profiles/profile-use.html')
            context = {
                'item': temp_item,
                'super_user': request.user.is_superuser,
                'icons': ItemBasicEdit.UI_ICONS,
                'field_group_vis': InputFieldGroup.GROUP_VIS,
                'base_url': base_url
            }
            return HttpResponse(template.render(context, request))
        else:
            json_output = json.dumps({'error': 'edit permission required'},
                                     indent=4,
                                     ensure_ascii=False)
            return HttpResponse(json_output,
                                content_type='application/json; charset=utf8',
                                status=401)
    else:
        raise Http404


@ensure_csrf_cookie
@cache_control(no_cache=True)
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
            context = {
                'item': temp_item,
                'super_user': request.user.is_superuser,
                'icons': ItemBasicEdit.UI_ICONS,
                'field_group_vis': InputFieldGroup.GROUP_VIS,
                'base_url': base_url
            }
            return HttpResponse(template.render(context, request))
        else:
            json_output = json.dumps({'error': 'edit permission required'},
                                     indent=4,
                                     ensure_ascii=False)
            return HttpResponse(json_output,
                                content_type='application/json; charset=utf8',
                                status=401)
    else:
        raise Http404


@cache_control(no_cache=True)
@never_cache
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


@cache_control(no_cache=True)
@never_cache
def profile_item_list(request, profile_uuid):
    """ Handles JSON requests for a profile
    """
    ipt = InputProfileTemplating()
    exists = ipt.check_exists(profile_uuid)
    if exists:
        rp = RootPath()
        ipt.base_url = rp.get_baseurl()
        # now check to see if the we have edit permissions
        proj_inp = ProjectInputs(ipt.project_uuid, request)
        if proj_inp.edit_permitted or request.user.is_superuser:
            start = 0
            rows = 10
            sort = False
            last = False
            if 'start' in request.GET:
                start = request.GET['start']
            if 'rows' in request.GET:
                rows = request.GET['rows']
            if 'sort' in request.GET:
                sort = request.GET['sort']
            if 'last' in request.GET:
                last = True
            result = ipt.get_item_list(profile_uuid,
                                       start,
                                       rows,
                                       sort,
                                       last)
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


# ------------------------------------------------
# BELOW HANDLE AJAX REQUESTS
# TO get a JSON Index of
# InputProfiles for a project
# ------------------------------------------------
@cache_control(no_cache=True)
@never_cache
def index_json(request, project_uuid):
    """ handles get requests to make
        a JSON index of input profiles for a project
    """
    proj_inp = ProjectInputs(project_uuid, request)
    if proj_inp.manifest is not False:
        if proj_inp.edit_permitted or request.user.is_superuser:
            result = proj_inp.get_profiles()
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


@cache_control(no_cache=True)
@never_cache
def label_check(request, project_uuid):
    """ handles get requests to check on the
        validity of a proposed item label
    """
    proj_inp = ProjectInputs(project_uuid, request)
    if proj_inp.manifest is not False or request.user.is_superuser:
        if proj_inp.edit_permitted or request.user.is_superuser:
            ilab = InputLabeling()
            ilab.project_uuid = project_uuid
            in_error = False
            error = {'error': ''}
            if 'item_type' in request.GET:
                ilab.item_type = request.GET['item_type']
            else:
                in_error = True
                error['error'] += 'Need an "item_type" parameter in request. '
                ilab.item_type = False
            if 'context_uuid' in request.GET:
                ilab.context_uuid = request.GET['context_uuid']
            if 'prefix' in request.GET:
                prefix = request.GET['prefix']
            else:
                prefix = ''
            if 'id_len' in request.GET:
                try:
                    id_len = int(float(request.GET['id_len']))
                except:
                    error['error'] += 'Need an integer value for the "id_len" parameter. '
            else:
                id_len = False
            if 'label' in request.GET:
                label = request.GET['label']
            else:
                label = False
            if 'uuid' in request.GET:
                ilab.uuid = request.GET['uuid']
            else:
                ilab.uuid = False
            if in_error is False:
                result = ilab.check_make_valid_label(label,
                                                     prefix,
                                                     id_len)
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                return HttpResponse(json_output,
                                    content_type='application/json; charset=utf8')
            else:
                json_output = json.dumps(error,
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
        raise Http404


@cache_control(no_cache=True)
def create_update_profle_item(request, profile_uuid, edit_uuid):
    """ handles POST requests to make
        or update an item with a given profile
    """
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
            field_data = False
            if 'field_data' in request.POST:
                field_data_json = request.POST['field_data']
                try:
                    field_data = json.loads(field_data_json)
                except:
                    field_data = False
            if field_data is False:
                json_output = json.dumps({'error': 'Need to POST "field_data" with JSON encoded text.'},
                                         indent=4,
                                         ensure_ascii=False)
                return HttpResponse(json_output,
                                    content_type='application/json; charset=utf8',
                                    status=400)
            if proj_inp.edit_permitted or request.user.is_superuser:
                ipt = InputProfileTemplating()
                profile_obj = ipt.make_json(profile_uuid)
                ipu = InputProfileUse()
                ipu.edit_uuid = edit_uuid
                ipu.item_type = profile_obj['item_type']
                ipu.profile_uuid = profile_uuid
                ipu.profile_obj = profile_obj
                ipu.project_uuid = project_uuid
                result = ipu.create_update(field_data)
                # result = ipu.test(field_data)
                result['errors'] = ipu.errors
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


# ------------------------------------------------
# BELOW HANDLE AJAX REQUESTS
# TO CREATE, UPDATE, DELETE, and DUPLICATE
# InputProfiles
# ------------------------------------------------
@cache_control(no_cache=True)
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


@cache_control(no_cache=True)
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


@cache_control(no_cache=True)
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


@cache_control(no_cache=True)
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


# ------------------------------------------------
# BELOW HANDLE AJAX REQUESTS
# TO CREATE, UPDATE, DELETE, and DUPLICATE
# InputFieldGroups AND InputFields
# ------------------------------------------------
@cache_control(no_cache=True)
def reorder_item(request, uuid):
    """ handles a request to reorder an item """
    found = False
    fieldgroup_obj = False
    field_obj = False
    mifg = ManageInputFieldGroup()
    fieldgroup_obj = mifg.get_field_group(uuid)
    if fieldgroup_obj is not False:
        found = True
        project_uuid = fieldgroup_obj.project_uuid
        item_type = 'field-groups'
    else:
        mif = ManageInputField()
        field_obj = mif.get_field(uuid)
        if field_obj is not False:
            project_uuid = field_obj.project_uuid
            found = True
            item_type = 'fields'
    if found:
        if request.method == 'POST':
            proj_inp = ProjectInputs(project_uuid, request)
            if proj_inp.edit_permitted or request.user.is_superuser:
                # ok to reorder the item
                if 'sort_change' in request.POST:
                    sort_change = request.POST['sort_change']
                else:
                    sort_change = 0
                result = mifg.update_sort_field_group_or_field(sort_change, uuid, item_type)
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


# ------------------------------------------------
# BELOW HANDLE AJAX REQUESTS
# TO CREATE, UPDATE, DELETE, and DUPLICATE
# InputFieldGroups
# ------------------------------------------------
@cache_control(no_cache=True)
def create_field_group(request, profile_uuid):
    """ Creates a field group for a given InputProfile
    """
    ipt = InputProfileTemplating()
    exists = ipt.check_exists(profile_uuid)
    if exists:
        if request.method == 'POST':
            # now check to see if the we have edit permissions
            proj_inp = ProjectInputs(ipt.project_uuid, request)
            if proj_inp.edit_permitted or request.user.is_superuser:
                mifg = ManageInputFieldGroup()
                mifg.project_uuid = ipt.project_uuid
                mifg.profile_uuid = profile_uuid
                result = mifg.create_update_from_post(request.POST)
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


@cache_control(no_cache=True)
def update_field_group(request, fgroup_uuid):
    """ Updates a field group for a given InputProfile
    """
    mifg = ManageInputFieldGroup()
    inp_obj = mifg.get_field_group(fgroup_uuid)
    if inp_obj is not False:
        if request.method == 'POST':
            # now check to see if the we have edit permissions
            proj_inp = ProjectInputs(inp_obj.project_uuid, request)
            if proj_inp.edit_permitted or request.user.is_superuser:
                result = mifg.create_update_from_post(request.POST,
                                                      fgroup_uuid)
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


@cache_control(no_cache=True)
def delete_field_group(request, fgroup_uuid):
    """ Delete a field group for a given InputProfile
    """
    mifg = ManageInputFieldGroup()
    inp_obj = mifg.get_field_group(fgroup_uuid)
    if inp_obj is not False:
        if request.method == 'POST':
            # now check to see if the we have edit permissions
            proj_inp = ProjectInputs(inp_obj.project_uuid, request)
            if proj_inp.edit_permitted or request.user.is_superuser:
                result = mifg.delete(fgroup_uuid)
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


# ------------------------------------------------
# BELOW HANDLE AJAX REQUESTS
# TO CREATE, UPDATE, DELETE, and DUPLICATE
# InputFields
# ------------------------------------------------
@cache_control(no_cache=True)
def create_field(request, fgroup_uuid):
    """ Creates a field group for a given InputProfile
    """
    mifg = ManageInputFieldGroup()
    inp_obj = mifg.get_field_group(fgroup_uuid)
    if inp_obj is not False:
        mif = ManageInputField()
        mif.fgroup_uuid = fgroup_uuid
        mif.profile_uuid = inp_obj.profile_uuid
        mif.project_uuid = inp_obj.project_uuid
        if request.method == 'POST':
            # now check to see if the we have edit permissions
            proj_inp = ProjectInputs(inp_obj.project_uuid, request)
            if proj_inp.edit_permitted or request.user.is_superuser:
                # now finally try to create the Field
                result = mif.create_update_from_post(request.POST)
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


@cache_control(no_cache=True)
def update_field(request, field_uuid):
    """ Updates a field group for a given InputProfile
    """
    mifg = ManageInputFieldGroup()
    inp_obj = mifg.get_field_group(fgroup_uuid)
    if inp_obj is not False:
        if request.method == 'POST':
            # now check to see if the we have edit permissions
            proj_inp = ProjectInputs(inp_obj.project_uuid, request)
            if proj_inp.edit_permitted or request.user.is_superuser:
                result = mifg.create_update_from_post(request.POST,
                                                      fgroup_uuid)
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


@cache_control(no_cache=True)
def delete_field(request, field_uuid):
    """ Delete a field group for a given InputProfile
    """
    mif = ManageInputField()
    inp_obj = mif.get_field(field_uuid)
    if inp_obj is not False:
        if request.method == 'POST':
            # now check to see if the we have edit permissions
            proj_inp = ProjectInputs(inp_obj.project_uuid, request)
            if proj_inp.edit_permitted or request.user.is_superuser:
                result = mif.delete(field_uuid)
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
