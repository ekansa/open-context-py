import copy
import json
import reversion

from django.conf import settings
from django.http import HttpResponse, Http404

from django.db import transaction

from django.template import loader
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

from opencontext_py.apps.all_items.legacy_all import update_old_id
from opencontext_py.apps.all_items.editorial import api as editorial_api

# These imports are for making aggregate geospatial regions.
from opencontext_py.apps.all_items.geospace import aggregate as geo_agg
from opencontext_py.apps.all_items.geospace import queue_utilities as geo_queue

from opencontext_py.apps.all_items import permissions
from opencontext_py.apps.all_items.editorial.item import edit_configs
from opencontext_py.apps.all_items.editorial.item import updater_manifest
from opencontext_py.apps.all_items.editorial.item import updater_assertions
from opencontext_py.apps.all_items.editorial.item import updater_spacetime
from opencontext_py.apps.all_items.editorial.item import updater_resources
from opencontext_py.apps.all_items.editorial.item import updater_identifiers
from opencontext_py.apps.all_items.editorial.item import updater_project
from opencontext_py.apps.all_items.editorial.item import item_validation
from opencontext_py.apps.all_items.editorial.item import projects_api

from opencontext_py.apps.all_items.representations.item import (
    get_item_assertions,
    get_observations_attributes_from_assertion_qs,
)

from opencontext_py.libs.models import (
    make_dict_json_safe,
    make_model_object_json_safe_dict
)

from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.utils.cache import patch_vary_headers


#----------------------------------------------------------------------
# NOTE: These are views relating to user interfaces for editing
# individual items and for handling requests to change individual
# items.
# ---------------------------------------------------------------------

def make_error_response(errors):
    output = {
        'message': f'Errors: {len(errors)}',
        'errors': errors,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8",
        status=400
    )



