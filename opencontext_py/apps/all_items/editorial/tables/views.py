import io
import json
import reversion

from django.http import StreamingHttpResponse, HttpResponse, Http404



from opencontext_py.apps.all_items.editorial.tables import queue_utilities
from opencontext_py.apps.all_items.editorial.tables import ui_utilities

from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


#----------------------------------------------------------------------
# NOTE: These are views relating to user interfaces for creating new
# export tables.
# ---------------------------------------------------------------------

@cache_control(no_cache=True)
@never_cache
def export_configs(request):
    """Get export configurations"""
    filter_args = None
    if request.GET.get('filter_args'):
        filter_args = json.loads(request.GET.get('filter_args'))
    exclude_args = None
    if request.GET.get('exclude_args'):
        exclude_args = json.loads(request.GET.get('exclude_args'))
    
    output = ui_utilities.make_export_config_dict(
        filter_args=filter_args, 
        exclude_args=exclude_args,
    )

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
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )
    if request.method != 'POST':
        return HttpResponse(
            'Must be a POST request', status=405
        )
    request_kwargs = json.loads(request.body)
    output = queue_utilities.single_stage_make_export_df(**request_kwargs)
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
def get_temp_export_table(request, export_id):
    """Gets a temporarily cached export result"""
    if not request.user.is_superuser:
        return HttpResponse(
            'Must be an authenticated super-user', status=403
        )

    df = queue_utilities.get_cached_export_df(export_id)
    if df is None:
        raise Http404
    
    stream = io.StringIO()
    df.to_csv(stream, index=False, encoding='utf-8')

    response = StreamingHttpResponse(
        stream.getvalue(),
        content_type="text/csv; charset=utf8"
    )
    response['Content-Disposition'] = (
        f'attachment; filename="oc-temp-export-{export_id}.csv"'
    )
    return response

