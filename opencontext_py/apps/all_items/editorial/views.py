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
    get_immediate_concept_children_objs_db,
    get_immediate_context_children_objs_db,
)
from opencontext_py.apps.all_items import utilities
from opencontext_py.apps.all_items.legacy_all import update_old_id

from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.views.decorators.cache import cache_page
from django.utils.cache import patch_vary_headers



def manifest_obj_to_json_safe_dict(manifest_obj):
    """Makes a dict safe for JSON expression from a manifest object"""
    return {
        'uuid': str(manifest_obj.uuid),
        'slug': manifest_obj.slug,
        'label': manifest_obj.label,
        'item_type': manifest_obj.item_type,
        'data_type': manifest_obj.data_type,
        'project_id': str(manifest_obj.project.uuid),
        'project__label': manifest_obj.project.label,
        'project__slug': manifest_obj.project.slug,
        'item_class_id': str(manifest_obj.item_class.uuid),
        'item_class__label': manifest_obj.item_class.label,
        'item_class__slug': manifest_obj.item_class.slug,
        'context_id': str(manifest_obj.context.uuid),
        'context__label': manifest_obj.context.label,
        'context__slug': manifest_obj.context.slug,
        'path': manifest_obj.path,
        'uri': manifest_obj.uri,
    }

@never_cache
def item_children_json(request, identifier):
    """ API for getting an item and immediate children items """
    _, new_uuid = update_old_id(identifier)
    
    man_obj = AllManifest.objects.filter(
        Q(uuid=new_uuid)
        |Q(slug=identifier)
        |Q(uri=AllManifest().clean_uri(identifier))
        |Q(item_key=identifier)
    ).first()
    if not man_obj:
        return Http404

    if man_obj.item_type == 'subjects':
        # Gets spatial context children
        children_objs =  get_immediate_context_children_objs_db(
            man_obj
        )
    else:
        # Gets concept hierarchy children.
        children_objs =  get_immediate_concept_children_objs_db(
            man_obj
        )
    
    if not len(children_objs) and man_obj.item_type == 'predicates' and man_obj.data_type == 'id':
        # We've got a predicate that may have types that is convenient to consider as
        # children.
        children_objs = AllManifest.objects.filter(
            item_type='types',
            context=man_obj,
        )

    output = manifest_obj_to_json_safe_dict(man_obj)
    output['children'] = []
    for child_obj in children_objs:
        child_dict = manifest_obj_to_json_safe_dict(child_obj)
        output['children'].append(child_dict)

    json_output = json.dumps(
        output,
        indent=4,
        ensure_ascii=False
    )
    return HttpResponse(
        json_output,
        content_type="application/json; charset=utf8"
    )

