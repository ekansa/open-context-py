import os
import hashlib
import time

import numpy as np
import pandas as pd

from django.db.models import OuterRef, Subquery

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

from opencontext_py.apps.all_items.representations import geojson

# ---------------------------------------------------------------------
# NOTE: These functions provide a means to export tabular data from
# Open Context. Open Context data is mainly organized in a graph,
# so exports to a matrix of tabular data requires some specialized
# processing. However, it is needed to make data easily consumable by
# wider audiences.
# ---------------------------------------------------------------------

"""
# testing

from opencontext_py.apps.all_items.editorial.tables import df as tabs_df

filter_args = {
    'subject__item_class__label__contains': 'Animal',
    'subject__path__contains': 'Italy',
}
exclude_args = {
    'subject__path__contains': 'Vescovado',
}
assert_qs = tabs_df.get_assert_qs(filter_args, exclude_args)
assert_df = tabs_df.get_raw_assertion_df(assert_qs)
df = tabs_df.prepare_df_from_assert_df(assert_df)
df = tabs_df.expand_context_path(df)

"""


# How many rows will we get in 1 database query?
DB_QS_CHUNK_SIZE = 100


def chunk_list(list_name, n=DB_QS_CHUNK_SIZE):
    """Breaks a long list into chunks of size n"""
    for i in range(0, len(list_name), n):
        yield list_name[i:i + n]


def get_assert_qs(filter_args, exclude_args=None):
    """Creates an assertion queryset"""
     # Limit this subquery to only 1 result, the first.
    thumbs_qs = AllResource.objects.filter(
        item=OuterRef('object'),
        resourcetype_id=configs.OC_RESOURCE_THUMBNAIL_UUID,
    ).values('uri')[:1]

    predicate_equiv_ld_qs = AllAssertion.objects.filter(
        subject=OuterRef('predicate'),
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        object__item_type__in=['class', 'property'],
        visible=True,
    ).exclude(
        object_id__in=[
            configs.PREDICATE_DCTERMS_CREATOR_UUID,
            configs.PREDICATE_DCTERMS_CONTRIBUTOR_UUID,
        ]
    ).select_related(
        'object'
    ).values('object')[:1]

    predicate_equiv_ld_label = predicate_equiv_ld_qs.values(
        'object__label'
    )[:1]
    predicate_equiv_ld_uri = predicate_equiv_ld_qs.values(
        'object__uri'
    )[:1]

    object_equiv_ld_qs = AllAssertion.objects.filter(
        subject=OuterRef('object'),
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        object__item_type__in=['class', 'property', 'uri'],
        visible=True,
    ).select_related(
        'object'
    ).values('object')[:1]
    
    object_equiv_ld_label = object_equiv_ld_qs.values(
        'object__label'
    )[:1]
    object_equiv_ld_uri = object_equiv_ld_qs.values(
        'object__uri'
    )[:1]

    # DC-Creator equivalent predicate
    dc_creator_qs = AllAssertion.objects.filter(
        subject=OuterRef('predicate'),
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        object_id=configs.PREDICATE_DCTERMS_CREATOR_UUID,
        visible=True,
    ).select_related(
        'object'
    ).values('object__label')[:1]

    # DC-Contributor equivalent predicate
    dc_contributor_qs = AllAssertion.objects.filter(
        subject=OuterRef('predicate'),
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        object_id=configs.PREDICATE_DCTERMS_CONTRIBUTOR_UUID,
        visible=True,
    ).select_related(
        'object'
    ).values('object__label')[:1]

    qs = AllAssertion.objects.filter(
        visible=True,
    ).exclude(
        predicate_id=configs.PREDICATE_CONTAINS_UUID,
    ).filter(**filter_args)
    
    if exclude_args:
        # Add optional exclude args
        qs = qs.exclude(**exclude_args)
    
    qs = qs.select_related(
        'subject'
    ).select_related(
        'subject__item_class'
    ).select_related(
        'subject__project'
    ).select_related(
        'subject__context'
    ).select_related(
        'observation'
    ).select_related(
        'event'
    ).select_related( 
        'attribute_group'
    ).select_related(
        'predicate'
    ).select_related(
        'language'
    ).select_related( 
        'object'
    ).select_related( 
        'object__context'
    ).annotate(
        object_thumbnail=Subquery(thumbs_qs)
    ).annotate(
        # This will indicate if a predicate is equivalent to a
        # dublin core creator label
        predicate_dc_creator=Subquery(dc_creator_qs)
    ).annotate(
        # This will indicate if a predicate is equivalent to a
        # dublin core contributor label
        predicate_dc_contributor=Subquery(dc_contributor_qs)
    ).annotate(
        # This will add labels of linked data equivalents to the predicate
        # of the assertion.
        predicate_equiv_ld_label=Subquery(predicate_equiv_ld_label)
    ).annotate(
        # This will add URIs of linked data equivalents to the predicate
        # of the assertion.
        predicate_equiv_ld_uri=Subquery(predicate_equiv_ld_uri)
    ).annotate(
        # This will add labels of linked data equivalents to the object
        # of the assertion.
        object_equiv_ld_label=Subquery(object_equiv_ld_label)
    ).annotate(
        # This will add URIs of linked data equivalents to the object
        # of the assertion.
        object_equiv_ld_uri=Subquery(object_equiv_ld_uri)
    )
    return qs


