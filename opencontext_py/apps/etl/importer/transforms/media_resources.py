import logging

import numpy as np
import pandas as pd


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllResource,
)

from opencontext_py.apps.etl.importer.models import (
    DataSourceAnnotation,
)
from opencontext_py.apps.etl.importer import df as etl_df
from opencontext_py.apps.etl.importer.transforms import reconcile


logger = logging.getLogger("etl-importer-logger")

# ---------------------------------------------------------------------
# NOTE: These functions manage the transformations of item_type
# media and resource (file url) entities
# ---------------------------------------------------------------------
def get_media_resource_files_annotation_qs(ds_source):
    """Gets a queryset for media has files annotations for this data source"""
    return DataSourceAnnotation.objects.filter(
        data_source=ds_source,
        subject_field__item_type='media',
        predicate_id=configs.PREDICATE_OC_ETL_MEDIA_HAS_FILES,
    )


def get_media_files_field_num_list(ds_anno_media_qs):
    """Makes a list of media and resource files field numbers"""
    field_nums = list(
        set(
            [
                ds_anno.subject_field.field_num
                for ds_anno in ds_anno_media_qs
            ]
        )
    )
    field_nums += [
        ds_anno.object_field.field_num
        for ds_anno in ds_anno_media_qs
    ]
    return field_nums


def get_media_files_df(ds_source, limit_field_num_list=None):
    """Gets a dataframe relevant to spatial containment"""
    if not limit_field_num_list:
        ds_anno_media_qs =  get_media_resource_files_annotation_qs(ds_source)
        limit_field_num_list = get_media_files_field_num_list(ds_anno_media_qs)

    df = etl_df.db_make_dataframe_from_etl_data_source(
        ds_source,
        include_uuid_cols=True,
        include_error_cols=True,
        limit_field_num_list=limit_field_num_list,
    )
    return df


def reconcile_media_and_resource_files(media_ds_field, df, filter_index=None):
    """Reconciles entities in a ds_field of item_type media"""
    if media_ds_field.item_type != 'media':
        # This is not a media field, so skip out.
        return df

    media_uuid_col = f'{media_ds_field.field_num}_item'

    if filter_index is None:
        filter_index = df['row_num'] >= 0

    # Reconcile the media entities in the media_ds_field column
    # of the dataframe.
    # NOTE: This is the only step that does any update to the
    # dataframe and the DataSourceRecords. That's because item_type='media'
    # is stored in the Manifest types, but resources are NOT.
    df = reconcile.df_reconcile_id_field(
        df=df,
        ds_field=media_ds_field,
        do_recursive=False,
        filter_index=filter_index,
    )

    # Now get annotations for the resources (file urls) that we want to
    # create and associate with the Manifest objects of item_type = 'media'
    # that we just reconciled above.
    act_resource_anno_qs = DataSourceAnnotation.objects.filter(
        subject_field=media_ds_field,
        predicate_id=configs.PREDICATE_OC_ETL_MEDIA_HAS_FILES,
    )
    for ds_anno in act_resource_anno_qs:
        if ds_anno.object_field and ds_anno.object_field.item_type == 'resources':
            resource_field = ds_anno.object_field
            resource_type_obj = resource_field.item_class
            res_col = f'{resource_field.field_num}_col'
        elif ds_anno.object_str:
            # We have a URL that we want to associate with all of the
            # media_uuids. So it must be a thumbail.
            resource_field = None
            res_col = None
            resource_type_obj = AllManifest.objects.filter(
                uuid=configs.OC_RESOURCE_THUMBNAIL_UUID
            ).first()
        else:
            resource_type_obj = None

        if resource_type_obj is None:
            # We don't have a resource type, so we can't import resources
            continue

        if str(resource_type_obj.uuid) not in configs.OC_RESOURCE_TYPES_UUIDS:
            # The resource type is not valid, so we can't import.
            continue

        for media_uuid in df[filter_index][media_uuid_col].unique():
            if not media_uuid:
                continue
            if not '-' in str(media_uuid):
                # not a uuid
                continue
            media_index = df[media_uuid_col] == media_uuid
            if len(df[media_index].index) < 1:
                raise ValueError(f'Missing media uuid {media_uuid}')
            row_num = df[media_index]['row_num'].iloc[0]
            resource_file_url = None
            if resource_field is None and ds_anno.object_str:
                # We have a URL that we want to associate with all of the
                # media_uuids. This can only work as a thumbnail.
                resource_file_url = ds_anno.object_str
            elif resource_field:
                resource_file_url = df[media_index][res_col].iloc[0]
            if not resource_file_url:
                # The resource file URL is empty.
                continue

            resource_file_url = AllManifest().clean_uri(resource_file_url)

            resource_obj = None
            media_res_type_qs = AllResource.objects.filter(
                item_id=media_uuid,
                resourcetype=resource_type_obj,
            )
            # The rank let us import multiple resources of the same resource
            # type for the same item. It will be zero when this media item does
            # not already have a resource of the resource_type_obj.
            rank = len(media_res_type_qs)

            if rank > 0:
                # We already imported something of this resource type
                # for this media item. Now check to see if it also matches URL.
                resource_obj = media_res_type_qs.filter(
                    uri=resource_file_url,
                ).first()

            if resource_obj:
                # We already have this and we don't do anything else, because the resource item
                # is not a manifest object so we don't update the
                # DataSourceRecord to store it.
                continue

            # We don't already have this resource, so add it.
            res_dict = {
                'item_id': media_uuid,
                'project': media_ds_field.data_source.project,
                'resourcetype': resource_type_obj,
                'source_id': media_ds_field.data_source.source_id,
                'uri': resource_file_url,
                'rank': rank,
            }
            try:
                resource_obj = AllResource(**res_dict)
                resource_obj.save()
            except Exception as e:
                resource_obj = None
                if hasattr(e, 'message'):
                    error = e.message
                else:
                    error = str(e)
                logger.info(
                    f'Failed to create resource(file url) object at row {row_num}, field {media_ds_field.label} '
                    f'Error: {str(error)}'
                )
            continue
    return df


def reconcile_item_type_media_resources(ds_source, df=None, filter_index=None):
    """Reconciles all item_type='media' and 'resource' fields in a data_source"""

    ds_anno_media_qs =  get_media_resource_files_annotation_qs(ds_source)
    if not len(ds_anno_media_qs):
        # There are no media files to tranform and import.
        return None

    if df is None:
        # We get the dataframe of media and resource files
        limit_field_num_list = get_media_files_field_num_list(ds_anno_media_qs)
        df =  get_media_files_df(ds_source, limit_field_num_list)

    if df is None:
        # We have no dataframe of media and resource files
        # to reconcile.
        return None

    print(df.head())

    if filter_index is None:
        filter_index = df['row_num'] >= 0

    media_fields = list(
        set(
            [ds_anno.subject_field for ds_anno in ds_anno_media_qs]
        )
    )
    print(media_fields)
    for media_ds_field in media_fields:
        df = reconcile_media_and_resource_files(
            media_ds_field,
            df,
            filter_index=filter_index
        )

    return df
