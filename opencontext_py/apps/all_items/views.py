import json
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponse, Http404

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
from opencontext_py.apps.all_items import utilities
from opencontext_py.apps.all_items.representations import item
from opencontext_py.apps.all_items.legacy_all import update_old_id

from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.views.decorators.cache import cache_page
from django.utils.cache import patch_vary_headers





@never_cache
def test_json(request, uuid):
    """ API for searching Open Context """
    _, new_uuid = update_old_id(uuid)
    rep_dict = item.make_representation_dict(subject_id=new_uuid)
    json_output = json.dumps(
        rep_dict,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )


@never_cache
def test_html(request, uuid):
    """HTML representation for searching Open Context """
    # NOTE: There is NO templating here, this is strictly so we can 
    # use the Django debugger to optimize queries
    _, new_uuid = update_old_id(uuid)
    rep_dict = item.make_representation_dict(subject_id=new_uuid)
    json_output = json.dumps(
        rep_dict,
        indent=4,
        ensure_ascii=False
    )
    ouptut = (
        "<html>"
        "<head><title>Test All Items</title>"
        "</head>"
        "<body>"
        f"<p>{json_output}</p>"
        "</body>"
        "</html>"
    )
    return HttpResponse(
        ouptut,
        content_type="text/html; charset=utf8"
    )