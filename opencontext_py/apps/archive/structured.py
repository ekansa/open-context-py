import os
import shutil
from time import sleep

import pandas as pd

from django.conf import settings


from opencontext_py.apps.archive import db_update as zen_db
from opencontext_py.apps.archive import utilities as zen_utilities
from opencontext_py.apps.archive import metadata as zen_metadata
from opencontext_py.apps.archive.zenodo import ArchiveZenodo

from opencontext_py.apps.all_items import configs
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)



from opencontext_py.apps.all_items.editorial.archive import file_utilities as fu
from opencontext_py.apps.all_items.editorial.synchronize import safe_model_save
from opencontext_py.apps.all_items.editorial.tables import create_df

from opencontext_py.apps.all_items.representations import item
from opencontext_py.apps.indexer import index_new_schema as new_ind


"""
# Running this:
import importlib
from opencontext_py.apps.archive import structured as zen_struct

importlib.reload(zen_struct)

project_id = '7232a02f-a861-4860-af20-a905b5b3ae0b'
dep_uuids = zen_struct.gather_external_manifest_dependency_entity_uuids(project_id)

zen_struct.export_archive_project_structured_data(project_id, do_testing=True)

# Now test archiving all valid, reviewed projects.
zen_struct.export_archive_all_valid_projects_structured_data(limit=2, do_testing=True)

table_uuid = '0c14c4ad-fce9-4291-a605-8c065d347c5d'
zen_struct.export_archive_table_csv_and_json(table_uuid, do_testing=True)

# Now test archiving all valid, reviewed tables.
zen_struct.export_archive_all_valid_table_csv_and_json(limit=2, do_testing=True)
"""


MODEL_PROJECT_FILTER_CONFIGS = {
    AllManifest: {
        'entity_uuid': 'uuid',
        'proj_filter': 'project_id',
    },
    AllSpaceTime: {
        'entity_uuid': 'item_id',
        'proj_filter': 'item__project_id',
    },
    AllAssertion: {
        'entity_uuid': 'subject_id',
        'proj_filter': 'subject__project_id',
    },
    AllResource: {
        'entity_uuid': 'item_id',
        'proj_filter': 'item__project_id',
    },
    AllHistory: {
        'entity_uuid': 'item_id',
        'proj_filter': 'item__project_id',
    },
    AllIdentifier: {
        'entity_uuid': 'item_id',
        'proj_filter': 'item__project_id',
    },
}

JSON_LD_ITEM_TYPES = [
    'projects',
    'subjects',
    'media',
    'documents',
    'persons',
    'types',
    'predicates',
    'tables',
]

MANIFEST_CSV_FIELDS = [
    'uuid',
    'publisher_id',
    'project_id',
    'item_class_id',
    'source_id',
    'item_type',
    'data_type',
    'slug',
    'label',
    'sort',
    'views',
    'indexed',
    'vcontrol',
    'archived',
    'published',
    'revised',
    'updated',
    'uri',
    'item_key',
    'hash_id',
    'context_id',
    'path',
    'meta_json',
]

ASSERTION_CSV_FIELDS = [
    'uuid',
    'publisher_id',
    'project_id',
    'source_id',
    'subject_id',
    'observation_id',
    'obs_sort',
    'event_id',
    'event_sort',
    'attribute_group_id',
    'attribute_group_sort',
    'predicate_id',
    'sort',
    'visible',
    'certainty',
    'object_id',
    'language_id',
    'obj_string_hash',
    'obj_string',
    'obj_boolean',
    'obj_integer',
    'obj_double',
    'obj_datetime',
    'created',
    'updated',
    'meta_json',
]

SPACETIME_CSV_FIELDS = [
    'uuid',
    'publisher_id',
    'project_id',
    'source_id',
    'item_id',
    'event_id',
    'feature_id',
    'earliest',
    'start',
    'stop',
    'latest',
    'geometry_type',
    'latitude',
    'longitude',
    'geo_specificity',
    'geometry',
    'created',
    'updated',
    'meta_json',
]

