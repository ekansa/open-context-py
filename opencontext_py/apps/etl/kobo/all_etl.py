
from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)


from opencontext_py.apps.etl.kobo import bulk_finds
from opencontext_py.apps.etl.kobo import catalog
from opencontext_py.apps.etl.kobo import locus
from opencontext_py.apps.etl.kobo import media
from opencontext_py.apps.etl.kobo import small_finds
from opencontext_py.apps.etl.kobo import subjects
from opencontext_py.apps.etl.kobo import trenchbooks

from opencontext_py.apps.etl.kobo import pc_configs
from opencontext_py.apps.etl.kobo import db_updates

"""Consolidates all ETL related functions to extract and
transform data from Kobo Excel files.

import importlib

from opencontext_py.apps.etl.kobo import all_etl

all_etl.no_load_extract_transform_kobo_data()

all_etl.import_reset()
all_etl.extract_transform_load_kobo_data()

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
