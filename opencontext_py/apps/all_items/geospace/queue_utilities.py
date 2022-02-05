
import logging
import time

from django.core.cache import caches

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
)


from opencontext_py.apps.all_items.geospace import aggregate as geo_agg


from opencontext_py.libs.queue_utilities import (
    wrap_func_for_rq,
    make_hash_id_from_args,
    reset_request_process_cache,
    add_cache_key_to_request_cache_key_list,
    cache_item_and_cache_key_for_request,
)


# ---------------------------------------------------------------------
# NOTE: These functions provide a means to wrap functions for the 
# aggregation of geospatial data in a que / worker. Aggregation 
# functions can take some time, so they may need to be able to run in 
# the context of a queing system to avoid time-out problems with a
# web-server. 
#
#
# NOTE: Don't forget to start the worker to make redis queue actually
# work:
#
# python manage.py rqworker high
#
# ---------------------------------------------------------------------


logger = logging.getLogger("geospace-aggregate-logger")


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


def worker_add_agg_spacetime_objs(
    request_list,
    request=None,
    request_id=None,
    reset_cache=False,
):
    """Use worker and cache to make aggregate geospatial regions for item

    :param list request_list: A list of dictionary kwargs with items
        to get new aggregate geospatial objects.
    :param request request: A Django request object with authentication,
        user information to determine permissions
    :param str request_id: An identifier for this specific request.
    """
    kwargs = {
        'request_list': request_list,
    }
    if not request_id:
        request_id = make_hash_id_from_args(
            args=kwargs
        )
    
    if reset_cache:
        # Eliminate any cached items relevant to this request_id
        reset_request_process_cache(request_id)
    
    cache = caches['redis']

    # Cache the arguments used to generate this request.
    request_args_key = f'geo-agg-args-{request_id}'
    if not cache.get(request_args_key) and kwargs:
        cache_item_and_cache_key_for_request(
            request_id, 
            cache_key=request_args_key, 
            object_to_cache=kwargs,
        )

    cache_key_status = f'request-status-{request_id}'
    raw_status = cache.get(cache_key_status)
    if raw_status is None:
        status = {
            'request_id': request_id,
            'creation_args': kwargs,
        }
    else:
        status = raw_status.copy()
    
    print(f'Working on: {str(status)}')
    job_done = None
    if not status.get('done') or not status.get('complete'):
        # Now actually do the work cluster regions.

        # Add the request object after, since we only need
        # it for authentication.

        job_id, job_done, geo_tup = wrap_func_for_rq(
            func=geo_agg.add_agg_spacetime_objs, 
            kwargs=kwargs,
            job_id=status.get('job_id'),
        )
        status = add_job_metadata_to_stage_status(
            job_id, 
            job_done, 
            status
        )

    if job_done and geo_tup is not None:
        added, errors = geo_tup
        status['complete'] = True
        status['added'] = added
        status['errors'] = errors
    
    # Save this stake of the process to the cache.
    cache_item_and_cache_key_for_request(
        request_id, 
        cache_key=cache_key_status, 
        object_to_cache=status,
    )
    return status
