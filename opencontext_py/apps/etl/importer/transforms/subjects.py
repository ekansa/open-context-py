import logging

import numpy as np
import pandas as pd


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)

from opencontext_py.apps.etl.importer.models import (
    DataSourceField,
    DataSourceAnnotation,
    get_immediate_context_parent_obj_db,
)
from opencontext_py.apps.etl.importer import df as etl_df
from opencontext_py.apps.etl.importer.transforms import reconcile
from opencontext_py.apps.etl.importer.transforms import utilities as trans_utils


logger = logging.getLogger("etl-importer-logger")

# ---------------------------------------------------------------------
# NOTE: These functions manage the transformations of item_type
# subjects items
# ---------------------------------------------------------------------
def get_containment_annotation_qs(ds_source):
    """Gets a queryset for containment annotations for this data source"""
    return DataSourceAnnotation.objects.filter(
        data_source=ds_source,
        subject_field__item_type='subjects',
        predicate_id=configs.PREDICATE_CONTAINS_UUID,
        object_field__item_type='subjects',
    )


def get_ds_fields_in_containment(ds_source):
    """Gets a list of data sources fields in spatial containment relations"""
    contain_anno_qs = get_containment_annotation_qs(ds_source)
    # Make a list of the unique spatial containment fields.
    contain_fields = []
    for anno in contain_anno_qs:
        for field in [anno.subject_field, anno.object_field]:
            if field in contain_fields:
                continue
            contain_fields.append(field)
    return contain_fields


def get_contain_and_non_containment_subject_fields(ds_source):
    """Gets data source fields for item_type='subjects' that are and are not in containment relations"""
    contain_paths = get_containment_fields_in_hierarchy(ds_source)
    # This makes a "flat list" of each item_type='subjects' field in
    # a containment hierarchy in order of most general (parent) fields
    # to more specific child fields.
    contain_fields = []
    for path in contain_paths:
        for ds_field in path:
            if ds_field in contain_fields:
                continue
            contain_fields.append(ds_field)
    
    contain_uuids = [f.uuid for f in contain_fields]

    non_contain_subj_fields_qs = DataSourceField.objects.filter(
        data_source=ds_source,
        item_type='subjects',
        data_type='id',
    ).exclude(uuid__in=contain_uuids)
    non_contain_fields = [f for f in non_contain_subj_fields_qs]
    return contain_fields, non_contain_fields


def get_containment_root_annotations(ds_source):
    """Gets the root (top of hierarchy) containment annotation"""
    contain_qs = get_containment_annotation_qs(ds_source)

    children_field_qs = contain_qs.order_by(
        'object_field_id'
    ).distinct(
        'object_field'
    ).values_list('object_field', flat=True)

    root_contain_anno_qs = contain_qs.exclude(
        # The root is not the object of the another
        # containment annotation so exclude children fields
        # from the subject field.
        subject_field__in=children_field_qs
    )
    return root_contain_anno_qs


def get_deepest_ds_fields(ds_source):
    """Gets the deepest (child fields that are not parent fields)"""
    contain_qs = get_containment_annotation_qs(ds_source)

    children_field_qs = contain_qs.order_by(
        'object_field_id'
    ).distinct(
        'object_field'
    )

    deepest_fields = []
    for child_anno in children_field_qs:
        child_is_parent = contain_qs.filter(
            subject_field=child_anno.object_field
        ).first()
        if child_is_parent:
            continue
        deepest_fields.append(child_anno.object_field)
    return deepest_fields


def get_parent_fields_recursively(child_field_obj, path_items=None):
    """Gets the parents of a child_field by recursive database lookup"""
    if not path_items:
        path_items = []
    if not child_field_obj in path_items:
        path_items.append(child_field_obj)
    parent_field_obj = get_immediate_context_parent_obj_db(child_field_obj)
    if not parent_field_obj:
        return path_items
    path_items.append(parent_field_obj)
    return get_parent_fields_recursively(parent_field_obj, path_items)


def get_containment_fields_in_hierarchy(ds_source):
    """Gets containment fields in their hierarchy"""
    all_containment_paths = []
    for child_field in get_deepest_ds_fields(ds_source):
        parent_list = get_parent_fields_recursively(child_field)
        # The parent order needs to be reversed to make the most
        # general first, followed by the most specific.
        parent_list.reverse()
        all_containment_paths.append(parent_list)
    return all_containment_paths


def get_containment_df(ds_source):
    """Gets a dataframe relevant to spatial containment"""
    contain_fields = get_ds_fields_in_containment(ds_source)
    # Make a list of the integer field numbers for these containment fields.
    limit_field_num_list = [f.field_num for f in contain_fields]
    df = etl_df.db_make_dataframe_from_etl_data_source(
        ds_source, 
        include_uuid_cols=True,
        include_error_cols=True,
        limit_field_num_list=limit_field_num_list,
    )
    return df