RESOURCE_CSV_FIELDS = [
    'uuid',
    'item',
    'project_id',
    'resourcetype_id',
    'mediatype_id',
    'source_id',
    'uri',
    'sha256_checksum',
    'filesize',
    'rank',
    'is_static',
    'created',
    'updated',
    'meta_json',
]

IDENTIFIER_CSV_FIELDS = [
    'uuid',
    'item_id',
    'scheme',
    'rank',
    'id',
    'created',
    'updated',
    'meta_json',
]

HISTORY_CSV_FIELDS = [
    'uuid',
    'sha1_hash',
    'item_id',
    'created',
    'updated',
    'meta_json',
]


def create_save_rep_dict(act_path, uuid, save_in_item_type_dir=True):
    """Creates a JSON-LD dictionary representation of an Open Context
    item to save in a file
    """
    man_obj, rep_dict = item.make_representation_dict(
        subject_id=uuid,
        for_solr=False,
    )
    if man_obj is None:
        return None
    if save_in_item_type_dir:
        save_path = os.path.join(act_path, man_obj.item_type)
    else:
        save_path = act_path
    zen_utilities.save_serialized_json(
        path=save_path,
        filename=f'{str(man_obj.uuid)}.json',
        dict_obj=rep_dict,
    )
    return save_path


def make_dep_uuid_set_from_proj_entity_uuids(entity_uuids, project_id):
    """Gathers all entity UUIDs that are external dependencies for a project
    """
    fk_man_attrs = safe_model_save.MODEL_FK_MANIFEST_ATTRIBUTES.get(
        AllManifest,
        [],
    )
    # 1. Filter the entity_uuids to only include those that are not in the project
    dep_uuids = set()
    for chunk_entity_uuids in create_df.chunk_list(list(entity_uuids)):
        # We chunk the entity_uuids to avoid a large query
        m_qs = AllManifest.objects.filter(
            uuid__in=chunk_entity_uuids,
        ).exclude(
            project_id=project_id
        ).values_list(
            'uuid',
            flat=True,
        )
        dep_uuids.update(m_qs)
        # 2. Now gather all the foreign key dependencies for this chunk of entity_uuids.
        for fk_attr in fk_man_attrs:
            fk_uuid = f'{fk_attr}_id'
            exclude_args = {f'{fk_attr}__project_id': project_id}
            fk_qs = AllManifest.objects.filter(
                uuid__in=chunk_entity_uuids,
            ).exclude(
                **exclude_args
            ).order_by(
                fk_attr
            ).distinct(
                fk_attr
            ).values_list(fk_uuid, flat=True)
            dep_uuids.update(fk_qs)
    # 3. Now we can recursively gather foreign key dependencies for the dep_uuids
    # We will loop through this process until we run out of new dependencies to gather.
    continue_gathering = True
    loop_count = 0
    while continue_gathering:
        loop_count += 1
        current_count = len(dep_uuids)
        for chunk_dep_uuids in create_df.chunk_list(list(dep_uuids)):
            for fk_attr in fk_man_attrs:
                fk_uuid = f'{fk_attr}_id'
                exclude_args = {f'{fk_attr}__project_id': project_id}
                fk_qs = AllManifest.objects.filter(
                    uuid__in=chunk_dep_uuids,
                ).exclude(
                    **exclude_args
                ).order_by(
                    fk_attr
                ).distinct(
                    fk_attr
                ).values_list(fk_uuid, flat=True)
                dep_uuids.update(fk_qs)
        if len(dep_uuids) == current_count:
            continue_gathering = False
        if loop_count > 20:
            continue_gathering = False
    # 4. Do a final cleanup so we don't have any UUIDs from the current project.
    clean_dep_uuids = set()
    for chunk_dep_uuids in create_df.chunk_list(list(dep_uuids)):
        m_qs = AllManifest.objects.filter(
            uuid__in=chunk_dep_uuids,
        ).exclude(
            project_id=project_id
        ).values_list(
            'uuid',
            flat=True,
        )
        clean_dep_uuids.update(m_qs)
    print(f'Gathered {len(clean_dep_uuids)} external dependencies entity UUIDs from {loop_count} loops.')
    return clean_dep_uuids


