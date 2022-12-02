import logging

import numpy as np
import pandas as pd

from django.core.cache import caches

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllSpaceTime,
    AllResource,
    AllHistory,
)

from opencontext_py.apps.etl.importer.models import (
    DataSourceField,
    DataSourceRecord,
    DataSourceAnnotation,
)

from opencontext_py.apps.etl.importer import df as etl_df

from opencontext_py.apps.etl.importer.transforms import assertions
from opencontext_py.apps.etl.importer.transforms import general_named_entities
from opencontext_py.apps.etl.importer.transforms import media_resources
from opencontext_py.apps.etl.importer.transforms import predicates_types_variables
from opencontext_py.apps.etl.importer.transforms import space_time_events
from opencontext_py.apps.etl.importer.transforms import subjects


logger = logging.getLogger("etl-importer-logger")

ETL_CACHE_LIFE = 60 * 60 * 6 # 6 hours.
DF_LOAD_BATCH_SIZE = 250

PROCESS_STAGES = [
    (
        'initialize_df',
        'Gather data for transform and load',
        None,
        DF_LOAD_BATCH_SIZE,
        True,
    ),
    (
        'media_resources',
        'Load media and link to files',
        media_resources.reconcile_item_type_media_resources,
        50,
        True,
    ),
    (
        'subjects',
        'Load locations, objects, and context relationships',
        subjects.reconcile_item_type_subjects,
        150,
        True,
    ),
    (
        'named_entities',
        'Load misc. named entities',
        general_named_entities.reconcile_general_named_entities,
        100,
        True,
    ),
    (
        'space_time',
        'Load spatial and chronological (event) data',
        space_time_events.reconcile_space_time,
        100,
        True,
    ),
    (
        'predicates_types_variables',
        'Load descriptive attributes and controlled vocabs',
        predicates_types_variables.reconcile_predicates_types_variables,
        100,
        True,
    ),
    (
        'link_assertions',
        'Load misc. linking assertions',
        assertions.make_all_linking_assertions,
        300,
        False,
    ),
    (
        'descriptive_assertions',
        'Load descriptive assertions',
        assertions.make_all_descriptive_assertions,
        300,
        False,
    ),
]



# ---------------------------------------------------------------------
# NOTE: These functions manage the transformation and loading of
# a data_source after the user has completed adding annotations that
# configure the process.
# ---------------------------------------------------------------------
def delete_data_source_reconciled_associations(ds_source):
    """Removes reconciled associations between a data source and the manifest"""

    # Remove item and context reconciliation values from the data source
    # records. This makes sure we don't delete rows from this model if they've
    # been reconciled and then deleted from the manifest.
    ds_rec_qs = DataSourceRecord.objects.filter(
        data_source=ds_source,
    ).update(
        item=None
    )
    ds_rec_qs = DataSourceRecord.objects.filter(
        data_source=ds_source,
    ).update(
        context=None
    )

    # Remove item_class and context references associated
    # for ds_fields that may be associated with already imported items.
    ds_field_qs = DataSourceField.objects.filter(
        item_class__source_id=ds_source.source_id,
    ).update(
        item_class_id=configs.DEFAULT_CLASS_UUID
    )

    ds_field_qs = DataSourceField.objects.filter(
        context__source_id=ds_source.source_id,
    )
    for ds_field in ds_field_qs:
        ds_field.context = None
        ds_field.save()

    # Delete if the predicate is from this same data source.
    ds_anno_qs = DataSourceAnnotation.objects.filter(
        predicate__source_id=ds_source.source_id,
    ).delete()
    # Delete if the object is from this same data source.
    ds_anno_qs = DataSourceAnnotation.objects.filter(
        object__source_id=ds_source.source_id,
    ).delete()
    # Delete if the observation is from this same data source.
    ds_anno_qs = DataSourceAnnotation.objects.filter(
        observation__source_id=ds_source.source_id,
    ).delete()
    # Delete if the event is from this same data source.
    ds_anno_qs = DataSourceAnnotation.objects.filter(
        event__source_id=ds_source.source_id,
    ).delete()
    # Delete if theattribute_group is from this same data source.
    ds_anno_qs = DataSourceAnnotation.objects.filter(
        attribute_group__source_id=ds_source.source_id,
    ).delete()



