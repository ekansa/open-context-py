import copy
import hashlib
from operator import sub
import re

import numpy as np
import pandas as pd

from django.core.cache import caches

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)
from opencontext_py.apps.all_items.legacy_all import update_old_id

from opencontext_py.apps.etl.importer.models import (
    DataSourceField,
    DataSourceAnnotation,
)

from opencontext_py.apps.all_items import configs

from opencontext_py.apps.all_items.editorial.api import get_man_obj_by_any_id


from opencontext_py.apps.etl.kobo import pc_configs




DB_LOAD_RESULT_A_COL = 'OC_DB_LOAD_OK'
DB_LOAD_RESULT_B_COL = 'OC_DB_LOAD_B_OK'
DEFAULT_OBS_NUM = 1

RECONCILE_PROJECT_IDS = [
    configs.OPEN_CONTEXT_PROJ_UUID,
    pc_configs.PROJECT_UUID,
]


def make_cache_key(item_id):
    hash_obj = hashlib.sha1()
    item_id = str(item_id)
    hash_obj.update(item_id.encode('utf-8'))
    return 'key-' + hash_obj.hexdigest()


def cache_get_man_obj_by_any_id(item_id):
    cache_key = make_cache_key(item_id)
    cache = caches['redis']
    item_obj = cache.get(cache_key)
    if item_obj:
        return item_obj
    item_obj = get_man_obj_by_any_id(item_id)
    try:
        cache.set(cache_key, item_obj)
    except:
        pass
    return item_obj


def reconcile_manifest_obj(
    item_type,
    item_label,
    item_class_obj,
    item_any_id=None,
    context=None,
    reconcile_project_ids=None,
    item_data_type='id',
    meta_json=None,
):
    """Attempts to reconcile a manifest item via arguments."""
    if not meta_json:
        meta_json = {}

    if not reconcile_project_ids:
        reconcile_project_ids = copy.deepcopy(RECONCILE_PROJECT_IDS)

    if context and item_type == 'subjects' and context.item_type == 'projects':
        # We are only trying to reconcile by a project, we lack a
        # parent spatial context for item
        reconcile_project_ids.append(context.uuid)
        context = None

    item_label = AllManifest().clean_label(item_label)
    man_qs = AllManifest.objects.filter(
        project_id__in=reconcile_project_ids,
        item_type=item_type,
        data_type=item_data_type,
    )
    if context:
        if item_type == 'subjects' and context.item_type == 'projects':
            # Don't do a context filter.
            pass
        else:
            man_qs = man_qs.filter(context=context)

    if not item_any_id:
        item_any_id = item_label

    if item_type in configs.URI_CONTEXT_PREFIX_ITEM_TYPES:
        # Some flexibility in reconcile these.
        man_qs = man_qs.filter(
            Q(uri=AllManifest().clean_uri(item_any_id))
            | Q(item_key=item_any_id)
            | Q(slug=item_any_id)
            | Q(label=item_label)
        )
    elif item_type == 'persons' and meta_json.get('reconcile_on_initials'):
        # We're allowing reconciliation on initials.
        man_qs = man_qs.filter(
            Q(meta_json__initials=item_label)
            | Q(meta_json__combined_name=item_label)
            | Q(label=item_label)
        )
    elif item_type == 'persons' and not meta_json.get('reconcile_on_initials'):
        # We're reconciling a persons item, but not with initials.
        man_qs = man_qs.filter(
            Q(meta_json__combined_name=item_label)
            | Q(label=item_label)
        )
    else:
        # Use the label as the main identifier (obviously with other
        # filter to contextualize)
        man_qs = man_qs.filter(
            Q(label=item_label)
            | Q(slug=item_any_id)
        )
       
    if (item_type == 'predicates'
        and (
            not item_class_obj 
            or 
            str(item_class_obj.uuid) not in configs.CLASS_LIST_OC_PREDICATES
        )
    ):
        # We are attempting to reconcile an item_type = 'predicates'
        # item, but we don't have a correct record_item_class_obj set. So
        # default to the class for a variable (not a link)
        item_class_obj = cache_get_man_obj_by_any_id(
            configs.CLASS_OC_VARIABLES_UUID
        )

    if item_class_obj:
        man_qs = man_qs.filter(item_class=item_class_obj)
    
    # Now handle the results where of our query to attempt to 
    # find matching records for this specific item.
    made_new = False
    num_matching = len(man_qs) 
    if num_matching == 1:
        # We have found exactly one match for this, meaning this
        # entity already exists so return it
        return man_qs[0], made_new, num_matching
    return None, made_new, num_matching


