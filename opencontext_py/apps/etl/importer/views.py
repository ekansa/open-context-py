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


def uuid_to_string(dict_obj):
    for key, val in dict_obj.items():
        if not isinstance(val, GenUUID.UUID):
            continue
        dict_obj[key] = str(val)
    return dict_obj


@ensure_csrf_cookie
@cache_control(no_cache=True)
@never_cache
def home_html(request, source_id):
    _, valid_uuid = update_old_id(source_id)
    ds_source = DataSource.objects.filter(
        Q(source_id=source_id)|Q(uuid=valid_uuid)
    ).first()
    if not ds_source:
        return Http404
    rp = RootPath()
    ds_fields_item_types =  [
        {'item_type': item_type, 'label': label,}
        for item_type, label, _ in DataSourceField.USER_SELECT_ITEM_TYPES
    ]
    ds_fields_data_types =  [
        {'data_type': data_type, 'label': label,}
        for data_type, label in DataSourceField.USER_SELECT_DATA_TYPES
    ]
    context = {
        'base_url': rp.get_baseurl(),
        'ds_source': ds_source,
        'oc_item_class_null': str(configs.DEFAULT_CLASS_UUID),
        'ds_fields_item_types': json.dumps(ds_fields_item_types),
        'ds_fields_data_types': json.dumps(ds_fields_data_types),
    }
    template = loader.get_template('bootstrap_vue/etl/etl.html')
    response = HttpResponse(template.render(context, request))
    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
    return response


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


@cache_control(no_cache=True)
@never_cache
def etl_field_record_examples(request, field_uuid):
    """Get JSON list of example values in a data source field"""
    source_id = request.GET.get('source_id')
    field_num = request.GET.get('field_num')
    if source_id and field_num:
        # Get the field by specifying the data_source id
        # and the field number.
        _, valid_souce_uuid = update_old_id(source_id)
        ds_field = DataSourceField.objects.filter(
             Q(data_source__source_id=source_id)
             |Q(data_source_id=valid_souce_uuid)
        ).filter(
            field_num=field_num
        ).first()

    else:
        # Get the field by the field's UUID.
        _, valid_field_uuid = update_old_id(field_uuid)
        ds_field = DataSourceField.objects.filter(
            uuid=valid_field_uuid,
        ).first()
    if not ds_field:
        return Http404

    # Default to random sorting
    sort = request.GET.get('sort', '?')
    # Default to staring at the begining
    start = request.GET.get('start', 0)
    # Default to 5 rows returned.
    rows = request.GET.get('rows', 5)
    if rows < 1:
        rows = 1

    ds_rec_qs = DataSourceRecord.objects.filter(
        data_source=ds_field.data_source,
        field_num=ds_field.field_num,
    ).select_related(
        'context'
    ).select_related(
        'item'
    ).select_related(
        'item__item_class'
    ).distinct(
        'record'
    ).order_by(
    ).values(
        'uuid',
        'data_source_id',
        'data_source__label',
        'data_source__source_id',
        'row_num',
        'field_num',
        'context_id',
        'context__item_type',
        'context__label',
        'item_id',
        'item__item_type',
        'item__label',
        'item__item_class_id',
        'item__item_class__label',
        'record',
    )[start:(start + rows)]
    
    output = []
    for r_dict in ds_rec_qs:
        r_dict['ds_field_id'] = str(ds_field.uuid)
        r_dict['ds_field__label'] = ds_field.label
        r_dict = uuid_to_string(r_dict)
        if ds_field.value_prefix:
            r_dict['record'] = (
                str(ds_field.value_prefix)
                + r_dict.get('record', '')
            )
        output.append(r_dict )

    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )