import json
import uuid as GenUUID
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponse, Http404

from django.db.models import Q

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

from opencontext_py.apps.etl.importer.models import (
    DataSource,
    DataSourceField,
    DataSourceRecord,
    DataSourceAnnotation,
)
from opencontext_py.apps.etl.importer.setup import updater as etl_setup_updater


from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.views.decorators.cache import cache_page
from django.utils.cache import patch_vary_headers


# NOTE: This handles HTTP POST requests to setup an ETL and 
# ingest process for Open Context.

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
def etl_update_fields(request):
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    updated, errors = etl_setup_updater.update_fields(request_json)
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

