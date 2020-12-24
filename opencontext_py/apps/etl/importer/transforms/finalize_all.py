import json
import logging

import numpy as np
import pandas as pd

from django.core.cache import caches
from django.db.models import Q

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllSpaceTime,
    AllResource,
    AllIdentifier,
)

from opencontext_py.apps.etl.importer.models import (
    DataSource,
    DataSourceField,
    DataSourceRecord,
    DataSourceAnnotation,
    get_immediate_context_parent_obj_db,
    get_immediate_context_children_objs_db,
)

from opencontext_py.apps.etl.importer import df as etl_df
from opencontext_py.apps.etl.importer import utilities as etl_utils

from opencontext_py.apps.etl.importer.transforms import assertions
from opencontext_py.apps.etl.importer.transforms import general_named_entities
from opencontext_py.apps.etl.importer.transforms import media_resources
from opencontext_py.apps.etl.importer.transforms import predicates_types_variables
from opencontext_py.apps.etl.importer.transforms import space_time_events
from opencontext_py.apps.etl.importer.transforms import subjects


logger = logging.getLogger("etl-importer-logger")


DF_LOAD_BATCH_SIZE = 250

PROCESS_STAGES = [
    (
        'initialize_df', 
        'Gather data for transform and load', 
        None, 
        DF_LOAD_BATCH_SIZE,
    ),
    (
        'media_resources', 
        'Load media and link to files', 
        media_resources.reconcile_item_type_media_resources, 
        50,
    ),
    (
        'subjects', 
        'Load locations, objects, and their contexts',
        subjects.reconcile_item_type_subjects,
        100,
    ),
    (
        'named_entities', 
        'Load misc. named entities',
        general_named_entities.reconcile_general_named_entities,
        500,
    ),
    (
        'space_time', 
        'Load spatial and chronological (event) data',
        space_time_events.reconcile_space_time,
        500,
    ),
    (
        'predicates_types_variables', 
        'Load descriptive attributes and controlled vocabs',
        predicates_types_variables.reconcile_predicates_types_variables,
        500,
    ),
    (
        'link_assertions', 
        'Load linking assertions',
        assertions.make_all_linking_assertions,
        500,
    ),
    (
        'descriptive_assertions', 
        'Load descriptive assertions',
        assertions.make_all_descriptive_assertions,
        500,
    ),
]



# ---------------------------------------------------------------------
# NOTE: These functions manage the transformation and loading of
# a data_source after the user has completed adding annotations that
# configure the process.
# ---------------------------------------------------------------------
def delete_imported_from_datasource(ds_source):
    """Deletes already imported data from this data source"""
    models = [
        AllResource,
        AllSpaceTime,
        AllAssertion,
        AllManifest,
    ]
    all_n = 0
    for model in models:
        n, _ = model.objects.filter(
            source_id=ds_source.source_id
        ).delete()
        all_n += n
    return all_n


def reset_data_source_etl_process_cache(ds_source):
    """Resets the cached items relating to the etl process for this data_source"""
    cache = caches['redis']
    key_list_cache_key = f'all-etl-cache-key-{str(ds_source.uuid)}'  
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


def reset_data_source_transform_load(ds_source):
    """Resets the Transform, Load stage of the ETL process"""
    count_prior_load_deleted = delete_imported_from_datasource(ds_source)
    count_etl_cache_deleted = reset_data_source_etl_process_cache(ds_source)
    return count_prior_load_deleted, count_etl_cache_deleted


def add_cache_key_to_etl_cache_key_list(ds_source, new_key):
    """Adds a cache key to the the process cache key list for this data source etl"""
    cache = caches['redis']
    key_list_cache_key = f'all-etl-cache-key-{str(ds_source.uuid)}'  
    keys = cache.get(key_list_cache_key)
    if not keys:
        # Initial set up a list of keys.
        keys = []

    if new_key in keys:
        # We already have this new_key in our cached key list.
        return None

    keys.append(new_key)
    try:
        cache.set(key_list_cache_key, keys)
    except:
        logger.info(f'Cache failure with: {key_list_cache_key}')


def cache_item_and_cache_key_for_etl_source(ds_source, cache_key, object_to_cache):
    """Caches an item and saves the key to our ETL key list for this data source"""
    cache = caches['redis']
    add_cache_key_to_etl_cache_key_list(ds_source, cache_key)
    try:
        cache.set(cache_key, object_to_cache)
    except:
        logger.info(f'Cache failure with: {cache_key}')
    return object_to_cache


