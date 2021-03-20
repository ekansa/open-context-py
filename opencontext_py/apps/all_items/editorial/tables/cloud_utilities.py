import os
import hashlib
import time
import uuid as GenUUID
import io


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

def list_export_table_objs():
    """Lists objects in the export table container/bucket"""
    driver = get_cloud_storage_driver()
    if driver is None:
        return None
    container = driver.get_container(
        container_name=settings.CLOUD_CONTAINER_EXPORTS
    )
    return driver.list_container_objects(container)


def cloud_store_df_csv(df, uuid, version=1):
    """Stores a dataframe in cloud storage keyed by uuid and version

    :param DataFrame df: The dataframe that we want to store in
        cloud storage
    :param UUID uuid: A uuid (or uuid string) used to make the
        cloud storage object key
    :param int version: An optional version number for the object
    """
    driver = get_cloud_storage_driver()
    if driver is None:
        return None
    container = driver.get_container(
        container_name=settings.CLOUD_CONTAINER_EXPORTS
    )
    object_name = f'{str(uuid)}--v{version}.csv'
    with io.BytesIO() as buffer:
        # NOTE: This is a bit convoluted, but it seems to be a good
        # way to stream upload a Pandas dataframe while respecting 
        # UTF-8. 
        sb = io.TextIOWrapper(buffer, 'utf-8')
        df.to_csv(sb, index=False, encoding='utf-8')
        sb.flush()
        buffer.seek(0)
        obj = driver.upload_object_via_stream(
            iterator=buffer,
            container=container,
            object_name=object_name,
            extra={'Content-Type': 'text/csv; charset=utf8'},
            headers={'Content-Type': 'text/csv; charset=utf8'},
        )
        buffer.close()
    return uuid, obj


def cloud_store_csv_from_cached_export(cache_id, uuid=None, version=1):
    """Stores a cached dataframe in cloud storage keyed by uuid and version

    :param DataFrame df: Cache ID for the dataframe that we want to store in
        cloud storage
    :param UUID uuid: A uuid (or uuid string) used to make the
        cloud storage object key
    :param int version: An optional version number for the object
    """
    cache = caches['redis']
    df = cache.get(cache_id)
    if df is None:
        return None, None
    if not uuid:
        uuid = GenUUID.uuid4()
    uuid, obj = cloud_store_df_csv(df, uuid=uuid, version=version)
    return uuid, obj