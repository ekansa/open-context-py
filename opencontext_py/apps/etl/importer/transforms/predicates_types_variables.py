import json
import logging

import numpy as np
import pandas as pd

from django.db.models import Q

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
)

from opencontext_py.apps.etl.importer.models import (
    DataSource,
    DataSourceField,
    DataSourceRecord,
    DataSourceAnnotation,
    get_immediate_context_parent_obj_db,
    get_immediate_context_children_objs_db,
)
from opencontext_py.apps.etl.importer import df as etl_df
from opencontext_py.apps.etl.importer.transforms import reconcile


logger = logging.getLogger("etl-importer-logger")

# ---------------------------------------------------------------------
# NOTE: These functions manage the transformations for NAMED ENTITIES 
# of item_type 'predicates' and 'types', 
# ---------------------------------------------------------------------

def get_variable_paired_with_types_annotation_qs(ds_source):
    """Gets a queryset for variables paired with types, annotations for this data source"""
    # NOTE: We handle these kinds of annotations a lot like we handle
    # spatial hierarchy, because the each item_type == 'types' object
    # has an item_type == 'predicates' context. The df_field 'variables' 
    # is used to indicate that each record of the field should be reconciled
    # as a predicate, whereas normally the field_label is reconciled
    # as a predicate.
    return DataSourceAnnotation.objects.filter(
        data_source=ds_source,
        subject_field__item_type='variables',
        subject_field__data_type='id',
        predicate_id=configs.PREDICATE_RDFS_RANGE_UUID,
        object_field__item_type='types',
        object_field__data_type='id',
    )


def get_predicates_types_variables_df(ds_source):
    """Makes a data frame with predicate, types, variables, fields"""
    fields_qs = DataSourceField.objects.filter(
        data_source=ds_source,
        item_type__in=['predicates', 'types', 'variables'],
    )
    if not len(fields_qs):
        return None
    limit_field_num_list = [f.field_num for f in fields_qs]
    df = etl_df.db_make_dataframe_from_etl_data_source(
        ds_source, 
        include_uuid_cols=True,
        include_error_cols=True,
        limit_field_num_list=limit_field_num_list,
    )
    return df


def update_predicate_context_for_ds_field(ds_field, raise_on_error=True):
    """Updates a context object for ds_field types if one is not present"""
    if ds_field.item_type not in ['predicates', 'types']:
        # We're not changing anything that is not for
        # item_type = predicates or types.
        return ds_field
    
    if ds_field.context and ds_field.context.item_type == 'predicates':
        # This ds_field already has a context 
        # of item_type = 'predicates' as expected.
        return ds_field
    
    # If we try to reconcile records from an item_type 'types'
    # field, the context for these fields needs to be of 
    # item type = 'predicates'. 
    # To meet this requirement, we will reconcile the ds_field.label
    # among predicates for this project. If we succeed in getting or
    # making manifest object of item_type='predicates', then that will
    # serve as the So we will use the field's label to
    # obtain the predicate context.
    
    # Keep the actual item type, since for purposes of reconciliation
    # we will temporarily make this of type predicates.
    actual_item_type = ds_field.item_type
    ds_field.item_type = 'predicates'
    context, _, num_matching = reconcile.get_or_create_manifest_entity(
        ds_field, 
        context=ds_field.data_source.project, 
        raw_column_record=ds_field.label
    )
    if not context:
        # For some reason, we couldn't make a predicates item
        # from the ds_field.label.
        if not raise_on_error:
            return None
        raise ValueError(
            f'Reconcile failure for manifest predicate for field {ds_field.label} '
            f'(field_num: {ds_field.field_num}). Number matching: {num_matching}'
        )

    ds_field.item_type = actual_item_type
    ds_field.context = context
    ds_field.save()
    return ds_field


