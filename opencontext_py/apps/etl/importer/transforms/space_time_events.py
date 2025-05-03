import json
import logging
import pytz

import numpy as np
import pandas as pd

from django.conf import settings
from django.utils import timezone
from django.db.models import Q

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllSpaceTime,
)

from opencontext_py.apps.etl.importer.models import (
    DataSourceField,
    DataSourceAnnotation,
)
from opencontext_py.apps.etl.importer import df as etl_df
from opencontext_py.apps.etl.importer import utilities as etl_utils


logger = logging.getLogger("etl-importer-logger")

# ---------------------------------------------------------------------
# NOTE: These functions manage the transformations of space, time
# event data.
#
# NOTE: These functions must be invoked AFTER reconciliation / import
# of the subjects of the space-time objects. 
# ---------------------------------------------------------------------
SPACE_TIME_ITEM_TYPES = [i_t for i_t, _, _ in DataSourceField.SPACE_TIME_USER_SELECT_ITEM_TYPES]

# UUID related attributes for space-time objects
SPACE_TIME_ID_ATTRIBUTES = [
    'item_id',
    'event_id',
    'earliest',
    'start',
    'stop',
    'latest',
    'latitude',
    'longitude',
    'geometry',
]


def get_space_time_annotation_qs(ds_source):
    """Gets a queryset for space-time annotations for this data source"""
    return DataSourceAnnotation.objects.filter(
        data_source=ds_source,
        predicate_id=configs.PREDICATE_OC_ETL_DESCRIBED_BY,
    ).filter(
        Q(object_field__item_type__in=SPACE_TIME_ITEM_TYPES)
        | Q(meta_json__object_item_type__in=SPACE_TIME_ITEM_TYPES)
    )


def get_space_time_field_num_list(ds_anno_space_time_qs):
    """Makes a list of space-time related field numbers"""
    field_nums = list(
        set(
            [
                ds_anno.subject_field.field_num 
                for ds_anno in ds_anno_space_time_qs
            ]
        )
    )
    field_nums += list(
        set(
            [
                ds_anno.event_field.field_num 
                for ds_anno in ds_anno_space_time_qs
                if ds_anno.event_field
            ]
        )
    )
    field_nums += [
        ds_anno.object_field.field_num 
        for ds_anno in ds_anno_space_time_qs
    ]
    return field_nums


def get_space_time_df(ds_source, limit_field_num_list=None):
    """Gets a dataframe relevant to spatial containment"""
    if not limit_field_num_list:
        ds_anno_space_time_qs = get_space_time_annotation_qs(ds_source)
        limit_field_num_list = get_space_time_field_num_list(ds_anno_space_time_qs)

    df = etl_df.db_make_dataframe_from_etl_data_source(
        ds_source, 
        include_uuid_cols=True,
        include_error_cols=True,
        limit_field_num_list=limit_field_num_list,
    )
    return df


