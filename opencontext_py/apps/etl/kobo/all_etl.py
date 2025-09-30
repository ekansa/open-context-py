import pandas as pd

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

from opencontext_py.apps.all_items.geospace import aggregate as geo_agg
from opencontext_py.apps.utilities import geospace_contains

from opencontext_py.apps.etl.kobo import bulk_finds
from opencontext_py.apps.etl.kobo import catalog
from opencontext_py.apps.etl.kobo import locus
from opencontext_py.apps.etl.kobo import media
from opencontext_py.apps.etl.kobo import small_finds
from opencontext_py.apps.etl.kobo import subjects
from opencontext_py.apps.etl.kobo import trenchbooks

from opencontext_py.apps.etl.kobo import pc_configs
from opencontext_py.apps.etl.kobo import utilities
from opencontext_py.apps.etl.kobo import db_updates
from opencontext_py.apps.etl.kobo import db_lookups

"""Consolidates all ETL related functions to extract and
transform data from Kobo Excel files.

import importlib

from opencontext_py.apps.etl.kobo import all_etl

# Just do the preparation to load data, gives chance for manual edits
all_etl.no_load_extract_transform_kobo_data()

# Just load the prepared data, after manual edits
all_etl.db_update_only()

all_etl.import_reset()
all_etl.extract_transform_load_kobo_data()

configs = [('catalog',
  'pc2025-v1-cat-attrib-2022-fix',
  '/home/ekansa/pc-data-2025/oc-import/catalog-attribs.csv'),
]
db_updates.load_general_subjects_attributes(configs=configs)

"""

def import_reset():
    n = AllSpaceTime.objects.filter(
        source_id__in=pc_configs.ALL_SOURCE_IDS,
        project_id=pc_configs.PROJECT_UUID
    ).delete()
    print(f'Deleted {n} space-time rows')
    n = AllResource.objects.filter(
        source_id__in=pc_configs.ALL_SOURCE_IDS,
        project_id=pc_configs.PROJECT_UUID
    ).delete()
    print(f'Deleted {n} media file rows')
    n = AllIdentifier.objects.filter(
        item__source_id__in=pc_configs.ALL_SOURCE_IDS,
        item__project_id=pc_configs.PROJECT_UUID
    ).delete()
    print(f'Deleted {n} identifier rows')
    n = AllAssertion.objects.filter(
        source_id__in=pc_configs.ALL_SOURCE_IDS,
        project_id=pc_configs.PROJECT_UUID
    ).delete()
    print(f'Deleted {n} assertion rows')
    n = AllManifest.objects.filter(
        source_id__in=pc_configs.ALL_SOURCE_IDS,
        project_id=pc_configs.PROJECT_UUID
    ).delete()
    print(f'Deleted {n} manifest rows')


def no_load_extract_transform_kobo_data():
    """Extracts and transforms kobo data prior to loading."""
    subjects_df = subjects.make_and_classify_subjects_df()
    print(f'Made a subjects_df with {len(subjects_df.index)} rows.')
    _ = trenchbooks.prepare_attributes_links()
    print(f'Prepared trenchbooks attributes and links.')
    _ = bulk_finds.prepare_attributes_links()
    print(f'Prepared bulk finds attributes and links.')
    _ = catalog.prepare_attributes_links()
    print(f'Prepared catalog attributes and links.')
    _ = small_finds.prepare_attributes_links()
    print(f'Prepared small finds attributes and links.')
    _ = locus.prepare_attributes_links()
    print(f'Prepared locus attributes and links.')
    df_media = media.prepare_media()
    print(f'Extracted media {len(df_media.index)} references from all Kobo excel files.')
    df_media = media.make_opencontext_file_versions()
    print(f'Made OC media file versions {len(df_media.index)} for downloaded media files.')
    _ = media.prepare_media_links_df()
    print('Made media resource links')


def extract_transform_load_subject_items():
    subjects_df = subjects.make_and_classify_subjects_df()
    print(f'Made a subjects_df with {len(subjects_df.index)} rows.')
    subjects.validate_subjects_df()
    print(f'Saved subjects items validation report.')
    subjects_df = db_updates.load_subjects_dataframe(subjects_df)
    print(f'Loaded subjects items.')
    return subjects_df


def extract_transform_load_kobo_data():
    """Extracts and transforms kobo data prior to loading."""
    # Extract and load all subjects items. Do this first because the
    # entities need to be in the database to support reconciliation
    # of identifiers while preparing the other data.
    extract_transform_load_subject_items()

    # Now prepare the trenchbooks.
    _ = trenchbooks.prepare_attributes_links()
    print(f'Prepared trenchbooks attributes and links.')
    # Load the trenchbooks to make them available for reconciliation
    # while preparing the other data files.
    db_updates.load_trench_books_and_attributes()

    # Now do the extract and transforms on the other general datasets
    _ = bulk_finds.prepare_attributes_links()
    print(f'Prepared bulk finds attributes and links.')
    _ = catalog.prepare_attributes_links()
    print(f'Prepared catalog attributes and links.')
    _ = small_finds.prepare_attributes_links()
    print(f'Prepared small finds attributes and links.')
    _ = locus.prepare_attributes_links()
    print(f'Prepared locus attributes and links.')
    df_media = media.prepare_media()
    print(f'Extracted media {len(df_media.index)} references from all Kobo excel files.')
    df_media = media.make_opencontext_file_versions()
    print(f'Made OC media file versions {len(df_media.index)} for downloaded media files.')
    _ = media.prepare_media_links_df()
    print('Made media resource links')

    # Now load the media resources
    db_updates.load_media_files_and_attributes()
    # Now load the other general attribute data
    db_updates.load_general_subjects_attributes()
    # Now load the linking relationship data
    db_updates.make_all_link_assertion()
    # Now make sure the page order is resonable.
    db_updates.sort_page_order()
    # Finally make sure that images actually link to something
    db_updates.add_trench_book_media_main_links()


