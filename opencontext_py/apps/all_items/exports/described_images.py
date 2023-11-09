
import copy
import pandas as pd
import tiktoken
from unidecode import unidecode

from django.db.models import Count, OuterRef, Subquery

from django.template.defaultfilters import slugify

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
path = '~/github/archaeology-images-ai/csv_data/artifact_images_w_descriptions.csv'
filter_args = {'subject__item_class__slug__in': ARTIFACT_CLASS_SLUGS}
df = get_describe_images_related_to_one_subject_df(filter_args=filter_args)
df.to_csv(path, index=False)

import pandas as pd
from opencontext_py.apps.all_items.exports.described_images import *


path = '~/github/archaeology-images-ai/csv_data/artifact_images_w_descriptions.csv'
save_path = '~/github/archaeology-images-ai/json_data/artifact_images_w_sentence_captions.json'
df = pd.read_csv(path)
df_main = df.copy()
df_main = make_natural_language_caption_df_for_json_from_main_df(df_main)
df_main.to_json(save_path, orient='records', indent=4)
"""


ARTIFACT_CLASS_SLUGS = [
    'oc-gen-cat-object',
    'oc-gen-cat-arch-element',
    'oc-gen-cat-coin',
    'oc-gen-cat-pottery',
]

# Name of the OpenAI encoding tokenizer thing
ENCODING_NAME = "cl100k_base"
MAX_TOKEN_LEN = 75 # CLIP is 77, but this adds a little safety margin in CLIP tokenizes differently.

def num_tokens_from_string(string: str, encoding_name: str=ENCODING_NAME) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens


def truncate_to_max_tokens(string: str, max_token_len: int=MAX_TOKEN_LEN, encoding_name: str=ENCODING_NAME) -> str:
    """Returns a string trimmed to an allowed number of tokens"""
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(string)
    num_tokens = len(encoding.encode(string))
    if num_tokens <= max_token_len:
        # We're OK with the token length, no trimming needed
        return string
    tokens = tokens[:max_token_len]
    return encoding.decode(tokens)


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
    ).exclude(
        subject__meta_json__has_key='flag_human_remains'
    ).exclude(
        object__meta_json__has_key='flag_human_remains'
    ).annotate(
        image_file__uri=Subquery(image_qs)
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
        'object__uri',
        'image_file__uri',
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


def consolidate_oc_predicate_cols(df, all_col='project_specific_descriptions'):
    """Stylizes a dataframe so all the project specific Open Context predicate
    values get combined into a single cell.

    :param dataframe df: A dataframe of image objects with columns of
        descriptions from the associated item_type subjects items

    returns dataframe df
    """
    oc_cols = [col for col in df.columns.tolist() if 'opencontext.org/predicates/' in col]
    if not oc_cols:
        # No open context descriptive predicates columns
        return df
    df[all_col] = ''
    col_val_delim = ''
    for col in oc_cols:
        col_ex = col.split('[https://opencontext.org/predicates/')
        col_label = col_ex[0].strip()
        col_index = ~df[col].isnull()
        df.loc[col_index, all_col] = (
            df[col_index][all_col]
            + col_val_delim
            + col_label
            + ': '
            + df[col_index][col]
        )
        col_val_delim = ' '
        print(f'Consolidated {len(df[col_index].index)} values from {col}')
    df.drop(columns=oc_cols, inplace=True)
    df[all_col] = df[all_col].str.strip()
    return df


def remove_unwanted_cols(df):
    """Removes some columns that aren't useful.

    :param dataframe df: A dataframe of image objects with columns of
        descriptions from the associated item_type subjects items

    returns dataframe df
    """
    drop_cols = [col for col in df.columns.tolist() if col.endswith('_id')]
    drop_cols += [
        'subject__item_type',
        'subject__sort',
        'persistent_ark',
    ]
    df.drop(columns=drop_cols, inplace=True)
    return df


def rename_reorder_cols(df):
    """Reorders column for legibility

    :param dataframe df: A dataframe of image objects with columns of
        descriptions from the associated item_type subjects items

    returns dataframe df
    """
    rename_dict = {
        'object__label': 'media__label',
        'object__uri': 'media__uri',
    }

    df.rename(columns=rename_dict, inplace=True)
    media_cols = [
        'image_file__uri',
        'media__label',
        'media__uri',
    ]
    subj_cols = [col for col in df.columns.tolist() if col.startswith('subject__')]
    items_cols = [col for col in df.columns.tolist() if col.startswith('item__')]
    context_cols = [col for col in df.columns.tolist() if col.startswith('context__')]
    first_cols = media_cols + subj_cols + items_cols + context_cols
    other_cols = [col for col in df.columns.tolist() if col not in first_cols]
    df = df[(first_cols + other_cols)].copy()
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
    # Add prefixes to all the uri column values.
    df = create_df.add_prefix_to_uri_col_values(df)
    if not filter_args:
        filter_args = {}
    filter_args['predicate__data_type'] = 'id'
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
    descriptive_index = ~df['subject__uri'].isnull()
    df = df[descriptive_index].copy()
    df = create_df.merge_lists_in_df_by_delim(df, delim=';  ')
    df = consolidate_oc_predicate_cols(df)
    df = remove_unwanted_cols(df)
    df = rename_reorder_cols(df)
    return df


def make_time_range_str_col(df_main):
    """Makes string column for more human readable date ranges.

    :param dataframe df_main: A comprehensive, with lots of likely unwanted columns
        dataframe of image objects with columns of
        descriptions from the associated item_type subjects items

    returns dataframe df
    """
    df_main['time_range'] = ''
    df_main['item__earliest__year'] = None
    df_main['item__latest__year'] = None
    df_main['item__earliest__bce'] = ''
    df_main['item__latest__bce'] = ''
    df_main['item__earliest__latest__to'] = ''
    early_index = (
        ~df_main['item__earliest'].isnull()
    )

    early_bce_index = early_index & (df_main['item__earliest'] < 0)
    late_index = (
        ~df_main['item__latest'].isnull()
    )
    late_bce_index = late_index & (df_main['item__latest'] < 0)

    df_main.loc[early_index, 'item__earliest__year'] = df_main[early_index]['item__earliest'].astype(int).abs()
    df_main.loc[late_index, 'item__latest__year'] = df_main[early_index]['item__latest'].astype(int).abs()
    df_main.loc[early_bce_index, 'item__earliest__bce'] = ' BCE'
    df_main.loc[late_bce_index, 'item__latest__bce'] = ' BCE'

    to_index = (
        ~df_main['item__earliest__year'].isnull()
        & ~df_main['item__latest__year'].isnull()
        & (
            df_main['item__earliest__year'] != df_main['item__latest__year']
        )
    )
    df_main.loc[to_index, 'time_range'] = (
        df_main[to_index]['item__earliest__year'].astype(str)
        + df_main[to_index]['item__earliest__bce'].astype(str)
        + ' to '
        + df_main[to_index]['item__latest__year'].astype(str)
        + df_main[to_index]['item__latest__bce'].astype(str)
    )
    same_index = (
        ~df_main['item__earliest__year'].isnull()
        & (
            df_main['item__earliest__year'] == df_main['item__latest__year']
        )
    )
    df_main.loc[same_index, 'time_range'] = (
        df_main[same_index]['item__earliest__year'].astype(str)
        + df_main[same_index]['item__earliest__bce'].astype(str)
    )
    df_main.drop(
        columns=[
            'item__earliest__year',
            'item__latest__year',
            'item__earliest__bce',
            'item__latest__bce',
        ],
        inplace=True,
    )
    return df_main


def make_df_for_json_from_main_df(df_main):
    """Makes a dataframe suitable for JSON expression, maybe for AI training

    :param dataframe df_main: A comprehensive, with lots of likely unwanted columns
        dataframe of image objects with columns of
        descriptions from the associated item_type subjects items

    returns dataframe df
    """
    df_main['image_genre'] = 'archaeology'
    df_main['image_type'] = 'artifact'
    df_main = make_time_range_str_col(df_main)
    cols = [
        'image_file__uri',
        'media__uri',
        'image_genre',
        'image_type',
        'subject__item_class__label',
        'context___1',
        'context___2',
        'context___3',
        'time_range',
    ]
    label_cols = [c for c in df_main.columns.tolist() if '(Label) [http' in c]
    last_cols = ['project_specific_descriptions']
    uri_cols = [c for c in df_main.columns.tolist() if '(URI) [http' in c]
    all_cols = [c for c in (cols + label_cols + last_cols) if c in df_main.columns.tolist()]
    df = df_main[(cols + label_cols + last_cols)].copy()
    label_col_renames = {}
    for col in label_cols:
        if col not in df.columns.tolist():
            continue
        col_ex = col.split('(Label) [http')
        new_col = col_ex[0].strip()
        new_col = slugify(unidecode(new_col))
        label_col_renames[col] = new_col.replace(' ', '_').replace('-', '_').replace(',', '_')
    df.rename(columns=label_col_renames, inplace=True)
    return df


def add_cidoc_crm_sentences_and_chronology_to_caption(df_main, require_type=True):
    type_col = 'Has type (Label) [https://erlangen-crm.org/current/P2_has_type]'
    consists_col = 'Consists of (Label) [https://erlangen-crm.org/current/P45_consists_of]'
    df_main[type_col] = df_main[type_col].astype(str)
    df_main[consists_col] = df_main[consists_col].astype(str)
    type_index = (
        ~df_main[type_col].isnull() & (df_main[type_col] != 'nan')
    )
    if require_type:
        # Make sure the dataset has a type
        df_main = df_main[type_index].copy()
    consists_of_index = (
        ~df_main[consists_col].isnull()  & (df_main[consists_col] != 'nan')
    )
    # fix repeated consists of
    df_main.loc[consists_of_index, consists_col] = df_main[consists_of_index][consists_col].str.replace('; ', ' ')
    df_main.loc[consists_of_index, consists_col] = df_main[consists_of_index][consists_col].str.replace(r'\b(\w+)(\s+\1)+\b', r'\1')
    df_main.loc[consists_of_index, consists_col] = df_main[consists_of_index][consists_col].apply(lambda x: ' '.join(pd.Series(x.split()).unique()))
    df_main.loc[consists_of_index, consists_col] = df_main[consists_of_index][consists_col].apply(lambda x: ' '.join(pd.Series(x.split()).unique()))
    df_main.loc[consists_of_index, consists_col] = df_main[consists_of_index][consists_col].str.replace('terracotta terracotta', 'terracotta')

    all_crm_index = (
        type_index & consists_of_index
    )
    type_only_index = type_index & ~consists_of_index
    consists_only_index = ~type_index & consists_of_index
    df_main.loc[all_crm_index , 'caption'] = (
        df_main[all_crm_index]['caption']
        + 'This ' + df_main[all_crm_index]['subject__item_class__label'].str.lower()
        + ', ' + df_main[all_crm_index][type_col].str.lower()
        + ', mainly consists of '
        + df_main[all_crm_index][consists_col].str.lower()
        + '. '
    )
    df_main.loc[type_only_index , 'caption'] = (
        df_main[type_only_index]['caption']
        + 'This ' + df_main[type_only_index]['subject__item_class__label'].str.lower()
        + ' is classified as ' + df_main[type_only_index][type_col].str.lower()
        + '. '
    )
    df_main.loc[consists_only_index , 'caption'] = (
        df_main[consists_only_index]['caption']
        + 'This ' + df_main[consists_only_index]['subject__item_class__label'].str.lower()
        + 'It mainly consists of ' + df_main[consists_only_index][consists_col].str.lower()
        + '. '
    )
    time_index = ~df_main['time_range'].isnull()
    itself_index = (
        df_main['item__chrono_source'].str.startswith('Given')
        & time_index
    )
    inferred_index = (
        df_main['item__chrono_source'].str.startswith('Inferred')
        & time_index
    )
    df_main.loc[itself_index, 'caption'] = (
        df_main[itself_index]['caption']
        + 'It appears made around '
        + df_main[itself_index]['time_range']
        + '. '
    )
    df_main.loc[inferred_index, 'caption'] = (
        df_main[inferred_index]['caption']
        + 'Context suggests dates of '
        + df_main[inferred_index]['time_range']
        + '. '
    )
    return df_main


def add_other_standard_sentences_to_caption(df_main):
    origin_col = 'Origin place (Label) [https://gawd.atlantides.org/terms/origin]'
    taxa_col = 'Has taxonomic identifier (Label) [https://purl.obolibrary.org/obo/FOODON_00001303]'
    body_col = 'Has anatomical identification (Label) [https://opencontext.org/vocabularies/open-context-zooarch/has-anat-id]'
    df_main[origin_col] = df_main[origin_col].astype(str)
    df_main[taxa_col] = df_main[taxa_col].astype(str)
    df_main[body_col] = df_main[body_col].astype(str)
    origin_place_index = (
        ~df_main[origin_col].isnull() & (df_main[origin_col] != 'nan')
    )
    taxa_body_index = (
        ~df_main[taxa_col].isnull()
        & ~df_main[body_col].isnull()
        & (df_main[taxa_col] != 'nan')
        & (df_main[body_col] != 'nan')
    )
    df_main.loc[origin_place_index , 'caption'] = (
        df_main[origin_place_index]['caption']
        + 'It was originally made at ' + df_main[origin_place_index][origin_col]
        + '. '
    )
    df_main.loc[taxa_body_index, 'caption'] = (
        df_main[taxa_body_index]['caption']
        + 'Anatomically, it is a ' + df_main[taxa_body_index][body_col].str.lower()
        + ' of the taxa ' + df_main[taxa_body_index][taxa_col]
        + '. '
    )
    return df_main


def make_natural_language_caption_df_for_json_from_main_df(df_main):
    """Makes a dataframe suitable for JSON expression, with more 'natural language' captioning
    that may be better suited for AI training

    :param dataframe df_main: A comprehensive, with lots of likely unwanted columns
        dataframe of image objects with columns of
        descriptions from the associated item_type subjects items

    returns dataframe df
    """
    df_main = make_time_range_str_col(df_main)
    df_main['media__uuid'] = df_main['media__uri'].str.replace('https://opencontext.org/media/', '')
    df_main['caption'] = 'Image of an archaeological artifact found at ' + df_main['context___3']
    off_world_index = df_main['context___1'] == 'Off World'
    # For materials on earth
    df_main.loc[~off_world_index, 'caption'] = (
        df_main[~off_world_index]['caption']
        + ', in ' + df_main['context___2']
        + '. '
    )
    # Off world
    df_main.loc[off_world_index, 'caption'] = (
        df_main[off_world_index]['caption']
        + ', ' + df_main['context___2']
        + '. '
    )
    # Add a type, consists, and dating sentences
    df_main = add_cidoc_crm_sentences_and_chronology_to_caption(df_main)
    # Add sentences(s) relating to other standards
    df_main = add_other_standard_sentences_to_caption(df_main)
    proj_index = ~df_main['project_specific_descriptions'].isnull()
    df_main.loc[proj_index , 'caption'] = (
        df_main[proj_index]['caption']
        + df_main[proj_index]['project_specific_descriptions']
    )
    # Remove repeating words
    df_main['caption'] = df_main['caption'].str.replace(r'\b(\w+)(\s+\1)+\b', r'\1')
    df_main['caption'] = df_main['caption'].str.replace('::', ', ')
    df_main['caption'] = df_main['caption'].str.replace('  ', ' ')
    df_main['caption'] = df_main['caption'].str.replace('  ', ' ')
    # Replace common things that repeat
    replace_tups = [
        ('pottery, vessel; pottery (visual works); vessel', 'pottery vessel'),
        ('terracotta terracotta', 'terracotta'),
        ('plaque; plaques (flat objects)', 'plaque or flat object'),
        ('lid; lids (covers),', 'lid or cover,'),
        ('Fragment Noted: true', ''),
        ('Fragment Noted: false', ''),
        ('. This object,', '. This'),
        ('acroterion; akroterion; acroteria', 'acroterion, acroteria',),
        ('vessel; pottery (visual works)', 'vessel', ),
    ]
    for f, r in replace_tups:
        df_main['caption'] = df_main['caption'].str.replace(f, r)

    df_main['caption'] = df_main['caption'].apply(truncate_to_max_tokens)
    df_main['token_count'] = df_main['caption'].apply(num_tokens_from_string)

    cols = [
        'image_file__uri',
        'media__uuid',
        'media__uri',
        'token_count',
        'caption',
    ]
    return df_main[cols]