def reconcile_space_time_event(
    subj_ds_field, 
    df, 
    event_obj=None, 
    event_field=None, 
    filter_index=None
):
    """Reconciles a spacetime event."""

    if event_obj is None and event_field is None:
        # We shouldn't be in this state of no event nodes.
        return df

    # NOTE: We do NOT attempt entity reconciliation on the entities in the
    # subj_ds_field. Items in this field must be ALREADY reconciled.
    subj_uuid_col = f'{subj_ds_field.field_num}_item'

    # Check to make sure we've already reconciled these times.
    if df[~df[subj_uuid_col].isnull()].empty:
        # The subject column is empty, so nothing to associate to 
        # space-time objects. Skip out.
        return df
    
    if filter_index is None:
        filter_index = df['row_num'] >= 0
    
    # geo_specificity is an integer that gives a sense about the level of
    # accuracy given in providing geospatial data. If we intend to obfuscate
    # geo data, then the geo_specificity would be a negative integer.
    # NOTE: This defaults to None, and that's OK.
    if event_obj:
        meta_json = event_obj.meta_json
        all_event_uuid = str(event_obj.uuid)
        event_uuid_col = None
    else:
        meta_json = event_field.meta_json
        event_uuid_col = f'{event_field.field_num}_item'

    geo_specificity = meta_json.get(
        # Check if the event has geo_specificity indicated.
        'geo_specificity',
        # If not, the second fallback is the sub_ds_field.meta_json
        subj_ds_field.meta_json.get(
            # Check first if the subject of the geo data has geo_specificity set.
            'geo_specificity',
            # As a fallback, check to see if the project has geo_specificity set.
            subj_ds_field.data_source.project.meta_json.get('geo_specificity')
        )
    )

    # Now get annotations for the space time related fields assoctiated
    # with the subj_ds_field and event.
    space_time_fields = {}
    for space_time_type in SPACE_TIME_ITEM_TYPES:
        ds_anno = DataSourceAnnotation.objects.filter(
            subject_field=subj_ds_field,
            predicate_id=configs.PREDICATE_OC_ETL_DESCRIBED_BY,
            event=event_obj,
            event_field=event_field,
            object_field__item_type=space_time_type,
        ).first()
        if not ds_anno:
            continue
        space_time_fields[space_time_type] = ds_anno.object_field
    
    for subject_uuid in df[filter_index][subj_uuid_col].unique():
        if not subject_uuid:
            continue
        subject_index = df[subj_uuid_col] == subject_uuid
        if df[subject_index].empty:
            # We have no data for this subject, so skip out.
            continue
        row_num = df[subject_index]['row_num'].iloc[0]
        if event_uuid_col:
            # Get the event uuid from this already reconciled event field.
            event_uuid = df[subject_index][event_uuid_col].iloc[0]
        else:
            event_uuid = all_event_uuid
        if not event_uuid:
            event_uuid = configs.DEFAULT_EVENT_UUID
        
        geometry_type = None
        act_event_dict = {
            'publisher': subj_ds_field.data_source.publisher,
            'project': subj_ds_field.data_source.project,
            'source_id': subj_ds_field.data_source.source_id,
            'item_id': subject_uuid,
            'event_id': event_uuid,
        }
        for space_time_type, sp_t_field in space_time_fields.items():
            sp_t_col = f'{sp_t_field.field_num}_col'
            raw_val = df[subject_index][sp_t_col].iloc[0]
            validated_val = etl_utils.validate_transform_data_type_value(
                raw_val, 
                sp_t_field.data_type
            )
            if (space_time_type == 'longitude'
                and not AllSpaceTime().validate_longitude(validated_val)):
                logger.info(
                    f'Row {row_num}, field {sp_t_field.field_num} has invalid longitude'
                )
                validated_val = None
            elif (space_time_type == 'latitude'
                and not AllSpaceTime().validate_latitude(validated_val)):
                logger.info(
                    f'Row {row_num}, field {sp_t_field.field_num} has invalid latitude'
                )
                validated_val = None
                
            if space_time_type != 'geometry':
                # No further processing and validation to do with
                # non-geometry space time attributes
                act_event_dict[space_time_type] = validated_val
                continue
            try:
                geo_dict = json.loads(raw_val)
            except:
                geo_dict = None
            if not geo_dict:
                logger.info(
                    f'Row {row_num}, field {sp_t_field.field_num} has invalid JSON'
                )
                continue
            if geo_dict.get('geometry'):
                # We have a GeoJSON feature object, so grab the geometry part
                geo_dict = geo_dict.get('geometry')
            if not geo_dict.get('coordinates'):
                logger.info(
                    f'Row {row_num}, field {sp_t_field.field_num} '
                    f'geometry must have coordinates listed.'
                )
                continue
            geometry_type = geo_dict.get('type')
            if geometry_type not in AllSpaceTime.GEOMETRY_TYPES:
                logger.info(
                    f'Row {row_num}, field {sp_t_field.field_num} '
                    f'geometry type must be in {str(AllSpaceTime.GEOMETRY_TYPES)}'
                )
                continue
            # OK, at this point our validation checks have passed.
            act_event_dict[space_time_type] = geo_dict
        
        if (geometry_type is None
            and act_event_dict.get('longitude') 
            and act_event_dict.get('latitude')):
            # We have valid longitude, latitude coordinates but no geometry so
            # make this a point
            geometry_type = 'Point'

        # Add geo-specificity if we have a geometry we want to add.
        act_event_dict['geometry_type'] = geometry_type
        if geometry_type:
            act_event_dict['geo_specificity'] = geo_specificity

        # Check to see if we already imported this same space time entity,
        # ignoring the geometry dict
        filter_dict = {
            k:v 
            for k, v in act_event_dict.items() 
            if k not in ['geometry', 'geo_specificity']
        }
        space_time_obj = AllSpaceTime.objects.filter(**filter_dict).first()
        if space_time_obj:
            # OK this already exists, so skip and don't change the database
            continue

        uuid_kargs = {k:act_event_dict.get(k) for k in SPACE_TIME_ID_ATTRIBUTES}
        uuid = AllSpaceTime().primary_key_create(**uuid_kargs)
        act_event_dict['uuid'] = uuid
        act_event_dict['created'] = timezone.now()
        if False:
            act_event_dict['created'] = pytz.timezone(settings.TIME_ZONE).localize(
                timezone.now(), 
                is_dst=None
            )
        # OK. Try to create the new space time event for this item.
        try:
            space_time_obj = AllSpaceTime(**act_event_dict)
            space_time_obj.save()
        except Exception as e:
            space_time_obj = None
            if hasattr(e, 'message'):
                error = e.message
            else:
                error = str(e)
            error_message = (
                f'Failed to create space time object at row {row_num}, field {subj_ds_field.label} '
                f'Error: {str(error)}'
            )
            logger.info(error_message)
            print(error_message)
        
    return df


