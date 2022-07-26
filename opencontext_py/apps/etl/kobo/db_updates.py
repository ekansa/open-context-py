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

from opencontext_py.apps.etl.kobo import db_lookups
from opencontext_py.apps.etl.kobo import pc_configs


DB_LOAD_RESULT_A_COL = 'OC_DB_LOAD_OK'
DB_LOAD_RESULT_B_COL = 'OC_DB_LOAD_B_OK'
DEFAULT_OBS_NUM = 1



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
        man_obj, num_matching = db_lookups.reconcile_manifest_obj(
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
    item_class_obj = db_lookups.cache_get_man_obj_by_any_id(child_item_class_slug)
    if not item_class_obj:
        print(
            f'Cannot find item_class {child_item_class_slug} '
        )
        # Skip the rest.
        return False
    parent_man_obj = db_lookups.cache_get_man_obj_by_any_id(parent_uuid)
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
        context=parent_man_obj,
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
    subjects_df,
    parent_child_col_tup,
    source_id=pc_configs.SOURCE_ID_SUBJECTS,
    extra_filter_index=None,
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
    if extra_filter_index is not None:
        index &= extra_filter_index
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


def load_catalog_no_locus(
    subjects_df,
    source_id=pc_configs.SOURCE_ID_SUBJECTS,
):
    """Loads catalog subjects not contained in a locus"""
    req_cols = [
        'unit_uuid', 
        'locus_name',
        'locus_uuid',
        'trench_year',
        'catalog_name', 
        'catalog_uuid', 
        'catalog_item_class_slug',
    ]
    if not set(req_cols).issubset(subjects_df.columns.tolist()):
        print(f'Missing required import columns {str(req_cols)}')
        return subjects_df
    no_loci_indx = (
        (
            (subjects_df['locus_name'] == 'Locus -1')
            | (subjects_df['trench_year'] < 1995)
        )
        & subjects_df['locus_uuid'].isnull()
    )
    parent_child_col_tup = (
        'unit_uuid',
        'catalog_name', 
        'catalog_uuid', 
        'catalog_item_class_slug',
    )
    return load_subjects_parent_child_cols_df(
        source_id,
        subjects_df,
        parent_child_col_tup,
        extra_filter_index=no_loci_indx,
    )


def load_subjects_dataframe(
    subjects_df,
    source_id=pc_configs.SOURCE_ID_SUBJECTS,
):
    """Loads the subjects dataframe"""
    if subjects_df is None or subjects_df.empty:
        return subjects_df
    for parent_child_col_tup in pc_configs.SUBJECTS_IMPORT_TREE_COL_TUPS:
        subjects_df = load_subjects_parent_child_cols_df(
            subjects_df,
            parent_child_col_tup,
            source_id,
        )
    # Load catalog items that are not contained in a locus.
    subjects_df = load_catalog_no_locus(
        subjects_df,
        source_id=source_id,
    )
    return subjects_df


# ---------------------------------------------------------------------
# ATTRIBUTES RELATED FUNCTIONS
# Attributes are loaded into the importer that normally gets data from
# via the user interface. The following functions load data from a
# dataframe with attributes, sets up the field types and relationships,
# assigns UUIDs where feasible, and imports the data into Open Context.
# The main expectation is that entities receiving attributes have been
# already created. 
# ---------------------------------------------------------------------
