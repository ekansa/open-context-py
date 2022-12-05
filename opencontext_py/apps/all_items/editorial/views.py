import json
from django.http import HttpResponse


from opencontext_py.apps.all_items.editorial import api as editorial_api


from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache



@never_cache
@cache_control(no_cache=True)
def item_children_json(request, identifier):
    """ API for getting an item and immediate children items """
    api_result = editorial_api.get_item_children(identifier)
    if not api_result:
        return HttpResponse(
            json.dumps([]),
            content_type="application/json; charset=utf8",
            status=404
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
def item_assert_examples_json(request, identifier):
    """ API for getting examples of an item when used in assertions """
    api_result = editorial_api.get_item_assertion_examples(identifier)
    if not api_result:
        return HttpResponse(
            json.dumps([]),
            content_type="application/json; charset=utf8",
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
def item_look_up_json(request):
    """API for looking up an item based on a wide range of search criteria"""
    request_dict = {}
    for key, key_val in request.GET.items():
        request_dict[key] = request.GET.get(key)

    api_result, total_count = editorial_api.lookup_manifest_dicts(request_dict)
    output = {
        'totalResults': total_count,
        'results': api_result,
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


@never_cache
@cache_control(no_cache=True)
def item_meta_look_up_json(request):
    """API for looking up contextual metadata (project, item_class, context) for item lookups"""
    request_dict = {}
    for key, key_val in request.GET.items():
        request_dict[key] = request.GET.get(key)

    api_result = editorial_api.lookup_up_and_group_general_distinct_metadata(request_dict)
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
def html_validate(request):
    """Checks if a string in the request body is valid HTML"""
    if request.method == 'POST':
        # For big strings of text to validate.
        request_str_dict = json.loads(request.body)
        request_str = request_str_dict.get('str')
    else:
        # Easier for testing short strings.
        request_str = request.GET.get('str')
    if request_str is None:
        return HttpResponse(
            json.dumps({'error': 'Need to POST a JSON dict with "str" key, or GET with "str" param.'}),
            content_type="application/json; charset=utf8",
            status=400
        )
    is_valid, errors = editorial_api.html_validate(request_str)
    output = {
        'ok':  is_valid,
        'errors': errors,
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
