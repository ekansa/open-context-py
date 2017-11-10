import json
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import redirect
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.ocitems.ocitem.models import OCitem
from opencontext_py.apps.ocitems.ocitem.templating import TemplateItem
from opencontext_py.apps.edit.items.itembasic import ItemBasicEdit
from opencontext_py.apps.edit.items.itemassertion import ItemAssertion
from opencontext_py.apps.edit.items.itemannotation import ItemAnnotation
from opencontext_py.apps.edit.items.itemcreate import ItemCreate
from opencontext_py.apps.edit.items.itemgeotime import ItemGeoTime
from opencontext_py.apps.edit.items.itemdelete import ItemDelete
from opencontext_py.apps.edit.inputs.profiles.templating import InputProfileTemplating
from opencontext_py.apps.ldata.linkentities.manage import LinkEntityManage
from opencontext_py.apps.ocitems.editorials.models import Editorial
from django.db import transaction
import reversion
from opencontext_py.apps.edit.versioning.models import VersionMetadata
from opencontext_py.apps.edit.versioning.deletion import DeletionRevision
from django.template import RequestContext, loader
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_control


# These views provide forms for editing items
def index(request):
    return HttpResponse("Hello, world. You're at the edit index.")


def check_profile_use(manifest):
    """ checks to see if the item
        was created using a input profile
    """
    output = False
    if ':' in manifest.source_id:
        source_ex = manifest.source_id.split(':')
        if(len(source_ex) == 2):
            profile_uuid = source_ex[1]
            ipt = InputProfileTemplating()
            exists = ipt.check_exists(profile_uuid)
            if exists:
                output = ipt.inp_prof
    return output


