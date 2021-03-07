import os
import hashlib
import time
import uuid as GenUUID


import numpy as np
import pandas as pd

from django.db.models import Q, OuterRef, Subquery

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

from opencontext_py.apps.all_items.representations.item import (
    add_select_related_contexts_to_qs
)

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
from opencontext_py.apps.all_items.editorial.tables import df as tabs_df
importlib.reload(tabs_df)


filter_args = {
    'subject__item_class__label__contains': 'Object',
    'subject__path__contains': 'Italy',
}

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
df = tabs_df.add_authors_to_df(df, assert_df)

df = tabs_df.add_spacetime_to_df(df)
df = tabs_df.expand_context_path(df)

df = tabs_df.add_df_linked_data_from_assert_df(df, assert_df)
"""


# How many rows will we get in 1 database query?
DB_QS_CHUNK_SIZE = 100

# Make a list of default Manifest objects for which we prohibit 
# edits.
DEFAULT_UUIDS = [m.get('uuid') for m in DEFAULT_MANIFESTS if m.get('uuid')]


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
        # Add optional exclude args
        qs = qs.exclude(**exclude_args)
    
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

def get_raw_assertion_df(assert_qs):
    assert_qs = assert_qs.values(
        'subject_id',
        'subject__label',
        'subject__item_type',
        'subject__item_class__label',
        'subject__project_id',
        'subject__project__label',
        'subject__project__uri',
        'subject__path',
        'subject__sort',
        'subject__context__uri',
        'project_id',
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
    
    # Last little clean up of a column temporarily used for processing
    df.drop(columns=[p_delim_count_col], inplace=True, errors='ignore')
    return df


def prepare_df_from_assert_df(assert_df):
    """Prepares a (final) dataframe from the assert df"""
    df = assert_df[
        [
            'subject_id',
            'project_id',
            'subject__label',
            'subject__item_type',
            'subject__item_class__label',
            'subject__project_id',
            'subject__project__label',
            'subject__project__uri',
            'subject__path',
            'subject__sort',
            'subject__context__uri',
        ]
    ].groupby(by=['subject_id']).first().reset_index()
    df.columns = df.columns.get_level_values(0)
    df.sort_values(
        by=['subject__sort', 'subject__path', 'subject__label'],
        inplace=True,
    )
    df.reset_index(drop=True, inplace=True)
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
        'geo_specificity',
        'project__meta_json',
    )
    spacetime_df = pd.DataFrame.from_records(spacetime_qs)
    return spacetime_df


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
    df_levels['item__latitude'] = np.nan
    df_levels['item__longitude'] = np.nan
    df_levels['item__geo_specificity'] = np.nan
    df_levels['item__geo_source'] = np.nan
    df_levels['item__earliest'] = np.nan
    df_levels['item__latest'] = np.nan
    df_levels['item__chrono_source'] = np.nan
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
            sp_index = spacetime_df['item_id'] == uuid
            process_tups = [
                (l_geo_index, 'latitude', 'longitude', True, 'geo'), 
                (l_time_index, 'earliest', 'latest', False, 'chrono'),
            ]
            for l_index, x, y, geo_sp, t in process_tups:
                sp_index = (
                    sp_index 
                    & ~spacetime_df[x].isnull()
                    & ~spacetime_df[y].isnull()
                )
                if spacetime_df[sp_index].empty:
                    continue
                df_levels.loc[l_index, f'item__{x}'] = spacetime_df[sp_index][x].values[0]
                df_levels.loc[l_index, f'item__{y}'] = spacetime_df[sp_index][y].values[0]
                if geo_sp:
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
    """Adds spacetime columns to a df"""
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
    role_id=configs.PREDICATE_DCTERMS_CREATOR_UUID
):
    """Get a dataframe of project authors based on the uri of their role
    
    :param list project_ids: A list (or other iterator) of project ids.
    :param str role_id: The ID of the predicate for the authorship role
    """
    roles_dict = {
        configs.PREDICATE_DCTERMS_CREATOR_UUID: 'dc_creator',
        configs.PREDICATE_DCTERMS_CONTRIBUTOR_UUID: 'dc_contributor',
    }
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
        df[f'{role}_label'] = np.nan
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


def combine_author_lists(x, col):
    """Combine weird numpy series of lists, adding creators to contribs"""
    contribs = x['dc_contributor_label']
    creators = x['dc_creator_label']
    output = [
        x for x in contribs if isinstance(auth, str) or instance(aut)
    ]
    output += [
        auth 
        for auth in creators if isinstance(auth, str) and auth not in contribs
    ]
    return output


def add_authors_to_df(df, assert_df, drop_roles=True):
    """Adds authorship columns to a df"""
    
    pred_roles_tups = [
        (configs.PREDICATE_DCTERMS_CONTRIBUTOR_UUID, 'dc_contributor'),
        (configs.PREDICATE_DCTERMS_CREATOR_UUID, 'dc_creator'),
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
            df[f'{role}_id'] = np.nan
            df[f'{role}_label'] = np.nan

    # Get the project authorship roles
    df_proj_auths = get_df_project_authors(
        assert_df['project_id'].unique().tolist()
    )
    df_proj_auths_grp = df_proj_auths.groupby(
        by=['project_id']
    ).agg([list]).reset_index()
    df_proj_auths_grp.columns = df_proj_auths_grp.columns.get_level_values(0)
    
    # Do a little clean up to remove columns with a list of np.nan, and remove the np.nan's
    # if they are inside lists with otherwise valid values.
    for col in ['dc_contributor_id', 'dc_contributor_label', 'dc_creator_id', 'dc_creator_label']:
        l_null = ~df_proj_auths_grp[col].isnull()
        df_proj_auths_grp.loc[l_null, col] = df_proj_auths_grp[l_null].apply(
            lambda row: clean_lists(row[col]), axis=1
        )

    no_item_roles = df['dc_contributor_label'].isnull() & df['dc_creator_label'].isnull()
    for has_missing_proj_id in df[no_item_roles]['project_id'].unique():
        # Add missing contributor, creator names from projects for items that are missing
        # BOTH contributors and creators.
        act_index = no_item_roles & (df['project_id'] == has_missing_proj_id)
        proj_index = df_proj_auths_grp['project_id'] == has_missing_proj_id
        
        df.loc[act_index, 'dc_contributor_id'] = df_proj_auths_grp[proj_index]['dc_contributor_id'].iloc[0]
        df.loc[act_index, 'dc_contributor_label'] = df_proj_auths_grp[proj_index]['dc_contributor_label'].iloc[0]
        df.loc[act_index, 'dc_creator_id'] = df_proj_auths_grp[proj_index]['dc_creator_id'].iloc[0]
        df.loc[act_index, 'dc_creator_label'] = df_proj_auths_grp[proj_index]['dc_creator_label'].iloc[0]

    # Now combine the contributors and the creators into a single author column
    df['authors'] = np.nan

    # Make authors for where either the contributor or the creator columns
    # are not null, but not both.
    null_tups = [
        ('dc_contributor_label', 'dc_creator_label',),
        ('dc_creator_label', 'dc_contributor_label'),
    ]
    for not_null, is_null in null_tups:
        act_index = ~df[not_null].isnull() & df[is_null].isnull()
        df.loc[act_index, 'authors'] = df[act_index][not_null]

    # Now, for where there are both contributors and creators, combine them together.
    act_index = (
        ~df['dc_contributor_label'].isnull() 
        & ~df['dc_creator_label'].isnull()
        & df['authors'].isnull()
    )
    df.loc[act_index, 'authors'] = df[act_index].apply(lambda x: combine_author_lists, axis=1)
 
    if drop_roles:
        # Remove the columns for the roles that fed our author information.
        df.drop(columns=['dc_contributor_label', 'dc_creator_label'], inplace=True)

    return df


def get_df_entity_equiv_linked_data(oc_entity_ids, output_col_prefix='object'):
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


def add_df_linked_data_from_assert_df(df, assert_df):
    """Prepares a (final) dataframe from the assert df"""
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
    ld_assert_df = ld_assert_df.merge(
        obj_equiv_df,
        left_on='object_id', 
        right_on='object_id',
        how='outer',
    )
    obj_index = ~ld_assert_df['object_equiv_ld_uri'].isnull()
    ld_assert_df.loc[obj_index, 'object_equiv_ld_uri'] = 'https://' + ld_assert_df[obj_index]['object_equiv_ld_uri']
    
    # 1: Add linked data where the object is a linked entity (not a literal)
    id_index = ld_assert_df['predicate__data_type'] == 'id'
    for pred_uri in ld_assert_df[id_index]['predicate_equiv_ld_uri'].unique():
        pred_index = id_index & (ld_assert_df['predicate_equiv_ld_uri'] == pred_uri)
        pred_label = ld_assert_df[pred_index]['predicate_equiv_ld_label'].values[0]

        # NOTE: TODO Maybe add URIs to ALL the predicate columns? That will make
        # sure they are uniquely labeled, and we can add special output features
        # to strip them to make a more user friendly output.
        col_uris = f'{pred_label} (URI) [https://{pred_uri}]'
        col_labels = f'{pred_label} (Label) [https://{pred_uri}]'
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
        # Add them to our main, glorious dataframe.
        df = df.merge(
            act_ld_df,
            how="left",
            left_on='subject_id', 
            right_on='subject_id'
        )
    
    # 2: Add linked data where the object is a literal value. For different data-types
    # the literal value will be in different columns. So the mappings between data-types
    # and object literal value columns is in the list of tuples below.
    literal_type_tups = [
        ('xsd:string', 'obj_string',),
        ('xsd:boolean', 'obj_boolean',),
        ('xsd:integer', 'obj_integer',),
        ('xsd:double', 'obj_double',),
        ('xsd:date', 'obj_datetime',),
    ]
    for literal_type, object_col in literal_type_tups:
        lit_index = ld_assert_df['predicate__data_type'] == literal_type
        for pred_uri in ld_assert_df[lit_index]['predicate_equiv_ld_uri'].unique():
            pred_index = lit_index & (ld_assert_df['predicate_equiv_ld_uri'] == pred_uri)
            pred_label = ld_assert_df[pred_index]['predicate_equiv_ld_label'].values[0]

            # NOTE: TODO Maybe add URIs to ALL the predicate columns? That will make
            # sure they are uniquely labeled, and we can add special output features
            # to strip them to make a more user friendly output.
            col_value = f'{pred_label} (Value) [https://{pred_uri}]'
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
            # Sort the dataframe columns.
            act_ld_df = act_ld_df[['subject_id', col_value]]
            # Add them to our main, glorious dataframe.
            df = df.merge(
                act_ld_df,
                how="left",
                left_on='subject_id', 
                right_on='subject_id'
            )

    return df