def delete_imported_from_datasource(ds_source):
    """Deletes already imported data from this data source"""

    all_n, _ = AllHistory.objects.filter(
        item__source_id=ds_source.source_id
    ).delete()
    models = [
        AllResource,
        AllSpaceTime,
        AllAssertion,
        AllManifest,
    ]
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
    delete_data_source_reconciled_associations(ds_source)
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
        cache.set(key_list_cache_key, keys, timeout=ETL_CACHE_LIFE)
    except:
        logger.info(f'Cache failure with: {key_list_cache_key}')


def cache_item_and_cache_key_for_etl_source(ds_source, cache_key, object_to_cache):
    """Caches an item and saves the key to our ETL key list for this data source"""
    cache = caches['redis']
    add_cache_key_to_etl_cache_key_list(ds_source, cache_key)
    try:
        cache.set(cache_key, object_to_cache, timeout=ETL_CACHE_LIFE)
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
    print_progress=True,
):
    """Applies a transform function to a data source, changing the data source dataframe"""
    # NOTE: This is where we do a transformation that changes the data source dataframe.
    # Transforms are done on batches of rows, but we don't care about the number
    # of columns involved in the "batches".
    cache = caches['redis']

    if df is None:
        # Try to get the dataframe for the data source.
        df =  get_ds_source_df_if_ready(ds_source)
    if df is None:
        return None, None, None, None, None

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

    if last_batch_row > max_row_num:
        last_batch_row = max_row_num

    transform_result = transform_function(
        ds_source,
        df=df,
        filter_index=batch_index
    )


    if transform_result is None:
        # There are no transforms to do.
        return None, 0, 0

    # Cache the last_batch_media_row as the prior media row for the
    cache_item_and_cache_key_for_etl_source(
        ds_source,
        prior_row_cache_key,
        last_batch_row
    )

    # We expected to change th dataframe.
    df = transform_result

    # Cache the altered data frame.
    df_cache_key = f'df-{str(ds_source.uuid)}'
    cache_item_and_cache_key_for_etl_source(ds_source, df_cache_key, df)

    return df,  last_batch_row,  max_row_num


def apply_transform_function_on_annotation(
    ds_source,
    transform_function,
    progress_key_name,
    chunk_size,
    df=None,
    print_progress=True,
):
    """Applies a transform/load function based on a specific DataSourceAnnotation"""
    # NOTE: This is were we do a transformation that DOES NOT change the data source dataframe.
    # Transforms are done on batches of rows, and we the transform on each user defined
    # DataSourceAnnotation, one at a time.
    cache = caches['redis']

    if df is None:
        # Try to get the dataframe for the data source.
        df =  get_ds_source_df_if_ready(ds_source)
    if df is None:
        return None, None, None, None, None

    max_row_num = df['row_num'].max()
    prior_row_cache_key = f'{progress_key_name}-{str(ds_source.uuid)}'
    prior_row = cache.get(prior_row_cache_key)

    if not prior_row:
        prior_row = 0

    anno_count_cache_key = f'{progress_key_name}-anno-count-{str(ds_source.uuid)}'
    anno_count = cache.get(anno_count_cache_key)

    anno_index_cache_key = f'{progress_key_name}-anno-{str(ds_source.uuid)}'
    anno_index = cache.get(anno_index_cache_key)
    if anno_index is None:
        anno_index = 0

    if anno_count and anno_index >= anno_count and prior_row >= max_row_num:
        # This is already done. so skip out.
        return df,  max_row_num,  max_row_num, anno_index, anno_count

    # Make the dataframe filter index for this batch.
    last_batch_row = prior_row + chunk_size
    batch_index = (
        (df['row_num'] >= prior_row)
        & (df['row_num'] <= last_batch_row)
    )

    if last_batch_row > max_row_num:
        last_batch_row = max_row_num

    count_anno_qs = transform_function(
        ds_source,
        df=df,
        filter_index=batch_index,
        ds_anno_index_limit=anno_index,
    )

    if last_batch_row >= max_row_num and anno_index < count_anno_qs:
        # We've finished the last row for so move on to the next annotation
        # to process.
        anno_index += 1
        last_batch_row = 0
        cache_item_and_cache_key_for_etl_source(
            ds_source,
            anno_index_cache_key,
            anno_index
        )

    # Cache the last_batch_media_row as the prior media row for the
    cache_item_and_cache_key_for_etl_source(
        ds_source,
        prior_row_cache_key,
        last_batch_row
    )

    # Save the total annotation count for this transform.
    anno_count = count_anno_qs
    cache_item_and_cache_key_for_etl_source(
        ds_source,
        anno_count_cache_key,
        anno_count
    )

    return last_batch_row, max_row_num, anno_index, anno_count