@ensure_csrf_cookie
@cache_control(no_cache=True)
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
            editorial_types = json.dumps(Editorial.EDITORIAL_TYPES,
                                         indent=4,
                                         ensure_ascii=False)
            template = loader.get_template('edit/item-edit.html')
            context = {
                'item': temp_item,
                'profile': check_profile_use(ocitem.manifest),
                'super_user': request.user.is_superuser,
                'icons': ItemBasicEdit.UI_ICONS,
                'editorial_types': editorial_types,
                'base_url': base_url
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
        # not in the manifest, check to see if this is an data entry input profile
        ipt = InputProfileTemplating()
        exists = ipt.check_exists(uuid)
        if exists:
            rp = RootPath()
            base_url = rp.get_baseurl()
            return redirect(base_url + '/edit/inputs/profiles/' + uuid + '/edit')
        else:
            raise Http404


@ensure_csrf_cookie
@cache_control(no_cache=True)
def check_list_view(request, uuid):
    """ Displays the HTML item editing interface """
    ocitem = OCitem()
    ocitem.get_item(uuid)
    if ocitem.manifest is not False:
        if ocitem.manifest.item_type == 'projects':
            rp = RootPath()
            base_url = rp.get_baseurl()
            temp_item = TemplateItem(request)
            temp_item.check_edit_permitted = True
            temp_item.read_jsonld_dict(ocitem.json_ld)
            if temp_item.edit_permitted:
                template = loader.get_template('edit/check-list.html')
                context = {
                    'item': temp_item,
                    'super_user': request.user.is_superuser,
                    'icons': ItemBasicEdit.UI_ICONS,
                    'base_url': base_url
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
    else:
        raise Http404


@cache_control(no_cache=True)
@transaction.atomic()
@reversion.create_revision()
def update_item_basics(request, uuid):
    """ Handles POST requests to update an item """
    item_edit = ItemBasicEdit(uuid, request)
    if item_edit.manifest is not False:
        if request.method == 'POST':
            if ('edit_status' in request.POST \
               or 'project_uuid' in request.POST)\
               and request.user.is_superuser:
                # some parameters in the request require super-user privelages
                result = item_edit.update_project_sensitives(request.POST)
                result['errors'] = item_edit.errors
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                rev_label = 'Project status updated'
                reversion.set_user(request.user)
                reversion.add_meta(VersionMetadata,
                                   project_uuid=item_edit.manifest.project_uuid,
                                   uuid=item_edit.manifest.uuid,
                                   item_type=item_edit.manifest.item_type,
                                   label=rev_label,
                                   json_note=json_output)
                return HttpResponse(json_output,
                                    content_type='application/json; charset=utf8')
            elif item_edit.edit_permitted or request.user.is_superuser:
                result = {}
                rev_label = 'Update item ' + item_edit.manifest.label
                if 'label' in request.POST:
                    # version control metadata
                    rev_label = 'Update item label in ' + item_edit.manifest.label
                    result = item_edit.update_label(request.POST['label'],
                                                    request.POST)
                elif 'class_uri' in request.POST:
                    rev_label = 'Update category in ' + item_edit.manifest.label
                    result = item_edit.update_class_uri(request.POST['class_uri'])
                elif 'content' in request.POST \
                     and 'content_type' in request.POST:
                    rev_label = 'Update item text content in ' + item_edit.manifest.label
                    result = item_edit.update_string_content(request.POST['content'],
                                                             request.POST['content_type'],
                                                             request.POST)
                result['errors'] = item_edit.errors
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                reversion.set_user(request.user)
                reversion.add_meta(VersionMetadata,
                                   project_uuid=item_edit.manifest.project_uuid,
                                   uuid=item_edit.manifest.uuid,
                                   item_type=item_edit.manifest.item_type,
                                   label=rev_label,
                                   json_note=json_output)
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
@transaction.atomic()
@reversion.create_revision()
def update_predicate_sort_order(request, uuid):
    """ Handles POST requests to update an item """
    item_edit = ItemBasicEdit(uuid, request)
    if item_edit.manifest is not False:
        if request.method == 'POST':
            if item_edit.edit_permitted or request.user.is_superuser:
                result = {}
                rev_label = 'Update item sort ' + item_edit.manifest.label
                result = item_edit.update_predicate_sort_order(request.POST)
                result['errors'] = item_edit.errors
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                reversion.set_user(request.user)
                reversion.add_meta(VersionMetadata,
                                   project_uuid=item_edit.manifest.project_uuid,
                                   uuid=item_edit.manifest.uuid,
                                   item_type=item_edit.manifest.item_type,
                                   label=rev_label,
                                   json_note=json_output)
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
@transaction.atomic()
@reversion.create_revision()
def update_project_hero(request, uuid):
    """ Handles POST requests to update a hero picture for an item """
    item_edit = ItemBasicEdit(uuid, request)
    if item_edit.manifest is not False:
        if request.method == 'POST':
            if item_edit.edit_permitted or request.user.is_superuser:
                # some parameters in the request require super-user privelages
                result = item_edit.update_project_hero(request.POST)
                result['errors'] = item_edit.errors
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                rev_label = 'Project hero image updated'
                reversion.set_user(request.user)
                reversion.add_meta(VersionMetadata,
                                   project_uuid=item_edit.manifest.project_uuid,
                                   uuid=item_edit.manifest.uuid,
                                   item_type=item_edit.manifest.item_type,
                                   label=rev_label,
                                   json_note=json_output)
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
@transaction.atomic()
@reversion.create_revision()
def update_media_file(request, uuid):
    """ Handles POST requests to update a media file for an item """
    item_edit = ItemBasicEdit(uuid, request)
    if item_edit.manifest is not False:
        if request.method == 'POST':
            if item_edit.edit_permitted or request.user.is_superuser:
                # some parameters in the request require super-user privelages
                result = item_edit.update_media_file(request.POST)
                result['errors'] = item_edit.errors
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                rev_label = 'Media file updated'
                reversion.set_user(request.user)
                reversion.add_meta(VersionMetadata,
                                   project_uuid=item_edit.manifest.project_uuid,
                                   uuid=item_edit.manifest.uuid,
                                   item_type=item_edit.manifest.item_type,
                                   label=rev_label,
                                   json_note=json_output)
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
@transaction.atomic()
@reversion.create_revision()
def add_edit_item_assertion(request, uuid):
    """ Handles POST requests to add an assertion for an item """
    item_edit = ItemBasicEdit(uuid, request)
    if item_edit.manifest is not False:
        if request.method == 'POST':
            if item_edit.edit_permitted or request.user.is_superuser:
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
                else:
                    item_ass = ItemAssertion()
                    item_ass.uuid = uuid
                    item_ass.project_uuid = item_edit.manifest.project_uuid
                    result = item_ass.add_edit_assertions(field_data,
                                                          item_edit.manifest)
                    result['errors'] = item_edit.errors
                    json_output = json.dumps(result,
                                             indent=4,
                                             ensure_ascii=False)
                    # version control metadata
                    rev_label = 'Update item assertion(s) in ' + item_edit.manifest.label
                    reversion.set_user(request.user)
                    reversion.add_meta(VersionMetadata,
                                       project_uuid=item_edit.manifest.project_uuid,
                                       uuid=item_edit.manifest.uuid,
                                       item_type=item_edit.manifest.item_type,
                                       label=rev_label,
                                       json_note=json_output)
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
@transaction.atomic()
@reversion.create_revision()
def add_edit_string_translation(request, string_uuid):
    """ Handles POST requests to add a containment assertion for an item """
    item_edit = ItemBasicEdit(False, False)
    string_exists = item_edit.check_string_edit(string_uuid, request)
    if string_exists:
        if request.method == 'POST':
            if item_edit.edit_permitted or request.user.is_superuser:
                item_ass = ItemAssertion()
                result = item_ass.add_edit_string_translation(string_uuid,
                                                              request.POST)
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
@transaction.atomic()
@reversion.create_revision()
def add_edit_item_containment(request, uuid):
    """ Handles POST requests to add a containment assertion for an item """
    item_edit = ItemBasicEdit(uuid, request)
    if item_edit.manifest is not False:
        if request.method == 'POST':
            if item_edit.edit_permitted or request.user.is_superuser:
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
                else:
                    item_ass = ItemAssertion()
                    item_ass.uuid = uuid
                    item_ass.project_uuid = item_edit.manifest.project_uuid
                    result = item_ass.add_edit_containment(field_data,
                                                           item_edit.manifest)
                    result['errors'] = item_edit.errors
                    json_output = json.dumps(result,
                                             indent=4,
                                             ensure_ascii=False)
                    # version control metadata
                    rev_label = 'Update containment for ' + item_edit.manifest.label
                    reversion.set_user(request.user)
                    reversion.add_meta(VersionMetadata,
                                       project_uuid=item_edit.manifest.project_uuid,
                                       uuid=item_edit.manifest.uuid,
                                       item_type=item_edit.manifest.item_type,
                                       label=rev_label,
                                       json_note=json_output)
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
@transaction.atomic()
@reversion.create_revision()
def sort_item_assertion(request, uuid):
    """ Handles POST requests to DELETE an assertion for an item """
    item_edit = ItemBasicEdit(uuid, request)
    if item_edit.manifest is not False:
        if request.method == 'POST':
            if item_edit.edit_permitted or request.user.is_superuser:
                item_ass = ItemAssertion()
                item_ass.uuid = uuid
                item_ass.project_uuid = item_edit.manifest.project_uuid
                if 'hash_id' in request.POST:
                    result = item_ass.rank_assertion_value(request.POST,
                                                           item_edit.manifest)
                    result['errors'] = item_edit.errors
                    json_output = json.dumps(result,
                                             indent=4,
                                             ensure_ascii=False)
                    # version control metadata
                    rev_label = 'Update item assertion sorting in ' + item_edit.manifest.label
                    reversion.set_user(request.user)
                    reversion.add_meta(VersionMetadata,
                                       project_uuid=item_edit.manifest.project_uuid,
                                       uuid=item_edit.manifest.uuid,
                                       item_type=item_edit.manifest.item_type,
                                       label=rev_label,
                                       json_note=json_output)
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
def delete_item_assertion(request, uuid):
    """ Handles POST requests to DELETE an assertion for an item """
    item_edit = ItemBasicEdit(uuid, request)
    if item_edit.manifest is not False:
        if request.method == 'POST':
            if item_edit.edit_permitted or request.user.is_superuser:
                item_ass = ItemAssertion()
                item_ass.uuid = uuid
                item_ass.project_uuid = item_edit.manifest.project_uuid
                result = item_ass.delete_assertion(request.POST)
                result['errors'] = item_edit.errors
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                if item_ass.hash_id is not False:
                    rev_label = 'Delete item assertion in ' + item_edit.manifest.label
                    drev = DeletionRevision()
                    drev.project_uuid = item_edit.manifest.project_uuid
                    drev.uuid = item_edit.manifest.uuid
                    drev.item_type = item_edit.manifest.item_type
                    drev.user_id = request.user.id
                    drev.assertion_keys.append(item_ass.hash_id)
                    drev.save_delete_revision(rev_label, json_output)
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
@transaction.atomic()
@reversion.create_revision()
def add_update_geo_data(request, uuid):
    """ Handles POST requests to update an date ranges for an item """
    item_geotime = ItemGeoTime(uuid, request)
    if item_geotime.manifest is not False:
        if request.method == 'POST':
            if item_geotime.edit_permitted or request.user.is_superuser:
                item_geotime.creator_uuid = str(request.user.id)
                result = item_geotime.add_update_geo_data(request.POST)
                result['errors'] = item_geotime.errors
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                reversion.set_user(request.user)
                reversion.add_meta(VersionMetadata,
                                   project_uuid=item_geotime.manifest.project_uuid,
                                   uuid=item_geotime.manifest.uuid,
                                   item_type=item_geotime.manifest.item_type,
                                   label=item_geotime.manifest.label,
                                   json_note=json_output)
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
@transaction.atomic()
@reversion.create_revision()
def add_update_project_geo(request, uuid):
    """ Handles POST requests to update an date ranges for an item """
    item_geotime = ItemGeoTime(uuid, request)
    if item_geotime.manifest is not False:
        if request.method == 'POST':
            if item_geotime.edit_permitted or request.user.is_superuser:
                item_geotime.creator_uuid = str(request.user.id)
                result = item_geotime.add_update_project_geo(request.POST)
                result['errors'] = item_geotime.errors
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                reversion.set_user(request.user)
                reversion.add_meta(VersionMetadata,
                                   project_uuid=item_geotime.manifest.project_uuid,
                                   uuid=item_geotime.manifest.uuid,
                                   item_type=item_geotime.manifest.item_type,
                                   label=item_geotime.manifest.label,
                                   json_note=json_output)
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
@transaction.atomic()
@reversion.create_revision()
def add_update_date_range(request, uuid):
    """ Handles POST requests to update an date ranges for an item """
    item_geotime = ItemGeoTime(uuid, request)
    if item_geotime.manifest is not False:
        if request.method == 'POST':
            if item_geotime.edit_permitted or request.user.is_superuser:
                item_geotime.creator_uuid = str(request.user.id)
                result = item_geotime.add_update_date_range(request.POST)
                result['errors'] = item_geotime.errors
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                reversion.set_user(request.user)
                reversion.add_meta(VersionMetadata,
                                   project_uuid=item_geotime.manifest.project_uuid,
                                   uuid=item_geotime.manifest.uuid,
                                   item_type=item_geotime.manifest.item_type,
                                   label=item_geotime.manifest.label,
                                   json_note=json_output)
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
@transaction.atomic()
@reversion.create_revision()
def delete_date_range(request, uuid):
    """ Handles POST requests to delete an date ranges for an item """
    item_geotime = ItemGeoTime(uuid, request)
    if item_geotime.manifest is not False:
        if request.method == 'POST':
            if item_geotime.edit_permitted or request.user.is_superuser:
                item_geotime.creator_uuid = str(request.user.id)
                result = item_geotime.delete_date_range(request.POST)
                result['errors'] = item_geotime.errors
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                reversion.set_user(request.user)
                reversion.add_meta(VersionMetadata,
                                   project_uuid=item_geotime.manifest.project_uuid,
                                   uuid=item_geotime.manifest.uuid,
                                   item_type=item_geotime.manifest.item_type,
                                   label=item_geotime.manifest.label,
                                   json_note=json_output)
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
@transaction.atomic()
@reversion.create_revision()
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
                # version control metadata
                rev_label = 'Add item annotation in ' + item_anno.manifest.label
                reversion.set_user(request.user)
                reversion.add_meta(VersionMetadata,
                                   project_uuid=item_anno.manifest.project_uuid,
                                   uuid=item_anno.manifest.uuid,
                                   item_type=item_anno.manifest.item_type,
                                   label=rev_label,
                                   json_note=json_output)
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
@transaction.atomic()
@reversion.create_revision()
def edit_annotation(request, entity_id):
    """ Handles POST requests to edit an annotation of an item """
    item_anno = ItemAnnotation(entity_id, request)
    if item_anno.manifest is not False:
        if request.method == 'POST':
            if item_anno.edit_permitted or request.user.is_superuser:
                result = {}
                rev_label = 'Update item annotation in ' + item_anno.manifest.label
                if 'sort_change' in request.POST:
                    result = item_anno.sort_change_annotation(request.POST)
                    rev_label = 'Update item annotation sorting in ' + item_anno.manifest.label
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                reversion.set_user(request.user)
                reversion.add_meta(VersionMetadata,
                                   project_uuid=item_anno.manifest.project_uuid,
                                   uuid=item_anno.manifest.uuid,
                                   item_type=item_anno.manifest.item_type,
                                   label=rev_label,
                                   json_note=json_output)
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
@transaction.atomic()
@reversion.create_revision()
def delete_annotation(request, entity_id):
    """ Handles POST requests to delete an annotation on an item """
    item_anno = ItemAnnotation(entity_id, request)
    if item_anno.manifest is not False:
        if request.method == 'POST':
            if item_anno.edit_permitted or request.user.is_superuser:
                result = item_anno.delete_annotation(request.POST)
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                if item_anno.hash_id is not False:
                    rev_label = 'Delete item annotation in ' + item_anno.manifest.label
                    drev = DeletionRevision()
                    drev.project_uuid = item_anno.manifest.project_uuid
                    drev.uuid = item_anno.manifest.uuid
                    drev.item_type = item_anno.manifest.item_type
                    drev.user_id = request.user.id
                    drev.link_annotation_keys.append(item_anno.hash_id)
                    drev.save_delete_revision(rev_label, json_output)
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
def html_validate(request):
    """ checks to see if a posted string is valid for use as xhtml """
    item_edit = ItemBasicEdit(False, request)
    if request.method == 'POST':
        if 'text' in request.POST:
            text = request.POST['text']
            result = {}
            item_edit.errors = {}
            result['ok'] = item_edit.valid_as_html(text)
            result['errors'] = item_edit.errors
            json_output = json.dumps(result,
                                     indent=4,
                                     ensure_ascii=False)
            return HttpResponse(json_output,
                                content_type='application/json; charset=utf8')
        else:
            json_output = json.dumps({'error': 'need text in a "text" parameter'},
                                     indent=4,
                                     ensure_ascii=False)
            return HttpResponse(json_output,
                                content_type='application/json; charset=utf8',
                                status=400)
    else:
        return HttpResponseForbidden


@cache_control(no_cache=True)
@transaction.atomic()
@reversion.create_revision()
def add_update_ld_entity(request):
    """ Handles POST requests to create or update a linked-data entity """
    if request.method == 'POST':
        authorized = False
        lem = LinkEntityManage()
        if 'uri' in request.POST:
            uri = request.POST['uri']
        else:
            uri = False
        if uri is False:
            json_output = json.dumps({'error': 'uri parameter required'},
                                     indent=4,
                                     ensure_ascii=False)
            return HttpResponse(json_output,
                                content_type='application/json; charset=utf8',
                                status=400)
        else:
            # check to see if the URI is in a sensitive vocabulary
            # if so, one needs super-use status to edit
            uri_sensitive = lem.is_uri_sensitive(uri)
            if uri_sensitive and request.user.is_superuser:
                authorized = True
            elif uri_sensitive is False and request.user.is_authenticated():
                authorized = True
                # one needs to be an authenticated user to add or edit linked
                # data entities (for non-sensitive vocabs), since this just
                # adds data to a list. 
            else:
                authorized = False
        if authorized:
            result = lem.add_update(request.POST)
            result['errors'] = lem.errors
            json_output = json.dumps(result,
                                     indent=4,
                                     ensure_ascii=False)
            # version control metadata
            rev_label = 'Linked data entity added/updated: ' + uri
            reversion.set_user(request.user)
            reversion.add_meta(VersionMetadata,
                               project_uuid='0',
                               uuid=uri,
                               item_type='uri',
                               label=rev_label,
                               json_note=json_output)
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


@cache_control(no_cache=True)
@transaction.atomic()
@reversion.create_revision()
def add_item_stable_id(request, uuid):
    """ Handles POST requests to add an annotation to an item """
    item_anno = ItemAnnotation(uuid, request)
    if item_anno.manifest is not False:
        if request.method == 'POST':
            orcid_ok = item_anno.check_orcid_ok(request.POST)
            if (item_anno.edit_permitted and orcid_ok)\
               or request.user.is_superuser:
                # super user status generally required to edit stable ids
                # the exception is for users with edit privilages
                # who can add or delete ORCIDs to persons items
                item_anno.creator_uuid = str(request.user.id)
                result = item_anno.add_item_stable_id(request.POST)
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                rev_label = 'Add item stable ID in ' + item_anno.manifest.label
                reversion.set_user(request.user)
                reversion.add_meta(VersionMetadata,
                                   project_uuid=item_anno.manifest.project_uuid,
                                   uuid=item_anno.manifest.uuid,
                                   item_type=item_anno.manifest.item_type,
                                   label=rev_label,
                                   json_note=json_output)
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
@transaction.atomic()
@reversion.create_revision()
def delete_item_stable_id(request, uuid):
    """ Handles POST requests to add an annotation to an item """
    item_anno = ItemAnnotation(uuid, request)
    if item_anno.manifest is not False:
        if request.method == 'POST':
            orcid_ok = item_anno.check_orcid_ok(request.POST)
            if (item_anno.edit_permitted and orcid_ok)\
               or request.user.is_superuser:
                # super user status generally required to edit stable ids
                # the exception is for users with edit privilages
                # who can add or delete ORCIDs to persons items
                result = item_anno.delete_item_stable_id(request.POST)
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                rev_label = 'Delete item stable ID in ' + item_anno.manifest.label
                reversion.set_user(request.user)
                reversion.add_meta(VersionMetadata,
                                   project_uuid=item_anno.manifest.project_uuid,
                                   uuid=item_anno.manifest.uuid,
                                   item_type=item_anno.manifest.item_type,
                                   label=rev_label,
                                   json_note=json_output)
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
@transaction.atomic()
@reversion.create_revision()
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
                    if 'label' in request.POST:
                        label = request.POST['label']
                    else:
                        label = ''
                    if request.POST['item_type'] == 'persons':
                        item_type_fail = False
                        result = item_create.create_person(request.POST)
                    elif request.POST['item_type'] == 'predicates':
                        item_type_fail = False
                        result = item_create.create_predicate(request.POST)
                    elif request.POST['item_type'] == 'types':
                        item_type_fail = False
                        result = item_create.create_type(request.POST)
                    elif request.POST['item_type'] == 'media':
                        item_type_fail = False
                        result = item_create.create_media(request.POST)
                    else:
                        item_type_fail = True
                    result['errors'] = item_create.errors
                    json_output = json.dumps(result,
                                             indent=4,
                                             ensure_ascii=False)
                    if item_create.created_uuid is not False:
                        # version control metadata
                        rev_label = 'Add item ' + label + '(' + request.POST['item_type'] + ')'
                        reversion.set_user(request.user)
                        reversion.add_meta(VersionMetadata,
                                           project_uuid=project_uuid,
                                           uuid=item_create.created_uuid,
                                           item_type=request.POST['item_type'],
                                           label=rev_label,
                                           json_note=json_output)
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


@cache_control(no_cache=True)
@transaction.atomic()
@reversion.create_revision()
def create_project(request):
    """ Handles POST requests to create a project item """
    if request.method == 'POST':
        if request.user.is_superuser:
            # only super users can make new project
            if 'project_uuid' in request.POST:
                project_uuid = request.POST['project_uuid']
            else:
                project_uuid = '0'
            item_create = ItemCreate(project_uuid, request)
            if item_create.proj_manifest_obj is not False \
               or item_create.oc_root_project:
                # the new project is either at the Open Context root
                # (independent project) or is part of a larger project
                result = item_create.create_project(request.POST)
                result['errors'] = item_create.errors
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                if item_create.created_uuid is not False:
                    # version control metadata
                    if 'label' in request.POST:
                        label = request.POST['label']
                    else:
                        label = ''
                    rev_label = 'Add project ' + label
                    reversion.set_user(request.user)
                    reversion.add_meta(VersionMetadata,
                                       project_uuid=project_uuid,
                                       uuid=item_create.created_uuid,
                                       item_type='projects',
                                       label=rev_label,
                                       json_note=json_output)
                return HttpResponse(json_output,
                                    content_type='application/json; charset=utf8')
            else:
                json_output = json.dumps({'error': 'parent project is missing'},
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


@cache_control(no_cache=True)
@transaction.atomic()
@reversion.create_revision()
def delete_item(request, uuid):
    """ Handles POST requests to DELETE an item """
    item_edit = ItemBasicEdit(uuid, request)
    if item_edit.manifest is not False:
        if request.method == 'POST':
            if request.user.is_superuser:
                # only super users can delete an item, since deletion
                # can have big impacts
                item_del = ItemDelete(item_edit.manifest)
                result = item_del.delete_and_document(request.POST)
                if len(item_del.errors) > 0:
                    result['errors'] = item_del.errors
                else:
                    result['errors'] = []
                json_output = json.dumps(result,
                                         indent=4,
                                         ensure_ascii=False)
                # version control metadata
                rev_label = 'Delete item ' + item_del.manifest.label
                reversion.set_user(request.user)
                reversion.add_meta(VersionMetadata,
                                   project_uuid=item_del.manifest.project_uuid,
                                   uuid=item_del.manifest.uuid,
                                   item_type=item_del.manifest.item_type,
                                   label=rev_label,
                                   json_note=json_output)
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
def check_delete_item(request, uuid):
    """ Handles GET requests check on impacts of deleting an item """
    item_edit = ItemBasicEdit(uuid, request)
    if item_edit.manifest is not False:
        item_del = ItemDelete(item_edit.manifest)
        result = item_del.check_delete_item()
        json_output = json.dumps(result,
                                 indent=4,
                                 ensure_ascii=False)
        return HttpResponse(json_output,
                            content_type='application/json; charset=utf8')
    else:
        raise Http404