@never_cache
@cache_control(no_cache=True)
def item_add_configs_json(request):
    """JSON representation of item add configuration"""
    if request.GET.get('item_type') == 'tables':
        configs = edit_configs.api_single_item_type_config_response(
            edit_configs.TABLES_ADD_EDIT_CONFIG.copy()
        )
    else:
        configs = edit_configs.api_all_item_types_config_response()
    json_output = json.dumps(
        configs,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@never_cache
@cache_control(no_cache=True)
def item_edit_interface_html(request, uuid):
    """HTML representation for editing an Open Context item"""
    _, valid_uuid = update_old_id(uuid)
    man_obj = AllManifest.objects.filter(uuid=valid_uuid).first()
    if not man_obj:
        raise Http404

    _, ok_edit = permissions.get_request_user_permissions(
        request,
        man_obj
    )
    if not ok_edit:
        return HttpResponse(
            'Must have edit permissions', status=403
        )

    # NOTE: Used to get the default observation
    default_obs = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.DEFAULT_OBS_UUID,
        do_minimal=True,
    )
    # NOTE: Used to get the default event.
    default_event = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.DEFAULT_EVENT_UUID,
        do_minimal=True,
    )
    # NOTE: Used to get the default attribute group.
    default_attribute_group = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.DEFAULT_ATTRIBUTE_GROUP_UUID,
        do_minimal=True,
    )
    # NOTE: Used to get the default language
    default_lang = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.DEFAULT_LANG_UUID,
        do_minimal=True,
    )
    # NOTE: Used for general spatial containment
    pred_contains =  editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.PREDICATE_CONTAINS_UUID,
        do_minimal=True,
    )
    # NOTE: Used as a general (or not specified) item-class.
    default_class = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.DEFAULT_CLASS_UUID,
        do_minimal=True,
    )
    # NOTE: This is to identify predicates that take 'types' as objects
    oc_variables = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.CLASS_OC_VARIABLES_UUID,
        do_minimal=True,
    )
    oc_links = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.CLASS_OC_LINKS_UUID,
        do_minimal=True,
    )
    # NOTE: These are the main resource types expected for media resources
    oc_resource_fullfile = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.OC_RESOURCE_FULLFILE_UUID,
        do_minimal=True,
    )
    oc_resource_preview = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.OC_RESOURCE_PREVIEW_UUID,
        do_minimal=True,
    )
    oc_resource_thumbnail = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.OC_RESOURCE_THUMBNAIL_UUID,
        do_minimal=True,
    )
    oc_resource_hero = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.OC_RESOURCE_HERO_UUID,
        do_minimal=True,
    )

    item_type_edit_config = {}
    for group_configs in edit_configs.api_all_item_types_config_response():
        for act_item_type_config in group_configs.get('item_types', []):
            if act_item_type_config.get('item_type') != man_obj.item_type:
                continue
            item_type_edit_config = copy.deepcopy(act_item_type_config)

    item_project_uuids = []
    if man_obj.item_type == 'projects':
        # This item itself is a project, which means that we want
        # to use it as the editing_project in the user interface.
        item_project_uuids.append(str(man_obj.uuid))
        editing_project_dict = make_model_object_json_safe_dict(man_obj)
    else:
        # The item's project sets the editing project.
        editing_project_dict = make_model_object_json_safe_dict(man_obj.project)

    item_project = man_obj.project
    at_root_proj = False
    while not at_root_proj:
        project_uuid = str(item_project.uuid)
        if not project_uuid in item_project_uuids:
            item_project_uuids.append(project_uuid)
        else:
            at_root_proj = True
        if project_uuid == str(configs.OPEN_CONTEXT_PROJ_UUID):
            at_root_proj = True
        if not at_root_proj:
            # Now go up a level in the item hierarchy
            item_project = item_project.project

    rp = RootPath()
    context = {
        'BASE_URL': rp.get_baseurl(),
        'PAGE_TITLE': f'Open Context Edit: {man_obj.label}',
        'man_obj': man_obj,
        # NOTE: ITEM_PROJECT_UUIDS is the list of parent project uuids for an item
        'ITEM_PROJECT_UUIDS': json.dumps(item_project_uuids),
        'OPEN_CONTEXT_PROJ_UUID': str(configs.OPEN_CONTEXT_PROJ_UUID),
        # NOTE: This is the project that we are currently editing. It will be
        # the default project for new Open Context items to be created into.
        'EDITING_PROJECT': json.dumps(editing_project_dict),
        # This is the oc link class id, used in manifest editing to auto
        # trigger the data_type to change to 'id'.
        'OC_LINKS_ID': str(configs.CLASS_OC_LINKS_UUID),
        # This is the edit config for the current item type.
        'ITEM_TYPE_EDIT_CONFIG': json.dumps(item_type_edit_config),
        'DEFAULT_OBS': json.dumps(default_obs),
        'DEFAULT_EVENT': json.dumps(default_event),
        'DEFAULT_ATTRIBUTE_GROUP': json.dumps(default_attribute_group),
        'DEFAULT_LANG': json.dumps(default_lang),
        'PREDICATE_CONTAINS': json.dumps(pred_contains),
        'DEFAULT_CLASS': json.dumps(default_class),
        'OC_VARIABLES': json.dumps(oc_variables),
        'OC_LINKS': json.dumps(oc_links),
        'OC_PRED_LINK_OK_ITEM_TYPES': json.dumps(configs.OC_PRED_LINK_OK_ITEM_TYPES),
        'GEOMETRY_TYPES': json.dumps(AllSpaceTime.GEOMETRY_TYPES),
        'GEO_AGG_CLUSTER_METHODS': json.dumps(geo_agg.CLUSTER_METHODS),
        'MAPBOX_PUBLIC_ACCESS_TOKEN': settings.MAPBOX_PUBLIC_ACCESS_TOKEN,
        'OC_RESOURCE_FULLFILE': json.dumps(oc_resource_fullfile),
        'OC_RESOURCE_PREVIEW': json.dumps(oc_resource_preview),
        'OC_RESOURCE_THUMBNAIL': json.dumps(oc_resource_thumbnail),
        'OC_RESOURCE_HERO': json.dumps(oc_resource_hero),
        'OC_RESOURCE_TYPES_UUIDS': json.dumps(configs.OC_RESOURCE_TYPES_UUIDS),
        'OC_IDENTIFIER_SCHEME_CONFIGS': json.dumps(AllIdentifier.SCHEME_CONFIGS),
    }
    template = loader.get_template('bootstrap_vue/editorial/item/edit_item.html')
    response = HttpResponse(template.render(context, request))
    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
    return response


