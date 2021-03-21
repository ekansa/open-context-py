import os
import hashlib
import time
import uuid as GenUUID

import numpy as np
import pandas as pd

from django.conf import settings
from django.db.models import Count, Q, OuterRef, Subquery

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.defaults import (
    DEFAULT_MANIFESTS,
)
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

from opencontext_py.apps.all_items.editorial.item import edit_configs

from opencontext_py.apps.all_items.editorial.tables import queue_utilities

# ---------------------------------------------------------------------
# NOTE: These functions provide utilities to add metadata and download
# links to AllManifest item_type == tables items created by export
# processes here.
# ---------------------------------------------------------------------

def add_table_resource(
    man_obj, 
    export_id, 
    cloud_obj, 
    resourcetype_id=configs.OC_RESOURCE_FULLFILE_UUID
):
    """Adds table resource object objects

    :param AllManifest man_obj: An instance of the AllManifest model
        for a tables item associated with an export_id
    :param str export_id: Export ID for the process that made the 
        dataframe that we put in cloud storage
    :param Object cloud_obj: An object for the exported table now
        saved in cloud storage.
    :param uuid resourcetype_id: A resource type UUID (or string uuid)
    """
    if not man_obj or not cloud_obj:
        return None
    if not man_obj.item_type == 'tables':
        return None
    
    # Make the URL for the export download.
    obj_uri = AllManifest().clean_uri(
        f'{settings.CLOUD_BASE_UR}/{cloud_obj.container.name}/{cloud_obj.name}'
    )
    csv_file_dict = {
        'item': man_obj,
        'project': man_obj.project,
        'resourcetype_id': resourcetype_id,
        'rank': 1,
        'source_id': man_obj.source,
        'uri': obj_uri,
        'meta_json': {
            'export_id': export_id,
            'cloud_container_name': cloud_obj.container.name,
            'cloud_object_name': cloud_obj.name,
            'export_args': queue_utilities.get_cached_export_args(
                export_id
            )
        },
    }
    res_obj, _ = AllResource.objects.get_or_create(
        uuid=AllResource().primary_key_create(
            item_id=man_obj.uuid,
            resourcetype_id=resourcetype_id,
            rank=1,
        ),
        defaults=csv_file_dict,
    )
    return res_obj


def add_table_dc_metadata(man_obj, export_id):
    """Adds table Dublin core metadata inferred from export

    :param AllManifest man_obj: An instance of the AllManifest model
        for a tables item associated with an export_id
    :param str export_id: Export ID for the process that made the 
        dataframe that we put in cloud storage
    """
    df_ns = get_cached_no_style_df(export_id)
    if df_ns is None:
        # Somehow missing the non-styled dataframe, so we can't
        # automatically make metadata
        return None


def add_table_metadata_and_resources(man_obj, export_id, full_cloud_obj, preview_cloud_obj):
    """Adds table metadata and related resources objects

    :param AllManifest man_obj: An instance of the AllManifest model
        for a tables item associated with an export_id
    :param str export_id: Export ID for the process that made the 
        dataframe that we put in cloud storage
    :param Object cloud_obj: An object for the exported table now
        saved in cloud storage.
    """

    full_res_obj = add_table_resource(
        man_obj, 
        export_id, 
        cloud_obj=full_cloud_obj,
        resourcetype_id=configs.OC_RESOURCE_FULLFILE_UUID
    )
    preview_res_obj = add_table_resource(
        man_obj, 
        export_id, 
        cloud_obj=preview_cloud_obj,
        resourcetype_id=configs.OC_RESOURCE_PREVIEW_UUID,
    )
    # Add the dublin core metadata for this item.
    add_table_dc_metadata(man_obj, export_id)

    return full_res_obj, preview_res_obj