
import copy

import uuid as GenUUID

import numpy as np
import pandas as pd

from django.db.models import Q, OuterRef, Subquery

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.defaults import (
    DEFAULT_MANIFESTS,
)
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)
from opencontext_py.apps.all_items import hierarchy

from opencontext_py.apps.all_items.editorial.tables import create_df

from opencontext_py.apps.searcher.new_solrsearcher import db_entities
from opencontext_py.apps.searcher.new_solrsearcher import configs as search_configs

"""
# testing

import importlib
from opencontext_py.apps.all_items.isamples import create_df as isam_create_df
importlib.reload(isam_create_df)

df = isam_create_df.create_isamples_df(
    filter_args={'subject__label__contains': 'PC 2010'},
    add_manifest_without_asserts=True,
    add_manifest_filter_args={'label__contains': 'PC 2010'},
)
df = isam_create_df.create_isamples_df(
    filter_args={'subject__project__meta_json__omit_db_sampling_site': True},
    add_manifest_without_asserts=True,
    add_manifest_filter_args={'project__meta_json__omit_db_sampling_site': True},
)
"""

def get_isamples_item_classes():
    """Get all item-class manifest objects related to iSamples records"""
    m_qs = AllManifest.objects.filter(
        item_type='class',
        slug__in=search_configs.ISAMPLES_DEFAULT_CLASS_SLUGS,
    )
    isamples_item_classes = []
    for man_obj in m_qs:
        m_children = hierarchy.get_list_concept_children_recursive(man_obj)
        if man_obj not in isamples_item_classes:
            isamples_item_classes.append(man_obj)
        for child_obj in m_children:
            if child_obj not in isamples_item_classes:
                isamples_item_classes.append(child_obj)
    return isamples_item_classes




ISAMPLES_FILTER_ARGS = {
    'subject__item_type': 'subjects',
    'subject__meta_json__flag_do_not_index__isnull': True,
    'predicate__data_type__in': ['id'],
    'subject__item_class__in': get_isamples_item_classes(),
}

ISAMPLES_MANIFEST_FILTER_ARGS = {
    'meta_json__flag_do_not_index__isnull': True,
    'item_class__in': get_isamples_item_classes()
}


def reorder_first_columns(df, first_columns):
    """Reorders a columns in a dataframe so first_columns appear first"""
    return df[move_to_prefix(list(df.columns), first_columns)]


def move_to_prefix(all_list, prefix_list):
    """Reorders elements in a list to move the prefix_list elements first"""
    all_list = list(all_list)  # So we don't mutate all_list
    for p_element in prefix_list:
        all_list.remove(p_element)
    return prefix_list + all_list


def check_path_in_path_list(path, paths_list):
    """Check if a path is in a list of paths"""
    for act_path in paths_list:
        if path.startswith(act_path):
            return True
    return False


def get_parent_label_from_path(path):
    """Get the parent label from a path"""
    if not path:
        return None
    path_list = path.split('/')
    if len(path_list) < 1:
        return None
    elif len(path_list) == 1:
        return path_list[0]
    return path_list[-2]