def cache_get_data_source_row_count(ds_source):
    """Gets and caches the row count for the data source"""
    cache = caches['redis']
    cache_key = f'df-row-count-{str(ds_source.uuid)}'
    row_count = cache.get(cache_key)
    if row_count:
        return row_count
    
    # We're getting the unique row count directly from
    # the DataSourceRecord table, just in case we did something
    # weird, like added or deleted records after we extracted
    # from the original data source.
    row_count = DataSourceRecord.objects.filter(
        data_source=ds_source
    ).distinct('row_num').order_by('row_num').count()
    # Cache this item and save the key to the ETL datasource cache keys
    cache_item_and_cache_key_for_etl_source(ds_source, cache_key, row_count)
    return row_count


def cache_get_data_source_max_row_num(ds_source):
    """Gets and caches the row count for the data source"""
    cache = caches['redis']
    cache_key = f'df-max-row-num-{str(ds_source.uuid)}'
    max_row_num = cache.get(cache_key)
    if max_row_num:
        return max_row_num
    
    # We're getting the unique row count directly from
    # the DataSourceRecord table, just in case we did something
    # weird, like added or deleted records after we extracted
    # from the original data source.
    max_row_obj = DataSourceRecord.objects.filter(
        data_source=ds_source
    ).order_by('-row_num').first()
    max_row_num = max_row_obj.row_num
    # Cache this item and save the key to the ETL datasource cache keys
    cache_item_and_cache_key_for_etl_source(ds_source, cache_key, max_row_num)
    return max_row_num


def cache_get_batch_df(
    ds_source, 
    limit_row_num_start=1, 
    limit_row_count=DF_LOAD_BATCH_SIZE, 
    limit_row_num_last=None
):
    """Caches and gets a dataframe with part of the etl data records"""
    cache = caches['redis']
    cache_key = f'df-{limit_row_num_start}-{limit_row_count}-{limit_row_num_last}-{str(ds_source.uuid)}'  
    df = cache.get(cache_key)
    if df is not None:
        return df
    
    # Get this batch from the database.
    exclude_row_list = None
    if False and limit_row_num_start > 1:
        exclude_row_list = [limit_row_num_start]

    df = etl_df.db_make_dataframe_from_etl_data_source(
        ds_source, 
        include_uuid_cols=True,
        include_error_cols=True,
        use_column_labels=False,
        limit_field_num_list=None,
        limit_row_num_start=limit_row_num_start,
        limit_row_num_last=limit_row_num_last,
        limit_row_count=limit_row_count,
        limit_row_num_list=None,
        exclude_row_list=exclude_row_list,
    )
    # Cache this item and save the key to the ETL datasource cache keys
    cache_item_and_cache_key_for_etl_source(ds_source, cache_key, df)
    return df


def initialize_df(ds_source):
    """Initial setup of the data source dataframe"""
    cache = caches['redis']
    # Get out expected max_row_num for this data source.
    max_row_num = cache_get_data_source_max_row_num(ds_source)

    df_cache_key = f'df-{str(ds_source.uuid)}'
    df = cache.get(df_cache_key)
    if df is None:
        # We don't have a df for this data source, load it.
        df = cache_get_batch_df(
            ds_source, 
            limit_row_num_start=1, 
            limit_row_count=DF_LOAD_BATCH_SIZE
        )
        # Cache it.
        cache_item_and_cache_key_for_etl_source(ds_source, df_cache_key, df)
        # Report on how complete our dataframe is.
        cached_max = df['row_num'].max()
        return df, cached_max, max_row_num
    
    # Our cache was not empty, but do we have all the data loaded yet?
    cached_max = df['row_num'].max()
    if cached_max == max_row_num:
        # We've got a complete dataframe for this ds_source
        return df, cached_max, max_row_num
    
    # We don't yet have a complete data frame, so get the next batch.
    df_batch = cache_get_batch_df(
        ds_source, 
        limit_row_num_start=(cached_max + 1), 
        limit_row_num_last=(cached_max + DF_LOAD_BATCH_SIZE)
    )
    # Append the new batch data to this dataframe.
    df = df.append(df_batch, ignore_index=True)
    df.drop_duplicates(subset=['row_num'], inplace=True)
    # Update the cache with the added data from this last batch.
    cache_item_and_cache_key_for_etl_source(ds_source, df_cache_key, df)
    # Return the dataframe and how compete it is.
    cached_max = df['row_num'].max()
    return df, cached_max, max_row_num