def reconcile_predicates_types_variables(ds_source, df=None, filter_index=None):
    """Reconciles all item_type='predicates' and 'types' fields in a data_source"""
    if df is None:
        # We get the dataframe of predicates and types only fields.
        df = get_predicates_types_variables_df(ds_source)

    if df is None:
        # We have no fields of item_type = 'predicates' or 'types'
        # to reconcile.
        return None
    
    if filter_index is None:
        # No filter index set, so process the whole dataframe df
        filter_index = df['row_num'] >= 0
    
    # Get the predicates and types that are paired with an rdfs:range 
    # annotation. For these paired predicates and types, the records
    # that become predicate objects will provide context to the associated
    # types records.
    vars_types_pairs_qs = get_variable_paired_with_types_annotation_qs(ds_source)
    for root_anno in vars_types_pairs_qs:
        ds_field = root_anno.subject_field
        # The row records inside an item_type = 'variables' ds_field
        # are for 'predicates', so make this ds_field have item_type = 'predicates'
        # for reconciliation purposes.
        # NOTE: we do_recursive here because the variable field is tied
        # to a types field. The variable field will have records reconciled
        # as predicates that will serve as contexts for the entities in the
        # types field.
        ds_field.item_type = 'predicates'
        df = reconcile.df_reconcile_id_field(
            df=df,
            ds_field=ds_field,
            do_recursive=True,
            filter_index=filter_index,
        )

    # Now get all the variables and types fields that are NOT
    # paired together and reconcile those.
    paired_field_uuids = []
    for anno in vars_types_pairs_qs:
        paired_field_uuids += [anno.subject_field.uuid, anno.object_field.uuid]
    
    # Now reconcile all of the record rows inside each ds_field of
    # item_type = 'variables' that are NOT paired with an item_type = 'types'
    # field. These ds_fields of item_type variable will be associated
    # with literal values imported later.
    literal_paired_var_fields_qs = DataSourceField.objects.filter(
        data_source=ds_source,
        item_type='variables',
    ).exclude(
        uuid__in=paired_field_uuids,
        data_type='id',
    )
    for ds_field in literal_paired_var_fields_qs:
        # The row records inside an item_type = 'variables' ds_field
        # are for 'predicates', so make this ds_field have item_type = 'predicates'
        # for reconciliation purposes.
        # NOTE: this is not recursive, because the variable fields will
        # be paired to literal values.
        ds_field.item_type = 'predicates'
        df = reconcile.df_reconcile_id_field(
            df=df,
            ds_field=ds_field,
            do_recursive=False,
            filter_index=filter_index,
        )

    non_paired_types_fields_qs = DataSourceField.objects.filter(
        data_source=ds_source,
        item_type='types',
    ).exclude(
        uuid__in=paired_field_uuids,
    )
    # Now, reconcile records from the types fields are not paired together.
    for ds_field in non_paired_types_fields_qs:
        # The following adds a manifest predicates object as a context
        # attribute to ds_field, if ds_field is of item_type = 'types' and
        # if the ds_field does not already have a predicate object as a
        # context. We do this because types must have predicates as contexts.
        ds_field = update_predicate_context_for_ds_field(ds_field)
        if not ds_field:
            # We somehow have a field that's a problem.
            continue
        df = reconcile.df_reconcile_id_field(
            df=df,
            ds_field=ds_field,
            context=ds_field.context,
            do_recursive=False,
            filter_index=filter_index,
        )
    
    # Finally, reconcile the field labels for predicates fields. In these
    # cases, the field_label is the thing that we will reconcile with the
    # database.
    pred_fields_qs = DataSourceField.objects.filter(
        data_source=ds_source,
        item_type='predicates',
    ).exclude(
        uuid__in=paired_field_uuids,
    )
    for ds_field in pred_fields_qs:
        # The following adds a manifest predicates object as a context
        # attribute to ds_field. This essentially imports new predicates
        # items from the field_label for this specific field.
        ds_field = update_predicate_context_for_ds_field(ds_field)
        # Now update the dataframe with the context
        col_context = f'{ds_field.field_num}_context'
        col = f'{ds_field.field_num}_col'
        update_index = filter_index & (~df[col].isnull() & ~(df[col] == ''))
        df.loc[update_index, col_context] = str(ds_field.context.uuid)
        for rows in etl_df.chunk_list(df[update_index]['row_num'].unique().tolist()):
            # Update the context and the item fields form this ds_field.
            # Storing these data will let us make assertions using this newly
            # reconciled predicate.
            DataSourceRecord.objects.filter(
                data_source=ds_field.data_source,
                field_num=ds_field.field_num,
                row_num__in=rows,
            ).update(
                context=ds_field.context,
            )

    return df

