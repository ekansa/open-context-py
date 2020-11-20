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


from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.views.decorators.cache import cache_page
from django.utils.cache import patch_vary_headers



# NOTE: This handles HTTP GET requests to give clients/users
# information about the setup and status of an ETL process.

@ensure_csrf_cookie
@cache_control(no_cache=True)
@never_cache
def view_html(request, source_id):
    _, valid_uuid = update_old_id(source_id)
    ds_source = DataSource.objects.filter(
        Q(source_id=source_id)|Q(uuid=valid_uuid)
    ).first()
    if not ds_source:
        return Http404
    rp = RootPath()
    # Disable the search template and just use vue with the JSON
    # API.
    # search_temp = SearchTemplate(response_dict.copy())
    context = {
        'base_url': rp.get_baseurl(),
        'ds_source': ds_source,
    }
    template = loader.get_template('bootstrap_vue/etl/etl.html')
    response = HttpResponse(template.render(context, request))
    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
    return response


def uuid_to_string(dict_obj):
    for key, val in dict_obj.items():
        if not isinstance(val, GenUUID.UUID):
            continue
        dict_obj[key] = str(val)
    return dict_obj


@cache_control(no_cache=True)
@never_cache
def etl_source(request, source_id):
    _, valid_uuid = update_old_id(source_id)
    ds_source = DataSource.objects.filter(
        Q(source_id=source_id)|Q(uuid=valid_uuid)
    ).select_related(
        'project'
    ).values(
        'uuid',
        'project_id',
        'project__label',
        'label',
        'field_count',
        'row_count',
        'source_type',
        'status',
        'meta_json',
    ).first()
    if not ds_source:
        return Http404
    json_output = json.dumps(
        uuid_to_string(ds_source),
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@cache_control(no_cache=True)
@never_cache
def etl_fields(request, source_id):
    _, valid_uuid = update_old_id(source_id)
    ds_fields_qs = DataSourceField.objects.filter(
        Q(data_source__source_id=source_id)
        |Q(data_source__uuid=valid_uuid)
    ).select_related(
        'data_source'
    ).select_related(
        'item_class'
    ).select_related(
        'context'
    ).values(
        'uuid',
        'data_source_id',
        'data_source__label',
        'data_source__source_id',
        'field_num',
        'label',
        'ref_orig_name',
        'item_type',
        'data_type',
        'item_class_id',
        'item_class__label',
        'context_id',
        'context__item_type',
        'context__label',
        'value_prefix',
        'unique_count',
        'meta_json', 
    )
    output = [
        uuid_to_string(f) for f in ds_fields_qs
    ]
    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


