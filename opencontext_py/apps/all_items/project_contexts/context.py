import logging

import numpy as np
import pandas as pd

from django.conf import settings
from django.core.cache import caches

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllAssertion,
    AllManifest,
)


logger = logging.getLogger("project-context-logger")

if settings.DEBUG:
    DEFAULT_TIMEOUT = 60 * 60   # 60 minutes.
else:
    DEFAULT_TIMEOUT = None # Do NOT time out.


# ---------------------------------------------------------------------
# NOTE: About context
#
# Open Context emphasizes JSON-LD for publishing structured data to the
# Web. Because each project defines its own set of descriptive
# attributes and linking relations (project-specific "predicates") and
# controlled vocabulary terms (project-specific "types"), each project
# needs a project-specific "context" dictionary for JSON-LD outputs.
#
# The functions here query the database to populate a dataframe that
# describes all of the "predicates" and "types" items used in a
# project. Please note! Some predicates and types items are SHARED by
# multiple projects, and so the context output will include these
# shared items, even if they come from a different project.
#
# Gathering context data to populate the dataframe requires a slow
# query, so it dataframe should be cached if it does not exist.
# Consider setting up a worker process to pre-cache project data
# in scenarios where a JSON-LD or HTML representations of many items
# from the same project will be requested.
#
# Internally, the easiest to use representation of project "context"
# data is a dataframe. Externally, the "context" data gets expressed
# as a JSON-LD context object.
#
# The Solr indexer and the item representation (esp. equivalent_ld)
# features both use project-context dataframes.
#
# ---------------------------------------------------------------------


def get_project_context_predicates(project_id):
    """Gets an assertion queryset for a project context"""

    pred_ids_qs = AllAssertion.objects.filter(
        subject__project_id=project_id,
        visible=True,
    )

    if str(project_id) != configs.OPEN_CONTEXT_PROJ_UUID:
        # Exclude predicates from the Open Context project.
        pred_ids_qs = pred_ids_qs.exclude(
            predicate__project_id=configs.OPEN_CONTEXT_PROJ_UUID,
        )

    # Get the distinct predicate IDs first, which is more efficient.
    predicate_ids = pred_ids_qs.values_list('predicate_id', flat=True).distinct()

    # Now, fetch the predicate objects.
    pred_qs = AllManifest.objects.filter(
        uuid__in=list(predicate_ids)
    ).order_by('uuid').values(
        'uuid',
        'uri',
        'slug',
        'item_type',
        'data_type',
        'label',
        'item_class_id',
    )
    # The original function expected specific column names.
    # We'll need to prepare the data for the dataframe conversion later.
    # The renaming will happen when creating the pandas DataFrame.
    # For the purpose of the queryset, this is sufficient.
    # We will adjust the dataframe creation part.
    return pred_qs


def get_project_context_object_types(project_id):
    """Gets an assertion queryset for a project context"""
    obj_ids_qs = AllAssertion.objects.filter(
        subject__project_id=project_id,
        object__item_type='types',
        visible=True,
    )

    if str(project_id) != configs.OPEN_CONTEXT_PROJ_UUID:
        # Exclude objects from the Open Context project.
        obj_ids_qs = obj_ids_qs.exclude(
            object__project_id=configs.OPEN_CONTEXT_PROJ_UUID,
        )
    
    # Get the distinct object IDs first.
    object_ids = obj_ids_qs.values_list('object_id', flat=True).distinct()

    # Then fetch the actual objects.
    obj_qs = AllManifest.objects.filter(
        uuid__in=list(object_ids)
    ).order_by('uuid').values(
        'uuid',
        'uri',
        'slug',
        'item_type',
        'data_type',
        'label',
        'item_class_id',
    )
    return obj_qs


def get_ld_assertions_on_item_qs(subject_id_list, project_id=None):
    """Gets linked data assertions on a list of items

    :param list subject_id_list: A list of assertion
        subject identifiers
    :param str project_id: A project's UUID or string UUID primary key
        identifier
    """
    ld_qs = AllAssertion.objects.filter(
        subject_id__in=subject_id_list,
        predicate__context__item_type='vocabularies',
    )
    if project_id and project_id != configs.OPEN_CONTEXT_PROJ_UUID:
        ld_qs = ld_qs.exclude(
            subject__project_id=configs.OPEN_CONTEXT_PROJ_UUID
        )

    ld_qs = ld_qs.select_related(
        'subject'
    ).select_related(
        'predicate'
    ).select_related(
        'predicate__context'
    ).select_related(
        'object'
    ).select_related(
        'object__context',
    ).order_by('subject_id').values(
        'subject_id',
        'subject__uri',
        'subject__slug',
        'subject__item_type',
        'subject__data_type',
        'subject__label',
        'subject__item_class_id',
        'predicate_id',
        'predicate__item_key',
        'predicate__uri',
        'predicate__slug',
        'predicate__item_type',
        'predicate__data_type',
        'predicate__label',
        'predicate__meta_json',
        'predicate__context_id',
        'predicate__context__label',
        'predicate__context__item_type',
        'predicate__context__uri',
        'predicate__context__meta_json',
        'object_id',
        'object__uri',
        'object__slug',
        'object__item_key',
        'object__item_type',
        'object__data_type',
        'object__label',
        'object__meta_json',
        'object__context_id',
        'object__context__item_type',
        'object__context__label',
        'object__context__uri',
        'object__context__meta_json',
    )
    return ld_qs


def rename_pred_obj_df_cols(df, df_type):
    """Renames pred_df and obj_df columns to be consistent"""
    if df_type == 'predicate':
        rename_dict = {
            'uuid': 'predicate_id',
            'uri': 'predicate__uri',
            'slug': 'predicate__slug',
            'item_type': 'predicate__item_type',
            'data_type': 'predicate__data_type',
            'label': 'predicate__label',
            'item_class_id': 'predicate__item_class_id',
        }
        df.rename(columns=rename_dict, inplace=True)
    elif df_type == 'object':
        rename_dict = {
            'uuid': 'object_id',
            'uri': 'object__uri',
            'slug': 'object__slug',
            'item_type': 'object__item_type',
            'data_type': 'object__data_type',
            'label': 'object__label',
            'item_class_id': 'object__item_class_id',
        }
        df.rename(columns=rename_dict, inplace=True)

    rename_dict = {
       c: ('subject__' + c.split(f'{df_type}__')[-1])
       for c in df.columns if c.startswith(f'{df_type}__')
    }
    rename_dict[f'{df_type}_id'] = 'subject_id'
    df.rename(
        columns=rename_dict,
        inplace=True
    )
    return df


def db_make_project_context_df(project_id):
    """Make a dataframe for a project context"""
    pred_qs = get_project_context_predicates(project_id)
    pred_df = pd.DataFrame.from_records(pred_qs)
    pred_df = rename_pred_obj_df_cols(pred_df, 'predicate')

    obj_qs = get_project_context_object_types(project_id)
    obj_df = pd.DataFrame.from_records(obj_qs)
    obj_df = rename_pred_obj_df_cols(obj_df, 'object')

    df = pd.concat([pred_df, obj_df])
    if df.empty:
        return df

    ld_qs = get_ld_assertions_on_item_qs(df['subject_id'].unique().tolist())
    df_ld = pd.DataFrame.from_records(ld_qs)

    # Avoid duplicating columns already in df
    if len(ld_qs) and not df_ld.empty:
        drop_cols = [c for c in df_ld.columns if c.startswith('subject__')]
        df_ld.drop(columns=drop_cols, inplace=True)

        df = df.merge(
            df_ld,
            how='left',
            left_on='subject_id',
            right_on='subject_id'
        )

    # Now make all the uuids simple strings.
    for col in df.columns:
        if col.endswith('_id'):
            df[col] = df[col].astype(str)
    return df


def make_project_context_cache_key(project_id):
    """Makes a cache key for a project context"""
    return f'{settings.CACHE_PREFIX_PROJ_CONTEXT}{str(project_id)}-context-df'


def get_project_context_df_from_cache(project_id):
    """Gets a project context df from the cache, if it exists

    :param str project_id: A project's UUID or string UUID primary key
        identifier
    """
    cache = caches['redis_context']
    cache_key = make_project_context_cache_key(project_id)
    return cache.get(cache_key)


def clear_project_context_df_from_cache(project_id):
    cache = caches['redis_context']
    cache_key = make_project_context_cache_key(project_id)
    return cache.delete(cache_key)


def get_cache_project_context_df(project_id, use_cache=True, reset_cache=False):
    """Gets and caches a project context dataframe

    :param str project_id: A project's UUID or string UUID primary key
        identifier
    :param bool use_cache: Boolean flag to use the cache or not
    :param bool reset_cache: Force the cache to be reset.
    """
    if not use_cache:
        return db_make_project_context_df(project_id)

    cache = caches['redis_context']
    df = None
    cache_key = make_project_context_cache_key(project_id)
    if not reset_cache:
        df = cache.get(cache_key)

    if df is not None:
        return df

    df = db_make_project_context_df(project_id)
    try:
        cache.set(cache_key, df, timeout=DEFAULT_TIMEOUT)
    except:
        logger.info(f'Cache failure with: {cache_key}')
    return df



def get_item_context_df(subject_id_list, project_id, pref_project_context=True):
    """Gets an item's context dataframe if a project df is not cached

    :param list subject_id_list: A list of assertion
        subject identifiers
    :param str project_id: A project's UUID or string UUID primary key
        identifier
    """
    df = get_project_context_df_from_cache(project_id)
    if df is not None:
        # The requirement is satisfied because we have the
        # project's context df
        return df

    if pref_project_context:
        df = get_cache_project_context_df(project_id)

    if pref_project_context and df is not None:
        # Satisfy the requirement with the project context.
        return df

    # As a fallback, make a dataframe of linked data
    # relating to items in the subject_id_list. These
    # are relevant to an item's context.
    ld_qs = get_ld_assertions_on_item_qs(
        subject_id_list,
        project_id=project_id,
    )
    df_ld = pd.DataFrame.from_records(ld_qs)
    for col in df_ld.columns:
        if col.endswith('_id'):
            df_ld[col] = df_ld[col].astype(str)
    return df_ld