def db_update_only():
    """Does a DB update ONLY!"""
    subjects_df = pd.read_csv(pc_configs.SUBJECTS_CSV_PATH)
    subjects.validate_subjects_df()
    print(f'Saved subjects items validation report.')
    subjects_df = db_updates.load_subjects_dataframe(subjects_df)
    print(f'Loaded subjects items.')
    db_updates.load_trench_books_and_attributes()
    db_updates.load_media_files_and_attributes()
    db_updates.load_general_subjects_attributes()
    db_updates.load_locus_grid_attributes()
    db_updates.add_persons()
    db_updates.make_all_link_assertion()
    db_updates.fix_trench_book_main_links()
    db_updates.sort_page_order()


def clean_duplicate_catalog_items():
    subjects_df = pd.read_csv(pc_configs.SUBJECTS_CSV_PATH)
    print(f'subjects_df has {len(subjects_df.index)} rows')
    df_sub_exists = db_lookups.make_catalog_exists_df(
        df_cat_data=subjects_df,
        cat_label_col='catalog_name',
        cat_uuid_col='catalog_uuid',
    )
    subjects_df = catalog.redact_existing_records_already_with_data(
        subjects_df,
        'catalog_name',
        'catalog_uuid'
    )
    subjects_df.to_csv(pc_configs.SUBJECTS_CSV_PATH, index=False)
    print(f'subjects_df now has {len(subjects_df.index)} rows')
    df_cat_attributes =  pd.read_csv(pc_configs.CATALOG_ATTRIB_CSV_PATH)
    df_cat_exists = db_lookups.make_catalog_exists_df(
        df_cat_data=df_cat_attributes,
        cat_label_col='subject_label',
        cat_uuid_col='subject_uuid',
    )
    print(f'catalog_attribure_df has {len(df_cat_attributes.index)} rows')
    df_cat_attributes = catalog.redact_existing_records_already_with_data(
        df_cat_attributes,
        'subject_label',
        'subject_uuid'
    )
    df_cat_attributes.to_csv(pc_configs.CATALOG_ATTRIB_CSV_PATH, index=False)
    print(f'catalog_attribure_df now has {len(df_cat_attributes.index)} rows')
    return df_sub_exists, df_cat_exists


def clean_duplicate_bulk_small_find_items():
    subjects_df = pd.read_csv(pc_configs.SUBJECTS_CSV_PATH)
    print(f'subjects_df has {len(subjects_df.index)} rows')
    configs = [
        (pc_configs.SMALL_FINDS_ATTRIB_CSV_PATH, 'find_name', 'find_uuid',),
        (pc_configs.BULK_FINDS_ATTRIB_CSV_PATH, 'bulk_name', 'bulk_uuid',),
    ]
    for attrib_csv_path, subj_label_col, subj_uuid_col in configs:
        df = pd.read_csv(attrib_csv_path)
        print(f'{subj_label_col}  has {len(df.index)} rows')
        delete_suggestions = utilities.get_ids_to_deduplicate(
            df,
            label_col='subject_label',
            uuid_col='subject_uuid',
        )
        print(f'{subj_label_col}  has {len(delete_suggestions)} delete_suggestions')
        df = utilities.redact_suggested_deletions(
            df,
            uuid_col='subject_uuid',
            delete_suggestions=delete_suggestions
        )
        print(f'{subj_label_col} now has {len(df.index)} rows')
        subjects_df = utilities.redact_suggested_deletions(
            subjects_df,
            uuid_col=subj_uuid_col,
            delete_suggestions=delete_suggestions
        )
        print(f'subjects_df now has {len(subjects_df.index)} rows')
        df.to_csv(attrib_csv_path, index=False)
        subjects_df.to_csv(pc_configs.SUBJECTS_CSV_PATH, index=False)


def add_aggregate_unit_geospatial_data():
    """Adds aggregate geospatial data for units in this import"""
    trench_df = pd.read_csv(pc_configs.TRENCH_CSV_PATH)
    unit_uuids = trench_df['uuid'].unique().tolist()
    request_list = [
        {'item_id': uuid, 'max_clusters': 1, 'min_cluster_size_km': 0.0005}
        for uuid in unit_uuids
    ]
    return geo_agg.add_agg_spacetime_objs(
        request_list=request_list,
        source_id=pc_configs.SOURCE_ID_UNIT_AGG_GEO,
    )


def check_aggregate_unit_geospatial_data():
    trench_df = pd.read_csv(pc_configs.TRENCH_CSV_PATH)
    dfs = []
    for parent_uuid in trench_df['uuid'].unique().tolist():
        report_dict = geospace_contains.report_child_coordinate_outliers(
            item_id=parent_uuid
        )
        if not report_dict:
            continue
        if not report_dict.get('child_geo_outliers'):
            continue
        df = pd.DataFrame(data=report_dict.get('child_geo_outliers'))
        df.reset_index(inplace=True, drop=True)
        dfs.append(df)
    df_all = pd.concat(dfs, axis=0)
    df_all.reset_index(drop=True, inplace=True)
    df_all.to_csv(pc_configs.UNIT_GEO_QUALITY_REPORT, index=False)
    return df_all