def gather_external_manifest_dependency_entity_uuids(project_id):
    """Gathers all entity UUIDs from external dependencies
    """
    entity_uuids = set()
    # 1. Gather all the entity UUIDs for the project
    for model, config_dict in MODEL_PROJECT_FILTER_CONFIGS.items():
        ent_attrib = config_dict['entity_uuid']
        proj_filter_dict = {config_dict['proj_filter']: project_id}
        qs = model.objects.filter(
            **proj_filter_dict
        ).values_list(
            ent_attrib,
            flat=True,
        )
        entity_uuids.update(qs)
        # 2. Now gather other related entities that are referenced by foreign keys
        # in rows defined by this model.
        fk_attrs = safe_model_save.MODEL_FK_MANIFEST_ATTRIBUTES.get(model, [])
        for fk_attr in fk_attrs:
            fk_uuid = f'{fk_attr}_id'
            if fk_uuid == ent_attrib:
                # we don't want to gather the same UUIDs twice
                continue
            fk_qs =  model.objects.filter(
                **proj_filter_dict
            ).values_list(
                fk_uuid,
                flat=True,
            )
            entity_uuids.update(fk_qs)
        print(f'Gathered {len(entity_uuids)} entity UUIDs after {model._meta.label}.')
    # 3. Now that we have all the entity UUIDs, we can gather all the external dependencies
    dep_uuids = make_dep_uuid_set_from_proj_entity_uuids(entity_uuids, project_id)
    return dep_uuids


def clean_null_data_types(act_df):
    """Cleans up data type values in a dataframe
    """
    if act_df is None or act_df.empty:
        return act_df
    for col in act_df.columns:
        if act_df[col].isnull().all():
            act_df[col] = act_df[col].astype(str)
            act_df[col] = ''
    return act_df


