import copy
import os
import hashlib
import logging
import time
import uuid as GenUUID

import numpy as np
import pandas as pd

import django_rq

from django.core.cache import caches

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.defaults import (
    DEFAULT_MANIFESTS,
)
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

from opencontext_py.apps.all_items.editorial.tables import create_df
from opencontext_py.apps.all_items.editorial.tables import ui_utilities
from opencontext_py.apps.all_items.editorial.tables import cloud_utilities

from opencontext_py.libs.queue_utilities import (
    wrap_func_for_rq,
    make_hash_id_from_args,
    reset_request_process_cache,
    add_cache_key_to_request_cache_key_list,
    cache_item_and_cache_key_for_request,
)


# ---------------------------------------------------------------------
# NOTE: These functions provide a means to wrap functions for the 
# export of tabular data in a que / worker. Exports functions can take
# lots of time, so they need to be able to run in the context of a 
# queing system. 
#
#
# NOTE: Don't forget to start the worker to make redis queue actually
# work:
#
# python manage.py rqworker high
#
# ---------------------------------------------------------------------
logger = logging.getLogger("tab-exporter-logger")

EXPORT_CACHE_LIFE = 60 * 60 * 6 # 6 hours. 
DEFAULT_TIMEOUT = 60 * 30   # 30 minutes.

PROCESS_STAGES = [
    (
        'prepare_assert_df', 
        'Initial query of items, their attributes and links',
        False, # expect assert_df for function to work
        False, # expect df for function to work
    ),
    (
        'prepare_df_from_assert_df', 
        'Consolidate items and basic metadata',
        True,
        False,
    ),
    (
        'add_spacetime_to_df', 
        'Add location and chronology metadata',
        True,
        True,
    ),
    (
        'expand_context_path', 
        'Add context hierarchy columns',
        True,
        True,
    ),
    (
        'add_authors_to_df', 
        'Add authorship metadata',
        True,
        True,
    ),
    (
        'add_media_resource_files_to_df',
        'Add media resource file columns (if applicable)',
        True,
        True,
    ),
    (
        'add_df_linked_data_from_assert_df', 
        'Add equivalent linked data columns',
        True,
        True,
    ),
    (
        'add_attribute_data_to_df', 
        'Add project-specific attribute and relationships columns',
        True,
        True,
    ),
    (
        'stylize_df', 
        'Stylize the output data to be more user-friendly',
        True,
        True,
    ),
]


def get_cached_export_df(export_id):
    """Gets an export dataframe object from the cache
    
    :param str export_id: The identifier for a specific 
        cached export process.
    """
    cache = caches['redis']
    df = cache.get(f'df__{export_id}')
    if df is not None:
        return df
    df = cache.get(export_id)
    return df


def get_cached_no_style_df(export_id):
    """Gets an export dataframe object before final styling
    
    :param str export_id: The identifier for a specific 
        cached export process.
    """
    cache = caches['redis']
    df = cache.get(f'df_no_style__{export_id}')
    return df


def get_cached_export_args(export_id):
    """Gets cached argument dict used to make an export

    :param str export_id: The identifier for a specific 
        cached export process.
    """
    cache = caches['redis']
    # Key for cache the arguments used to generate an export.
    export_args_key = f'export-args-{export_id}'
    return cache.get(export_args_key)


def make_hash_id_from_df(df):
    """Makes a hash identifier from a dataframe"""
    hash_obj = hashlib.sha1()
    hash_obj.update(str(df.to_csv()).encode('utf-8'))
    return hash_obj.hexdigest()


def make_uuid_from_df_hash(df):
    """Makes a hash identifier from a dataframe"""
    hash_id = make_hash_id_from_df(df)
    return GenUUID.UUID(hex=hash_id[:32])



def cache_item_and_cache_key_for_request(export_id, cache_key, object_to_cache):
    """Caches an item and saves the key to our ETL key list for this data source"""
    cache = caches['redis']
    add_cache_key_to_request_cache_key_list(export_id, cache_key)
    try:
        cache.set(cache_key, object_to_cache, timeout=EXPORT_CACHE_LIFE)
    except:
        logger.info(f'Cache failure with: {cache_key}')
    return object_to_cache


def add_job_metadata_to_stage_status(job_id, job_done, stage_status):
    """Adds job metadata to the stage_status dict

    :param str job_id: String UUID for the redis queue job assoctiated
        with a stage_status
    :param bool job_done: Boolean value, True if the job is completed
    :param dict stage_status: Dictionary describing the work of an
        export process stage
    """
    stage_status['job_id'] = job_id
    if not stage_status.get('job_started'):
        stage_status['job_started'] = time.time()
        stage_status['job_finish_duration'] = None
    if job_done:
        stage_status['job_finish_duration'] = time.time() - stage_status.get('job_started', 0)
        stage_status['done'] = True
    else:
        stage_status['done'] = False
    return stage_status



def staged_make_export_df(
    filter_args=None, 
    exclude_args=None,
    add_entity_ld=True,
    add_literal_ld=True,
    add_object_uris=True,
    node_pred_unique_prefixing=create_df.NODE_PRED_UNIQUE_PREDFIXING,
    reset_cache=False,
    export_id=None,
):
    
    args = {
        'filter_args': filter_args,
        'exclude_args': exclude_args,
        'add_entity_ld': add_entity_ld,
        'add_literal_ld': add_literal_ld,
        'add_object_uris': add_object_uris,
        'node_pred_unique_prefixing': node_pred_unique_prefixing,
    }
    
    if not export_id:
        export_id = make_hash_id_from_args(
            args=args
        )
    
    if reset_cache:
        # Eliminate any cached items relevant to this export_id
        reset_request_process_cache(export_id)
    
    cache = caches['redis']

    # Cache the arguments used to generate this export.
    export_args_key = f'export-args-{export_id}'
    if not cache.get(export_args_key) and kwargs:
        cache_item_and_cache_key_for_request(
            export_id, 
            cache_key=export_args_key, 
            object_to_cache=args,
        )

    cache_key_stages = f'export-stages-{export_id}'
    raw_stages = cache.get(cache_key_stages)
    if raw_stages is None:
        act_stages = {
            k:{'done': False, 'label': label, 'export_id': export_id,} 
            for k, label, _, _ in PROCESS_STAGES
        }
        act_stages['creation_args'] = args
    else:
        act_stages = raw_stages.copy()
    
    df = None
    assert_df = None
    do_next_stage = True
    for process_stage, label, expect_assert_df, expect_df in PROCESS_STAGES:
        stage_status = act_stages.get(process_stage)
        if not stage_status:
            # Weird! We should have this, but if we don't
            # continue
            continue

        # Redundant, but easy!
        stage_status['export_id'] = export_id
        stage_status['df__key'] = f'df__{export_id}'
        stage_status['df_assert__key'] = f'assert_df__{export_id}'
    
        if stage_status.get('done') or not do_next_stage:
            # This stage is done, so continue to the next stage
            continue

        if not stage_status.get('job_id'):
            # Only fetch these big objects from the cache
            # if we haven't yet started a job for this current
            # status stage.
            df = cache.get(f'df__{export_id}')
            assert_df = cache.get(f'assert_df__{export_id}')
        
            if expect_assert_df and assert_df is None:
                stage_status['error'] = f'Failed to get assert_df for {export_id}'
                do_next_stage = False
                continue

            if expect_df and df is None:
                stage_status['error'] = f'Failed to get df for {export_id}'
                do_next_stage = False
                continue

        if do_next_stage and process_stage == 'prepare_assert_df':
            # Make the initial assertion query and output the
            # resulting AllAssertion queryset into a "tall" dataframe.
            job_id, job_done, assert_df = wrap_func_for_rq(
                func=create_df.get_raw_assert_df_by_making_query, 
                kwargs={'filter_args':filter_args, 'exclude_args': exclude_args},
                job_id=stage_status.get('job_id'),
            )
            stage_status = add_job_metadata_to_stage_status(
                job_id, 
                job_done, 
                stage_status
            )

            if job_done and assert_df is not None:
                cache_item_and_cache_key_for_request(
                    export_id, 
                    cache_key=f'assert_df__{export_id}', 
                    object_to_cache=assert_df
                )
                
            do_next_stage = False

        elif do_next_stage and process_stage == 'prepare_df_from_assert_df':
            
            # Make the output dataframe, where there's a single row
            # for each "subject" of the assertions.
            job_id, job_done, df = wrap_func_for_rq(
                func=create_df.prepare_df_from_assert_df, 
                kwargs={'assert_df': assert_df},
                job_id=stage_status.get('job_id'),
            )
            stage_status = add_job_metadata_to_stage_status(
                job_id, 
                job_done, 
                stage_status
            )

            if job_done and df is not None:
                cache_item_and_cache_key_for_request(
                    export_id, 
                    cache_key=f'df__{export_id}', 
                    object_to_cache=df
                )
            do_next_stage = False
        
        elif do_next_stage and process_stage == 'add_spacetime_to_df':
            
            # Add geometry and chronology information to the output dataframe,
            # either directly added to the subject item, or inferred by 
            # spatial containment relationships.
            job_id, job_done, df = wrap_func_for_rq(
                func=create_df.add_spacetime_to_df, 
                kwargs={'df': df,},
                job_id=stage_status.get('job_id'),
            )
            stage_status = add_job_metadata_to_stage_status(
                job_id, 
                job_done, 
                stage_status
            )

            if job_done and df is not None:
                cache_item_and_cache_key_for_request(
                    export_id, 
                    cache_key=f'df__{export_id}', 
                    object_to_cache=df
                )

            do_next_stage = False
        
        elif do_next_stage and process_stage == 'expand_context_path':
            
            # OK. Add all of the spatial context columns
            job_id, job_done, df = wrap_func_for_rq(
                func=create_df.expand_context_path, 
                kwargs={'df': df,},
                job_id=stage_status.get('job_id'),
            )
            stage_status = add_job_metadata_to_stage_status(
                job_id, 
                job_done, 
                stage_status
            )

            if job_done and df is not None:
                cache_item_and_cache_key_for_request(
                    export_id, 
                    cache_key=f'df__{export_id}', 
                    object_to_cache=df
                )

            do_next_stage = False
        
        elif do_next_stage and process_stage == 'add_authors_to_df':
           
            # Add author information to the output dataframe, either directly
            # added as dublin core properties on the subject item, inferred
            # from equivalence relations between other predicates and 
            # dublin core authors, or inferred from dublin core authors 
            # assigned to the parent projects.
            job_id, job_done, df = wrap_func_for_rq(
                func=create_df.add_authors_to_df, 
                kwargs={'df': df, 'assert_df': assert_df},
                job_id=stage_status.get('job_id'),
            )
            stage_status = add_job_metadata_to_stage_status(
                job_id, 
                job_done, 
                stage_status
            )

            if job_done and df is not None:
                cache_item_and_cache_key_for_request(
                    export_id, 
                    cache_key=f'df__{export_id}', 
                    object_to_cache=df
                )

            do_next_stage = False
        
        elif do_next_stage and process_stage == 'add_media_resource_files_to_df':
            # Add media resource files to media items, if present.
            job_id, job_done, df = wrap_func_for_rq(
                func=create_df.add_media_resource_files_to_df, 
                kwargs={'df': df,},
                job_id=stage_status.get('job_id'),
            )
            stage_status = add_job_metadata_to_stage_status(
                job_id, 
                job_done, 
                stage_status
            )

            if job_done and df is not None:
                cache_item_and_cache_key_for_request(
                    export_id, 
                    cache_key=f'df__{export_id}', 
                    object_to_cache=df
                )

            do_next_stage = False
        
        elif do_next_stage and process_stage == 'add_df_linked_data_from_assert_df':
            # Add equivalent linked data descriptions to the subject.
            job_id, job_done, df = wrap_func_for_rq(
                func=create_df.add_df_linked_data_from_assert_df, 
                kwargs={
                    'df': df,
                    'assert_df': assert_df,
                    'add_entity_ld': add_entity_ld,
                    'add_literal_ld': add_literal_ld,
                },
                job_id=stage_status.get('job_id'),
            )
            stage_status = add_job_metadata_to_stage_status(
                job_id, 
                job_done, 
                stage_status
            )

            if job_done and df is not None:
                cache_item_and_cache_key_for_request(
                    export_id, 
                    cache_key=f'df__{export_id}', 
                    object_to_cache=df
                )

            do_next_stage = False
        
        elif do_next_stage and process_stage == 'add_attribute_data_to_df':
            
            # Add the project specific attributes asserted about
            # the subject items.
            job_id, job_done, df = wrap_func_for_rq(
                func=create_df.add_attribute_data_to_df, 
                kwargs={
                    'df': df,
                    'assert_df': assert_df,
                    'add_object_uris': add_object_uris,
                    'node_pred_unique_prefixing': node_pred_unique_prefixing,
                },
                job_id=stage_status.get('job_id'),
            )
            stage_status = add_job_metadata_to_stage_status(
                job_id, 
                job_done, 
                stage_status
            )

            if job_done and df is not None:
                cache_item_and_cache_key_for_request(
                    export_id, 
                    cache_key=f'df__{export_id}', 
                    object_to_cache=df
                )

            do_next_stage = False
        
        elif do_next_stage and process_stage == 'stylize_df':
            
            # Stylize the dataframe and then we are finished!!
            # First, let's cache the pre-styled dataframe
            cache_item_and_cache_key_for_request(
                export_id, 
                cache_key=f'df__no_style_{export_id}', 
                object_to_cache=df
            )
            stage_status['df_no_style__key'] = f'df_no_style__{export_id}'

            # Now actually do the work to fix style issues.
            job_id, job_done, df = wrap_func_for_rq(
                func=create_df.stylize_df, 
                kwargs={'df': df,},
                job_id=stage_status.get('job_id'),
            )
            stage_status = add_job_metadata_to_stage_status(
                job_id, 
                job_done, 
                stage_status
            )

            if job_done and df is not None:
                cache_item_and_cache_key_for_request(
                    export_id, 
                    cache_key=f'df__{export_id}', 
                    object_to_cache=df
                )

            do_next_stage = False
    
    # Check if we're all complete with this export process.
    all_done = True
    for process_stage, _, _, _ in PROCESS_STAGES:
        stage_status = act_stages[process_stage]
        if not stage_status.get('done'):
            all_done = False
    act_stages['complete'] = all_done

    # Save this stake of the process to the cache.
    cache_item_and_cache_key_for_request(
        export_id, 
        cache_key=cache_key_stages, 
        object_to_cache=act_stages
    )
    return act_stages