@never_cache
@cache_control(no_cache=True)
def item_history_json(request, uuid):
    """JSON representation of a manifest object's edit history"""
    _, valid_uuid = update_old_id(uuid)
    man_obj = AllManifest.objects.filter(uuid=valid_uuid).first()
    if not man_obj:
        return HttpResponse(
            json.dumps([]),
            content_type="application/json; charset=utf8",
            status=404
        )
    # Get the edit history of this particular manifest object.
    api_result = []
    history_qs = AllHistory.objects.filter(
        item=man_obj
    ).order_by('-updated')
    for hist_obj in history_qs:
        api_result.append(
            make_model_object_json_safe_dict(hist_obj)
        )

    json_output = json.dumps(
        api_result,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )



# ---------------------------------------------------------------------
# NOTE: Item Manifest Edit endpoints
# ---------------------------------------------------------------------
@never_cache
@cache_control(no_cache=True)
def item_manifest_json(request, uuid):
    """JSON representation of a manifest object"""
    _, valid_uuid = update_old_id(uuid)
    man_obj = AllManifest.objects.filter(uuid=valid_uuid).first()
    if not man_obj:
        return HttpResponse(
            json.dumps({}),
            content_type="application/json; charset=utf8",
            status=404
        )

    api_result = make_model_object_json_safe_dict(
        man_obj,
        more_attributes=[
            'meta_json',
            'item_class__label',
            'context__label',
            'project__label'
        ]
    )
    json_output = json.dumps(
        api_result,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@never_cache
@cache_control(no_cache=True)
def item_manifest_validation(request):
    """JSON representation of a manifest object"""
    request_dict = {}
    for key, key_val in request.GET.items():
        request_dict[key] = request.GET.get(key)

    api_result = item_validation.api_validate_manifest_attributes(request_dict)
    json_output = json.dumps(
        api_result,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def update_manifest_objs(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    updated, errors = updater_manifest.update_manifest_objs(
        request_json,
        request=request,
    )
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'updated': updated,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def add_manifest_objs(request):
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    added, errors = updater_manifest.add_manifest_objs(request_json)
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'added': added,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
# @reversion.create_revision()
def delete_manifest(request):
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    deleted, errors = updater_manifest.delete_manifest_objs(request_json)
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'deleted': deleted,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
# @reversion.create_revision()
def merge_manifest(request):
    if not request.user.is_superuser:
        # This can really mess things up, so only let this work
        # for super users
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    merges, errors, warnings = updater_manifest.api_merge_manifest_objs(request_json)
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'merges': merges,
        'warnings': warnings,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


# ---------------------------------------------------------------------
# NOTE: Item Assertion Edit endpoints
# ---------------------------------------------------------------------
@never_cache
@cache_control(no_cache=True)
def item_assertions_json(request, uuid):
    """JSON representation of assertions about an item"""
    _, valid_uuid = update_old_id(uuid)
    man_obj = AllManifest.objects.filter(uuid=valid_uuid).first()
    if not man_obj:
        return HttpResponse(
            json.dumps({}),
            content_type="application/json; charset=utf8",
            status=404
        )

    assert_qs = get_item_assertions(man_obj.uuid)

    if request.GET.get('linked-data'):
        # Limit assertions to linked data class and properties
        assert_qs = assert_qs.filter(
            predicate__item_type__in=['class', 'property',]
        )
    else:
        # Exclude assertions with linked data class and properties predicates
        assert_qs = assert_qs.exclude(
            predicate__item_type__in=['class', 'property',]
        )

    observations = get_observations_attributes_from_assertion_qs(
        assert_qs,
        for_edit=True
    )
    api_result = make_dict_json_safe(
        observations,
        javascript_friendly_keys=True
    )

    json_output = json.dumps(
        api_result,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def update_assertions_objs(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    updated, errors = updater_assertions.update_attribute_objs(
        request_json,
        request=request,
    )
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'updated': updated,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def add_assertions(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    added, errors = updater_assertions.add_assertions(
        request_json,
        request=request,
    )
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'added': added,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def delete_assertions(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    deleted, errors = updater_assertions.delete_assertions(
        request_json,
        request=request,
    )
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'added': deleted,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
def sort_item_assertions(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    count_updated, errors = updater_assertions.sort_item_assertions(
        request_json,
        request=request,
    )
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'count_updated': count_updated,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
def sort_project_assertions(request):

    # NOTE: This request inputs and outputs have the same standard as
    # other project-wide editorial commands that require use of the
    # cache and / or queue.

    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    sorts_done, updated, errors = updater_assertions.sort_project_assertions(
        request_json,
        request=request,
    )
    if len(errors):
        # We failed.
        return make_error_response(errors)

    count_updated = 0
    progress = 0
    message = 'Sort started'
    if updated and len(updated):
        complete = sorts_done
        for update in updated:
            count_updated = update.get('last_chunk_index', 0)
            complete &= update.get('done', False)
            progress = (
                updated[0].get('last_chunk_index', 0)
                / updated[0].get('total_chunks', 1)
            )
            if complete:
                message = (
                    f"Finished sort of {update.get('total_uuids_count', 1)} items"
                )
            else:
                message = (
                    f"Batch {update.get('last_chunk_index', 0)} "
                    f"of {update.get('total_chunks', 1)}, "
                    f"{update.get('total_uuids_count', 1)} total items"
                )

    output = {
        'ok': True,
        'complete': complete,
        'updated': updated,
        'count_updated': count_updated,
        'progress': progress,
        'message': message,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


# ---------------------------------------------------------------------
# NOTE: Item Spacetime Edit endpoints
# ---------------------------------------------------------------------
@never_cache
@cache_control(no_cache=True)
def item_spacetime_json(request, uuid):
    """JSON representation of space-time about an item"""
    _, valid_uuid = update_old_id(uuid)
    man_obj = AllManifest.objects.filter(uuid=valid_uuid).first()
    if not man_obj:
        return HttpResponse(
            json.dumps({}),
            content_type="application/json; charset=utf8",
            status=404
        )

    # List of related object attributes to add to the JSON
    # output for each space-time object.
    more_attributes = [
        'item__label',
        'event__label',
        'event__item_class_id',
        'event__item_class__label',
    ]
    api_result = []
    spacetime_qs = AllSpaceTime.objects.filter(
        item=man_obj
    )
    for spacetime_obj in spacetime_qs:
        api_result.append(
            make_model_object_json_safe_dict(
                spacetime_obj,
                more_attributes=more_attributes
            )
        )

    json_output = json.dumps(
        api_result,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def update_space_time_objs(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    updated, errors = updater_spacetime.update_spacetime_objs(
        request_json,
        request=request,
    )
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'updated': updated,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def add_space_time(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    added, errors = updater_spacetime.add_spacetime_objs(
        request_json,
        request=request,
    )
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'added': added,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def add_aggregate_space_time(request):
    if not request.user.is_superuser:
        # Since this uses a worker, safer to make it only
        # for super users.
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    output = geo_queue.worker_add_agg_spacetime_objs(
        **request_json
    )
    if len(output.get('errors', [])):
        # We failed.
        return make_error_response(output.get('errors'))

    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def delete_space_time(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    deleted, errors = updater_spacetime.delete_spacetime_objs(
        request_json,
        request=request,
    )
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'deleted': deleted,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


# ---------------------------------------------------------------------
# NOTE: Item Resource Edit endpoints
# ---------------------------------------------------------------------
@never_cache
@cache_control(no_cache=True)
def item_resources_json(request, uuid):
    """JSON representation of resources about an item"""
    _, valid_uuid = update_old_id(uuid)
    man_obj = AllManifest.objects.filter(uuid=valid_uuid).first()
    if not man_obj:
        return HttpResponse(
            json.dumps({}),
            content_type="application/json; charset=utf8",
            status=404
        )

    # List of related object attributes to add to the JSON
    # output for each resources object.
    more_attributes = [
        'item__label',
        'resourcetype__label',
        'mediatype__label',
    ]
    api_result = []
    resource_qs = AllResource.objects.filter(
        item=man_obj
    ).order_by('-filesize')
    for resource_obj in resource_qs:
        api_result.append(
            make_model_object_json_safe_dict(
                resource_obj,
                more_attributes=more_attributes
            )
        )

    json_output = json.dumps(
        api_result,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def update_resource_objs(request):
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    updated, errors = updater_resources.update_resource_objs(request_json)
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'updated': updated,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def add_resources(request):
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    added, errors = updater_resources.add_resource_objs(request_json)
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'added': added,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def delete_resources(request):
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    deleted, errors = updater_resources.delete_resource_objs(request_json)
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'deleted': deleted,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )



# ---------------------------------------------------------------------
# NOTE: Flag human remains in a project's records
# ---------------------------------------------------------------------
@cache_control(no_cache=True)
@never_cache
def flag_project_human_remains(request):

    # NOTE: This request inputs and outputs have the same standard as
    # other project-wide editorial commands that require use of the
    # cache and / or queue.

    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    hr_done, updated, errors = updater_project.queued_flag_project_human_remains(
        request_json,
        request=request
    )
    if len(errors):
        # We failed.
        return make_error_response(errors)

    count_updated = 0
    progress = 0
    message = 'Flagging started'
    job_id = None
    if updated and len(updated):
        complete = hr_done
        for update in updated:
            count_updated += update.get('count_updated', 0)
            job_id = update.get('job_id')
            if not update.get('done', False):
                complete = False
                progress = 0.45
            if complete:
                message = (
                    f"Finished human remains flagging of {count_updated} records"
                )
                progress = 1
            else:
                message = (
                   f"Continuing to flag human remains records..."
                )
    output = {
        'ok': True,
        'complete': complete,
        'updated': updated,
        'count_updated': count_updated,
        'progress': progress,
        'message': message,
        'job_id': job_id,
    }

    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


# ---------------------------------------------------------------------
# NOTE: Item Identifier Edit endpoints
# ---------------------------------------------------------------------
@never_cache
@cache_control(no_cache=True)
def item_identifiers_json(request, uuid):
    """JSON representation of identifiers about an item"""
    _, valid_uuid = update_old_id(uuid)
    man_obj = AllManifest.objects.filter(uuid=valid_uuid).first()
    if not man_obj:
        return HttpResponse(
            json.dumps({}),
            content_type="application/json; charset=utf8",
            status=404
        )

    # List of related object attributes to add to the JSON
    # output for each resources object.
    more_attributes = [
        'item__label',
    ]
    api_result = []
    id_qs = AllIdentifier.objects.filter(
        item=man_obj
    )
    for id_obj in id_qs:
        api_result.append(
            make_model_object_json_safe_dict(
                id_obj,
                more_attributes=more_attributes
            )
        )

    json_output = json.dumps(
        api_result,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def update_identifier_objs(request):
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    updated, errors = updater_identifiers.update_identifier_objs(request_json)
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'updated': updated,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def add_identifiers(request):
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    added, errors = updater_identifiers.add_identifier_objs(request_json)
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'added': added,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
@transaction.atomic()
@reversion.create_revision()
def delete_identifiers(request):
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    deleted, errors = updater_identifiers.delete_identifier_objs(request_json)
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'deleted': deleted,
    }
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


# ---------------------------------------------------------------------
# NOTE: The views below support user interfaces for navigating the
# content of projects
# ---------------------------------------------------------------------
@never_cache
@cache_control(no_cache=True)
def project_descriptions_tree_json(request, identifier):
    """ API for getting a project's tree of descriptive predicates """
    api_result = projects_api.project_descriptions_tree(identifier)
    if not api_result:
        return HttpResponse(
            json.dumps([]),
            content_type="application/json; charset=utf8",
            status=404
        )

    json_output = json.dumps(
        api_result,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@never_cache
@cache_control(no_cache=True)
def project_spatial_tree_json(request, identifier):
    """ API for getting a project's tree of spatial/subjects items """
    api_result = projects_api.project_spatial_tree(identifier)
    if not api_result:
        return HttpResponse(
            json.dumps([]),
            content_type="application/json; charset=utf8",
            status=404
        )

    json_output = json.dumps(
        api_result,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@never_cache
@cache_control(no_cache=True)
def project_data_sources_json(request, identifier):
    """ API for getting a project's ETL data sources """
    api_result = projects_api.project_data_sources(identifier)

    json_output = json.dumps(
        api_result,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@never_cache
@cache_control(no_cache=True)
def project_persons_json(request, identifier):
    """ API for getting a project's people """
    api_result = projects_api.project_persons(identifier)
    json_output = json.dumps(
        api_result,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )