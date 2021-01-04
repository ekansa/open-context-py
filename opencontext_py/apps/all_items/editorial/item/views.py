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
from opencontext_py.apps.all_items.editorial.item import updater as item_updater

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

    rp = RootPath()
    context = {
        'base_url': rp.get_baseurl(),
        'man_obj': man_obj,
        'OPEN_CONTEXT_PROJ_UUID': str(configs.OPEN_CONTEXT_PROJ_UUID),
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
        man_obj
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
def update_manifest_fields(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    updated, errors = item_updater.update_manifest_fields(request_json)
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
def update_assertions_fields(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    return HttpResponse(
        '[]',
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
    return HttpResponse(
        '[]',
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
    return HttpResponse(
        '[]',
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
