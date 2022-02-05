import logging
import time

import django_rq

from django.core.cache import caches

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
)

from opencontext_py.apps.all_items import permissions

# For adding human remains flagging
from opencontext_py.apps.all_items import sensitive_content

from opencontext_py.libs.queue_utilities import (
    wrap_func_for_rq,
    make_hash_id_from_args,
    reset_request_process_cache,
    add_cache_key_to_request_cache_key_list,
    cache_item_and_cache_key_for_request,
)


logger = logging.getLogger("rq-worker-logger")

# ---------------------------------------------------------------------
# NOTE: This will handle major project-level editing, publishing, and
# indexing functions. Since many of these functions require long 
# execution times, job-queue and worker utilities will be needed to
# wrap functions for use Web based user interfaces 
# ---------------------------------------------------------------------

REQUEST_CACHE_LIFE = 60 * 60 * 6 # 6 hours. 
DEFAULT_TIMEOUT = 60 * 30   # 30 minutes.


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



def queued_flag_human_remains_items_in_project(project_id, reset_cache=False):
    """Wraps the sensitive_content.flag_human_remains_items_in_project in a job queue
    
    :param str project_id: A project's UUID or string UUID primary key
        identifier
    """

    cache = caches['redis']
    cache_key = f'proj-human-remains-flag-{project_id}'
    raw_status = cache.get(cache_key)
    if reset_cache or raw_status is None:
        status = {
            'project_id': str(project_id),
            'done': False,
        }
    else:
        status = raw_status.copy()
    
    kwargs = {
        'project_id': project_id,
        'use_cache': True,
        'reset_cache': True,
    }
    
    job_done = None
    if not status.get('done') or not status.get('complete'):
        job_id, job_done, count_flagged = wrap_func_for_rq(
            func=sensitive_content.flag_human_remains_items_in_project, 
            kwargs=kwargs,
            job_id=status.get('job_id'),
        )
        status = add_job_metadata_to_stage_status(
            job_id, 
            job_done, 
            status
        )

    if job_done and count_flagged is not None:
        status['done'] = True
        status['count_updated'] = count_flagged

    status['ok'] = True

    cache.set(
        cache_key, 
        status, 
        timeout=REQUEST_CACHE_LIFE,
    )
    return status


def queued_flag_project_human_remains(request_json, request=None):
    flagging_done = None
    updated = []
    errors = []
    if not isinstance(request_json, list):
        errors.append('Request json must be a list of dictionaries to update')
        return  flagging_done, updated, errors

    flagging_done = True
    for proj_hr in request_json:
        uuid = proj_hr.get('uuid')
        if not uuid:
            errors.append('Must have "uuid" attribute.')
            continue

        proj_context = AllManifest.objects.filter(
            uuid=uuid,
            item_type__in=['projects'],
        ).first()
        if not proj_context:
            errors.append(f'Cannot find {uuid} as a project or vocab in the manifest.')
            continue

        _, ok_edit = permissions.get_request_user_permissions(
            request, 
            proj_context, 
            null_request_ok=True
        )
        if not ok_edit:
            errors.append(f'Need permission to edit manifest object {proj_context}')
            continue
        
        update_dict = queued_flag_human_remains_items_in_project(
            proj_context.uuid,
            reset_cache=proj_hr.get('reset', False)
        )
        if not update_dict.get('done'):
            # The process is not done yet.
            flagging_done = False
        updated.append(update_dict)
    return flagging_done, updated, errors