def single_stage_make_export_df(
    filter_args=None, 
    exclude_args=None,
    add_entity_ld=True,
    add_literal_ld=True,
    add_object_uris=True,
    node_pred_unique_prefixing=create_df.NODE_PRED_UNIQUE_PREDFIXING,
    reset_cache=False,
    export_id=None,
):
    
    kwargs = {
        'filter_args': filter_args,
        'exclude_args': exclude_args,
        'add_entity_ld': add_entity_ld,
        'add_literal_ld': add_literal_ld,
        'add_object_uris': add_object_uris,
        'node_pred_unique_prefixing': node_pred_unique_prefixing,
    }
    if not export_id:
        export_id = make_hash_id_from_args(
            args=kwargs
        )
    
    if reset_cache:
        # Eliminate any cached items relevant to this export_id
        reset_request_process_cache(export_id)
    
    cache = caches['redis']

    # Cache the arguments used to generate this export.
    export_args_key = f'export-args-{export_id}'
    if not cache.get(export_args_key) and kwargs:
        cache_item_and_cache_key_for_request(
            export_id, 
            cache_key=export_args_key, 
            object_to_cache=kwargs,
        )

    cache_key_status = f'export-no-stages-{export_id}'
    raw_status = cache.get(cache_key_status)
    if raw_status is None:
        status = {
            'export_id': export_id,
            'creation_args': kwargs,
            'df__key': f'df__{export_id}',
            'df_no_style__key': f'df_no_style__{export_id}',
        }
    else:
        status = raw_status.copy()
    
    
    job_done = None
    if not status.get('done') or not status.get('complete'):
        # Now actually do the work to fix style issues.
        job_id, job_done, df_tup = wrap_func_for_rq(
            func=create_df.make_clean_export_df, 
            kwargs=kwargs,
            job_id=status.get('job_id'),
        )
        status = add_job_metadata_to_stage_status(
            job_id, 
            job_done, 
            status
        )

    if job_done and df_tup is not None:
        df, df_no_style = df_tup
        cache_item_and_cache_key_for_request(
            export_id, 
            cache_key=f'df__{export_id}', 
            object_to_cache=df
        )
        cache_item_and_cache_key_for_request(
            export_id, 
            cache_key=f'df_no_style__{export_id}', 
            object_to_cache=df_no_style
        )
        status['complete'] = True
        status['count_columns'] = len(df.columns)
        status['count_rows'] = len(df.index)
        status['columns'] = df.columns.tolist()
    
    # Save this stake of the process to the cache.
    cache_item_and_cache_key_for_request(
        export_id, 
        cache_key=cache_key_status, 
        object_to_cache=status,
    )
    return status