def add_prefix_to_uri_col_values(
    act_df,
    uri_cols=['uri'],
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
        if col not in uri_cols:
            continue
        # This makes sure we only add the prefix to non-blank rows
        # that don't already have that prefix.
        col_index = (
            ~act_df[col].isnull()
            & ~act_df[col].str.startswith(prefix_uris, na=False)
        )
        act_df.loc[col_index, col] = prefix_uris + act_df[col_index][col]
    return act_df


def create_project_and_dependency_manifest_df(project_id):
    """Creates a dataframe of all manifest data for a project and its dependencies
    """
    dep_uuids = gather_external_manifest_dependency_entity_uuids(project_id)
    manifest_dfs = []
    # 1. Gather all the manifest data for project dependency entities
    for chunk_dep_uuids in create_df.chunk_list(list(dep_uuids)):
        qs = AllManifest.objects.filter(
            uuid__in=chunk_dep_uuids,
        ).values(
            *MANIFEST_CSV_FIELDS
        )
        df = pd.DataFrame.from_records(qs)
        if df.empty:
            continue
        df = clean_null_data_types(df)
        manifest_dfs.append(df)
    # 2. Gather all the manifest data for project entities
    proj_man_qs = AllManifest.objects.filter(
        project_id=project_id
    ).values(
        *MANIFEST_CSV_FIELDS
    )
    proj_df = pd.DataFrame.from_records(proj_man_qs)
    proj_df  = clean_null_data_types(proj_df)
    manifest_dfs.append(proj_df)
    man_df = pd.concat(manifest_dfs, ignore_index=True)
    man_df = add_prefix_to_uri_col_values(man_df)
    return man_df


def create_project_assertions_df(project_id):
    """Creates a dataframe of assertion data for a project
    """
    # 3. Generate the assertions dataframe and save it to a CSV file
    ass_qs = AllAssertion.objects.filter(
        subject__project_id=project_id,
    ).values(
        *ASSERTION_CSV_FIELDS
    )
    ass_df = pd.DataFrame.from_records(ass_qs)
    ass_df  = clean_null_data_types(ass_df)
    return ass_df


def create_project_and_dependency_spacetime_df(man_df):
    """Creates a dataframe of spacetime data for a project and its dependencies
    """
    dfs = []
    for chunk_uuids in create_df.chunk_list(man_df['uuid'].unique().tolist()):
        qs = AllSpaceTime.objects.filter(
            item_id__in=chunk_uuids,
        ).values(
            *SPACETIME_CSV_FIELDS
        )
        df = pd.DataFrame.from_records(qs)
        if df.empty:
            continue
        df = clean_null_data_types(df)
        dfs.append(df)
    spacetime_df = pd.concat(dfs, ignore_index=True)
    return spacetime_df


def create_project_and_dependency_resource_df(man_df):
    """Creates a dataframe of resource data for a project and its dependencies
    """
    dfs = []
    for chunk_uuids in create_df.chunk_list(man_df['uuid'].unique().tolist()):
        qs = AllResource.objects.filter(
            item_id__in=chunk_uuids,
        ).values(
            *RESOURCE_CSV_FIELDS
        )
        df = pd.DataFrame.from_records(qs)
        if df.empty:
            continue
        df = clean_null_data_types(df)
        dfs.append(df)
    resource_df = pd.concat(dfs, ignore_index=True)
    resource_df  = add_prefix_to_uri_col_values(resource_df)
    return resource_df


def create_project_and_dependency_identifier_df(man_df):
    """Creates a dataframe of identifier data for a project and its dependencies
    """
    dfs = []
    for chunk_uuids in create_df.chunk_list(man_df['uuid'].unique().tolist()):
        qs = AllIdentifier.objects.filter(
            item_id__in=chunk_uuids,
        ).values(
            *IDENTIFIER_CSV_FIELDS
        )
        df = pd.DataFrame.from_records(qs)
        if df.empty:
            continue
        df = clean_null_data_types(df)
        dfs.append(df)
    identifier_df = pd.concat(dfs, ignore_index=True)
    return identifier_df


def create_project_history_df(project_id):
    """Creates a dataframe of history data for a project
    """
    # 3. Generate the assertions dataframe and save it to a CSV file
    qs = AllHistory.objects.filter(
        item__project_id=project_id,
    ).values(
        *HISTORY_CSV_FIELDS
    )
    df = pd.DataFrame.from_records(qs)
    df = clean_null_data_types(df)
    return df


def save_df_to_csv(model_db_table, project_id, df):
    """Saves a dataframe to a CSV file
    """
    if df is None or df.empty:
        return None
    csv_path = zen_utilities.make_project_data_csv_model_export_path(
        model_db_table=model_db_table,
        project_uuid=project_id,
    )
    df.to_csv(csv_path, index=False)


def refresh_project_metadata_caches(project_id):
    """Refreshes the metadata caches for a project
    """
    new_ind.reset_project_context_and_metadata_cache(project_id)


def save_project_json_ld(project_id, man_df):
    """Saves JSON-LD representations of project items to files
    """
    act_path = zen_utilities.make_project_data_json_dir_path(project_id)
    index = man_df['item_type'].isin(JSON_LD_ITEM_TYPES)
    # Make sure we have refreshed the caches associated with generating
    # JSON-LD representations for items in each project represented
    # in this export (the main project, and projects for any dependencies).
    for act_project_id in man_df[index]['project_id'].unique().tolist():
        print(f'Refreshing metadata caches for {act_project_id}')
        new_ind.reset_project_context_and_metadata_cache(act_project_id)
    uuids = man_df[index]['uuid'].unique().tolist()
    uuid_count = len(uuids)
    i = 0
    print(f'Save {uuid_count} items')
    for uuid in man_df[index]['uuid'].unique().tolist():
        i += 1
        create_save_rep_dict(act_path, uuid)
        print(f'Saved JSON-LD for {uuid} ({i} of {uuid_count})', end="\r",)
    print('\n')
    print('\n')
    print(f'FINISHED saving JSON-LD for {uuid_count} items')


def export_project_structured_data_files(project_id):
    """Exports all structured data for a project to files in a project export directory.
    """
    # 1. Make a dataframe of all the manifest data for the project and its dependencies
    man_df = create_project_and_dependency_manifest_df(project_id)
    save_df_to_csv(AllManifest._meta.db_table, project_id, man_df)
    # 3. Generate the assertions dataframe and save it to a CSV file
    ass_df = create_project_assertions_df(project_id)
    save_df_to_csv(AllAssertion._meta.db_table, project_id, ass_df)
    # 4. Generate the spacetime dataframe and save it to a CSV file
    spacetime_df = create_project_and_dependency_spacetime_df(man_df)
    save_df_to_csv(AllSpaceTime._meta.db_table, project_id, spacetime_df)
    # 5. Generate the resource dataframe and save it to a CSV file
    resource_df = create_project_and_dependency_resource_df(man_df)
    save_df_to_csv(AllResource._meta.db_table, project_id, resource_df)
    # 5. Generate the identifier dataframe and save it to a CSV file
    identifier_df = create_project_and_dependency_identifier_df(man_df)
    save_df_to_csv(AllIdentifier._meta.db_table, project_id, identifier_df)
    # 6. Generate the history dataframe and save it to a CSV file
    history_df = create_project_history_df(project_id)
    save_df_to_csv(AllHistory._meta.db_table, project_id, history_df)
    # 7. Now make and save JSON-LD documents
    save_project_json_ld(project_id, man_df)


def export_and_zip_project_structured_data_files(project_id):
    """Exports all structured data for a project to files in a
    project export directory, and then zip them up.
    """
    # 1. Export the structured data files
    export_project_structured_data_files(project_id)
    # 2. Compress the exported data files into two zip files
    zen_utilities.zip_structured_data_files(project_id)


def validate_item_ok_for_archive(
    man_obj,
    default_edit_status=0,
    check_published_date=True,
    require_doi=True,
    deposition_type='structured_data',
    require_media_files_count=None,
):
    """Validates that an item is OK to export structured data
    """
    if check_published_date and man_obj.published is None:
        print(f'Item "{man_obj.label}" [{man_obj.uuid}] has no publication date, so do NOT archive.')
        return False
    if man_obj.meta_json.get('edit_status', default_edit_status) < 2:
        print(f'Item "{man_obj.label}" [{man_obj.uuid}] lacks sufficient editorial review, so do NOT archive.')
        return False
    if man_obj.meta_json.get('flag_do_not_index'):
        print(f'Item "{man_obj.label}" [{man_obj.uuid}] flagged for no indexing, so do NOT archive.')
        return False
    if man_obj.meta_json.get('view_group_id'):
        print(f'Item "{man_obj.label}" [{man_obj.uuid}] has private views configured, so do NOT archive.')
        return False
    # Check to see if the item has a DOI (which is required for structured data deposition)
    doi_obj = AllIdentifier.objects.filter(
        item_id=man_obj.uuid,
        scheme='doi',
    ).first()
    if require_doi and not doi_obj:
        print(f'Item "{man_obj.label}" [{man_obj.uuid}] lacks a DOI, so do NOT archive.')
        return False
    if not require_doi and not doi_obj:
        # Check if this has an ARK. If it does, that's and OK substitute for a DOI.
        ark_obj = AllIdentifier.objects.filter(
            item_id=man_obj.uuid,
            scheme='ark',
        ).first()
        if not ark_obj:
            print(f'Item "{man_obj.label}" [{man_obj.uuid}] lacks a DOI and lacks an ARK, so do NOT archive.')
            return False
    # Check to see if the item already has a structured data deposition
    exist_dep_assert = None
    exist_dep_qs = AllAssertion.objects.filter(
        subject_id=man_obj.uuid,
        object__context_id=configs.ZENODO_VOCAB_UUID,
    )
    if deposition_type:
        exist_dep_qs = exist_dep_qs.filter(
            object__meta_json__deposition_type=deposition_type,
        )
    exist_dep_assert = exist_dep_qs.first()
    if exist_dep_assert:
        print(f'Item "{man_obj.label}" [{man_obj.uuid}] already has a {deposition_type} deposition.')
        return False
    if require_media_files_count and require_media_files_count > 0:
        if man_obj.item_type == 'projects':
            media_count = AllResource.objects.filter(
                item__project=man_obj,
            ).count()
        else:
            media_count = AllResource.objects.filter(
                item=man_obj,
            ).count()
        if media_count < require_media_files_count:
            print(f'Item "{man_obj.label}" [{man_obj.uuid}] only has {media_count} media files -> do not archive.')
            return False
    return True


def export_archive_project_structured_data(
    project_id,
    deposition_id=None,
    do_testing=False,
):
    """Exports and compresses structured data files for a project and uploads them
    to Zenodo.
    """
    proj_obj, proj_dict = item.make_representation_dict(
        subject_id=project_id,
        for_solr=False,
    )
    if proj_obj is None:
        raise ValueError(f'Cannot find project: {project_id}')
    # Check to make sure the project is OK to archive structured data in Zenodo
    if not validate_item_ok_for_archive(
        man_obj=proj_obj,
        default_edit_status=0,
        check_published_date=True,
    ):
        return None
    print(f'Project "{proj_obj.label}" [{project_id}] is OK to archive structured data.')
    # 1. Set up the Zenodo deposition
    az = ArchiveZenodo(do_testing=do_testing)
    bucket_url = None
    if not deposition_id:
        deposition_dict = az.create_empty_deposition()
        if not deposition_dict:
            raise ValueError(f'Cannot create an empty deposition for: "{proj_obj.label}" [{project_id}]')
        deposition_id = az.get_deposition_id_from_metadata(deposition_dict)
        bucket_url = az.get_bucket_url_from_metadata(deposition_dict)
    if not bucket_url and deposition_id:
        bucket_url = az.get_remote_deposition_bucket_url(deposition_id)
    if not bucket_url:
        raise ValueError(f'Cannot get bucket url for: "{proj_obj.label}" [{project_id}]')
    if not deposition_id:
        raise ValueError(f'Cannot get deposition id for: "{proj_obj.label}" [{project_id}]')
    # 2. Save the deposition object to the database, that way we can include the
    # relationship between the project and the deposition in the database and archive it!
    if not do_testing:
        _, _ = zen_db.record_zenodo_deposition_for_item(
            man_obj=proj_obj,
            deposition=None,
            rep_dict=proj_dict,
            deposition_id=deposition_id,
            deposition_type='structured_data',
        )
    # 3. Export and compress the structured data files
    export_and_zip_project_structured_data_files(project_id)
    # 4. Upload the compressed files
    act_path = zen_utilities.make_project_data_dir_path(
        project_uuid=project_id
    )
    for filename in ['csv_files.zip', 'json_files.zip',]:
        zip_path = os.path.join(act_path, filename)
        zenodo_resp = az.upload_file_by_put(
            bucket_url=bucket_url,
            full_path_file=zip_path,
            filename=filename,
        )
        if not zenodo_resp:
            raise ValueError(f'Cannot upload file to bucket: {zip_path}')
    # 5. Make metadata for the the Zenodo deposition
    dep_meta_dict = zen_metadata.make_zenodo_proj_stuctured_data_files_metadata(
        proj_dict,
    )
    az.update_metadata(deposition_id, dep_meta_dict)
    print(
        f'Archived structured data to deposition {deposition_id}; {dep_meta_dict.get("title")}'
    )
    return dep_meta_dict


def export_archive_all_valid_projects_structured_data(limit=None, do_testing=False):
    """Exports structured data for all reviewed projects
    """
    proj_qs = AllManifest.objects.filter(
        item_type='projects',
    ).order_by(
        'published',
        'label',
    )
    deposit_count = 0
    for proj_obj in proj_qs:
        project_id = proj_obj.uuid
        dep_meta_dict = export_archive_project_structured_data(
            project_id,
            do_testing=do_testing
        )
        if dep_meta_dict:
            deposit_count += 1
        if limit and deposit_count >= limit:
            break


def download_cache_table_csv(table_obj, act_path):
    """Downloads a CSV file of a table from the project cache
    """
    filename = f'{table_obj.slug}.csv'
    csv_path = fu.get_cache_file(
        file_uri=f'https://{table_obj.uri}.csv',
        cache_filename=filename,
        cache_dir=act_path,
    )
    if not csv_path:
        raise ValueError(f'Cannot download CSV file for: {table_obj.uri}')
    return csv_path


def export_archive_table_csv_and_json(
    table_uuid,
    deposition_id=None,
    do_testing=False,
):
    """Creates a JSON-LD dictionary representation of an Open Context
    item to save in a file
    """
    table_obj, rep_dict = item.make_representation_dict(
        subject_id=table_uuid,
        for_solr=False,
    )
    if table_obj is None:
        return None
    # Check to make sure the table is OK to archive structured data in Zenodo
    if not validate_item_ok_for_archive(
        man_obj=table_obj,
        default_edit_status=2,
        check_published_date=False,
        require_doi=False,
    ):
        return None
    # Prepare the directory for the table structured data files
    act_path = zen_utilities.make_table_data_dir_path(
        table_uuid=str(table_obj.uuid),
    )
    os.makedirs(act_path, exist_ok=True)
    # 1. Download the CSV file
    csv_path = download_cache_table_csv(table_obj, act_path)
    # We have the CSV file, so we can now make a Zenodo deposition
    az = ArchiveZenodo(do_testing=do_testing)
    bucket_url = None
    if not deposition_id:
        deposition_dict = az.create_empty_deposition()
        if not deposition_dict:
            raise ValueError(f'Cannot create an empty deposition for: "{table_obj.label}" [{table_obj.uuid}]')
        deposition_id = az.get_deposition_id_from_metadata(deposition_dict)
        bucket_url = az.get_bucket_url_from_metadata(deposition_dict)
    if not bucket_url and deposition_id:
        bucket_url = az.get_remote_deposition_bucket_url(deposition_id)
    if not bucket_url:
        raise ValueError(f'Cannot get bucket url for: "{table_obj.label}" [{table_obj.uuid}]')
    if not deposition_id:
        raise ValueError(f'Cannot get deposition id for: "{table_obj.label}" [{table_obj.uuid}]')
    # 2. Save the deposition object to the database, that way we can include the
    # relationship between the project and the deposition in the database and archive it!
    if not do_testing:
        _, _ = zen_db.record_zenodo_deposition_for_item(
            man_obj=table_obj,
            deposition=None,
            rep_dict=rep_dict,
            deposition_id=deposition_id,
            deposition_type='structured_data',
        )
        # Update rep_dict, because not it has a relatonship to the deposition
        _, rep_dict = item.make_representation_dict(
            subject_id=table_uuid,
            for_solr=False,
        )
    # 3. Save the JSON-LD representation of the table
    json_path = os.path.join(act_path, f'{table_obj.slug}.json')
    zen_utilities.save_serialized_json(
        path=act_path,
        filename=f'{table_obj.slug}.json',
        dict_obj=rep_dict,
    )
    for filename in [f'{str(table_obj.slug)}.csv', f'{table_obj.slug}.json',]:
        file_path = os.path.join(act_path, filename)
        zenodo_resp = az.upload_file_by_put(
            bucket_url=bucket_url,
            full_path_file=file_path,
            filename=filename,
        )
        if not zenodo_resp:
            raise ValueError(f'Cannot upload file to bucket: {file_path}')
    # 5. Make metadata for the the Zenodo deposition
    dep_meta_dict = zen_metadata.make_zenodo_table_stuctured_data_files_metadata(
        rep_dict,
    )
    az.update_metadata(deposition_id, dep_meta_dict)
    print(
        f'Archived structured data to deposition {deposition_id}; {dep_meta_dict.get("title")}'
    )
    return dep_meta_dict


def export_archive_all_valid_table_csv_and_json(limit=None, do_testing=False):
    """Exports structured data for all reviewed projects
    """
    tables_qs = AllManifest.objects.filter(
        item_type='tables',
    ).order_by(
        'published',
        'label',
    )
    deposit_count = 0
    for table_obj in tables_qs:
        table_uuid = table_obj.uuid
        dep_meta_dict = export_archive_table_csv_and_json(
            table_uuid,
            do_testing=do_testing
        )
        if dep_meta_dict:
            deposit_count += 1
        if limit and deposit_count >= limit:
            break