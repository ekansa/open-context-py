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

from opencontext_py.apps.all_items.editorial.tables import create_df
from opencontext_py.apps.all_items.editorial.tables import create_que


from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.views.decorators.cache import cache_page
from django.utils.cache import patch_vary_headers


#----------------------------------------------------------------------
# NOTE: These are views relating to user interfaces for creating new
# export tables.
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


@cache_control(no_cache=True)
@never_cache
def test_export(request, export_id=None):
    """Makes tests an export that is temporarily cached"""
    if export_id == 'start':
        export_id = None

    kwargs = {
        'filter_args': {
            'subject__item_class__label__contains': 'Animal',
            'subject__path__contains': 'Italy',
        },
        'exclude_args': {'subject__path__contains': 'Vescovado'},
        'add_entity_ld': True,
        'add_literal_ld': True,
        'add_object_uris': True,
        'reset_cache': True,
        'export_id': export_id,
    }
    if kwargs.get('export_id'):
        kwargs['reset_cache'] = False

    output = create_que.staged_make_export_df(**kwargs)
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
def make_export(request):
    """Makes an export that is temporarily cached"""
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
@reversion.create_revision()
def save_export(request):
    """Save an export as an Open Context item_type tables object"""
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    output = {
        'ok': True,
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