def get_raw_assertion_df(assert_qs):
    assert_qs = assert_qs.values(
        'subject_id',
        'subject__label',
        'subject__item_type',
        'subject__item_class__label',
        'subject__project__label',
        'subject__project__uri',
        'subject__path',
        'subject__sort',
        'subject__context__uri',
        'observation_id',
        'observation__label',
        'event_id',
        'event__label',
        'attribute_group_id',
        'attribute_group__label',
        'predicate_id',
        'predicate__label',
        'predicate__uri',
        'predicate__data_type',
        'sort',
        'language__uri',
        'language__label',
        'object__label',
        'object__item_type',
        'object__path',
        'object__uri',
        "obj_string",
        "obj_boolean",
        "obj_integer",
        "obj_double",
        "obj_datetime",
        "object_thumbnail",
        "predicate_dc_creator",
        "predicate_dc_contributor",
        "predicate_equiv_ld_label",
        "predicate_equiv_ld_uri",
        "object_equiv_ld_label",
        "object_equiv_ld_uri",
    )
    assert_df = pd.DataFrame.from_records(assert_qs)
    return assert_df


def expand_context_path(
    df, 
    path_col_prefix='subject', 
    path_delim='/', 
    result_col_prefix='context', 
    result_col_delim='___',
):
    """Expand a dataframe context path column into several columns

    :param DataFrame df: The dataframe with context path column to
        expand.
    :param str path_col_prefix: The Django model attribute prefix
        for the particular path column and related label column
        that we're trying to expand.
    :param str path_delim: The delimiter string for seperating
        different parts of the context in the context path.
    :param str result_col_prefix: The prefix for the resulting
        expanded columns of contexts
    :param str result_col_delim: A delimiter between the context
        column prefix and the context hierarchy level part of
        the expanded column names.
    """
    label_col = f'{path_col_prefix}__label'
    path_col = f'{path_col_prefix}__path'
    if not label_col in df.columns or not path_col in df.columns:
        # This doesn't exist in this dataframe
        return df

    # NOTE: This is a vectorized (hopefully fast) way of splitting
    # a context path string column into several columns.
    # This also removes the last part of the context path which
    # if it is the same as the item label.
    p_delim_count_col = f'{path_col}__levels'
    df[p_delim_count_col] = df[path_col].str.count('/')

    df_p = df[path_col].str.split(
        '/',
        expand=True,
    ).rename(
        columns=(lambda x: f"{result_col_prefix}{result_col_delim}{x+1}")
    )

    # Merge in our newly seperated context path columns
    df = df.merge(
        df_p,
        left_index=True,
        right_index=True,
    )

    # Now for some cleanup. Remove the last context path label if
    # that label is the same as the item label in the label_col.
    # This makes sure we're only providing columns with the path
    # of the PARENT item, not the item in the label_col.
    for delim_count in df[p_delim_count_col].unique():
        last_col = f"{result_col_prefix}{result_col_delim}{delim_count + 1}"
        if not last_col in df.columns:
            continue
        label_last_index = (
            (df[p_delim_count_col] == delim_count)
            & (df[label_col] == df[last_col])
        )
        # Remove the last context value if it is the same as the
        # item label.
        df.loc[label_last_index, last_col] = np.nan
        # Now check if this column is completely empty. Drop if
        # it is.
        col_not_null = ~df[last_col].isnull()
        if df[col_not_null].empty:
            # Drop the empty column.
            df.drop(columns=[last_col], inplace=True,)
    
    df.drop(columns=[p_delim_count_col], inplace=True, errors='ignore')

    return df

def prepare_df_from_assert_df(assert_df):
    """Prepares a (final) dataframe from the assert df"""
    df = assert_df[
        [
            'subject_id',
            'subject__label',
            'subject__item_type',
            'subject__item_class__label',
            'subject__project__label',
            'subject__project__uri',
            'subject__path',
            'subject__sort',
            'subject__context__uri',
        ]
    ].groupby(by=['subject_id']).first().reset_index()
    return df
