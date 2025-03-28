import uuid as GenUUID

import numpy as np
import pandas as pd

from django.db.models import Q, OuterRef, Subquery
from django.core.paginator import Paginator


from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.defaults import (
    DEFAULT_MANIFESTS,
)
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

from opencontext_py.apps.all_items.representations.item import (
    add_select_related_contexts_to_qs
)

from opencontext_py.apps.all_items.editorial.tables.ui_utilities import check_set_project_inventory

# ---------------------------------------------------------------------
# NOTE: These functions provide a means to export tabular data from
# Open Context. Open Context data is mainly organized in a graph,
# so exports to a matrix of tabular data requires some specialized
# processing. However, it is needed to make data easily consumable by
# wider audiences.
# ---------------------------------------------------------------------

"""
# testing

import importlib
from opencontext_py.apps.all_items.editorial.tables import create_df
importlib.reload(create_df)
importlib.reload(cloud_utilities)

filter_args = {
    'subject__item_class__label__contains': 'Object',
    'subject__path__contains': 'Italy',
}

filter_args = {
    'subject__item_class__label__contains': 'Animal',
    'subject__path__contains': 'Italy',
}
exclude_args = {
    'predicate__label': 'Links',
}

filter_args = {
    'subject__item_type': 'subjects',
    'subject__project_id': 'e682f907-6e4a-44cc-8a5f-3e2c73001673',
}
exclude_args = None


df, df_ns = create_df.make_clean_export_df(filter_args, exclude_args=exclude_args)


assert_qs = create_df.get_assert_qs(filter_args, exclude_args)
assert_df = create_df.get_raw_assertion_df(assert_qs)

df = create_df.prepare_df_from_assert_df(assert_df)


df = create_df.add_authors_to_df(df, assert_df)

df = create_df.add_spacetime_to_df(df)
df = create_df.expand_context_path(df)

df = create_df.add_df_linked_data_from_assert_df(df, assert_df)

preds_df = create_df.get_sort_preds_df(assert_df)

df = create_df.add_attribute_data_to_df(df, assert_df)

"""

# How many rows will we get in 1 database query?
DB_QS_CHUNK_SIZE = 100

# Make a list of default Manifest objects for which we prohibit
# edits.
DEFAULT_UUIDS = [m.get('uuid') for m in DEFAULT_MANIFESTS if m.get('uuid')]


# List of tuples that associate a literal data type with the
# object column that has values for that data type
LITERAL_DATA_TYPE_COL_TUPS = [
    ('xsd:string', 'obj_string', ),
    ('xsd:boolean', 'obj_boolean', ),
    ('xsd:integer', 'obj_integer', ),
    ('xsd:double', 'obj_double', ),
    ('xsd:date', 'obj_datetime', ),
]

PRED_DATA_TYPE_COLS = {dt: (col, None,) for dt, col in LITERAL_DATA_TYPE_COL_TUPS}
PRED_DATA_TYPE_COLS['id'] = ('object__label', 'object__uri',)


DC_AUTHOR_ROLES_TUPS = [
    (configs.PREDICATE_DCTERMS_CONTRIBUTOR_UUID, 'dc_contributor'),
    (configs.PREDICATE_DCTERMS_CREATOR_UUID, 'dc_creator'),
]

DC_AUTHOR_ROLES_DICT = {k:v for k,v in DC_AUTHOR_ROLES_TUPS}



# Delimiter between different 'nodes' that may contain predicates in assertions.
DEFAULT_NODE_DELIM = '::'

# Config for making predicates within nodes have unique labels.
NODE_PRED_UNIQUE_PREDFIXING = [
    # ('observation_id', configs.DEFAULT_OBS_UUID, 'observation__label', DEFAULT_NODE_DELIM,),
    ('event_id', configs.DEFAULT_EVENT_UUID, 'event__label', DEFAULT_NODE_DELIM,),
    ('attribute_group_id', configs.DEFAULT_ATTRIBUTE_GROUP_UUID, 'attribute_group__label', DEFAULT_NODE_DELIM,),
]

# Multivalue attributes get mushed together into lists when
# we make an export table. This sets a delimiter between different
# values of these lists.
DEFAULT_LIST_JOIN_DELIM = ' +++ '

# This makes sure we don't have confusion, where our multi-value
# delimiter is inside an individual value.
DEFAULT_DELIM_ELEMENT_REPLACE = '--'

DEFAULT_DROP_COLS = [
    'subject_id',
    'subject__project_id',
    'project_id',
    'subject__item_type',
    'subject__sort',
    'subject__revised',
    'subject__path',
    'dc_creator_id',
    'dc_creator_label',
    'dc_contributor_id',
    'dc_contributor_label',
    'item__geometry_type',
]

CONTEXT_COL_RENAMES = {f'context___{i}': f'Context ({i})' for i in range(1, 30)}

DEFAULT_COL_RENAMES = {
    'subject__uri': 'Item URI',
    'subject__label': 'Item Label',
    'persistent_doi': 'Persistent ID (DOI)',
    'persistent_ark': 'Persistent ID (ARK)',
    'persistent_orcid': 'Identifier (ORCID)',
    'subject__item_class__label': 'Item Category',
    'subject__project__label': 'Project Label',
    'subject__project__uri': 'Project URI',
    'authors': 'Authors and Contributors',
    'subject__context__uri': 'Item Context URI',
    'subject__published': 'Item Published Date',
    'subject__revised': 'Item Revised Date',
    'item__latitude': 'Latitude (WGS-84)',
    'item__longitude': 'Longitude (WGS-84)',
    'item__geo_specificity': 'Geospatial Note',
    'item__geo_source': 'Geospatial Inference',
    'item__earliest': 'Earliest Year (-BCE/+CE)',
    'item__latest': 'Latest Year (-BCE/+CE)',
    'item__chrono_source': 'Chronology Inference',
}

MAX_CELL_STRING_LENGTH = 1500


def chunk_list(list_name, n=DB_QS_CHUNK_SIZE):
    """Breaks a long list into chunks of size n"""
    for i in range(0, len(list_name), n):
        yield list_name[i:i + n]


def get_manifest_qs(
    filter_args, 
    exclude_args=None):
    """Creates an manifest queryset. We may want to use this to
    add records of manifest items that otherwise lack description in
    the assertions table.

    :param dict filter_args: A dictionary of filter arguments
        needed to filter the AllAssertion model to make
        the AllAssertion queryset used to generate the
        output dataframe.
    :param dict exclude_args: An optional dict of exclude
        arguments to with exclusion criteria for the
        AllAssertion model to make the AllAssertion queryset
        used to generate the output dataframe.
    """
    # Get the 3 major ID schemes we would want to
    # export.
    doi_qs = AllIdentifier.objects.filter(
        item_id=OuterRef('uuid'),
        scheme='doi',
    ).values('id')[:1]

    ark_qs = AllIdentifier.objects.filter(
        item_id=OuterRef('uuid'),
        scheme='ark',
    ).values('id')[:1]

    orcid_qs = AllIdentifier.objects.filter(
        item_id=OuterRef('uuid'),
        scheme='orcid',
    ).values('id')[:1]

    qs = AllManifest.objects.all().filter(**filter_args)

    if exclude_args:
        if isinstance(exclude_args, dict):
            # Add optional exclude args
            qs = qs.exclude(**exclude_args)
        else:
            qs = qs.exclude(exclude_args)

    # Add lots of select related objects so we don't
    # need to do many, many, many future queries.
    qs = qs.select_related(
        'item_class'
    ).select_related(
        'project'
    ).select_related(
        'context'
    )

    # Now add annotations to the query set.
    qs = qs.annotate(
        # Add DOI identifiers to subject items, if they exist
        persistent_doi=Subquery(doi_qs)
    ).annotate(
        # Add ARK identifiers to subject items, if they exist
        persistent_ark=Subquery(ark_qs)
    ).annotate(
        # Add ORCID identifiers to subject items, if they exist
        persistent_orcid=Subquery(orcid_qs)
    )
    qs = qs.order_by(
        'sort',
        'path',
        'label',
    )
    return qs


