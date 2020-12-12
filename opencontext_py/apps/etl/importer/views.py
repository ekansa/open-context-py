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
from opencontext_py.apps.all_items.editorial import api as editorial_api

from opencontext_py.apps.etl.importer.models import (
    DataSource,
    DataSourceField,
    DataSourceRecord,
    DataSourceAnnotation,
)
from opencontext_py.apps.etl.importer import df as etl_df

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

    pred_link = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.PREDICATE_LINK_UUID,
        do_minimal=True,
    )
    # NOTE: Used for general spatial containment
    pred_contains =  editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.PREDICATE_CONTAINS_UUID,
        do_minimal=True,
    )
    # NOTE: Used to define relationships between media and (file) resources
    pred_media_has_files = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.PREDICATE_CONTAINS_UUID,
        do_minimal=True,
    )
    # NOTE: Used to define variable->value relationsips.
    pred_rdfs_range = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.PREDICATE_RDFS_RANGE_UUID,
        do_minimal=True,
    )
    # NOTE: Used to define 'described by' relationships.
    pred_described_by = editorial_api.get_manifest_item_dict_by_uuid(
        uuid=configs.PREDICATE_OC_ETL_DESCRIBED_BY,
        do_minimal=True,
    )

    context = {
        'base_url': rp.get_baseurl(),
        'ds_source': ds_source,
        'OPEN_CONTEXT_PROJ_UUID': str(configs.OPEN_CONTEXT_PROJ_UUID),
        'DEFAULT_CLASS_UUID': str(configs.DEFAULT_CLASS_UUID),
        'DESCRIBED_BY_LINK_OK_ITEM_TYPES': json.dumps(
            DataSourceAnnotation.DESCRIBED_BY_LINK_OK_ITEM_TYPES
        ),
        'DESCRIBED_BY_OK_OBJECT_TYPES': json.dumps(
            DataSourceAnnotation.DESCRIBED_BY_OK_OBJECT_TYPES
        ),
        'PREDICATE_LINK': json.dumps(pred_link),
        'PREDICATE_CONTAINS': json.dumps(pred_contains),
        'PREDICATE_OC_ETL_MEDIA_HAS_FILES': json.dumps(pred_media_has_files),
        'PREDICATE_RDFS_RANGE': json.dumps(pred_rdfs_range),
        'PREDICATE_OC_ETL_DESCRIBED_BY': json.dumps(pred_described_by),
        'DS_FIELDS_ITEM_TYPES': json.dumps(ds_fields_item_types),
        'DS_FIELDS_DATA_TYPES': json.dumps(ds_fields_data_types),
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
        editorial_api.dict_uuids_to_string(ds_source),
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
        editorial_api.dict_uuids_to_string(f) for f in ds_fields_qs
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
    start = editorial_api.make_integer_or_default(
        raw_value=request.GET.get('start', 0),
        default_value=0
    )
    # Default to 5 rows returned.
    rows = editorial_api.make_integer_or_default(
        raw_value=request.GET.get('rows', 5),
        default_value=5
    )
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
        r_dict = editorial_api.dict_uuids_to_string(r_dict)
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


@cache_control(no_cache=True)
@never_cache
def etl_annotations(request, source_id):
    _, valid_uuid = update_old_id(source_id)
    ds_anno_qs = DataSourceAnnotation.objects.filter(
        Q(data_source__source_id=source_id)
        |Q(data_source__uuid=valid_uuid)
    ).select_related(
        'data_source'
    ).select_related(
        'subject_field'
    ).select_related(
        'subject_field__item_class'
    ).select_related(
        'subject_field__context'
    ).select_related(
        'predicate'
    ).select_related(
        'predicate_field'
    ).select_related(
        'object'
    ).select_related(
        'object__item_class'
    ).select_related(
        'object__context'
    ).select_related(
        'object_field'
    ).select_related(
        'object_field__item_class'
    ).select_related(
        'object_field__context'
    ).select_related(
        'observation'
    ).select_related(
        'observation_field'
    ).select_related(
        'event'
    ).select_related(
        'event_field'
    ).select_related(
        'attribute_group'
    ).select_related(
        'attribute_group_field'
    ).select_related(
        'language'
    ).select_related(
        'language_field'
    ).values(
        'uuid',
        'data_source_id',
        'data_source__label',
        'data_source__source_id',

        'subject_field_id',
        'subject_field__field_num',
        'subject_field__label',
        'subject_field__item_type',
        'subject_field__data_type',
        'subject_field__item_class_id',
        'subject_field__item_class__label',
        'subject_field__context_id',
        'subject_field__context__item_type',
        'subject_field__context__label',
        'subject_field__unique_count',

        'predicate_id',
        'predicate__label',
        'predicate__data_type',
        'predicate_field_id',
        'predicate_field__field_num',
        'predicate_field__label',
        'predicate_field__data_type',

        'object_id',
        'object__label',
        'object__item_class_id',
        'object__item_class__label',
        'object__context_id',
        'object__context__label',
        'object_field_id',
        'object_field__field_num',
        'object_field__label',
        'object_field__item_class_id',
        'object_field__item_class__label',
        'object_field__context_id',
        'object_field__context__label',

        'obj_string',
        'obj_boolean',
        'obj_integer',
        'obj_double',
        'obj_datetime',

        'observation_id',
        'observation__label',
        'observation_field_id',
        'observation_field__field_num',
        'observation_field__label',
       
        'event_id',
        'event__label',
        'event_field_id',
        'event_field__field_num',
        'event_field__label',

        'attribute_group_id',
        'attribute_group__label',
        'attribute_group_field_id',
        'attribute_group_field__field_num',
        'attribute_group_field__label',
    
        'language_id',
        'language__label',
        'language_field_id',
        'language_field__field_num',
        'language_field__label',

        'meta_json', 
    )
    output = [
        editorial_api.dict_uuids_to_string(ds_anno) 
        for ds_anno in ds_anno_qs
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
def etl_described_by_examples(request, source_id):
    """Returns examples of described by replationships"""

    number_examples = request.GET.get('number_examples', 5)

    _, valid_uuid = update_old_id(source_id)
    ds_anno_qs = DataSourceAnnotation.objects.filter(
        Q(data_source__source_id=source_id)
        |Q(data_source__uuid=valid_uuid)
    ).filter(
        predicate_id=configs.PREDICATE_OC_ETL_DESCRIBED_BY
    ).select_related(
        'data_source'
    ).select_related(
        'subject_field'
    ).select_related(
        'subject_field__item_class'
    ).select_related(
        'object_field'
    ).order_by('subject_field__field_num', 'object_field__field_num')

    if not len(ds_anno_qs):
        return HttpResponse(
            '[]',
            content_type="application/json; charset=utf8"
        )
    
    ds_source = ds_anno_qs[0].data_source
    
    subjs_objects = {ds_anno.subject_field:[] for ds_anno in ds_anno_qs}
    for ds_anno in ds_anno_qs:
        subjs_objects[ds_anno.subject_field].append(
            ds_anno.object_field
        )
    
    results = []
    for subject_field, object_field_list in subjs_objects.items():
        # Get records for the subject field. This will be
        # non-blank records.
        sub_rec_qs = DataSourceRecord.objects.filter(
            data_source=ds_source,
            field_num=subject_field.field_num,
        )[0:number_examples]
        if not len(sub_rec_qs):
            # We don't have any subject records.
            continue
        # Make a list of rows to limit for a dataframe.
        row_list = [r.row_num for r in sub_rec_qs]
        object_field_nums = [o_f.field_num for o_f in object_field_list]
        print(f'Object fields: {object_field_nums}')
        df = etl_df.db_make_dataframe_from_etl_data_source(
            ds_source,
            use_column_labels=True,
            limit_field_num_list=([subject_field.field_num] + object_field_nums),
            limit_row_num_list=row_list,
        )
        
        # Add value prefixes if needed to the subject field.
        if subject_field.value_prefix and subject_field.label in df.columns:
            df[subject_field.label] = subject_field.value_prefix + df[subject_field.label]

        # Arrange columns so the subject field is first. Drop the row number.
        df.drop(columns=['row_num'], inplace=True, errors='ignore')
        object_cols = [c for c in df.columns if c != subject_field.label]
        if subject_field.label in df.columns:
            final_cols = [subject_field.label] + object_cols
        else:
            final_cols = object_cols
        
        result = {
            'subject_field_id': str(subject_field.uuid),
            'subject_field__field_num': subject_field.field_num,
            'subject_field__label': subject_field.label,
            'subject_field__item_type': subject_field.item_type,
            'subject_field__item_class_id': str(subject_field.item_class.uuid),
            'subject_field__item_class__label': subject_field.item_class.label,
            'examples': df[final_cols].to_dict('records'),
        }
        results.append(result)

    json_output = json.dumps(
        results,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )
