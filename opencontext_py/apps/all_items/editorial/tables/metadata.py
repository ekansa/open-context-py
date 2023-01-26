
import numpy as np
import pandas as pd

from django.conf import settings

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllResource,
)


from opencontext_py.apps.all_items.editorial.tables import create_df
from opencontext_py.apps.all_items.editorial.tables import queue_utilities

# ---------------------------------------------------------------------
# NOTE: These functions provide utilities to add metadata and download
# links to AllManifest item_type == tables items created by export
# processes here.
# ---------------------------------------------------------------------
COLUMN_PREDICATE_CONFIGS = [
    ('project_id', configs.PREDICATE_DCTERMS_SOURCE_UUID,),
] + [
    (f'{role}_id', pred,)
    for pred, role in create_df.DC_AUTHOR_ROLES_TUPS
]



def add_table_resource(
    man_obj,
    export_id,
    cloud_obj,
    resourcetype_id=configs.OC_RESOURCE_FULLFILE_UUID
):
    """Adds table resource object objects

    :param AllManifest man_obj: An instance of the AllManifest model
        for a tables item associated with an export_id
    :param str export_id: Export ID for the process that made the
        dataframe that we put in cloud storage
    :param Object cloud_obj: An object for the exported table now
        saved in cloud storage.
    :param uuid resourcetype_id: A resource type UUID (or string uuid)
    """
    if not man_obj or not cloud_obj:
        return None
    if not man_obj.item_type == 'tables':
        return None

    # Make the URL for the export download.
    obj_uri = AllManifest().clean_uri(
        f'{settings.CLOUD_BASE_URL}/{cloud_obj.container.name}/{cloud_obj.name}'
    )
    csv_file_dict = {
        'item': man_obj,
        'project': man_obj.project,
        'resourcetype_id': resourcetype_id,
        'rank': 1,
        'source_id': man_obj.source_id,
        'uri': obj_uri,
        'meta_json': {
            'export_id': export_id,
            'cloud_container_name': cloud_obj.container.name,
            'cloud_object_name': cloud_obj.name,
            'export_args': queue_utilities.get_cached_export_args(
                export_id
            )
        },
    }
    res_obj, _ = AllResource.objects.get_or_create(
        uuid=AllResource().primary_key_create(
            item_id=man_obj.uuid,
            resourcetype_id=resourcetype_id,
            rank=1,
        ),
        defaults=csv_file_dict,
    )
    return res_obj


def add_assertions_for_entities_in_col(man_obj, df_ns, col, predicate_id, start_sort=1):
    """Adds assertions of entities named in a dataframe col to a manifest obj

    :param AllManifest man_obj: An instance of the AllManifest model
        for a tables item associated with an export_id
    :param DataFrame df_ns: Dataframe with named entity identifiers
    :param str col: Column in the dataframe with named entity ids
    :param UUID predicate_id: UUID or (uuid string) for the predicate to
        use with these assertions
    :param int start_sort: The starting sort value for assertions with this
        predicate.
    """
    if col not in df_ns.columns:
        # This column does not exist.
        return None

    if 'subject_id' not in df_ns.columns:
        # This column does not exist.
        return None

    no_null = ~df_ns[col].isnull()
    if df_ns[no_null].empty:
        # This column has no data
        return None

    # Pre-delete in case we're replacing some of these metadata assertions.
    AllAssertion.objects.filter(
        subject=man_obj,
        predicate_id=predicate_id,
    ).delete()

    df_ns = df_ns[no_null]
    # NOTE: Some columns will have lists of entity ids, so lets make them
    # delimited strings.
    df_ns[col] = df_ns.apply(
        lambda row: create_df.join_by_delim(
            row[col],
            delim=';',
            delim_sub=';',
        ),
        axis=1
    )
    df_g = df_ns[['subject_id', col]].groupby(
        [col]
    )['subject_id'].agg('count').reset_index()

    df_g.sort_values(
        by=['subject_id'],
        ascending=False,
        inplace=True,
    )

    object_ids = []
    sort = start_sort
    for _, row in df_g.iterrows():
        # NOTE: each row[col] may have a ';' delimited
        # list of multiple object_ids. Each one of these
        # will
        act_counts_for_ranking = row['subject_id']
        act_object_ids = str(row[col]).split(';')
        for object_id in act_object_ids:
            if object_id in object_ids:
                # We already included this object for assertions,
                # so skip.
                continue
            object_ids.append(object_id)
            obj = AllManifest.objects.filter(
                uuid=object_id
            ).first()
            if not obj:
                # We can't find this object, so skip.
                continue
            sort += 0.001
            assert_dict = {
                'project': man_obj.project,
                'publisher': man_obj.publisher,
                'source_id': man_obj.source_id,
                'subject': man_obj,
                'predicate_id': predicate_id,
                'sort': sort,
                'object': obj,
                'meta_json': {
                    'table_object_count': act_counts_for_ranking,
                },
            }
            ass_obj, _ = AllAssertion.objects.get_or_create(
                uuid=AllAssertion().primary_key_create(
                    subject_id=assert_dict['subject'].uuid,
                    predicate_id=assert_dict['predicate_id'],
                    object_id=assert_dict['object'].uuid,
                ),
                defaults=assert_dict
            )


def add_table_dc_metadata(man_obj, export_id, col_configs=COLUMN_PREDICATE_CONFIGS):
    """Adds table Dublin core metadata inferred from export

    :param AllManifest man_obj: An instance of the AllManifest model
        for a tables item associated with an export_id
    :param str export_id: Export ID for the process that made the
        dataframe that we put in cloud storage
    """
    df_ns = queue_utilities.get_cached_no_style_df(export_id)
    if df_ns is None:
        # Somehow missing the non-styled dataframe, so we can't
        # automatically make metadata
        return None

    i = 0
    for col, predicate_id in col_configs:
        i += 1
        df_ns = df_ns.copy()
        add_assertions_for_entities_in_col(
            man_obj,
            df_ns,
            col,
            predicate_id,
            start_sort=i
        )


def add_table_metadata_and_resources(man_obj, export_id, full_cloud_obj, preview_cloud_obj):
    """Adds table metadata and related resources objects

    :param AllManifest man_obj: An instance of the AllManifest model
        for a tables item associated with an export_id
    :param str export_id: Export ID for the process that made the
        dataframe that we put in cloud storage
    :param Object cloud_obj: An object for the exported table now
        saved in cloud storage.
    """

    full_res_obj = add_table_resource(
        man_obj,
        export_id,
        cloud_obj=full_cloud_obj,
        resourcetype_id=configs.OC_RESOURCE_FULLFILE_UUID
    )
    preview_res_obj = add_table_resource(
        man_obj,
        export_id,
        cloud_obj=preview_cloud_obj,
        resourcetype_id=configs.OC_RESOURCE_PREVIEW_UUID,
    )
    # Add the dublin core metadata for this item.
    add_table_dc_metadata(man_obj, export_id)

    return full_res_obj, preview_res_obj


def get_table_related_subjects(man_obj, full_cloud_obj=None, csv_uri=None, df=None, max_subj_count=5):
    """Gets the primary (most common and most general) subjects items in a table.

    :param AllManifest man_obj: An instance of the AllManifest model
        for a tables item associated with an export_id
    :param str export_id: Export ID for the process that made the
        dataframe that we put in cloud storage
    :param Object full_cloud_obj: An object for the exported table now
        saved in cloud storage.
    :param str csv_uri: A string URL to the CSV data table
    :param DataFrame df: A pandas dataframe from the data table csv data
    :param int max_subj_count: The maximum number of subjects items in the table
        to return
    """
    if df is None and csv_uri is None and full_cloud_obj is not None:
        csv_uri = AllManifest().clean_uri(
            f'{settings.CLOUD_BASE_URL}/{full_cloud_obj.container.name}/{full_cloud_obj.name}'
        )
    if df is None:
        df = pd.read_csv(csv_uri, low_memory=False)
    # Extract the columns that are about contexts.
    c_cols = [c for c in df.columns.tolist() if c.startswith('Context (') and c.endswith(')')]
    if not c_cols:
        # There are no context columns in this data table
        return None
    act_cols = []
    best_df_g = None
    for col in c_cols:
        act_cols.append(col)
        df_g = df[act_cols].groupby(act_cols, as_index=False).size()
        if len(df_g.index) > max_subj_count:
            # There are too many unique subjects in this dataframe,
            # so skip out. We'll use the previously defined best_df_g
            # instead.
            break
        best_df_g = df_g.copy()
        if len(df_g.index) > 1:
            # We've got more than one subjects paths, but still less than
            # the maximum allowed, so this is a happy place to quit the
            # loop. We'll use the current best_df_g.
            break
    if best_df_g is None:
        return None
    best_df_g.sort_values(by=['size'], ascending=False, inplace=True)
    act_cols = [c for c in best_df_g.columns if c != 'size']
    rel_subjs = []
    for _, row in best_df_g.iterrows():
        path = '/'.join([row[c] for c in act_cols])
        label = str(row[act_cols[-1]])
        sub_obj = AllManifest.objects.filter(
            item_type='subjects',
            label=label,
            path__endswith=path,
        ).first()
        if not sub_obj:
            continue
        rel_subjs.append((sub_obj, row['size']))
    return rel_subjs


def link_table_related_subjects(
    man_obj,
    full_cloud_obj=None,
    csv_uri=None,
    df=None,
    max_subj_count=5,
    tab_to_subj_uuid=configs.PREDICATE_LINK_UUID,
    subj_to_tab_uuid=configs.PREDICATE_LINK_UUID,
):
    """Links the primary (most common and most general) subjects items in a table.

    :param AllManifest man_obj: An instance of the AllManifest model
        for a tables item associated with an export_id
    :param str export_id: Export ID for the process that made the
        dataframe that we put in cloud storage
    :param Object full_cloud_obj: An object for the exported table now
        saved in cloud storage.
    :param str csv_uri: A string URL to the CSV data table
    :param DataFrame df: A pandas dataframe from the data table csv data
    :param int max_subj_count: The maximum number of subjects items in the table
        to return
    :param UUID tab_to_subj_uuid: UUID for a predicate linking the table
        Manifest to a subject Manifest item
    :param UUID subj_to_tab_uuid: UUID for a predicate linking the subject
        Manifest item to the table Manifest item
    """
    rel_subjs = get_table_related_subjects(
        man_obj=man_obj,
        full_cloud_obj=full_cloud_obj,
        csv_uri=csv_uri,
        df=df,
        max_subj_count=max_subj_count,
    )
    if not rel_subjs:
        return None
    sort = 0
    assert_objs = []
    for rel_subj_obj, count in rel_subjs:
        sort += 1
        assert_dict = {
            'project': man_obj.project,
            'publisher': man_obj.publisher,
            'source_id': man_obj.source_id,
            'subject': man_obj,
            'predicate_id': tab_to_subj_uuid,
            'sort': sort,
            'object': rel_subj_obj,
            'meta_json': {
                'table_object_count': count,
            },
        }
        ass_obj, _ = AllAssertion.objects.get_or_create(
            uuid=AllAssertion().primary_key_create(
                subject_id=assert_dict['subject'].uuid,
                predicate_id=assert_dict['predicate_id'],
                object_id=assert_dict['object'].uuid,
            ),
            defaults=assert_dict
        )
        assert_objs.append(ass_obj)
        print(
            f'Assertion {ass_obj.uuid}: '
            f'is {ass_obj.subject.label} [{ass_obj.subject.uuid}]'
            f'-> {ass_obj.predicate.label} [{ass_obj.predicate.uuid}]'
            f'-> {ass_obj.object.label} [{ass_obj.object.uuid}] '
        )
        # Now make the reciprocal assertion
        r_assert_dict = {
            'project': man_obj.project,
            'publisher': man_obj.publisher,
            'source_id': man_obj.source_id,
            'subject': rel_subj_obj,
            'predicate_id': subj_to_tab_uuid,
            'sort': sort,
            'object': man_obj,
            'meta_json': {
                'table_object_count': count,
            },
        }
        r_ass_obj, _ = AllAssertion.objects.get_or_create(
            uuid=AllAssertion().primary_key_create(
                subject_id=r_assert_dict['subject'].uuid,
                predicate_id=r_assert_dict['predicate_id'],
                object_id=r_assert_dict['object'].uuid,
            ),
            defaults=r_assert_dict
        )
        print(
            f'Reciprocal Assertion {r_ass_obj.uuid}: '
            f'is {r_ass_obj.subject.label} [{r_ass_obj.subject.uuid}]'
            f'-> {r_ass_obj.predicate.label} [{r_ass_obj.predicate.uuid}]'
            f'-> {r_ass_obj.object.label} [{r_ass_obj.object.uuid}] '
        )
        assert_objs.append(r_ass_obj)
    return assert_objs