def get_ds_source_df_if_ready(ds_source):
    """Get a dataframe for a data source"""
    cache = caches['redis']

    # Get the current state of the ETL process
    cache_key_stages = f'done-stages-{str(ds_source.uuid)}'
    etl_stages = cache.get(cache_key_stages)
    if etl_stages is None:
        # We don't have any stages.
        return None

    stage = etl_stages.get('initialize_df', {})
    if not stage.get('done'):
        # The dataframe isn't done yet.
        return None

    df_cache_key = f'df-{str(ds_source.uuid)}'
    return cache.get(df_cache_key)


def apply_transform_function(
    ds_source, 
    transform_function, 
    progress_key_name, 
    chunk_size,
    df=None,
    print_progress=True
):
    """Applies a transform function to a data source"""
    cache = caches['redis']

    if df is None:
        # Try to get the dataframe for the data source.
        df =  get_ds_source_df_if_ready(ds_source)
    if df is None:
        return None

    max_row_num = df['row_num'].max()
    prior_row_cache_key = f'{progress_key_name}-{str(ds_source.uuid)}'
    prior_row = cache.get(prior_row_cache_key)
    
    if not prior_row:
        prior_row = 0
    
    if prior_row >= max_row_num:
        # This is already done. so skip out.
        return df,  max_row_num,  max_row_num
    
    last_batch_row = prior_row + chunk_size
    
    batch_index = (
        (df['row_num'] >= prior_row)
        & (df['row_num'] <= last_batch_row)
    )
    
    df= transform_function(
        ds_source, 
        df=df,
        filter_index=batch_index
    )
    if df is None:
        # There are no transforms to do.
        return None, 0, 0
    
    # Cache the altered data frame.
    df_cache_key = f'df-{str(ds_source.uuid)}'
    cache_item_and_cache_key_for_etl_source(ds_source, df_cache_key, df)

    # Cache the last_batch_media_row as the prior media row for the 
    cache_item_and_cache_key_for_etl_source(
        ds_source, 
        prior_row_cache_key, 
        last_batch_row
    )

    return df,  last_batch_row,  max_row_num


def transform_load(ds_source):
    """Transforms and loads a data source"""
    cache = caches['redis']
    cache_key_stages = f'done-stages-{str(ds_source.uuid)}'

    etl_stages = cache.get(cache_key_stages)
    if etl_stages is None:
        etl_stages = {k:{'done': False} for k, _, _, _ in PROCESS_STAGES}

    do_next_stage = True
    for process_stage, label, transform_function, chunk_size in PROCESS_STAGES:
        stage_status = etl_stages[process_stage]
        stage_status['label'] = label
        if stage_status.get('done') or not do_next_stage:
            # This stage is done, so continue to the next stage
            continue
        if do_next_stage and process_stage == 'initialize_df':
            df, cached_max, max_row_num = initialize_df(ds_source)
            stage_status['done_count'] = cached_max
            stage_status['total_count'] = max_row_num
            if df is not None:
                stage_status['len_df'] = len(df.index)
            if cached_max ==  max_row_num:
                stage_status['done'] = True
            do_next_stage = False
        elif do_next_stage and transform_function is not None:
            df, max_done_row, max_row_num = apply_transform_function(
                ds_source,
                df=None,
                transform_function=transform_function, 
                progress_key_name=f'prior-row-{process_stage}', 
                chunk_size=chunk_size, 
                print_progress=True
            )
            stage_status['done_count'] = max_done_row
            stage_status['total_count'] = max_row_num
            if df is not None:
                stage_status['len_df'] = len(df.index)
            if max_done_row ==  max_row_num:
                stage_status['done'] = True
            do_next_stage = False
    
    # Check if all the stages are complete.
    all_done = True
    for process_stage, _, _, _ in PROCESS_STAGES:
        stage_status = etl_stages[process_stage]
        if not stage_status.get('done'):
            all_done = False
    
    etl_stages['complete'] = all_done
    
    # Save this stake of the process to the cache.
    cache_item_and_cache_key_for_etl_source(ds_source, cache_key_stages, etl_stages)
    return etl_stages