def get_item_type_subjects_df(ds_source, subj_fields_qs=None):
    """Gets a dataframe of item_type='subjects' fields"""
    if subj_fields_qs is None:
        subj_fields_qs = DataSourceField.objects.filter(
            data_source=ds_source,
            item_type='subjects',
            data_type='id',
        )
    if not len(subj_fields_qs):
        return None
    limit_field_num_list = [f.field_num for f in subj_fields_qs]
    df = etl_df.db_make_dataframe_from_etl_data_source(
        ds_source, 
        include_uuid_cols=True,
        include_error_cols=True,
        limit_field_num_list=limit_field_num_list,
    )
    return df


def make_containment_assertions_for_ds_field(df, ds_field, filter_index=None):
    """Makes containment relationships for reconciled items in a ds_field"""
    if filter_index is None:
        # No filter index set, so process the whole dataframe df
        filter_index = df['row_num'] >= 0

    col_context = f'{ds_field.field_num}_context'
    col_item =  f'{ds_field.field_num}_item'
    contexts = {}
    df_act = df[filter_index][[col_context, col_item]].copy()
    df_grp = df_act.groupby([col_context, col_item]).first().reset_index()

    assert_uuids = []
    unsaved_assert_objs = []
    for i, row in df_grp.iterrows():
        context_uuid = str(row[col_context])
        item_uuid = str(row[col_item])
        if not context_uuid or not item_uuid:
            # We are missing identifiers for one of the two entities
            # for an assertion relationship.
            continue
        context = contexts.get(context_uuid)
        if not context:
            context = AllManifest.objects.filter(
                uuid=context_uuid, 
                item_type='subjects',
            ).first()
        if context and not contexts.get(context_uuid):
            contexts[context_uuid] = context
        child_obj = AllManifest.objects.filter(
            uuid=item_uuid,
            item_type='subjects',
        ).first()
        if not context or not child_obj:
            continue
        assert_dict = {
            'project': ds_field.data_source.project,
            'publisher': ds_field.data_source.project.publisher,
            'source_id': ds_field.data_source.source_id,
            'subject': context,
            'predicate_id': configs.PREDICATE_CONTAINS_UUID,
            'object': child_obj,
        }

        assert_uuid = AllAssertion().primary_key_create(
            subject_id=assert_dict['subject'].uuid,
            predicate_id=assert_dict['predicate_id'],
            object_id=assert_dict['object'].uuid,
        )
        assert_uuids.append(assert_uuid)
        assert_dict['uuid'] = assert_uuid
        assert_obj = AllAssertion(**assert_dict)
        unsaved_assert_objs.append(assert_obj)

        # OK, we're now read to make an assertion relationship.
        logger.info(assert_obj)

    # Bulk save these assertions. This does a fallback to saving saving assertion
    # objects individually if something goes wrong, but that's far slower.
    trans_utils.bulk_create_assertions(
        assert_uuids, 
        unsaved_assert_objs
    )


def reconcile_item_type_subjects(ds_source, df=None, filter_index=None):
    """Reconciles all item_type='subjects' fields in a data_source"""
    if df is None:
        # We get the dataframe of subjects only fields.
        df = get_item_type_subjects_df(ds_source)

    if df is None:
        # We have no fields of item_type = 'subjects'
        # to reconcile.
        return None
    
    if filter_index is None:
        # No filter index set, so process the whole dataframe df
        filter_index = df['row_num'] >= 0
    
    contain_fields, non_contain_fields = get_contain_and_non_containment_subject_fields(ds_source)
    # First, reconcile the fields that DO NOT have spatial containment
    # relationships.
    for ds_field in non_contain_fields:
        df = reconcile.df_reconcile_id_field(
            df=df,
            ds_field=ds_field,
            do_recursive=False,
            filter_index=filter_index,
        )

    # Now process the fields that DO HAVE spatial containment hierarchy
    # relations, starting with the root fields first.
    # NOTE: We can have multiple root fields in one data_source, though
    # this will probably be rare.
    root_contain_anno_qs = get_containment_root_annotations(ds_source)
    for root_anno in root_contain_anno_qs:
        df = reconcile.df_reconcile_id_field(
            df=df,
            ds_field=root_anno.subject_field,
            do_recursive=True,
            filter_index=filter_index,
        )
    
    # Finally, make spatial containment assertions items in each of the fields
    # with containment relations. The contain_fields list should be in order
    # of bigest (most general) fields followed by more specific child fields.
    for ds_field in contain_fields:
        make_containment_assertions_for_ds_field(
            df, 
            ds_field,
            filter_index=filter_index,
        )

    return df

