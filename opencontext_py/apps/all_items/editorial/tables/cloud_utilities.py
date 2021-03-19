import os
import hashlib
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

def list_export_table_objs():
    driver = get_cloud_storage_driver()
    container = driver.get_container(
        container_name=settings.CLOUD_CONTAINER_EXPORTS
    )
    return driver.list_container_objects(container)