import logging
import pandas as pd

from django.conf import settings
from django.core.cache import caches

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities

from opencontext_py.libs.queue_utilities import make_hash_id_from_args



if settings.DEBUG:
    FACET_DF_CACHE_TIMEOUT = 60 # 1 minute
else:
    FACET_DF_CACHE_TIMEOUT = 60 * 60 * 24 * 7 # 1 week


def make_df_of_solr_facets(solr_json, path_keys_list=configs.FACETS_SOLR_ROOT_PATH_KEYS):
    """Make a Pandas Dataframe with a matrix of facet_fields, facet_values, and facet_counts
    
    :param dict solr_json: A dictionary derived from the raw solr query request response
    :param list path_keys_list: List of keys to identify the facet fields
        and their facet values and counts
    
    returns DataFrame df
    """
    all_facets_dict = utilities.get_dict_path_value(
        path_keys_list,
        solr_json,
        default={}
    )
    rows = []
    for facet_key, solr_facet_value_count_list in all_facets_dict.items():
        if not solr_facet_value_count_list or not isinstance(solr_facet_value_count_list, list):
            continue
        for i in range(0, len(solr_facet_value_count_list), 2):
            facet_value = str(solr_facet_value_count_list[i])
            facet_count = solr_facet_value_count_list[(i + 1)]
            row = {'facet_field_key': facet_key, 'facet_value': facet_value, 'facet_count': facet_count}
            rows.append(row)
    df = pd.DataFrame(
        data=rows, 
    )
    return df


def make_cache_df_of_solr_facets(
    request_dict,
    solr_json, 
    path_keys_list=configs.FACETS_SOLR_ROOT_PATH_KEYS,
    reset_cache=False
):
    """Make a Pandas Dataframe with a matrix of facet_fields, facet_values, and facet_counts
    
    :param dict request_dict: A dictionary mapping solr facet fields and
        client request paramters. We use this as a basis of a cache key
    :param dict solr_json: A dictionary derived from the raw solr query request response
    :param list path_keys_list: List of keys to identify the facet fields
        and their facet values and counts
    
    returns DataFrame df
    """
    skip_params = configs.SORT_NEW_URL_IGNORE_PARAMS + ['rows']
    cache_key_dict = {}
    for key, val in request_dict.items():
        if key in skip_params:
            continue
        cache_key_dict[key] = val
    cache = caches['redis_search']
    cache_key_suffix = make_hash_id_from_args(
        args=cache_key_dict
    )
    cache_key = f'{settings.CACHE_PREFIX_FACET_DF}{str(cache_key_suffix)}'
    df = None
    if not reset_cache:
        df = cache.get(cache_key)
    if df is not None:
        # We have a result from the cache, so return it.
        print(f'Solr facets dataframe from cache {cache_key}')
        return df
    # Do the hard work of computing the result from scratch
    df = make_df_of_solr_facets(solr_json, path_keys_list=path_keys_list)
    try:
        cache.set(cache_key, df, timeout=FACET_DF_CACHE_TIMEOUT)
    except:
        pass
    return df