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
from opencontext_py.apps.etl.importer.transforms import finalize_all


from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.views.decorators.cache import cache_page
from django.utils.cache import patch_vary_headers


# NOTE: This handles HTTP POST requests to setup an ETL and 
# ingest process for Open Context.


@cache_control(no_cache=True)
@never_cache
def etl_reset_transform_load(request, source_id):
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    _, valid_uuid = update_old_id(source_id)
    ds_source = DataSource.objects.filter(
        Q(source_id=source_id)|Q(uuid=valid_uuid)
    ).first()
    if not ds_source:
        return Http404
    
    count_prior_load_deleted, count_etl_cache_deleted = finalize_all.reset_data_source_transform_load(
        ds_source
    )
    output = {
        'ok': True,
        'count_prior_load_deleted': count_prior_load_deleted,
        'count_etl_cache_deleted': count_etl_cache_deleted,
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
def etl_transform_load(request, source_id):
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    _, valid_uuid = update_old_id(source_id)
    ds_source = DataSource.objects.filter(
        Q(source_id=source_id)|Q(uuid=valid_uuid)
    ).first()
    if not ds_source:
        return Http404
    
    etl_stages = finalize_all.transform_load(ds_source)
    
    json_output = json.dumps(
        etl_stages,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )