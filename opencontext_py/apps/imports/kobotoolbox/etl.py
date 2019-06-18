import csv
import uuid as GenUUID
import os, sys, shutil
import codecs
import numpy as np
import pandas as pd

from django.db import models
from django.db.models import Q
from django.conf import settings
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.subjects.models import Subject
from opencontext_py.apps.imports.kobotoolbox.utilities import (
    UUID_SOURCE_KOBOTOOLBOX,
    UUID_SOURCE_OC_KOBO_ETL,
    UUID_SOURCE_OC_LOOKUP,
    list_excel_files,
    read_excel_to_dataframes,
    make_directory_files_df,
    drop_empty_cols,
    reorder_first_columns,
    lookup_manifest_uuid,
)
from opencontext_py.apps.imports.kobotoolbox.catalog import (
    CATALOG_ATTRIBUTES_SHEET,
    prepare_catalog
)
from opencontext_py.apps.imports.kobotoolbox.contexts import (
    context_sources_to_dfs,
    preload_contexts_to_df,
    prepare_all_contexts
)
from opencontext_py.apps.imports.kobotoolbox.media import (
    make_all_export_media_df,
    combine_media_with_files,
    prepare_media
)
from opencontext_py.apps.imports.kobotoolbox.preprocess import (
    make_locus_stratigraphy_df,
    prep_field_tables,
    make_final_trench_book_relations_df
)

"""
from opencontext_py.apps.imports.kobotoolbox.etl import (
    make_kobo_to_open_context_etl_files
)
make_kobo_to_open_context_etl_files()

"""

PROJECT_UUID = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
SOURCE_PATH = settings.STATIC_IMPORTS_ROOT +  'pc-2018/'
DESTINATION_PATH = settings.STATIC_IMPORTS_ROOT +  'pc-2018/2018-oc-etl/'

FILENAME_ALL_CONTEXTS = 'all-contexts-subjects.csv'
FILENAME_ATTRIBUTES_CATALOG = 'attributes--catalog.csv'
FILENAME_LINKS_TRENCHBOOKS = 'links--trench-books.csv'
FILENAME_LINKS_STRATIGRAPHY = 'links--locus-stratigraphy.csv'


def make_kobo_to_open_context_etl_files(
    project_uuid=PROJECT_UUID,
    year=2018,
    source_path=SOURCE_PATH,
    destination_path=DESTINATION_PATH
):
    """Prepares files for Open Context ingest."""
    source_dfs = context_sources_to_dfs(source_path)
    all_contexts_df = prepare_all_contexts(
        project_uuid,
        year,
        source_dfs
    )
    all_contexts_path = destination_path + FILENAME_ALL_CONTEXTS
    all_contexts_df.to_csv(
        all_contexts_path,
        index=False,
        quoting=csv.QUOTE_NONNUMERIC
    )
    
    catalog_dfs = prepare_catalog(project_uuid, source_path)
    attribs_catalog_path = destination_path + FILENAME_ATTRIBUTES_CATALOG
    catalog_dfs[CATALOG_ATTRIBUTES_SHEET].to_csv(
        attribs_catalog_path,
        index=False,
        quoting=csv.QUOTE_NONNUMERIC
    )
    
    field_config_dfs = prep_field_tables(source_path, project_uuid, year)
    for act_sheet, act_dict_dfs in field_config_dfs.items():
        file_path =  destination_path + act_dict_dfs['file']
        df = act_dict_dfs['dfs'][act_sheet]
        df.to_csv(file_path, index=False, quoting=csv.QUOTE_NONNUMERIC)

    # Prepare Trench Book relations    
    tb_dfs = field_config_dfs['Trench Book Entry']['dfs']
    tb_all_rels_df = make_final_trench_book_relations_df(field_config_dfs)
    tb_all_rels_path = destination_path + FILENAME_LINKS_TRENCHBOOKS
    tb_all_rels_df.to_csv(tb_all_rels_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    
    # Now do the stratigraphy.
    locus_dfs = field_config_dfs['Locus Summary Entry']['dfs']
    df_strat = make_locus_stratigraphy_df(locus_dfs)
    strat_path = destination_path +  FILENAME_LINKS_STRATIGRAPHY
    df_strat.to_csv(strat_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    


    