def get_or_create_manifest_obj(
    item_type,
    item_label,
    item_class_obj,
    source_id,
    item_uuid=None,
    item_any_id=None,
    context=None,
    reconcile_project_ids=None,
    item_data_type='id',
    field_num=None,
    meta_json=None,
):
    """Gets or creates a manifest entity after reconciliation"""
    num_matching = 0
    if item_uuid:
        man_obj = AllManifest.objects.filter(
            uuid=item_uuid
        ).first()
    else:
        man_obj, made_new, num_matching = reconcile_manifest_obj(
            item_type=item_type,
            item_label=item_label,
            item_class_obj=item_class_obj,
            item_any_id=item_any_id,
            context=context,
            reconcile_project_ids=reconcile_project_ids,
            item_data_type=item_data_type,
            meta_json=meta_json,
        )

    if num_matching > 1:
        print(f'Found {num_matching}, too many possible matches for {item_label} ')
        return None, False

    if man_obj:
        # We have an existing manifest object, so
        # don't make it again.
        return man_obj, False
    
    # Make a new Manifest item
    man_dict = {
        'publisher_id': configs.OPEN_CONTEXT_PUB_UUID,
        'project_id': pc_configs.PROJECT_UUID,
        'source_id': source_id,
        'item_type': item_type,
        'data_type': item_data_type,
        'label': item_label,
        'context': context,
    }
    if item_uuid:
        man_dict['uuid'] = item_uuid
    if item_class_obj:
        man_dict['item_class'] = item_class_obj
    if item_type == 'predicates' and field_num:
        man_dict['meta_json'] = {
            'sort': field_num,
        }
    try:
        man_obj = AllManifest(**man_dict)
        man_obj.save()
        made_new = True
    except Exception as e:
        man_obj = None
        made_new = False
        print(f'Failed to make new manifest item: {str(man_dict)}')
        print(str(e))
    return man_obj, made_new 


# ---------------------------------------------------------------------
# CONTEXT (item_type: subjects) RELATED FUNCTIONS
# ---------------------------------------------------------------------
def load_subject_and_containment( 
    source_id, 
    parent_uuid, 
    child_label,
    child_uuid,
    child_item_class_slug,
):
    """Loads a subject item and containment relation into the database"""
    item_class_obj = cache_get_man_obj_by_any_id(child_item_class_slug)
    if not item_class_obj:
        print(
            f'Cannot find item_class {child_item_class_slug} '
        )
        # Skip the rest.
        return False
    parent_man_obj = cache_get_man_obj_by_any_id(parent_uuid)
    if parent_man_obj is None:
        print(
            f'Cannot find parent_uuid {parent_uuid} '
            f'for {child_label} ({child_uuid})'
        )
        # Skip the rest.
        return False
    # OK to continue
    man_obj, made_new = get_or_create_manifest_obj(
        item_type='subjects',
        item_label=child_label,
        item_class=item_class_obj,
        source_id=source_id,
        contex2t=parent_man_obj,
    )
    if not man_obj:
        # We failed to make or reconcile the item.
        return False
    if not made_new:
        # This item already exists.
        return True
    # Now make the containment assertion
    assert_dict = {
        'project_id': pc_configs.PROJECT_UUID,
        'publisher_id': configs.OPEN_CONTEXT_PUB_UUID,
        'source_id': source_id,
        'subject': parent_man_obj,
        'predicate_id': configs.PREDICATE_CONTAINS_UUID,
        'object':man_obj,
    }
    assert_uuid = AllAssertion().primary_key_create(
        subject_id=assert_dict['subject'].uuid,
        predicate_id=assert_dict['predicate_id'],
        object_id=assert_dict['object'].uuid,
    )
    assert_dict['uuid'] = assert_uuid
    assert_obj = AllAssertion(**assert_dict)
    try:
        assert_obj.save()
    except Exception as e:
        print(str(e))
        return False
    return True


def load_subjects_parent_child_cols_df(
    source_id,
    subjects_df,
    parent_child_col_tup
):
    if not set(parent_child_col_tup).issubset(subjects_df.columns.tolist()):
        print(f'Missing required import columns {str(parent_child_col_tup)}')
        return subjects_df
    parent_context_col, child_label_col, child_uuid_col, child_class_slug_col = parent_child_col_tup
    indx = (
        ~subjects_df[parent_context_col].isnull()
        & ~subjects_df[child_label_col].isnull()
        & ~subjects_df[child_uuid_col].isnull()
        & ~subjects_df[child_class_slug_col].isnull()
    )
    if subjects_df[indx].empty:
        print(f'No data to import columns {str(parent_child_col_tup)}')
        return subjects_df
    child_result_col = child_label_col.replace('_name', '_import')
    subjects_df[child_result_col] = np.nan
    grp_cols = list(parent_child_col_tup)
    df_g = df[indx][grp_cols].groupby(grp_cols, as_index=False).first()
    df_g.reset_index(drop=True, inplace=True)
    for _, row in df_g.iterrows():
        ok = load_subject_and_containment( 
            source_id=source_id, 
            parent_uuid=str(row[parent_context_col]), 
            child_label=str(row[child_label_col]),
            child_uuid=str(row[child_uuid_col]),
            child_item_class_slug=str(row[child_class_slug_col]),
        )
        act_indx = (
            (subjects_df[parent_context_col] == row[parent_context_col])
            & (subjects_df[child_uuid_col] == row[child_uuid_col])
        )
        subjects_df.loc[act_indx, child_result_col] = ok
    return subjects_df


def load_subjects_dataframe(
    source_id,
    subjects_df,
):
    """Loads the subjects dataframe"""
    if subjects_df is None or subjects_df.empty:
        return subjects_df
    for parent_child_col_tup in pc_configs.SUBJECTS_IMPORT_COLS:
        subjects_df = load_subjects_parent_child_cols_df(
            source_id,
            subjects_df,
            parent_child_col_tup
        )
    return subjects_df


# ---------------------------------------------------------------------
# ATTRIBUTES RELATED FUNCTIONS
# Attributes are loaded into the importer that normally gets data from
# an Open Refine source. The following functions load data from a
# dataframe with attributes, sets up the field types and relationships,
# assigns UUIDs where feasible, and imports the data into Open Context.
# The main expectation is that entities receiving attributes have been
# already created. 
# ---------------------------------------------------------------------