def get_assert_qs(
    filter_args, 
    exclude_args=None):
    """Creates an assertion queryset

    :param dict filter_args: A dictionary of filter arguments
        needed to filter the AllAssertion model to make
        the AllAssertion queryset used to generate the
        output dataframe.
    :param dict exclude_args: An optional dict of exclude
        arguments to with exclusion criteria for the
        AllAssertion model to make the AllAssertion queryset
        used to generate the output dataframe.
    """
     # Limit this subquery to only 1 result, the first.
    thumbs_qs = AllResource.objects.filter(
        item=OuterRef('object'),
        resourcetype_id=configs.OC_RESOURCE_THUMBNAIL_UUID,
    ).values('uri')[:1]

    # Get the 3 major ID schemes we would want to
    # export.
    doi_qs = AllIdentifier.objects.filter(
        item=OuterRef('subject'),
        scheme='doi',
    ).values('id')[:1]

    ark_qs = AllIdentifier.objects.filter(
        item=OuterRef('subject'),
        scheme='ark',
    ).values('id')[:1]

    orcid_qs = AllIdentifier.objects.filter(
        item=OuterRef('subject'),
        scheme='orcid',
    ).values('id')[:1]


    predicate_equiv_ld_qs = AllAssertion.objects.filter(
        subject=OuterRef('predicate'),
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        object__item_type__in=['class', 'property', 'uri',],
        visible=True,
    ).filter(
        Q(object__meta_json__deprecated__isnull=True)
        |Q(object__meta_json__deprecated=False)
    ).filter(
        Q(object__context__meta_json__deprecated__isnull=True)
        |Q(object__context__meta_json__deprecated=False)
    ).exclude(
        object_id__in=[
            configs.PREDICATE_DCTERMS_CREATOR_UUID,
            configs.PREDICATE_DCTERMS_CONTRIBUTOR_UUID,
        ]
    ).select_related(
        'object'
    ).order_by(
        'sort'
    ).values('object')[:1]

    predicate_equiv_ld_label = predicate_equiv_ld_qs.values(
        'object__label'
    )[:1]
    predicate_equiv_ld_uri = predicate_equiv_ld_qs.values(
        'object__uri'
    )[:1]

    qs = AllAssertion.objects.filter(
        visible=True,
    ).exclude(
        predicate_id=configs.PREDICATE_CONTAINS_UUID,
    ).filter(**filter_args)

    if exclude_args:
        if isinstance(exclude_args, dict):
            # Add optional exclude args
            qs = qs.exclude(**exclude_args)
        else:
            qs = qs.exclude(exclude_args)

    # Add lots of select related objects so we don't
    # need to do many, many, many future queries.
    qs = qs.select_related(
        'subject'
    ).select_related(
        'subject__item_class'
    ).select_related(
        'subject__project'
    ).select_related(
        'subject__context'
    ).select_related(
        'project'
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
    )

    # Now add annotations to the query set.
    qs = qs.annotate(
        object_thumbnail=Subquery(thumbs_qs)
    ).annotate(
        # Add DOI identifiers to subject items, if they exist
        persistent_doi=Subquery(doi_qs)
    ).annotate(
        # Add ARK identifiers to subject items, if they exist
        persistent_ark=Subquery(ark_qs)
    ).annotate(
        # Add ORCID identifiers to subject items, if they exist
        persistent_orcid=Subquery(orcid_qs)
    ).annotate(
        # This will add labels of linked data equivalents to the predicate
        # of the assertion.
        predicate_equiv_ld_label=Subquery(predicate_equiv_ld_label)
    ).annotate(
        # This will add URIs of linked data equivalents to the predicate
        # of the assertion.
        predicate_equiv_ld_uri=Subquery(predicate_equiv_ld_uri)
    )
    qs = qs.order_by(
        'subject__sort',
        'obs_sort',
        'event_sort',
        'attribute_group_sort',
        'sort',
    )
    return qs


def add_prefix_to_uri_col_values(
    act_df,
    suffixes_uri_col=['_uri'],
    prefix_uris='https://'
):
    """Adds a prefix to URIs in columns that end with a uri col suffix

    :param DataFrame act_df: The dataframe that will get prefixes
       on URI columns
    :param list suffixes_uri_col: A list of suffixes that indicate a
       column has URIs that need prefixes
    :param str prefix_uris: The URI prefix to add to URI values.
    """
    if not prefix_uris or act_df is None or act_df.empty:
        # We're not wanting to change anything
        return act_df

    for col in act_df.columns:
        suffix_found = False
        for col_suffix in suffixes_uri_col:
            if col.endswith(col_suffix):
                suffix_found = True
        if not suffix_found:
            continue
        # This makes sure we only add the prefix to non-blank rows
        # that don't already have that prefix.
        col_index = (
            ~act_df[col].isnull()
            & ~act_df[col].str.startswith(prefix_uris, na=False)
        )
        act_df.loc[col_index, col] = prefix_uris + act_df[col_index][col]
    return act_df


def make_urls_from_persistent_ids(act_df, prefix_uris='https://'):
    """Make URLs from persistent ids for a dataframe

    :param DataFrame act_df: The dataframe we want to
       edit so persistent IDs become URLs.
    """
    cols_schemes = [
        ('persistent_doi', 'doi',),
        ('persistent_ark', 'ark',),
        ('persistent_orcid', 'orcid',),
    ]
    if act_df is None or act_df.empty:
        # Empty data, so change nothing.
        return act_df

    if not prefix_uris:
        prefix_uris = ''

    for col, scheme in cols_schemes:
        if col not in act_df.columns:
            # this column is missing, so skip
            continue
        conf = AllIdentifier.SCHEME_CONFIGS.get(scheme, {})
        url_root = conf.get('url_root')
        if not url_root:
            # We don't have a URL root configured for
            # this scheme
            continue

        prefix = prefix_uris + url_root
        col_index = (
            ~act_df[col].isnull()
            & ~act_df[col].str.startswith(prefix, na=False)
        )
        act_df.loc[col_index, col] = prefix + act_df[col_index][col]
    return act_df


def get_raw_manifest_df(man_qs, prefix_uris='https://', chunk_size=10000):
    """Makes a dataframe from a manifest queryset"""
    man_qs = man_qs.values(
        'uuid',
        '_uri',
        'label',
        'persistent_doi',
        'persistent_ark',
        'persistent_orcid',
        'item_type',
        'item_class__label',
        'project_id',
        'project__label',
        'project__uri',
        'path',
        'sort',
        'context__uri',
        'published',
        'revised',
    )
    paginator = Paginator(man_qs, chunk_size)
    man_df = pd.DataFrame(data={})
    for page_number in paginator.page_range:
        page = paginator.page(page_number)
        act_df = pd.DataFrame.from_records(page)
        man_df = pd.concat([man_df, act_df], ignore_index=True)

    man_df = add_prefix_to_uri_col_values(
        man_df,
        prefix_uris=prefix_uris,
    )
    man_df = make_urls_from_persistent_ids(
        man_df,
        prefix_uris=prefix_uris,
    )
    return man_df


def get_raw_assertion_df(
    assert_qs, 
    truncate_long_text=False, 
    prefix_uris='https://', 
    chunk_size=10000,
):
    """Makes a dataframe from an assertion queryset
    
    :param bool truncate_long_text: If true, truncate long strings of text

    """
    assert_qs = assert_qs.values(
        'subject_id',
        'subject__uri',
        'subject__label',
        'persistent_doi',
        'persistent_ark',
        'persistent_orcid',
        'subject__item_type',
        'subject__item_class__label',
        'subject__project_id',
        'subject__project__label',
        'subject__project__uri',
        'subject__path',
        'subject__sort',
        'subject__context__uri',
        'subject__published',
        'subject__revised',
        'project_id',
        'observation_id',
        'observation__label',
        'obs_sort',
        'event_id',
        'event__label',
        'event_sort',
        'attribute_group_id',
        'attribute_group__label',
        'attribute_group_sort',
        'predicate_id',
        'predicate__label',
        'predicate__uri',
        'predicate__data_type',
        'sort',
        'language__uri',
        'language__label',
        'object_id',
        'object__label',
        'object__item_type',
        'object__path',
        'object__uri',
        'obj_string',
        'obj_boolean',
        'obj_integer',
        'obj_double',
        'obj_datetime',
        'object_thumbnail',
        'predicate_equiv_ld_label',
        'predicate_equiv_ld_uri',
        'updated',
    )
    paginator = Paginator(assert_qs, chunk_size)
    assert_df = pd.DataFrame(data={})
    for page_number in paginator.page_range:
        page = paginator.page(page_number)
        act_df = pd.DataFrame.from_records(page)
        assert_df = pd.concat([assert_df, act_df], ignore_index=True)

    if 'obj_string' in assert_df.columns.tolist() and truncate_long_text:
        long_index = assert_df['obj_string'].str.len() > MAX_CELL_STRING_LENGTH 
        assert_df.loc[long_index, 'obj_string'] = assert_df[long_index]['obj_string'].str.slice(0, MAX_CELL_STRING_LENGTH)

    assert_df = add_prefix_to_uri_col_values(
        assert_df,
        prefix_uris=prefix_uris,
    )
    assert_df = make_urls_from_persistent_ids(
        assert_df,
        prefix_uris=prefix_uris,
    )
    return assert_df


def get_raw_assert_df_by_making_query(
    filter_args,
    exclude_args=None,
    prefix_uris='https://'
):
    """Makes a query on the AllAssertion model and related models

    :param dict filter_args: A dictionary of filter arguments
        needed to filter the AllAssertion model to make
        the AllAssertion queryset used to generate the
        output dataframe.
    :param dict exclude_args: An optional dict of exclude
        arguments to with exclusion criteria for the
        AllAssertion model to make the AllAssertion queryset
        used to generate the output dataframe.
    """
    # Make the AllAssertion queryset based on filter arguments
    # and optional exclusion critera.
    assert_qs = get_assert_qs(
        filter_args=filter_args,
        exclude_args=exclude_args
    )

    # Turn the AllAssertion queryset into a "tall" dataframe.
    # Each row is a row for an assertion, so there will be many
    # assertions possible for each subject of the assertions.
    return get_raw_assertion_df(assert_qs, prefix_uris=prefix_uris)


