import copy
import hashlib
import logging

import django_rq

from django.core.cache import caches

logger = logging.getLogger("rq-worker-logger")


REQUEST_CACHE_LIFE = 60 * 60 * 6 # 6 hours. 
DEFAULT_TIMEOUT = 60 * 30   # 30 minutes.

# ---------------------------------------------------------------------
# NOTE: These are some utility functions to help with requests that 
# kick off long-lasting processes. They interact with the redis-cache
# where we store some state, and the rq_worker, which executes a long
# lasting process in a queued in a worker.
#
# NOTE: Don't forget to start the worker to make redis queue actually
# work:
#
# python manage.py rqworker high
#
# ---------------------------------------------------------------------


def wrap_func_for_rq(func, kwargs, job_id=None, default_timeout=DEFAULT_TIMEOUT):
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
    queue = django_rq.get_queue('high', default_timeout=default_timeout)
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


def reset_request_process_cache(request_id):
    """Resets the cached items relating to the request process"""
    cache = caches['redis']
    key_list_cache_key = f'all-request-cache-key-{request_id}'  
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


def add_cache_key_to_request_cache_key_list(request_id, new_key):
    """Adds a cache key to the the process cache key list for a request"""
    cache = caches['redis']
    key_list_cache_key = f'all-request-cache-key-{request_id}'  
    keys = cache.get(key_list_cache_key)
    if not keys:
        # Initial set up a list of keys.
        keys = []

    if new_key in keys:
        # We already have this new_key in our cached key list.
        return None

    keys.append(new_key)
    try:
        cache.set(key_list_cache_key, keys, timeout=REQUEST_CACHE_LIFE)
    except:
        logger.info(f'Cache failure with: {key_list_cache_key}')


def cache_item_and_cache_key_for_request(request_id, cache_key, object_to_cache):
    """Caches an item and saves the key to our request key list"""
    cache = caches['redis']
    add_cache_key_to_request_cache_key_list(request_id, cache_key)
    try:
        cache.set(cache_key, object_to_cache, timeout=REQUEST_CACHE_LIFE)
    except:
        logger.info(f'Cache failure with: {cache_key}')
    return object_to_cache