def import_subj_ds_field_space_time(subj_ds_field, df, filter_index=None):
    """Reconciles space-time event objects associated with subj_ds_field"""

    anno_qs = DataSourceAnnotation.objects.filter(
        subject_field=subj_ds_field,
        predicate_id=configs.PREDICATE_OC_ETL_DESCRIBED_BY,
        object_field__item_type__in=SPACE_TIME_ITEM_TYPES,
    )

    event_objs = list(
        set(
            [
                ds_anno.event
                for ds_anno in anno_qs
                if ds_anno.event 
            ]
        )
    )
    event_fields = list(
        set(
            [
                ds_anno.event_field
                for ds_anno in anno_qs
                if ds_anno.event_field 
            ]
        )
    )

    if filter_index is None:
        filter_index = df['row_num'] >= 0

    for event_obj in event_objs:
        print(f'Adding space time to field {subj_ds_field.label}, event {event_obj.label}')
        df = reconcile_space_time_event(
            subj_ds_field, 
            df, 
            event_obj=event_obj, 
            event_field=None,
            filter_index=filter_index,
        )
    
    for event_field in event_fields:
        df = reconcile_space_time_event(
            subj_ds_field, 
            df, 
            event_obj=None, 
            event_field=event_field,
            filter_index=filter_index,
        )
    
    return df


def reconcile_space_time(ds_source, df=None, filter_index=None):
    """Reconciles and imports space-time objects from a data_source"""

    # NOTE: This needs to be executed AFTER the subject_field items
    # have already been reconciled. This function assumes that those
    # fields have already been imported / reconciled.

    space_time_anno_qs = get_space_time_annotation_qs(ds_source)

    if not len(space_time_anno_qs):
        # We have no space time annotations. Skip out.
        return df

    if df is None:
        df = get_space_time_df(ds_source)
    
    if df is None:
        # We have no dataframe of space-time data
        # to reconcile.
        return None
    
    if filter_index is None:
        # No filter index set, so process the whole dataframe df
        filter_index = df['row_num'] >= 0
    
    # Get the unique subject fields (the entities that get space-time
    # objects associated with them).
    subject_item_fields = list(
        set(
            [
                ds_anno.subject_field
                for ds_anno in space_time_anno_qs
            ]
        )
    )

    for subj_ds_field in subject_item_fields:
        df = import_subj_ds_field_space_time(
            subj_ds_field, 
            df,
            filter_index=filter_index,
        )
    
    return df