import logging

import numpy as np
import pandas as pd



from opencontext_py.apps.etl.importer.models import (
    DataSourceField,
)
from opencontext_py.apps.etl.importer import df as etl_df
from opencontext_py.apps.etl.importer.transforms import reconcile


logger = logging.getLogger("etl-importer-logger")

# ---------------------------------------------------------------------
# NOTE: These functions manage the transformations for general
# NAMED ENTITIES ('persons', 'documents', etc.) 
# ---------------------------------------------------------------------

# The following item_types require more specialized processing
# for entity reconciliation and ingest. These following types are
# therefore excluded from these functions.
EXCLUDE_FROM_GENERAL_ITEM_TYPES = [
    'subjects',
    'media',
    'resources',
    'predicates',
    'types',
    'variables',
    'values',
]


def get_general_named_entities_df(ds_source):
    """Makes a data frame with predicate, types, variables, fields"""
    fields_qs = DataSourceField.objects.filter(
        data_source=ds_source,
    ).exclude(
        item_type__in=EXCLUDE_FROM_GENERAL_ITEM_TYPES,
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


def reconcile_general_named_entities(ds_source, df=None, filter_index=None):
    """Reconciles all item_type='predicates' and 'types' fields in a data_source"""
    if df is None:
        # We get the dataframe of general named entity fields.
        df = get_general_named_entities_df(ds_source)

    if df is None:
        # We have no general entity fields
        return None
    
    if filter_index is None:
        # No filter index set, so process the whole dataframe df
        filter_index = df['row_num'] >= 0
    
    # Iterate through all of the general named entity fields to
    # reconcile and create named entities.
    fields_qs = DataSourceField.objects.filter(
        data_source=ds_source,
        data_type='id',
    ).exclude(
        item_type__in=EXCLUDE_FROM_GENERAL_ITEM_TYPES,
    )
    for ds_field in fields_qs:
        df = reconcile.df_reconcile_id_field(
            df=df,
            ds_field=ds_field,
            do_recursive=False,
            filter_index=filter_index,
        )
    return df