def transform_load(ds_source):
    """Transforms and loads a data source"""
    cache = caches['redis']
    cache_key_stages = f'done-stages-{str(ds_source.uuid)}'

    raw_etl_stages = cache.get(cache_key_stages)
    if raw_etl_stages is None:
        etl_stages = {k:{'done': False} for k, _, _, _, _ in PROCESS_STAGES}
    else:
        etl_stages = raw_etl_stages.copy()

    do_next_stage = True
    for process_stage, label, transform_function, chunk_size, df_change_no_anno_index in PROCESS_STAGES:
        stage_status = etl_stages[process_stage]
        stage_status['label'] = label
        stage_status['last_anno_index'] = None
        stage_status['total_anno_count'] = None
        if stage_status.get('done') or not do_next_stage:
            # This stage is done, so continue to the next stage
            continue

        if do_next_stage and process_stage == 'initialize_df':
            # This is the step where we set up the dataframe for this data source.
            df, cached_max, max_row_num = initialize_df(ds_source)
            stage_status['done_count'] = cached_max
            stage_status['total_count'] = max_row_num
            if cached_max ==  max_row_num:
                stage_status['done'] = True
            do_next_stage = False

        elif do_next_stage and df_change_no_anno_index and transform_function is not None:
            # This is where we do a transformation that changes the data source dataframe.
            # Transforms are done on batches of rows, but we don't care about the number
            # of columns involved in the "batches".
            df, max_done_row, max_row_num = apply_transform_function(
                ds_source,
                df=None,
                transform_function=transform_function,
                progress_key_name=f'prior-row-{process_stage}',
                chunk_size=chunk_size,
                print_progress=True,
            )
            stage_status['done_count'] = max_done_row
            stage_status['total_count'] = max_row_num
            if max_done_row ==  max_row_num:
                stage_status['done'] = True
            do_next_stage = False
        elif do_next_stage and not df_change_no_anno_index and transform_function is not None:
            # This is were we do a transformation that DOES NOT change the data source dataframe.
            # Transforms are done on batches of rows, and we the transform on each user defined
            # DataSourceAnnotation, one at a time.
            max_done_row, max_row_num, anno_index, anno_count = apply_transform_function_on_annotation(
                ds_source,
                df=None,
                transform_function=transform_function,
                progress_key_name=f'prior-row-{process_stage}',
                chunk_size=chunk_size,
                print_progress=True,
            )
            stage_status['done_count'] = max_done_row
            stage_status['total_count'] = max_row_num
            stage_status['last_anno_index'] = anno_index
            stage_status['total_anno_count'] = anno_count
            if max_done_row ==  max_row_num and anno_index == anno_count:
                # We're only done if the rows and the column counts say we're done.
                stage_status['done'] = True
            do_next_stage = False

    # Check if all the stages are complete.
    all_done = True
    for process_stage, _, _, _, _ in PROCESS_STAGES:
        stage_status = etl_stages[process_stage]
        if not stage_status.get('done'):
            all_done = False

    etl_stages['complete'] = all_done

    # Save this stake of the process to the cache.
    cache_item_and_cache_key_for_etl_source(ds_source, cache_key_stages, etl_stages)
    return etl_stages