def combine_man_df_to_df_from_assert_df(df, man_df):
    """Combines a manifest dataframe with a dataframe of assertions

    :param DataFrame df: The dataframe of individual subject entities
    derived from the assert_df

    :param DataFrame man_df: The dataframe of individual manifest entities
    that must be included in the final result, even if they totally lack
    assertions
    """
    if man_df is None or man_df.empty:
        # Nothing to do here.
        return df
    col_rename_dict = {
        'uuid': 'subject_id',
        '_uri': 'subject__uri',
        'label': 'subject__label',
        'persistent_doi': 'persistent_doi',
        'persistent_ark': 'persistent_ark',
        'persistent_orcid': 'persistent_orcid',
        'item_type': 'subject__item_type',
        'item_class__label': 'subject__item_class__label',
        'project_id': 'subject__project_id',
        'project__label': 'subject__project__label',
        'project__uri': 'subject__project__uri',
        'path': 'subject__path',
        'sort': 'subject__sort',
        'context__uri': 'subject__context__uri',
        'published': 'subject__published',
        'revised': 'subject__revised',    
    }
    man_df.rename(columns=col_rename_dict, inplace=True)
    man_df['project_id'] = man_df['subject__project_id']
    ordered_cols = df.columns.tolist()
    reordered_cols = [c for c in ordered_cols if c in man_df.columns.tolist()]
    man_df = man_df[reordered_cols].copy()
    # Make an index of the subject_id column of rows that are not already
    # in the dataframe df.
    new_uuid_index = ~man_df['subject_id'].isin(df['subject_id'])
    print(f'Adding {len(man_df[new_uuid_index].index)} manifest records that lack assertions')
    df = pd.concat([df, man_df[new_uuid_index]], ignore_index=True)
    return df



