

from opencontext_py.apps.etl.kobo import bulk_finds
from opencontext_py.apps.etl.kobo import catalog
from opencontext_py.apps.etl.kobo import locus
from opencontext_py.apps.etl.kobo import media
from opencontext_py.apps.etl.kobo import small_finds
from opencontext_py.apps.etl.kobo import subjects
from opencontext_py.apps.etl.kobo import trenchbooks

from opencontext_py.apps.etl.kobo import pc_configs


"""Consolidates all ETL related functions to extract and
transform data from Kobo Excel files.

import importlib

from opencontext_py.apps.etl.kobo import all_etl

all_etl.extract_transform_kobo_data()
all_etl.prepare_media_files()

"""


def extract_transform_kobo_data():
    """Extracts and transforms kobo data prior to loading."""
    subjects_df = subjects.make_and_classify_subjects_df()
    print(f'Made a subjects_df with {len(subjects_df.index)} rows.')
    _ = bulk_finds.prepare_attributes_links()
    print(f'Prepared bulk finds attributes and links.')
    _ = catalog.prepare_attributes_links()
    print(f'Prepared catalog attributes and links.')
    _ = small_finds.prepare_attributes_links()
    print(f'Prepared small finds attributes and links.')
    _ = locus.prepare_attributes_links()
    print(f'Prepared locus attributes and links.')
    _ = trenchbooks.prepare_attributes_links()
    print(f'Prepared trenchbooks attributes and links.')
    df_media = media.prepare_media()
    print(f'Extracted media {len(df_media.index)} references from all Kobo excel files.')


def prepare_media_files():
    df_media = media.make_opencontext_file_versions()