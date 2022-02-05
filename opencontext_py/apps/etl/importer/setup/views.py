import json
from django.http import HttpResponse



from opencontext_py.apps.etl.importer.models import (
    DataSourceAnnotation,
)
from opencontext_py.apps.etl.importer.setup import updater as etl_setup_updater


from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


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
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
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


@cache_control(no_cache=True)
@never_cache
def etl_delete_annotations(request):
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )

    delete_uuids = json.loads(request.body)
    if not isinstance(delete_uuids, list):
        return HttpResponse(
            'Must POST a JSON encoded list of uuids to delete', status=400
        )
    
    num_deleted, _ = DataSourceAnnotation.objects.filter(
        uuid__in=delete_uuids
    ).delete()

    output = {
        'ok': True,
        'deleted': delete_uuids,
        'num_deleted': num_deleted,
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
def etl_add_annotations(request):
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_json = json.loads(request.body)
    created, errors = etl_setup_updater.add_annotations(request_json)
    if len(errors):
        # We failed.
        return make_error_response(errors)
    output = {
        'ok': True,
        'created': created,
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