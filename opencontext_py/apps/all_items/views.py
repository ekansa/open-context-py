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
from opencontext_py.apps.all_items.representations.template_prep import (
    prepare_for_item_dict_html_template
)
from opencontext_py.apps.all_items.representations.schema_org import (
    make_schema_org_json_ld
)
from opencontext_py.apps.all_items.representations import citation
from opencontext_py.apps.all_items.legacy_all import update_old_id

from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.views.decorators.cache import cache_page
from django.utils.cache import patch_vary_headers





@never_cache
def test_json(request, uuid):
    """ API for searching Open Context """
    _, ok_uuid = update_old_id(uuid)
    _, rep_dict = item.make_representation_dict(subject_id=ok_uuid)
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
    _, ok_uuid = update_old_id(uuid)
    man_obj, rep_dict = item.make_representation_dict(
        subject_id=ok_uuid,
        for_html=True,
    )
    item_dict = prepare_for_item_dict_html_template(man_obj, rep_dict)
    json_output = json.dumps(
        item_dict,
        indent=4,
        ensure_ascii=False
    )
    schema_org_meta = make_schema_org_json_ld(rep_dict)
    rp = RootPath()
    context = {
        'BASE_URL': rp.get_baseurl(),
        'PAGE_TITLE': f'Open Context: {rep_dict["label"]}',
        'SCHEMA_ORG_JSON_LD': json.dumps(
            schema_org_meta,
            indent=4,
            ensure_ascii=False
        ),
        # Expected order of related item_types
        'order_of_related_item_types': [
            'subjects', 
            'media', 
            'documents', 
            'tables', 
            'persons', 
            'subjects_children'
        ],
        'citation':citation.make_citation_dict(rep_dict),
        'man_obj': man_obj,
        'edit_status': man_obj.project.meta_json.get('edit_status'),
        'item': item_dict,
        'item_json': json_output,
    }
    template = loader.get_template('bootstrap_vue/item/item.html')
    response = HttpResponse(template.render(context, request))
    patch_vary_headers(response, ['accept', 'Accept', 'content-type'])
    return response