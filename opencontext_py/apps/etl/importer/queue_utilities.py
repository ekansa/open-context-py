import hashlib
import logging
import time
import uuid as GenUUID

import django_rq

from django.core.cache import caches


from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)
from opencontext_py.apps.etl.importer import df as imp_df

from opencontext_py.libs.models import make_model_object_json_safe_dict
from opencontext_py.libs.queue_utilities import (
    wrap_func_for_rq,
    make_hash_id_from_args,
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
logger = logging.getLogger("etl-import-logger")


def queued_load_csv_for_etl(
    project_id, file_path, source_exists=None
):
    """Wraps the ui_utilities.make_export_config_dict in a job queue

    :param str(UUID) project_id: Project manifest object uuid
    :param str file_path: Filepath for the CSV file
    :param str source_exists: Flag on what to do if the file already
        exists in for import
    """
    kwargs = {
        'project_id': project_id,
        'file_path': file_path,
    }
    if source_exists:
        kwargs['source_exists'] = source_exists
    job_id = make_hash_id_from_args(kwargs)
    job_id, job_done, ds_source = wrap_func_for_rq(
        func=imp_df.load_csv_for_etl,
        kwargs=kwargs,
        job_id=job_id,
    )
    ds_dict = None
    if ds_source:
        ds_dict = make_model_object_json_safe_dict(
            ds_source,
            more_attributes=['project__label', 'project__slug'],
        )
    return {
        'job_id': job_id,
        'job_done': job_done,
        'ds_source': ds_dict,
    }
