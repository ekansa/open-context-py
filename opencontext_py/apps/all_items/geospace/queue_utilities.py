
import copy
import hashlib
import logging
import time

from django.core.cache import caches

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllSpaceTime,
)

from opencontext_py.apps.all_items import permissions
from opencontext_py.apps.all_items.editorial.item import updater_spacetime

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


def make_geo_json_of_regions_for_item_id(
    item_id,
    request=None,
    max_clusters=geo_agg.MAX_CLUSTERS,
    min_cluster_size_km=geo_agg.MIN_CLUSTER_SIZE_KM,
    cluster_method=geo_agg.DEFAULT_CLUSTER_METHOD,
    request_id=None,
    reset_cache=False,
):
    """Use worker and cache to make aggregate geospatial regions for item

    :param UUID item_id: A UUID or string UUID for an AllManifest object.
    :param request request: A Django request object with authentication,
        user information to determine permissions
    :param int max_clusters: The maximum number of clusters
        to return
    :param float min_cluster_size_km: The minimum diagonal 
        length in KM between min(lat/lon) and max(lat/lon)
    :param str cluster_method: A string that names the sklearn
        clustering method to use on these data.
    :param str request_id: An identifier for this specific request.
    """
    man_obj = AllManifest.objects.filter(
        uuid=item_id,
    ).first()
    if not man_obj:
        # No manifest object to make aggregate spatial
        # regions!
        return None
    
    _, ok_edit = permissions.get_request_user_permissions(
        request, 
        man_obj, 
        null_request_ok=True
    )
    if not ok_edit:
        return None

    kwargs = {
        'man_obj': man_obj,
        'max_clusters': max_clusters,
        'min_cluster_size_km': min_cluster_size_km,
        'cluster_method': cluster_method,
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
    
    job_done = None
    if not status.get('done') or not status.get('complete'):
        # Now actually do the work to fix style issues.
        job_id, job_done, geo_tup = wrap_func_for_rq(
            func=geo_agg.make_geo_json_of_regions_for_man_obj, 
            kwargs=kwargs,
            job_id=status.get('job_id'),
        )
        status = add_job_metadata_to_stage_status(
            job_id, 
            job_done, 
            status
        )

    if job_done and geo_tup is not None:
        geometry, count_points = geo_tup
        add_list = [
            {
                'item_id': item_id,
                'geometry': geometry,
                'source_id': 'geospace-aggregate-function',
                'meta_json': {
                    'function': 'geo_agg.make_geo_json_of_regions_for_man_obj',
                    'max_clusters': max_clusters,
                    'min_cluster_size_km': min_cluster_size_km,
                    'cluster_method': cluster_method,
                    'count_points': count_points,
                }
            }
        ]

        added, errors = updater_spacetime.add_spacetime_objs(
            add_list
        )
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
