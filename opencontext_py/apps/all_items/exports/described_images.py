
import copy
import pandas as pd

from django.db.models import Count, OuterRef, Subquery

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

from opencontext_py.apps.all_items.editorial.tables import create_df

from opencontext_py.libs.models import (
    make_dict_json_safe
)


"""
# Test
from opencontext_py.apps.all_items.exports.described_images import *
filter_args = {'subject__item_class__slug__in': ARTIFACT_CLASS_SLUGS}
df = get_describe_images_related_to_one_subject_df(filter_args=filter_args)


"""


ARTIFACT_CLASS_SLUGS = [
    'oc-gen-cat-object',
    'oc-gen-cat-arch-element',
    'oc-gen-cat-coin',
    'oc-gen-cat-pottery',
]
    

def get_images_related_to_subjects_qs(
    filter_args=None, 
    resourcetype_id=configs.OC_RESOURCE_PREVIEW_UUID
):
    """Gets an AllAssertion queryset with image objects that are associated
    with item_type='subjects' subject items, filtered by filter_args
    
    :param dict filter_args: A dictionary for filtering a queryset of 
        the AllAssertions model
    :param str(uuid) resourcetype_id: A uuid identifier for a resourcetype
        URL to provide for each image object

    returns queryset assert_qs    
    """
    # Limit this subquery to only 1 result, the first.
    image_qs = AllResource.objects.filter(
        item=OuterRef('object'),
        resourcetype_id=resourcetype_id,
    ).values('uri')[:1]
    # The query to get image media
    assert_qs = AllAssertion.objects.filter(
        subject__item_type='subjects',
        object__item_type='media',
        object__item_class_id=configs.CLASS_OC_IMAGE_MEDIA,
    ).annotate(
        image_uri=Subquery(image_qs)
    ).select_related(
        'subject'
    ).select_related(
        'object'
    ).order_by(
        'subject__sort',
        'obs_sort',
        'event_sort',
        'attribute_group_sort',
        'sort',
        'object',
    )
    if filter_args:
        assert_qs = assert_qs.filter(**filter_args)
    return assert_qs


def get_images_related_to_subjects_df(
    filter_args=None, 
    resourcetype_id=configs.OC_RESOURCE_PREVIEW_UUID
):
    """Gets a dataframe from an AllAssertion queryset with image objects that are associated
    with item_type='subjects' subject items, filtered by filter_args
    
    :param dict filter_args: A dictionary for filtering a queryset of 
        the AllAssertions model
    :param str(uuid) resourcetype_id: A uuid identifier for a resourcetype
        URL to provide for each image object

    returns dataframe assert_df    
    """
    assert_qs = get_images_related_to_subjects_qs(
        filter_args=filter_args, 
        resourcetype_id=resourcetype_id,
    )
    assert_qs = assert_qs.values(
        'subject_id',
        'project_id',
        'object_id',
        'object__label',
        'image_uri',
    )
    assert_df = pd.DataFrame.from_records(assert_qs)
    return assert_df


def df_limit_to_images_with_one_subject(assert_df):
    """Filters out assert_df rows where an image
    object_id is NOT associated with exactly 1 subject
    item

    :param dataframe assert_df: A dataframe that we want to filter
        to include rows where the image object is associated with
        exactly 1 item_type='subjects' subject item.

    returns dataframe df
    """
    df_g = assert_df[['subject_id', 'object_id']].groupby(
        ['object_id'], 
        as_index=False
    )['subject_id'].nunique()
    df_g.reset_index(drop=True, inplace=True)
    df_g.rename(columns={'subject_id': 'image_subject_count'}, inplace=True)
    assert_df = pd.merge(assert_df, df_g, on='object_id', how='left')
    good_index = (
        (assert_df['image_subject_count'] == 1)
    )
    df = assert_df[good_index].copy().reset_index(drop=True)
    df.drop(columns=['image_subject_count'], inplace=True)
    return df


def get_images_related_to_one_subject_df(
    filter_args=None, 
    resourcetype_id=configs.OC_RESOURCE_PREVIEW_UUID
):
    """Gets a dataframe where each given image object is associated
    with exactly 1 subject item, filtered by filter_args
    
    :param dict filter_args: A dictionary for filtering a queryset of 
        the AllAssertions model
    :param str(uuid) resourcetype_id: A uuid identifier for a resourcetype
        URL to provide for each image object

    returns dataframe df    
    """
    assert_df = get_images_related_to_subjects_df(
        filter_args=filter_args, 
        resourcetype_id=resourcetype_id
    )
    df = df_limit_to_images_with_one_subject(assert_df)
    return df


def get_describe_images_related_to_one_subject_df(
    filter_args=None, 
    resourcetype_id=configs.OC_RESOURCE_PREVIEW_UUID
):
    """Gets a dataframe where each given image object is associated
    with exactly 1 subject item, filtered by filter_args
    
    :param dict filter_args: A dictionary for filtering a queryset of 
        the AllAssertions model
    :param str(uuid) resourcetype_id: A uuid identifier for a resourcetype
        URL to provide for each image object

    returns dataframe df    
    """
    assert_df = get_images_related_to_subjects_df(
        filter_args=filter_args, 
        resourcetype_id=resourcetype_id
    )
    df = df_limit_to_images_with_one_subject(assert_df)
    if not filter_args:
        filter_args = {}
    filter_args['object__item_type'] = 'types'
    i = 0
    project_ids = df['project_id'].unique().tolist()
    df_raws = []
    for project_id in project_ids:
        i += 1
        filter_args['project_id'] = project_id
        print(f'[{i} of {len(project_ids)}] Get description rows for project {project_id}')
        df_raw = create_df.make_export_df(
            filter_args=filter_args,
            add_entity_ld=True,
            add_literal_ld=False,
            add_object_uris=False,
        )
        print(f'Found {len(df_raw.index)} description rows for project {project_id}')
        df_raws.append(df_raw)
    # Now combine these description dataframes and merge them into
    # our dataframe associating subjects items with image objects.
    df_all_raw = pd.concat(df_raws)
    for col in df.columns.tolist():
        if col == 'subject_id' or col not in df_all_raw.columns.tolist():
            # We want to keep the subject or the column isn't in the
            # df_all_raw so nothing to do
            continue
        df_all_raw.drop(columns=[col], inplace=True)
    df = pd.merge(df, df_all_raw, on='subject_id', how='left')
    return df
