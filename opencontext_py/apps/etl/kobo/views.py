import json
from django.shortcuts import redirect
from django.http import HttpResponse, Http404

from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache


# NOTE: This is an quick and dirty kobo proxy
FORM_ID_CHANGES = {
    # Catalog form
    'a6aorrDfWR8TA8CMAsZmAP': [
        'AU6DPnmKWP1Uloay',
    ]
}

REAL_KOBO = 'https://kcat.opencontext.org'

@cache_control(no_cache=True)
@never_cache
def submissions_kobo_proxy(request):
    """Proxy requests to a kobo server"""
    url = request.get_full_path()
    for good_key, bad_ids in FORM_ID_CHANGES.items():
        for bad_id in bad_ids:
            if bad_id not in url:
                continue
            url.replace(bad_id, good_key)
    url = REAL_KOBO + url
    return redirect(url)