def prepare_df_from_assert_df(assert_df, man_df=None):
    """Prepares a (final) dataframe from the assert df

    :param DataFrame assert_df: The dataframe of raw assertions and
        referenced attributes of foreign key referenced objects
    """
    act_assert_cols = [
        'subject_id',
        'subject__uri',
        'project_id',
        'subject__label',
        'persistent_doi',
        'persistent_ark',
        'persistent_orcid',
        'subject__item_type',
        'subject__item_class__label',
        'subject__project_id',
        'subject__project__label',
        'subject__project__uri',
        'subject__path',
        'subject__sort',
        'subject__context__uri',
        'subject__published',
        'subject__revised',
    ]
    for col in act_assert_cols:
        if col in assert_df.columns.tolist():
            continue
        assert_df[col] = None
    df = assert_df[
        act_assert_cols
    ].groupby(by=['subject_id']).first().reset_index()
    df.columns = df.columns.get_level_values(0)
    df = combine_man_df_to_df_from_assert_df(df, man_df)
    df.sort_values(
        by=['subject__sort', 'subject__path', 'subject__label'],
        inplace=True,
    )
    df.reset_index(drop=True, inplace=True)
    return df


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

    path_col_index = ~df[path_col].isnull()
    if df[path_col_index].empty:
        # All the paths are empty, so skip out
        return df

    # Remove any leading or trailing blanks
    df[path_col] = df[path_col].str.strip()
    df[path_col] = df[path_col].str.strip(path_delim)

    # NOTE: This is a vectorized (hopefully fast) way of splitting
    # a context path string column into several columns.
    # This also removes the last part of the context path which
    # if it is the same as the item label.
    p_delim_count_col = f'{path_col}__levels'
    df[p_delim_count_col] = df[path_col].str.count(path_delim)

    df_p = df[path_col].str.split(
        path_delim,
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
        df.loc[label_last_index, last_col] = None
        # Now check if this column is completely empty. Drop if
        # it is.
        col_not_null = ~df[last_col].isnull()
        if df[col_not_null].empty:
            # Drop the empty column.
            df.drop(columns=[last_col], inplace=True,)

    # Last little clean up of a column temporarily used for processing
    df.drop(columns=[p_delim_count_col], inplace=True, errors='ignore')
    return df


def get_context_hierarchy_df(uuids):
    """Make a dataframe of uuids and columns for their context hierarchy

    :param list uuids: A list or other iterator of UUIDs to get
        their contet hierarchy
    """
    man_qs = AllManifest.objects.filter(uuid__in=uuids)
    man_qs = add_select_related_contexts_to_qs(
        man_qs,
        context_prefix='',
        depth=10,
    )
    data_dicts = []
    for man_obj in man_qs:
        data = {
            'level_0': man_obj.uuid,
        }
        i = 0
        act_context = man_obj.context
        while (
            act_context.item_type == 'subjects'
            and str(act_context.uuid)
            not in configs.DEFAULT_SUBJECTS_ROOTS
        ):
            i += 1
            data[f'level_{i}'] = act_context.uuid
            act_context = act_context.context

        data_dicts.append(data)
    df_levels = pd.DataFrame(data=data_dicts)
    return df_levels


def get_spacetime_df(uuids):
    """Make a dataframe with spacetime columns for a list of uuids

    :param list uuids: A list or other iterator of UUIDs to get
        space time attributes for these OR THEIR context parents!
    """
    spacetime_qs = AllSpaceTime.objects.filter(
        item__in=uuids,
    ).select_related(
        'item'
    ).select_related(
        'project'
    ).select_related(
        'event'
    ).select_related(
        'event__item_class'
    ).values(
        'item_id',
        'item__label',
        'item__uri',
        'event__label',
        'event__item_class_id',
        'event__item_class__label',
        'latitude',
        'longitude',
        'earliest',
        'latest',
        'geometry_type',
        'geo_specificity',
        'project__meta_json',
    )
    spacetime_df = pd.DataFrame.from_records(spacetime_qs)
    return spacetime_df


def is_null(df_value):
    """Checks if a dataframe value is null"""
    if df_value is np.nan:
        return True
    if df_value is None:
        return True
    return False


def get_spacetime_from_context_levels(uuids, main_item_id_col='subject_id'):
    """Make a dataframe of spacetime columns found in a context hierarchy for
    a list of uuids

    :param list uuids: A list or other iterator of UUIDs to get
        space time attributes for these OR THEIR context parents!
    :param str main_item_id_col: The column name for the original
        uuids list.
    """

    # NOTE: Spatial and chronological information may be either
    # given for a given manifest item, or it may be inferred via
    # context relationships to parent items. This function assigns
    # spacetime attributes to a set of manifest item uuids, by
    # preferring spacetime atttributes directly assigned to those
    # manifest items, and if none are assigned, by looking for
    # spacetime attributes assigned to parent items in the context
    # hierarchy.
    #
    # This works according to this general approach:
    # 1. Make df_levels, where we make a dataframe of the
    #    uuids and columns labeled 'level_{x}' for parent
    #    contexts.
    # 2. Iterate through the level columns to assign
    #    spacetime attributes to rows. We go from the
    #    original uuids (level_0) first, then up the
    #    context hierarchy to fill in missing spacetime
    #    attribute values.

    df_levels = get_context_hierarchy_df(uuids)
    df_levels['item__latitude'] = None
    df_levels['item__longitude'] = None
    df_levels['item__geometry_type'] = None
    df_levels['item__geo_specificity'] = None
    df_levels['item__geo_source'] = None
    df_levels['item__earliest'] = None
    df_levels['item__latest'] = None
    df_levels['item__chrono_source'] = None
    spacetime_done = False
    level_exists = True
    level = -1
    while level_exists and not spacetime_done:
        level += 1
        level_col = f'level_{level}'
        if not level_col in df_levels.columns:
            # We've exhausted the context hierarchy in df_levels.
            level_exists = False
            break
        # Are we still missing spacetime data?
        missing_geo = (
            df_levels['item__latitude'].isnull()
            | df_levels['item__longitude'].isnull()
        )
        missing_time = (
            df_levels['item__earliest'].isnull()
            | df_levels['item__latest'].isnull()
        )
        missing_index = (missing_geo | missing_time)
        if df_levels[missing_index].empty:
            # All the space time data is filled,
            # so no need to query for spacetime objects.
            spacetime_done = True
            break
        # Now get spacetime objects for the
        # uuids at this level.
        ok_l = ~df_levels[level_col].isnull()
        spacetime_df = get_spacetime_df(
            uuids=df_levels[ok_l][level_col].unique().tolist()
        )
        if spacetime_df is None or spacetime_df.empty:
            # No data returned, so go to the next level.
            continue
        ok_sp = ~spacetime_df['item_id'].isnull()
        for uuid in spacetime_df[ok_sp]['item_id'].unique():
            l_uuid_index = df_levels[level_col] == uuid
            if df_levels[(l_uuid_index & missing_index)].empty:
                # This particular uuid has filled data,
                # so skip it.
                continue
            l_geo_index = (
                l_uuid_index & missing_geo
            )
            l_time_index = (
                l_uuid_index & missing_time
            )
            sp_uuid_index = spacetime_df['item_id'] == uuid
            process_tups = [
                (l_geo_index, 'latitude', 'longitude', True, 'geo'),
                (l_time_index, 'earliest', 'latest', False, 'chrono'),
            ]
            for l_index, x, y, geo_sp, t in process_tups:
                sp_index = (
                    sp_uuid_index
                    & ~spacetime_df[x].isnull()
                    & ~spacetime_df[y].isnull()
                )
                if spacetime_df[sp_index].empty:
                    continue
                if is_null(spacetime_df[sp_index][x].values[0]) or is_null(spacetime_df[sp_index][y].values[0]):
                    # Only make updates if we have non-null values to update with.
                    continue
                df_levels.loc[l_index, f'item__{x}'] = spacetime_df[sp_index][x].values[0]
                df_levels.loc[l_index, f'item__{y}'] = spacetime_df[sp_index][y].values[0]
                if geo_sp:
                    # First, add the type of geometry to this. Record. In the future, this will make it
                    # easier to output the output dataframe as GeoJSON, since will know which rows will
                    # have non-point geometries.
                    df_levels.loc[l_index, 'item__geometry_type'] = spacetime_df[sp_index]['geometry_type'].values[0]
                    # Go through some convoluted work to assign a geo_specificity value to
                    # these geo coordinates. We preferr values assigned directly to the item's
                    # own geospatial data, but as a backup, we look to project metadata where
                    # a project may have some level of geo_specificity indicated in its
                    # meta_json.
                    item_geo_spec = spacetime_df[sp_index]['geo_specificity'].values[0]
                    proj_meta = spacetime_df[sp_index]['project__meta_json'].values[0]
                    proj_geo_spec = proj_meta.get('geo_specificity', 0)
                    geo_specs = [s for s in [item_geo_spec, proj_geo_spec] if s is not None and s != 0]
                    if geo_specs:
                        # We have a geo_specificity value we can use. Now assign it.
                        df_levels.loc[l_index, 'item__geo_specificity'] = geo_specs[0]
                # Now share information about the source of this type of information.
                if level == 0:
                    df_levels.loc[l_index, f'item__{t}_source'] = 'Given for: ' + spacetime_df[sp_index]['item__label'].values[0]
                else:
                    df_levels.loc[l_index, f'item__{t}_source'] = 'Inferred from: ' + spacetime_df[sp_index]['item__label'].values[0]

    # Now some cleanup, get rid of all the context levels above level 0.
    level = 0
    level_cols = []
    level_exists = True
    while level_exists:
        level += 1
        level_col = f'level_{level}'
        if not level_col in df_levels.columns:
            level_exists = False
            break
        level_cols.append(level_col)
    df_levels.drop(columns=level_cols, inplace=True)

    # Now rename the main id column to make it easier
    # to join/merge with the main df.
    df_levels.rename(
        columns={'level_0': main_item_id_col},
        inplace=True
    )
    return df_levels


def add_spacetime_to_df(df):
    """Adds spacetime columns to a df

    :param DataFrame df: The main dataframe for the export we want to
        create
    """
    sp_index = (
        ~df['subject_id'].isnull()
        & df['subject__item_type'].isin(
            ['subjects', 'projects', ]
        )
    )
    chunks = chunk_list(
        df[sp_index]['subject_id'].unique().tolist(),
        n=5000,
    )
    df_spacetime_list = []
    for chunk_uuids in chunks:
        df_spacetime_chunk = get_spacetime_from_context_levels(chunk_uuids)
        df_spacetime_list.append(df_spacetime_chunk)

    if not len(df_spacetime_list):
        # No spacetime items to merge in.
        return df
    # Concatenate all of these chunked spacetime datasets
    df_spacetime = pd.concat(df_spacetime_list)
    # Add them to our main, glorious dataframe.
    df = df.merge(df_spacetime, left_on='subject_id', right_on='subject_id')
    return df


def get_df_entities_equiv_to_entity(subject_ids, equiv_entity_id, renames=None):
    """Get a dataframe of subject entities that are equivalent to another entity

    :param list subject_ids: List (or iterator) of entities that are
        the subject of an equivalence relationship (typically open context
        entities)
    :param str equiv_entity_id: UUID of the object of the equivalence relation
        (typically a linked data entity)
    """

    # NOTE: Use ths function if you know the linked data entity object
    # and want the subject entities that are equivalent to that linked
    # data object.

    qs = AllAssertion.objects.filter(
        subject_id__in=subject_ids,
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        object_id=equiv_entity_id,
        visible=True,
    ).distinct(
        'subject_id'
    ).order_by(
        'subject_id'
    ).values('subject_id')
    act_df =  pd.DataFrame.from_records(qs)
    if renames:
        act_df.rename(columns=renames, inplace=True)
    return act_df


def get_df_project_authors_for_role(
    project_ids,
    role_id=configs.PREDICATE_DCTERMS_CREATOR_UUID,
    roles_dict=DC_AUTHOR_ROLES_DICT,
):
    """Get a dataframe of project authors based on the uri of their role

    :param list project_ids: A list (or other iterator) of project ids.
    :param str role_id: The ID of the predicate for the authorship role
    """
    role = roles_dict.get(role_id)

    qs = AllAssertion.objects.filter(
        subject_id__in=project_ids,
        predicate_id=role_id,
        visible=True,
    ).select_related(
        'object'
    ).values(
        'subject_id',
        'object_id',
        'object__label',
    )
    df_auth = pd.DataFrame.from_records(qs)
    df_auth.rename(
        columns={
            'subject_id': 'project_id',
            'object_id': f'{role}_id',
            'object__label': f'{role}_label',
            # 'object__uri': f'{role}_uri',
        },
        inplace=True,
    )
    if df_auth is None or df_auth.empty:
        df_auth = pd.DataFrame(
            data={'project_id':[], f'{role}_id':[], f'{role}_label':[]}
        )
    return df_auth


def get_df_project_authors(project_ids):
    """Get a dataframe of project authors

    :param list project_ids: A list (or other iterator) of project ids.
    """
    df_creator = get_df_project_authors_for_role(
        project_ids,
        role_id=configs.PREDICATE_DCTERMS_CREATOR_UUID,
    )
    df_contribs = get_df_project_authors_for_role(
        project_ids,
        role_id=configs.PREDICATE_DCTERMS_CONTRIBUTOR_UUID,
    )
    df_proj_auths = df_creator.merge(
        df_contribs,
        left_on='project_id',
        right_on='project_id',
        how='outer',
    )
    return df_proj_auths


def df_merge_authors_of_role_from_index(df, assert_df, act_index, role):
    """Merges in authors of a role into the main dataframe

    :param DataFrame df: The dataframe that we are adding authors of a
       given role into
    :param DataFrame assert_df: The raw assertion dataframe that may have
       authors of a given role
    :param DataFrame Index act_index: The index of rows in the
       assert_df that have authors of a given role.
    :param str role: The role for these authors (contributor or creator)
    """
    if assert_df[act_index].empty:
        # No authors of this role to add.
        df[f'{role}_label'] = None
        return df
    df_role = assert_df[act_index][
        [
            'subject_id',
            'object_id',
            'object__label',
        ]
    ].groupby(by=['subject_id']).agg([list]).reset_index()
    df_role.columns = df_role.columns.get_level_values(0)
    df_role.reset_index(drop=True, inplace=True)
    df_role.rename(
        columns={
            'object_id':  f'{role}_id',
            'object__label': f'{role}_label',
        }, inplace=True)
    # Add them to our main, glorious dataframe.
    df = df.merge(
        df_role,
        how="left",
        left_on='subject_id',
        right_on='subject_id'
    )
    return df


def clean_lists(col):
    """Cleans lists of dc_creator, and dc_contributors to remove np.nan values"""
    if not isinstance(col, list):
        return np.nan
    output = [
        x for x in col if isinstance(x, str) or isinstance(x, GenUUID.UUID)
    ]
    if not output:
        return np.nan
    return output


def combine_author_lists(contribs, creators):
    """Combine weird numpy series of lists, adding creators to contribs"""
    if is_null(contribs):
        contribs = []
    if is_null(creators):
        creators = []
    output = []
    for auth in (contribs + creators):
        if not isinstance(auth, str):
            continue
        if auth in output:
            # Don't add duplicates to the contributor list
            continue
        output.append(auth)
    return output


def combine_author_lists_by_row(row):
    """Combine weird numpy series of lists, adding creators to contribs, by a dataframe row"""
    contribs = row['dc_contributor_label']
    creators = row['dc_creator_label']
    output = combine_author_lists(contribs, creators)
    return output


def add_authors_to_df(df, assert_df, drop_roles=True, pred_roles_tups=DC_AUTHOR_ROLES_TUPS):
    """Adds authorship columns to a df

    :param DataFrame df: The dataframe that we are adding authors of a
       given role into
    :param DataFrame assert_df: The raw assertion dataframe that may have
       authors of a given role
    """

    if assert_df.empty or not 'predicate_id' in assert_df.columns.tolist():
        # Empty, so skip out.
        return df

    pred_roles_tups = [
        (configs.PREDICATE_DCTERMS_CONTRIBUTOR_UUID, 'dc_contributor'),
        (configs.PREDICATE_DCTERMS_CREATOR_UUID, 'dc_creator'),
    ]

    dc_cols = [
        'dc_contributor_id',
        'dc_contributor_label',
        'dc_creator_id',
        'dc_creator_label'
    ]

    for role_id, role in pred_roles_tups:
        # Get dc-contributors directly assigned to the subject item.
        df_role_preds = get_df_entities_equiv_to_entity(
            subject_ids=assert_df['predicate_id'].unique().tolist(),
            equiv_entity_id=role_id,
            renames={'subject_id': 'predicate_id'},
        )
        if df_role_preds is not None and not df_role_preds.empty:
            role_index = (
                (assert_df['object__item_type'] == 'persons')
                & (
                    (assert_df['predicate_id'] == GenUUID.UUID(role_id))
                    | assert_df['predicate_id'].isin(df_role_preds['predicate_id'].unique())
                )
            )
            df = df_merge_authors_of_role_from_index(df, assert_df, role_index, role)
        else:
            df[f'{role}_id'] = None
            df[f'{role}_label'] = None


    # Get the project authorship roles
    df_proj_auths = get_df_project_authors(
        assert_df['project_id'].unique().tolist()
    )
    df_proj_auths_grp = df_proj_auths.groupby(
        by=['project_id']
    ).agg([list]).reset_index()
    df_proj_auths_grp.columns = df_proj_auths_grp.columns.get_level_values(0)


    if not df_proj_auths_grp.empty:
        # Do a little clean up to remove columns with a list of np.nan, and remove the np.nan's
        # if they are inside lists with otherwise valid values.
        for col in dc_cols:
            l_null = ~df_proj_auths_grp[col].isnull()
            if df_proj_auths_grp[l_null].empty:
                # This is empty, so continue
                continue
            df_proj_auths_grp.loc[l_null, col] = df_proj_auths_grp[l_null].apply(
                lambda row: clean_lists(row[col]), axis=1
            )

        no_item_roles = df['dc_contributor_label'].isnull() & df['dc_creator_label'].isnull()
        for has_missing_proj_id in df[no_item_roles]['project_id'].unique():
            # Add missing contributor, creator names from projects for items that are missing
            # BOTH contributors and creators.
            act_index = no_item_roles & (df['project_id'] == has_missing_proj_id)
            proj_index = df_proj_auths_grp['project_id'] == has_missing_proj_id

            for col in dc_cols:
                col_act_index = act_index & df[col].isnull()
                col_proj_index = proj_index & ~df_proj_auths_grp[col].isnull()
                if df[col_act_index].empty or df_proj_auths_grp[col_proj_index].empty:
                    # We don't need or don't have data to fill, so skip.
                    continue
                # OK! Fill in the dc author column with values from the project authorship
                # metadata. not df.loc[col_act_index, col] fails when the col_values
                # is a list.
                col_values = df_proj_auths_grp[col_proj_index][col].values[0]
                if isinstance(col_values, list):
                    df[col] = df[col].astype(object)
                for i, _ in df[col_act_index].iterrows():
                    # This weirdness sets 1 column at a time without errors
                    # involved on setting a col_values (which may be a list).
                    df.at[i, col] = col_values

    # Now combine the contributors and the creators into a single author column
    df['authors'] = ''

    # Make authors for where either the contributor or the creator columns
    # are not null, but not both.
    null_tups = [
        ('dc_contributor_label', 'dc_creator_label',),
        ('dc_creator_label', 'dc_contributor_label'),
    ]
    for not_null, is_null in null_tups:
        act_index = ~df[not_null].isnull() & df[is_null].isnull()
        df.loc[act_index, 'authors'] = df[act_index][not_null]

    if False:
        print('Example contributors: ' + str(df[df['dc_contributor_label'].notnull()]['dc_contributor_label'].head(5)))
        print('Example creators: ' + str(df[df['dc_creator_label'].notnull()]['dc_creator_label'].head(5)))
        print('Example authors: ' + str(df[df['authors'] != '']['authors'].head(5)))
    # Now, for where there are both contributors and creators, combine them together.
    act_index = (
        ~df['dc_contributor_label'].isnull()
        & ~df['dc_creator_label'].isnull()
        & (df['authors'].isnull() | (df['authors'] == ''))
    )
    print(f'Combining authors where both dc_contributor and dc_creator are not null. Index count: {len(df[act_index])}')
    df.loc[act_index, 'authors'] = df.loc[act_index].apply(
        lambda row: combine_author_lists_by_row(row),
        axis=1
    )

    if drop_roles:
        # Remove the columns for the roles that fed our author information.
        df.drop(columns=['dc_contributor_label', 'dc_creator_label'], inplace=True)

    return df


def get_df_entity_equiv_linked_data(
    oc_entity_ids,
    output_col_prefix='object',
    prefix_uris='https://'
    ):
    """Gets a dataframe of linked data equivalence to Open Context ids"""

    # NOTE: Any given Open Context entity many have multiple linked data
    # equivalents or near equivalents. This creates a dataframe mapping
    # Open Context ids to their equivalent linked data entities

    object_equiv_ld_qs = AllAssertion.objects.filter(
        subject__in=oc_entity_ids,
        predicate_id__in=configs.PREDICATE_LIST_SBJ_EQUIV_OBJ,
        object__item_type__in=configs.URI_ITEM_TYPES,
        visible=True,
        object__meta_json__deprecated__isnull=True,
    ).filter(
        Q(object__meta_json__deprecated__isnull=True)
        |Q(object__meta_json__deprecated=False)
    ).filter(
        Q(object__context__meta_json__deprecated__isnull=True)
        |Q(object__context__meta_json__deprecated=False)
    ).select_related(
        'object'
    ).values(
        'subject_id',
        'object__label',
        'object__uri',
    )
    equiv_df = pd.DataFrame.from_records(object_equiv_ld_qs)

    # Add the https:// prefix to the uris
    equiv_df = add_prefix_to_uri_col_values(
        equiv_df,
        prefix_uris=prefix_uris,
    )

    equiv_df.rename(
        columns={
            'subject_id': f'{output_col_prefix}_id',
            'object__label': f'{output_col_prefix}_equiv_ld_label',
            'object__uri': f'{output_col_prefix}_equiv_ld_uri',
        },
        inplace=True,
    )
    if equiv_df is None or equiv_df.empty:
        equiv_df = pd.DataFrame(
            data={
                f'{output_col_prefix}_id':[],
                f'{output_col_prefix}_equiv_ld_label':[],
                f'{output_col_prefix}_equiv_ld_uri':[]
            }
        )
    return equiv_df


def add_df_id_linked_data_from_assert_df(df, assert_df=None, ld_assert_df=None):
    """Add named entity (id) linked data to the export dataframe

    :param DataFrame df: The dataframe that we are adding linked data
         entities to
    :param DataFrame assert_df: The raw assertion dataframe. This can be None
        if we already have the ld_assert_df defined.
    :param DataFrame ld_assert_df: A subset of the raw assertion dataframe
        that is filtered to only have rows and columns relevant to linked
        data.
    """

    if ld_assert_df is None:

        if assert_df is None:
            return df

        if assert_df.empty:
            # Empty, so skip out.
            return df

        ld_index = ~assert_df['predicate_equiv_ld_uri'].isnull()

        # Make a smaller assertion df that's only got linked
        # data.
        ld_assert_df = assert_df[ld_index][
            [
                'subject_id',
                'predicate_equiv_ld_label',
                'predicate_equiv_ld_uri',
                'predicate__data_type',
                'object_id',
                'obj_string',
                'obj_boolean',
                'obj_integer',
                'obj_double',
                'obj_datetime',
            ]
        ].copy()

    # Merge in the Linked Data equivalents to all the object_ids
    obj_index = ~ld_assert_df['object_id'].isnull()
    obj_equiv_df = get_df_entity_equiv_linked_data(
        ld_assert_df[obj_index]['object_id'].unique()
    )
    if obj_equiv_df is None or obj_equiv_df.empty:
        # There are no equivalent linked data objects to
        # add
        print(f'No obj_equiv_df')
        return df

    ld_assert_df = ld_assert_df.merge(
        obj_equiv_df,
        left_on='object_id',
        right_on='object_id',
        how='outer',
    )
    obj_index = ~ld_assert_df['object_equiv_ld_uri'].isnull()

    print(f'obj_equiv_df has {len(obj_equiv_df.index)} rows')
    print(f'Merged into ld_assert_df object equivalents have {len(ld_assert_df[obj_index].index)} rows')

    # 1: Add linked data where the object is a linked entity (not a literal)
    id_index = ld_assert_df['predicate__data_type'] == 'id'
    for pred_uri in ld_assert_df[id_index]['predicate_equiv_ld_uri'].unique():
        pred_index = id_index & (ld_assert_df['predicate_equiv_ld_uri'] == pred_uri)
        pred_label = ld_assert_df[pred_index]['predicate_equiv_ld_label'].values[0]

        # NOTE: TODO Maybe add URIs to ALL the predicate columns? That will make
        # sure they are uniquely labeled, and we can add special output features
        # to strip them to make a more user friendly output.
        col_uris = f'{pred_label} (URI) [{pred_uri}]'
        col_labels = f'{pred_label} (Label) [{pred_uri}]'
        pred_obj_index = pred_index & ~ld_assert_df['object_equiv_ld_uri'].isnull()

        # Make a dataframe for this predicate and the equivalent linked
        # objects.
        act_ld_df = ld_assert_df[pred_obj_index][
            [
                'subject_id',
                'object_equiv_ld_label',
                'object_equiv_ld_uri',
            ]
        ].groupby(by=['subject_id']).agg([list]).reset_index()

        act_ld_df.columns = act_ld_df.columns.get_level_values(0)
        act_ld_df.reset_index(drop=True, inplace=True)

        act_ld_df.rename(
            columns={
                'object_equiv_ld_label': col_labels,
                'object_equiv_ld_uri': col_uris,
            },
            inplace=True,
        )
        # Sort the dataframe columns.
        act_ld_df = act_ld_df[['subject_id', col_uris, col_labels]]
        print(f'Merge linked equiv data for {pred_label} ({pred_uri})')
        # Add them to our main, glorious dataframe.
        df = df.merge(
            act_ld_df,
            how="left",
            left_on='subject_id',
            right_on='subject_id'
        )

    return df


def add_df_literal_linked_data_from_assert_df(
    df,
    assert_df=None,
    ld_assert_df=None,
    literal_type_tups=LITERAL_DATA_TYPE_COL_TUPS
):
    """Add literal value (not named entity) linked data to the export dataframe

    :param DataFrame df: The dataframe that we are adding linked data
        literal values to
    :param DataFrame assert_df: The raw assertion dataframe. This can be None
        if we already have the ld_assert_df defined.
    :param DataFrame ld_assert_df: A subset of the raw assertion dataframe
        that is filtered to only have rows and columns relevant to linked
        data.
    :param list literal_type_tups: List of tuples that associate a literal
        data type with the object column that has values for that data type
    """

    if ld_assert_df is None:

        if assert_df is None:
            return df

        if assert_df.empty:
            # Empty, so skip out.
            return df

        ld_index = ~assert_df['predicate_equiv_ld_uri'].isnull()

        # Make a smaller assertion df that's only got linked
        # data.
        ld_assert_df = assert_df[ld_index][
            [
                'subject_id',
                'predicate_equiv_ld_label',
                'predicate_equiv_ld_uri',
                'predicate__data_type',
                'object_id',
                'obj_string',
                'obj_boolean',
                'obj_integer',
                'obj_double',
                'obj_datetime',
            ]
        ].copy()

    # Add linked data where the object is a literal value. For different data-types
    # the literal value will be in different columns. So the mappings between data-types
    # and object literal value columns is in the list of tuples below.
    for literal_type, object_col, in literal_type_tups:
        lit_index = ld_assert_df['predicate__data_type'] == literal_type
        for pred_uri in ld_assert_df[lit_index]['predicate_equiv_ld_uri'].unique():
            pred_index = lit_index & (ld_assert_df['predicate_equiv_ld_uri'] == pred_uri)
            pred_label = ld_assert_df[pred_index]['predicate_equiv_ld_label'].values[0]

            # NOTE: TODO Maybe add URIs to ALL the predicate columns? That will make
            # sure they are uniquely labeled, and we can add special output features
            # to strip them to make a more user friendly output.
            col_value = f'{pred_label} (Value) [{pred_uri}]'
            pred_obj_index = pred_index & ~ld_assert_df[object_col].isnull()

            # Make a dataframe for this predicate and the equivalent linked
            # objects.
            act_ld_df = ld_assert_df[pred_obj_index][
                [
                    'subject_id',
                    object_col,
                ]
            ].groupby(by=['subject_id']).agg([list]).reset_index()

            act_ld_df.columns = act_ld_df.columns.get_level_values(0)
            act_ld_df.reset_index(drop=True, inplace=True)

            act_ld_df.rename(
                columns={
                    object_col: col_value,
                },
                inplace=True,
            )
            # Just include the columns we care about.
            act_ld_df = act_ld_df[['subject_id', col_value]]
            # Add them to our main, glorious dataframe.
            df = df.merge(
                act_ld_df,
                how="left",
                left_on='subject_id',
                right_on='subject_id'
            )

    return df


def add_df_linked_data_from_assert_df(
    df,
    assert_df,
    add_entity_ld=True,
    add_literal_ld=True
):
    """Prepares a (final) dataframe from the assert df

    :param DataFrame df: The dataframe that we are adding linked data
        literal values to
    :param DataFrame assert_df: The raw assertion dataframe. This can be None
        if we already have the ld_assert_df defined.
    :param bool add_entity_ld: If true, add any linked data
        equivalents for named entities
    :param bool add_literal_ld: If true, add any linked data
        equivalents for literal values
    """
    if not add_entity_ld and not add_literal_ld:
        # We don't want to add linked data, so skip out without
        # changing the df
        return df

    if assert_df is None:
        return df

    if assert_df.empty:
        # Empty, so skip out.
        return df

    ld_index = ~assert_df['predicate_equiv_ld_uri'].isnull()

    # Make a smaller assertion df that's only got linked
    # data.
    ld_assert_df = assert_df[ld_index][
        [
            'subject_id',
            'predicate_equiv_ld_label',
            'predicate_equiv_ld_uri',
            'predicate__data_type',
            'object_id',
            'obj_string',
            'obj_boolean',
            'obj_integer',
            'obj_double',
            'obj_datetime',
        ]
    ].copy()

    print(f'ld_assert_df has {len(ld_assert_df.index)} rows, do add_entity_ld: {add_entity_ld}')

    if add_entity_ld:
        # 1: Add linked data where the object is a linked entity (not a literal)
        df = add_df_id_linked_data_from_assert_df(df, ld_assert_df=ld_assert_df)

    if not add_literal_ld:
        # We don't want to add the literal linked data, so we can
        # skip out.
        return df

    # 2: Add linked data where the object is a literal value. For different data-types
    # the literal value will be in different columns. So the mappings between data-types
    # and object literal value columns is in the list of tuples below.
    df = add_df_literal_linked_data_from_assert_df(df, ld_assert_df=ld_assert_df)
    return df



def make_node_prefix(row, node_pred_unique_prefixing=NODE_PRED_UNIQUE_PREDFIXING):
    """Makes a node prefix string from values of different columns in a dataframe row

    :param row row: A dataframe row object.
    :param list node_pred_unique_prefixing: A list configuring what nodes count for
        making a node_prefix
    """
    node_prefix = ''
    for node_id_col, default_node_id, node_label_col, node_delim in node_pred_unique_prefixing:
        if not node_id_col in row or not node_label_col in row:
            continue
        if str(row[node_id_col]) == default_node_id:
            # The node id is the default, so do not add a special prefix.
            continue
        if not isinstance(row[node_label_col], str):
            continue
        node_prefix += f'{row[node_label_col]}{node_delim}'
    return node_prefix


def get_sort_preds_df(assert_df, node_pred_unique_prefixing=NODE_PRED_UNIQUE_PREDFIXING):
    """Gets and sorts a dataframe of predicates sorted by node groupings

    :param DataFrame assert_df: The raw assertion dataframe. This can be None
        if we already have the ld_assert_df defined.
    :param list node_pred_unique_prefixing: A list configuring what nodes count for
        making a node_prefix
    """
    preds_cols = [
        'observation_id',
        'observation__label',
        'obs_sort',
        'event_id',
        'event__label',
        'event_sort',
        'attribute_group_id',
        'attribute_group__label',
        'attribute_group_sort',
        'predicate_id',
        'predicate__label',
        'predicate__uri',
        'predicate__data_type',
        'sort',
    ]

    empty_pred_df_data = {
        col:[] for col in (preds_cols + ['node_prefix'])
    }
    if assert_df is None:
        # Return an empty preds_df
        return pd.DataFrame(data=empty_pred_df_data)

    if assert_df.empty or not set(preds_cols).issubset(set(assert_df.columns.tolist())):
        # Return an empty preds_df
        return pd.DataFrame(data=empty_pred_df_data)

    preds_df = assert_df[
        preds_cols
    ].groupby(
        by = [
            'observation_id',
            'event_id',
            'attribute_group_id',
            'predicate_id',
        ]
    ).agg(
        {
            'observation__label' : 'first',
            'obs_sort': 'mean',
            'event__label': 'first',
            'event_sort': 'mean',
            'attribute_group__label': 'first',
            'attribute_group_sort': 'mean',
            'predicate__label': 'first',
            'predicate__uri': 'first',
            'predicate__data_type': 'first',
            'sort': 'mean',
        }
    ).reset_index()

    preds_df.columns = preds_df.columns.get_level_values(0)
    preds_df.sort_values(
        by=[
            'obs_sort',
            'event_sort',
            'attribute_group_sort',
            'sort',
            'predicate__data_type',
            'predicate__label',
        ],
        inplace=True,
    )

    # NOTE: We need to drop repeats.
    # The "same" predicate may be in multiple observations, events, and
    # attribute groups nodes. The default config selects event labels
    # and attribute group labels to prefix predicates to make unique
    # columns for the same predicates that may come in different events
    # or attribute groups.

    # However, the default config treats observations somewhat differently.
    # So we can drop repeated combos of events-attribute-predicates if
    # they come in different observations, because we don't care
    # about observations in the export dump.

    # Make an index where the columns used to figure out node prefixes are
    # not null.
    act_index = ~preds_df['predicate__uri'].isnull()
    for node_id_col, _, node_label_col, _ in node_pred_unique_prefixing:
        act_index &= ~preds_df[node_id_col].isnull()
        act_index &= ~preds_df[node_label_col].isnull()

    preds_df['node_prefix'] = ''
    preds_df.loc[act_index, 'node_prefix'] = preds_df[act_index].apply(
        lambda row: make_node_prefix(
            row,
            node_pred_unique_prefixing=node_pred_unique_prefixing
        ),
        axis=1
    )

    # Drop rows that aren't unique by 'node_prefix', 'predicate__uri'.
    # If you want some different config to determine node_prefix,
    # change the node_pred_unique_prefixing values.
    preds_df.drop_duplicates(
        subset=['node_prefix', 'predicate__uri'],
        keep='first',
        inplace=True,
    )

    return preds_df


def add_attribute_data_to_df(
    df,
    assert_df,
    add_object_uris=True,
    node_pred_unique_prefixing=NODE_PRED_UNIQUE_PREDFIXING,
    pred_data_type_cols=PRED_DATA_TYPE_COLS
):
    """Adds (project specific) attribute data to the output df

    :param DataFrame df: The dataframe that will get the attribute data.
    :param DataFrame assert_df: The raw assertion dataframe.
    :param bool add_object_uris: If true, add URI columns for named entities.
    :param list node_pred_unique_prefixing: A list configuring what nodes count for
        making a node_prefix
    :param dict pred_data_type_cols: A dict keyed by predicate data type
        that identifies object columns.
    """

    if assert_df is None:
        # Nothing to do here, return df
        return df

    if assert_df.empty:
        # Nothing to do here, return df
        return df

    # Get a dataframe of all the predicates, sorted by
    # observation, event, attribute group, and finally by
    # individual sort order.
    preds_df = get_sort_preds_df(
        assert_df,
        node_pred_unique_prefixing=node_pred_unique_prefixing
    )

    for _, prow in preds_df.iterrows():
        p_index = (
            (assert_df['observation_id'] == prow['observation_id'])
            & (assert_df['event_id'] == prow['event_id'])
            & (assert_df['attribute_group_id'] == prow['attribute_group_id'])
            & (assert_df['predicate_id'] == prow['predicate_id'])
        )
        object_col, obj_uri = pred_data_type_cols.get(
            prow['predicate__data_type'],
            (None, None,)
        )
        act_cols = [
            'subject_id',
            object_col,
        ]
        if add_object_uris and obj_uri:
            act_cols.append(obj_uri)

        # Get the values for this predicate
        act_df = assert_df[p_index][act_cols].groupby(
            by=['subject_id'],
        ).agg([list]).reset_index()
        act_df.columns = act_df.columns.get_level_values(0)

        # The following several lines are all about naming the columns
        # for the predicates.
        col_prefix = prow['node_prefix']
        if add_object_uris and obj_uri:
            # For cases where we named entities and we want to have their
            # URIs.
            col_uri = (
                f'{col_prefix}{str(prow["predicate__label"])} '
                f'(URI) [{str(prow["predicate__uri"])}]'
            )
            col_label = (
                f'{col_prefix}{str(prow["predicate__label"])} '
                f'(Label) [{str(prow["predicate__uri"])}]'
            )
            renames = {
                object_col: col_label,
                obj_uri: col_uri,
            }
        else:
            # For literals or for cases where we don't want to include
            # object URIs.
            col_label = (
                f'{col_prefix}{str(prow["predicate__label"])} '
                f'[{str(prow["predicate__uri"])}]'
            )
            renames = {
                object_col: col_label,
            }

        # Rename the columns to use the prefixed, predicate label
        # names.
        act_df.rename(columns=renames, inplace=True)

        # Add them to our main, glorious dataframe.
        df = df.merge(
            act_df,
            how="left",
            left_on='subject_id',
            right_on='subject_id'
        )

    return df


def get_media_resource_file_df(
    uuids,
    resource_type_ids=configs.OC_RESOURCE_TYPES_MAIN_UUIDS):
    """Gets a dataframe of Resources associated with uuids identified items

    :param list uuids: Ids for items associated with resource files.
    :param list resource_type_ids: Identifiers for the types of resources
        that we want to include, if present in the dataframe
    """
    qs = AllResource.objects.filter(
        item_id__in=uuids,
        resourcetype_id__in=resource_type_ids,
    ).values(
        'item_id',
        'resourcetype__label',
        'uri',
        'rank'
    )
    res_df = pd.DataFrame.from_records(qs)
    res_df.rename(
        columns={
            'item_id': 'subject_id',
        },
        inplace=True,
    )
    if res_df is None or res_df.empty:
        res_df = pd.DataFrame(
            data={
                'subject_id':[],
                'resourcetype__label':[],
                'uri':[]
            }
        )
        return res_df
    # Sort by rank
    res_df.sort_values(
        by=['rank', 'subject_id', 'resourcetype__label'],
        inplace=True
    )
    # Drop the rows that duplicates, keeping only the default
    res_df.drop_duplicates(
        subset=['subject_id', 'resourcetype__label'],
        inplace=True,
    )

    # Make sure the file URIs have a protocol prefix
    res_df = add_prefix_to_uri_col_values(
        res_df,
        suffixes_uri_col=['uri'],
        prefix_uris='https://'
    )
    # Drop the rank column.
    res_df.drop(columns=['rank'], inplace=True)
    return res_df


def add_media_resource_files_to_df(
    df,
    resource_type_ids=configs.OC_RESOURCE_TYPES_MAIN_UUIDS
):
    """Adds media files to a dataframe

    :param DataFrame df: The dataframe that will get the attribute data.
    :param list resource_type_ids: Identifiers for the types of resources
        that we want to include, if present in the dataframe
    """
    media_index = df['subject__item_type'] == 'media'
    if df[media_index].empty:
        # No media, so nothing to add.
        return df

    chunks = chunk_list(
        df[media_index]['subject_id'].unique().tolist(),
        n=5000,
    )
    df_res_list = []
    for chunk_uuids in chunks:
        chunk_res_df = get_media_resource_file_df(chunk_uuids)
        if chunk_res_df is None or chunk_res_df.empty:
            continue
        df_res_list.append(chunk_res_df)
    if not df_res_list:
        # No resources of these types found, nothing to add
        return df


    # Combine all the resource dataframes into one
    df_res = pd.concat(df_res_list)
    df_res_piv = df_res.pivot(
        index='subject_id',
        columns='resourcetype__label',
        values='uri'
    )

    # Set up some common merge keys of the same type.
    df_res_piv['subject_id_str'] = df_res_piv.index
    df_res_piv.reset_index(drop=True, inplace=True)
    df_res_piv['subject_id_str'] = df_res_piv['subject_id_str'].astype(str)
    df['subject_id_str'] = df['subject_id'].astype(str)

    # Now merge
    df = df.merge(
        df_res_piv,
        how='left',
        left_on='subject_id_str',
        right_on='subject_id_str',
    )
    df.drop(columns=['subject_id_str'], inplace=True)
    return df



def add_project_editorial_status_and_short_id_to_df(df):
    """Adds the editorial status of the project to the export

    :param DataFrame df: The dataframe that will get the attribute data.
    """
    proj_uuids = []
    subj_proj_index = df['subject__item_type'] == 'projects'
    proj_uuids += df[subj_proj_index]['subject_id'].unique().tolist()
    proj_uuids += df['project_id'].unique().tolist()
    proj_qs = AllManifest.objects.filter(
        uuid__in=proj_uuids,
        item_type='projects',
    ).values(
        'uuid',
        'meta_json__edit_status',
        'meta_json__short_id',
    )
    df_proj = pd.DataFrame.from_records(proj_qs)
    df = df.merge(
        df_proj,
        how='left',
        left_on='subject_id',
        right_on='uuid',
    )
    df.rename(
        columns={
            'meta_json__edit_status': 's_project_edit_status',
            'meta_json__short_id': 's_project_short_id',
        }, 
        inplace=True,
    )
    df = df.merge(
        df_proj,
        how='left',
        left_on='project_id',
        right_on='uuid',
    )
    df.rename(
        columns={
            'meta_json__edit_status': 'p_project_edit_status',
            'meta_json__short_id': 'p_project_short_id',
        }, 
        inplace=True,
    )
    # First use the editoria status directly assigned to the subject_id.
    df['Project Editorial Status'] = df['s_project_edit_status']
    df['Project Short ID'] = df['s_project_short_id']
    df.drop(columns=['s_project_edit_status', 's_project_short_id'], inplace=True)
    # Use the editorial status for the project if the subject_id does not have an editorial status.
    null_index = df['Project Editorial Status'].isnull()
    df.loc[null_index, 'Project Editorial Status'] = df[null_index]['p_project_edit_status']
    df.loc[null_index, 'Project Short ID'] = df[null_index]['p_project_short_id']
    df.drop(columns=['p_project_edit_status', 'p_project_short_id'], inplace=True)
    # Some more cleanup
    for col in ['uuid_x', 'uuid_y']:
        if not col in df.columns.tolist():
            continue
        df.drop(columns=[col], inplace=True)
    return df


def make_export_df(
    filter_args,
    exclude_args=None,
    add_entity_ld=True,
    add_literal_ld=True,
    add_object_uris=True,
    node_pred_unique_prefixing=NODE_PRED_UNIQUE_PREDFIXING,
    resource_type_ids=configs.OC_RESOURCE_TYPES_MAIN_UUIDS,
    more_exclude_args=None,
    add_manifest_without_asserts=False,
    add_manifest_filter_args=None,
    add_manifest_exclude_args=None,
    add_proj_editorial_status_short_id=False,
    truncate_long_text=False,
):
    """Makes a dataframe prepared for exports

    :param dict filter_args: A dictionary of filter arguments
        needed to filter the AllAssertion model to make
        the AllAssertion queryset used to generate the
        output dataframe.
    :param dict exclude_args: An optional dict of exclude
        arguments to with exclusion criteria for the
        AllAssertion model to make the AllAssertion queryset
        used to generate the output dataframe.
    :param bool add_entity_ld: If true, add any linked data
        equivalents for named entities
    :param bool add_literal_ld: If true, add any linked data
        equivalents for literal values
    :param bool add_object_uris: If true, add URI columns for
        named entities.
    :param list node_pred_unique_prefixing: A list configuring what nodes count for
        making a node_prefix
    :param dict more_exclude_args: An optional dict of more exclude
        arguments to with exclusion criteria for the
        AllAssertion model to make the AllAssertion queryset
        used to generate the output dataframe.
    :param bool add_manifest_without_asserts: If true, add manifest
        items that do not have any assertions.
    :param dict add_manifest_filter_args: An optional dict of more exclude
        arguments to with exclusion criteria for the
        AllAssertion model to make the AllAssertion queryset
        used to generate the output dataframe.
    :param dict add_manifest_exclude_args: An optional dict of more exclude
        arguments to with exclusion criteria for the
        AllAssertion model to make the AllAssertion queryset
        used to generate the output dataframe.
    :param bool add_proj_editorial_status_short_id: If true, add the editorial status
        and the short ID of the project to the export
    :param bool truncate_long_text: If true, truncate long strings of text
    """

    # NOTE: This function can take lots of time to execute.
    # Only invoke this command from the inside the manage.py shell
    # It is not suitable to be used with a Web interface without
    # a worker/que system.

    # Make the AllAssertion queryset based on filter arguments
    # and optional exclusion criteria.
    assert_qs = get_assert_qs(filter_args, exclude_args=exclude_args)

    if more_exclude_args:
        # Apply more exclusion criteria to the queryset
        assert_qs = assert_qs.exclude(**more_exclude_args)

    # Turn the AllAssertion queryset into a "tall" dataframe.
    assert_df = get_raw_assertion_df(
        assert_qs, 
        truncate_long_text=truncate_long_text,
    )

    man_df = None
    if add_manifest_without_asserts:
        man_qs = get_manifest_qs(
            filter_args=add_manifest_filter_args,
            exclude_args=add_manifest_exclude_args,
        )
        man_df = get_raw_manifest_df(man_qs)

    if assert_df is None or assert_df.empty:
        # Return an empty dataframe.
        return pd.DataFrame(data={})

    # Make the output dataframe, where there's a single row
    # for each "subject" of the assertions.
    df = prepare_df_from_assert_df(assert_df, man_df=man_df)

    # Add geometry and chronology information to the output dataframe,
    # either directly added to the subject item, or inferred by
    # spatial containment relationships.
    df = add_spacetime_to_df(df)

    # Expand the context path of the subject item into multiple
    # columns.
    df = expand_context_path(df)

    # Add author information to the output dataframe, either directly
    # added as dublin core properties on the subject item, inferred
    # from equivalence relations between other predicates and
    # dublin core authors, or inferred from dublin core authors
    # assigned to the parent projects.
    df = add_authors_to_df(df, assert_df)

    # Add media resource files to media items, if present.
    df = add_media_resource_files_to_df(
        df,
        resource_type_ids=resource_type_ids
    )

    # Add equivalent linked data descriptions to the subject.
    df = add_df_linked_data_from_assert_df(
        df,
        assert_df,
        add_entity_ld=add_entity_ld,
        add_literal_ld=add_literal_ld,
    )

    # Finally, add the project specific attributes asserted about
    # the subject items.
    df = add_attribute_data_to_df(
        df,
        assert_df,
        add_object_uris=add_object_uris,
        node_pred_unique_prefixing=node_pred_unique_prefixing,
    )

    if add_proj_editorial_status_short_id:
        df = add_project_editorial_status_and_short_id_to_df(df)

    # Now drop all the empty columns.
    df.dropna(how='all', axis=1, inplace=True)

    return df


def join_by_delim(
    cell_val,
    delim=DEFAULT_LIST_JOIN_DELIM,
    delim_sub=DEFAULT_DELIM_ELEMENT_REPLACE
):
    """Joins values by a delim

    :param Object cell_val: A value from a dataframe
        cell
    :param str delim: A string delimiter to mark different elements
        of the list when joined to a string
    :param str delim_sub: A string to substitute in cases where
        an individual value in a list has the delimiter present.
    """
    if not isinstance(cell_val, list):
        return cell_val
    str_cell_val = [
        str(v).replace(delim.strip(), delim_sub)
        for v in cell_val
        if v is not None and v is not np.nan
    ]
    return delim.join(str_cell_val)


def merge_lists_in_df_by_delim(
    df,
    delim=DEFAULT_LIST_JOIN_DELIM,
    delim_sub=DEFAULT_DELIM_ELEMENT_REPLACE,
):
    """Changes lists to strings seperated by a delim

    :param DataFrame df: The export dataframe that we're modifying.
    :param str delim: A string delimiter to mark different elements
        of the list when joined to a string
    :param str delim_sub: A string to substitute in cases where
        an individual value in a list has the delimiter present.
    """
    for col in df.columns:
        if df[col].dtypes != object:
            continue
        no_null = ~df[col].isnull()
        if df[no_null].empty:
            continue
        df.loc[no_null, col] = df[no_null].apply(
            lambda row: join_by_delim(
                row[col],
                delim=delim,
                delim_sub=delim_sub,
            ),
            axis=1
        )
    return df


def make_cols_readable(
    df,
    drop_cols=DEFAULT_DROP_COLS,
    context_col_renames=CONTEXT_COL_RENAMES,
    col_renames=DEFAULT_COL_RENAMES,
):
    """Cleans up columns for more readable output

    :param DataFrame: The export dataframe getting edited.
    :param list drop_cols: A list of columns to drop from
        the export dataframe.
    :param dict context_col_renames: A dictionary for
        renaming context columns (or any other)
    :param dict col_renames: A dictionary for other
        column renaming
    """

    # Drop specified columns if they actually exist in the
    # df.
    act_drop = [c for c in drop_cols if c in df.columns]
    df.drop(columns=act_drop, inplace=True)

    # Rename Context (Path) columns if they exist.
    act_context_rename = {
        c:r for c,r in context_col_renames.items()
        if c in df.columns
    }
    df.rename(
        columns=act_context_rename,
        inplace=True
    )

    act_renames =  {
        c:r for c,r in col_renames.items()
        if c in df.columns
    }
    df.rename(
        columns=act_renames,
        inplace=True
    )
    return df


def stylize_df(
    df,
    delim=DEFAULT_LIST_JOIN_DELIM,
    delim_sub=DEFAULT_DELIM_ELEMENT_REPLACE,
    drop_cols=DEFAULT_DROP_COLS,
    context_col_renames=CONTEXT_COL_RENAMES,
    col_renames=DEFAULT_COL_RENAMES,
    ):
    """Stylize an export dataframe nicely for wider use

    :param DataFrame: The export dataframe getting edited.
    :param str delim: A string delimiter between multiple values
        of joined list elements.
    :param str delim_sub: A string to substitute in cases where
        an individual value in a list has the delimiter present.
    :param list drop_cols: A list of columns to drop from
        the export dataframe.
    :param dict context_col_renames: A dictionary for
        renaming context columns (or any other)
    :param dict col_renames: A dictionary for other
        column renaming
    """
    df = merge_lists_in_df_by_delim(
        df=df,
        delim=delim,
        delim_sub=delim_sub
    )
    return make_cols_readable(
        df=df,
        drop_cols=drop_cols,
        context_col_renames=context_col_renames,
        col_renames=col_renames,
    )


def make_clean_export_df(
    filter_args,
    exclude_args=None,
    add_entity_ld=True,
    add_literal_ld=True,
    add_object_uris=True,
    node_pred_unique_prefixing=NODE_PRED_UNIQUE_PREDFIXING,
    resource_type_ids=configs.OC_RESOURCE_TYPES_MAIN_UUIDS,
    delim=DEFAULT_LIST_JOIN_DELIM,
    delim_sub=DEFAULT_DELIM_ELEMENT_REPLACE,
    drop_cols=DEFAULT_DROP_COLS,
    context_col_renames=CONTEXT_COL_RENAMES,
    col_renames=DEFAULT_COL_RENAMES,
    more_exclude_args=None,
    add_manifest_without_asserts=False,
    add_manifest_filter_args=None,
    add_manifest_exclude_args=None,
    add_proj_editorial_status_short_id=False,
    truncate_long_text=False,
):
    """Makes a dataframe prepared for exports

    :param dict filter_args: A dictionary of filter arguments
        needed to filter the AllAssertion model to make
        the AllAssertion queryset used to generate the
        output dataframe.
    :param dict exclude_args: An optional dict of exclude
        arguments to with exclusion criteria for the
        AllAssertion model to make the AllAssertion queryset
        used to generate the output dataframe.
    :param bool add_entity_ld: If true, add any linked data
        equivalents for named entities
    :param bool add_literal_ld: If true, add any linked data
        equivalents for literal values
    :param bool add_object_uris: If true, add URI columns for
        named entities.
    :param list node_pred_unique_prefixing: A list configuring what nodes count for
        making a node_prefix
    :param str delim: A string delimiter between multiple values
        of joined list elements.
    :param str delim_sub: A string to substitute in cases where
        an individual value in a list has the delimiter present.
    :param list drop_cols: A list of columns to drop from
        the export dataframe.
    :param dict context_col_renames: A dictionary for
        renaming context columns (or any other)
    :param dict col_renames: A dictionary for other
        column renaming
    :param dict more_exclude_args: An optional dict of more exclude
        arguments to with exclusion criteria for the
        AllAssertion model to make the AllAssertion queryset
        used to generate the output dataframe.
    :param bool add_manifest_without_asserts: If true, add manifest
        items that do not have any assertions.
    :param dict add_manifest_filter_args: An optional dict of more exclude
        arguments to with exclusion criteria for the
        AllAssertion model to make the AllAssertion queryset
        used to generate the output dataframe.
    :param dict add_manifest_exclude_args: An optional dict of more exclude
        arguments to with exclusion criteria for the
        AllAssertion model to make the AllAssertion queryset
        used to generate the output dataframe.
    :param bool add_proj_editorial_status_short_id: If true, add the editorial status
        and the short ID of the project to the export
    :param bool truncate_long_text: If True, truncate long strings of text
    """

    filter_args, do_project_inventory = check_set_project_inventory(filter_args)
    if do_project_inventory:
        # Add some extra metadata to a table specific to project inventories
        add_proj_editorial_status_short_id = True
        truncate_long_text = True
        

    # Do the hard, complicated job of making the export
    # dataframe. This is not styled at all yet.
    df = make_export_df(
        filter_args=filter_args,
        exclude_args=exclude_args,
        add_entity_ld=add_entity_ld,
        add_literal_ld=add_literal_ld,
        add_object_uris=add_object_uris,
        node_pred_unique_prefixing=node_pred_unique_prefixing,
        resource_type_ids=resource_type_ids,
        more_exclude_args=more_exclude_args,
        add_proj_editorial_status_short_id=add_proj_editorial_status_short_id,
        truncate_long_text=truncate_long_text,
    )

    df_no_style = df.copy()
    # Now do some styling to make the output more legible.
    df = stylize_df(
        df=df,
        delim=delim,
        delim_sub=delim_sub,
        drop_cols=drop_cols,
        context_col_renames=context_col_renames,
        col_renames=col_renames,
    )
    return df, df_no_style
