import hashlib
import io
import os
import time
import uuid as GenUUID

import numpy as np
import pandas as pd

from django.conf import settings
from django.core.cache import caches

from django.db.models import Count, Q, OuterRef, Subquery

from opencontext_py.libs.cloudstorage import get_cloud_storage_driver
from opencontext_py.apps.all_items import configs

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

from opencontext_py.apps.all_items.editorial.tables import queue_utilities

# ---------------------------------------------------------------------
# NOTE: These utilities use the Apache Libcloud library to interact
# with cloud storage service providers. Libcloud provides an
# abstraction layer that helps controll service provider specific
# dependency issues.
#
# NOTE: If you're doing some edge-case testing on a Linux subsystem
# for Windows, you may run in to date-syncing problems. It seems the
# Linux subsystem may not keep datetime information current if your
# computer falls asleep. This may cause your requests to remote
# cloud services to fail. Easiest solution is to restart.
# ---------------------------------------------------------------------

DEFAULT_PREVIEW_ROW_SIZE = 100


def list_export_table_objs():
    """Lists objects in the export table container/bucket"""
    driver = get_cloud_storage_driver()
    if driver is None:
        return None
    container = driver.get_container(
        container_name=settings.CLOUD_CONTAINER_EXPORTS
    )
    return driver.list_container_objects(container)


def cloud_store_df_csv(df, object_name):
    """Stores a dataframe in cloud storage keyed by uuid and version

    :param DataFrame df: The dataframe that we want to store in
        cloud storage
    :param str object_name: The name (or key) for the CSV file that
        we will write to cloud storage.
    """
    driver = get_cloud_storage_driver()
    if driver is None:
        return None
    container = driver.get_container(
        container_name=settings.CLOUD_CONTAINER_EXPORTS
    )
    with io.BytesIO() as buffer:
        # NOTE: This is a bit convoluted, but it seems to be a good
        # way to stream upload a Pandas dataframe while respecting 
        # UTF-8. 
        sb = io.TextIOWrapper(buffer, 'utf-8')
        df.to_csv(sb, index=False, encoding='utf-8')
        sb.flush()
        buffer.seek(0)
        cloud_obj = driver.upload_object_via_stream(
            iterator=buffer,
            container=container,
            object_name=object_name,
            extra={'Content-Type': 'text/csv; charset=utf8'},
            headers={'Content-Type': 'text/csv; charset=utf8'},
        )
        buffer.close()
    return cloud_obj


def cloud_store_csv_from_cached_export(
    export_id, 
    uuid=None, 
    version=1,
    object_name=None,
    preview_rows=None
):
    """Stores a cached dataframe in cloud storage keyed by uuid and version

    :param str export_id: Export ID for the process that made the 
        dataframe that we want to put in cloud storage
    :param UUID uuid: A uuid (or uuid string) used to make the
        cloud storage object key
    :param int version: An optional version number for the object
    :param str object_name: The name (or key) for the CSV file that
        we will write to cloud storage.
    :param int preview_rows: An optional limit of rows to save
        in order to make a preview table.
    """
    df = queue_utilities.get_cached_export_df(export_id)
    if df is None:
        return None, None
    if not uuid:
        uuid = GenUUID.uuid4()
    if preview_rows:
        df = df.head(preview_rows).copy()
        if not object_name:
            object_name = f'{str(uuid)}--v{version}--head{preview_rows}.csv'
    else:
        if not object_name:
            object_name = f'{str(uuid)}--v{version}--full.csv'
    cloud_obj = cloud_store_df_csv(df, object_name)
    return uuid, cloud_obj