def queued_export_config_dict(
    filter_args=None, 
    exclude_args=None,
):
    """Wraps the ui_utilities.make_export_config_dict in a job queue
    
    :param dict filter_args: Arguments for filtering an
        AllAssertion model queryset.
    :param dict exclude_args: Arguments for making exclusions in
        an AllAssertion model queryset.
    :param str job_id: String UUID for the redis queue job assoctiated
        with a stage_status
    :param list ui_configs: List of config tuples that give options
        and some description to filter and exclude options
    """
    kwargs = {
        'filter_args': filter_args,
        'exclude_args': exclude_args,
    }
    config_id = make_hash_id_from_args(
        args=kwargs
    )

    cache = caches['redis']
    cache_key_status = f'export-config-{config_id}'
    raw_status = cache.get(cache_key_status)
    if raw_status is None:
        status = {
            'config_id': config_id,
        }
    else:
        status = raw_status.copy()
    
    job_done = None
    config_dict = None
    if not status.get('done') or not status.get('complete'):
        job_id, job_done, config_dict = wrap_func_for_rq(
            func=ui_utilities.make_export_config_dict, 
            kwargs=kwargs,
            job_id=status.get('job_id'),
        )
        status = add_job_metadata_to_stage_status(
            job_id, 
            job_done, 
            status
        )

    if job_done and config_dict is not None:
        for key, values in config_dict.items():
            status[key] = values

    return status