def add_isamples_sampling_sites_cols(df):
    """Adds columns for sampling sites for iSamples. This is either a manifest item with the
    site item class or the last region item in the context list.
    
    :param DataFrame df: A pandas dataframe with iSamples data.
    :returns: A pandas dataframe with added columns for sampling sites.
    """
    if df is None or df.empty:
        return None
    first_cols = []
    for col in df.columns:
        if col.startswith('context___'):
            break
        else:
            first_cols.append(col)
    # Create the columns we want to populate for iSamples sampling sites.
    df['isam_sampling_site_label'] = ''
    df['isam_sampling_site_uri'] = ''
    # Make sure these columns come before the context columns.
    df = reorder_first_columns(df, (first_cols + ['isam_sampling_site_label', 'isam_sampling_site_uri']))
    # Start
    context_cols = [f'context___{i}' for i in range(1, 7)]
    act_context_cols  = []
    paths_with_sites = []
    paths_to_skip = []
    cols_for_df_g = ['subject__path', 'subject__context__uri', ]
    for col in context_cols:
        if not col in df.columns:
            continue
        act_context_cols.append(col)
        group_by_cols = ['subject__project_id'] + act_context_cols
        df_g = df[(cols_for_df_g + group_by_cols)].groupby(group_by_cols, as_index=False).first()
        df_g.reset_index(drop=True, inplace=True)
        print(f'Finding sampling sites on {len(df_g.index)} rows based on {group_by_cols}')
        for _, row in df_g.iterrows():
            proj_obj = db_entities.get_cache_man_obj_by_any_id(str(row['subject__project_id']))
            if not proj_obj:
                continue
            # Make the index of rows to update in the main df.
            act_index = (df['subject__project_id'] == row['subject__project_id'])
            for col in act_context_cols:
                act_index = act_index & (df[col] == row[col])
            if proj_obj.meta_json.get('omit_db_sampling_site'):
                # Omit a database search for a sampling site, and just return the
                # last context of each row.
                act_index = (df['subject__project_id'] == row['subject__project_id']) & (df['isam_sampling_site_uri'] == '')
                df.loc[act_index, 'isam_sampling_site_label'] = df[act_index]['subject__path'].apply(
                    get_parent_label_from_path
                )
                df.loc[act_index, 'isam_sampling_site_uri'] = df[act_index]['subject__context__uri']
                continue
            check_path_list = [row[col] for col in act_context_cols]
            check_path = '/'.join(check_path_list)
            if check_path_in_path_list(check_path, paths_with_sites):
                continue
            if check_path_in_path_list(check_path, paths_to_skip):
                continue
            man_obj = db_entities.get_cache_manifest_item_by_path(check_path)
            if not man_obj or not man_obj.item_class:
                paths_to_skip.append(check_path)
            if man_obj.item_class.slug in search_configs.ISAMPLES_SAMPLING_SITE_ITEM_CLASS_SLUGS:
                # We found a site, our preferred sampling location.
                df.loc[act_index, 'isam_sampling_site_label'] = man_obj.label
                df.loc[act_index, 'isam_sampling_site_uri'] = f'https://{man_obj.uri}'
                paths_with_sites.append(check_path)
                continue
            if man_obj.item_class.slug == 'oc-gen-cat-region':
                # We found a region, which is the second best option for a sampling site.
                df.loc[act_index, 'isam_sampling_site_label'] = man_obj.label
                df.loc[act_index, 'isam_sampling_site_uri'] = f'https://{man_obj.uri}'
                continue
            # The path is not a site or region, so we need to skip it in the future.
            # This saves time so we don't have to check it again.
            paths_to_skip.append(check_path)
    return df


def create_isamples_df(
    filter_args=None, 
    exclude_args=None,
    add_manifest_without_asserts=True,
    add_manifest_filter_args=None,
    add_manifest_exclude_args=None,
):
    """Create a dataframe of iSamples data. This is a dataframe of all iSamples data with
    standard attributes of interest to iSamples, including sampling sites.
    """
    act_filter_args = copy.deepcopy(ISAMPLES_FILTER_ARGS)
    if filter_args:
        act_filter_args.update(filter_args)
    act_manifest_filter_args = None
    if add_manifest_without_asserts:
        act_manifest_filter_args =copy.deepcopy(ISAMPLES_MANIFEST_FILTER_ARGS)
        if add_manifest_filter_args:
            act_manifest_filter_args.update(add_manifest_filter_args)

    df = create_df.make_export_df(
        filter_args=act_filter_args, 
        exclude_args=exclude_args,
        add_entity_ld=True,
        add_literal_ld=False,
        more_exclude_args=None,
        add_manifest_filter_args=act_manifest_filter_args,
        add_manifest_exclude_args=add_manifest_exclude_args,
    )
    df = add_isamples_sampling_sites_cols(df)
    return df


