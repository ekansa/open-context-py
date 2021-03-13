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

# ---------------------------------------------------------------------
# NOTE: These functions provide a means to wrap functions for the 
# export of tabular data in a que / worker. Exports functions can take
# lots of time, so they need to be able to run in the context of a 
# queing system. 
# ---------------------------------------------------------------------
logger = logging.getLogger("tab-exporter-logger")

EXPORT_CACHE_LIFE = 60 * 60 * 6 # 6 hours. 


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

"""
Note: We'll want to pickle a dataframe for cloud storage.

Here's an amazon example:

import io
import boto3

pickle_buffer = io.BytesIO()
s3_resource = boto3.resource('s3')

new_df.to_pickle(pickle_buffer)
s3_resource.Object(bucket, key).put(Body=pickle_buffer.getvalue())

"""

def wrap_func_for_rq(func, kwargs, job_id=None):
    """Wraps a function for use with the django redis queue

    :param str process_stage: The export stage that we are
        currently wrapping in a redis que
    :param str export_id: A unique ID for this specific export
        process
    :param Object func: The function that we are wrapping
        in the django redis que
    :param dict kwargs: Keyword argument dict that we're
        passing to the function func
    """
    queue = django_rq.get_queue('high')
    job = None
    if job_id:
        job = queue.fetch_job(job_id)

    if job is None:
        job = queue.enqueue(func, **kwargs)
        logger.info(f'Start queue for job: {job.id}')
        return job.id, False, None

    if job.result is None:
        # Still working on this job...
        return job.id, False, None
    
    logger.info(f'Finished job: {job.id}')
    return job.id, True, job.result


def make_hash_id_from_args(args):
    """Turns args into a hash identifier"""
    hash_obj = hashlib.sha1()
    hash_obj.update(str(args).encode('utf-8'))
    return hash_obj.hexdigest()


def make_hash_id_from_df(df):
    """Makes a hash identifier from a dataframe"""
    hash_obj = hashlib.sha1()
    hash_obj.update(str(df.to_csv()).encode('utf-8'))
    return hash_obj.hexdigest()


def make_uuid_from_df_hash(df):
    """Makes a hash identifier from a dataframe"""
    hash_id = make_hash_id_from_df(df)
    return GenUUID.UUID(hex=hash_id[:32])


def reset_export_process_cache(export_id):
    """Resets the cached items relating to the export process"""
    cache = caches['redis']
    key_list_cache_key = f'all-export-cache-key-{export_id}'  
    keys = cache.get(key_list_cache_key)
    if not keys:
        # We don't have any cached items relating to the ETL process
        # of this data source.
        return 0
    # Delete the cached items by their keys.
    cache.delete_many(keys)
    # Now delete the cached list of cache keys for this data_source.
    cache.delete(key_list_cache_key)
    return len(keys)


def add_cache_key_to_export_cache_key_list(export_id, new_key):
    """Adds a cache key to the the process cache key list for this data source etl"""
    cache = caches['redis']
    key_list_cache_key = f'all-export-cache-key-{export_id}'  
    keys = cache.get(key_list_cache_key)
    if not keys:
        # Initial set up a list of keys.
        keys = []

    if new_key in keys:
        # We already have this new_key in our cached key list.
        return None

    keys.append(new_key)
    try:
        cache.set(key_list_cache_key, keys, timeout=EXPORT_CACHE_LIFE)
    except:
        logger.info(f'Cache failure with: {key_list_cache_key}')


def cache_item_and_cache_key_for_export(export_id, cache_key, object_to_cache):
    """Caches an item and saves the key to our ETL key list for this data source"""
    cache = caches['redis']
    add_cache_key_to_export_cache_key_list(export_id, cache_key)
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
    node_delim=create_df.DEFAULT_NODE_DELIM,
    reset_cache=False,
    export_id=None,
):
    
    args = {
        'filter_args': filter_args,
        'exclude_args': exclude_args,
        'add_entity_ld': add_entity_ld,
        'add_literal_ld': add_literal_ld,
        'add_object_uris': add_object_uris,
        'node_delim': node_delim,
    }
    
    if not export_id:
        export_id = make_hash_id_from_args(
            args=args
        )
    
    if reset_cache:
        # Eliminate any cached items relevant to this export_id
        reset_export_process_cache(export_id)
    
    cache = caches['redis']
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
    
    df = cache.get(f'df__{export_id}')
    assert_df = cache.get(f'assert_df__{export_id}')
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
                cache_item_and_cache_key_for_export(
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
                cache_item_and_cache_key_for_export(
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
                cache_item_and_cache_key_for_export(
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
                cache_item_and_cache_key_for_export(
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
                cache_item_and_cache_key_for_export(
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
                cache_item_and_cache_key_for_export(
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
                cache_item_and_cache_key_for_export(
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
                    'node_delim': node_delim,
                },
                job_id=stage_status.get('job_id'),
            )
            stage_status = add_job_metadata_to_stage_status(
                job_id, 
                job_done, 
                stage_status
            )

            if job_done and df is not None:
                cache_item_and_cache_key_for_export(
                    export_id, 
                    cache_key=f'df__{export_id}', 
                    object_to_cache=df
                )

            do_next_stage = False
        
        elif do_next_stage and process_stage == 'stylize_df':
            
            # Stylize the dataframe and then we are finished!!
            # First, let's cache the pre-styled dataframe
            cache_item_and_cache_key_for_export(
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
                cache_item_and_cache_key_for_export(
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
    cache_item_and_cache_key_for_export(
        export_id, 
        cache_key=cache_key_stages, 
        object_to_cache=act_stages
    )
    return act_stages


