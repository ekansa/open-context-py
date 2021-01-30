import copy
import json
import reversion
import uuid as GenUUID

from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponse, Http404

from django.db.models import Q
from django.db import transaction

from django.template import RequestContext, loader
from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items.legacy_all import update_old_id
from opencontext_py.apps.all_items.editorial import api as editorial_api

from opencontext_py.apps.all_items.editorial.item import updater_manifest
from opencontext_py.apps.all_items.editorial.item import updater_assertions
from opencontext_py.apps.all_items.editorial.item import updater_spacetime
from opencontext_py.apps.all_items.editorial.item import updater_resource

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
from django.views.decorators.cache import cache_page
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
def item_edit_interface_html(request, uuid):
    """HTML representation for editing an Open Context item"""
    _, valid_uuid = update_old_id(uuid)
    man_obj = AllManifest.objects.filter(uuid=valid_uuid).first()
    if not man_obj:
        raise Http404

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

    item_project_uuids = []
    item_project = man_obj.project
    at_root_proj = False
    while at_root_proj:
        project_uuid = str(item_project.uuid)
        if not project_uuid in item_project_uuids:
            item_projects.append(project_uuid)
        else:
            at_root_proj = True
        if project_uuid == str(configs.OPEN_CONTEXT_PROJ_UUID):
            at_root_proj = True
        if not at_root_proj:
            # Now go up a level in the item hierarchy
            item_project = item_project.project

    rp = RootPath()
    context = {
        'base_url': rp.get_baseurl(),
        'man_obj': man_obj,
        # NOTE: ITEM_PROJECT_UUIDS is the list of parent project uuids for an item
        'ITEM_PROJECT_UUIDS': json.dumps(item_project_uuids),
        'OPEN_CONTEXT_PROJ_UUID': str(configs.OPEN_CONTEXT_PROJ_UUID),
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
        'MAPBOX_PUBLIC_ACCESS_TOKEN': settings.MAPBOX_PUBLIC_ACCESS_TOKEN,
        'OC_RESOURCE_FULLFILE': json.dumps(oc_resource_fullfile),
        'OC_RESOURCE_PREVIEW': json.dumps(oc_resource_preview),
        'OC_RESOURCE_THUMBNAIL': json.dumps(oc_resource_thumbnail),
        'OC_RESOURCE_HERO': json.dumps(oc_resource_hero),
        'OC_RESOURCE_TYPES_UUIDS': json.dumps(configs.OC_RESOURCE_TYPES_UUIDS),
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
        more_attributes=['item_class__label', 'context__label', 'project__label']
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
def update_manifest_fields(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    updated, errors = updater_manifest.update_manifest_fields(request_json)
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
def delete_manifest(request):
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
def update_assertions_fields(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    updated, errors = updater_assertions.update_attribute_fields(request_json)
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
    added, errors = updater_assertions.add_assertions(request_json)
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
    deleted, errors = updater_assertions.delete_assertions(request_json)
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
def update_space_time_fields(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    updated, errors = updater_spacetime.update_spacetime_fields(request_json)
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
    added, errors = updater_spacetime.add_spacetime_objs(request_json)
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
def delete_space_time(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    deleted, errors = updater_spacetime.delete_spacetime_objs(request_json)
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
def update_resource_fields(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    updated, errors = updater_resource.update_resource_fields(request_json)
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
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    added, errors = updater_resource.add_resource_objs(request_json)
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
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    deleted, errors = updater_resource.delete_resource_objs(request_json)
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
@transaction.atomic()
@reversion.create_revision()
def update_identifier_fields(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    return HttpResponse(
        '[]',
        content_type="application/json; charset=utf8"
    )
