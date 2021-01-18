import copy
import json
import uuid as GenUUID

import reversion

from django.conf import settings

from django.db.models import Q
from django.db import transaction
from django.utils import timezone


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import utilities as model_utils
from opencontext_py.apps.all_items.legacy_all import update_old_id
from opencontext_py.apps.all_items.editorial import api as editorial_api

from opencontext_py.libs.models import (
    make_dict_json_safe, 
    make_model_object_json_safe_dict
)


#----------------------------------------------------------------------
# NOTE: These are general methods used on the modification and history
# recording of items.
# ---------------------------------------------------------------------

def make_models_dict(models_dict=None, item_obj=None, obj_qs=None):
    """Makes an edit history dict, keyed by the model label"""
    if not item_obj and not obj_qs:
        return None
    if not models_dict:
        models_dict = {}
    items = []
    if item_obj:
        items.append(item_obj)
    if obj_qs:
        items += [m for m in obj_qs]
    for act_model in items:
        models_dict.setdefault(act_model._meta.label, [])
        models_dict[act_model._meta.label].append(
            make_model_object_json_safe_dict(act_model)
        )
    return models_dict


def create_edit_history_meta_json(
    edit_note,
    edit_dict=None,
    prior_to_edit_model_objs=None,
    prior_to_edit_model_dict=None,
    after_edit_model_objs=None,
    after_edit_model_dict=None,
):
    """Adds an edit history item to the meta_json of an object"""
    if not edit_dict:
        edit_dict = {}
    
    edit_dict['edit_note'] = edit_note
    edit_dict['edit_time'] = timezone.now().isoformat()

    if not prior_to_edit_model_dict and prior_to_edit_model_objs:
        prior_to_edit_model_dict = {}

    if prior_to_edit_model_objs:
        prior_to_edit_model_dict = make_models_dict(
            models_dict=prior_to_edit_model_dict, 
            obj_qs=prior_to_edit_model_objs
        )

    if not after_edit_model_dict and after_edit_model_objs:
        after_edit_model_dict = {}
    
    if after_edit_model_objs:
        after_edit_model_dict = make_models_dict(
            models_dict=after_edit_model_dict, 
            obj_qs=after_edit_model_objs
        )

    if not prior_to_edit_model_dict and not after_edit_model_dict:
        return None

    edit_dict['prior_to_edit'] = prior_to_edit_model_dict
    edit_dict['after_edit'] = after_edit_model_dict
    return edit_dict


def record_edit_history(
    man_obj,
    edit_note,
    edit_dict=None,
    prior_to_edit_model_objs=None,
    prior_to_edit_model_dict=None,
    after_edit_model_objs=None,
    after_edit_model_dict=None,
):
    """Records edit history of a man_obj item"""

    # NOTE: This a record of the history of an edit. The prior state
    # and after edit states are saved in the meta_json of the history object.
    edit_dict = create_edit_history_meta_json(
        edit_note,
        edit_dict=edit_dict,
        prior_to_edit_model_objs=prior_to_edit_model_objs,
        prior_to_edit_model_dict=prior_to_edit_model_dict,
        after_edit_model_objs=after_edit_model_objs,
        after_edit_model_dict=after_edit_model_dict,
    )
    history_obj = AllHistory()
    history_obj.created = timezone.now()
    history_obj.item = man_obj
    history_obj.meta_json = edit_dict
    history_obj.save()
    return history_obj


def add_queryset_objs_to_models_dict(models_dict, qs):
    """Adds objects from a queryset to a models dict
    
    :param dict models_dict: Dictionary of objects, keyed by object model type
        that records a dictionary of each model object
    :param queryset qs: A queryset of objects we want to add to a models_dict
    """
    for item_obj in qs:
        models_dict = make_models_dict(
            models_dict=models_dict,
            item_obj=item_obj
        )
    return models_dict