

from opencontext_py.apps.etl.kobo import catalog
from opencontext_py.apps.etl.kobo import locus
from opencontext_py.apps.etl.kobo import media
from opencontext_py.apps.etl.kobo import subjects

from opencontext_py.apps.etl.kobo import pc_configs


"""Consolidates all ETL related functions to extract and
transform data from Kobo Excel files.

import importlib

from opencontext_py.apps.etl.kobo import all_etl

all_etl.extract_transform_kobo_data()

"""


def extract_transform_kobo_data():
    """Extracts and transforms kobo data prior to loading."""
    subjects_df = subjects.make_and_classify_subjects_df()
    print(f'Made a subjects_df with {len(subjects_df.index)} rows.')
    _ = catalog.prepare_catalog()
    print(f'Prepared catalog attributes and links.')
    _ = locus.prepare_locus()
    print(f'Prepared locus attributes and links.')
    df_media = media.make_all_export_media_df()
    print(f'Extracted media {len(df_media.index)} references from all Kobo excel files.')