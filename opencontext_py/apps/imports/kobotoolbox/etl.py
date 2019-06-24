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

from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.sources.models import ImportSource

from opencontext_py.apps.imports.kobotoolbox.utilities import (
    UUID_SOURCE_KOBOTOOLBOX,
    UUID_SOURCE_OC_KOBO_ETL,
    UUID_SOURCE_OC_LOOKUP,
    LINK_RELATION_TYPE_COL,
    list_excel_files,
    read_excel_to_dataframes,
    make_directory_files_df,
    drop_empty_cols,
    reorder_first_columns,
    lookup_manifest_uuid,
)
from opencontext_py.apps.imports.kobotoolbox.attributes import (
    process_hiearchy_col_values
)
from opencontext_py.apps.imports.kobotoolbox.catalog import (
    CATALOG_ATTRIBUTES_SHEET,
    make_catalog_links_df,
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
    prepare_media,
    prepare_media_links_df
)
from opencontext_py.apps.imports.kobotoolbox.preprocess import (
    make_locus_stratigraphy_df,
    prep_field_tables,
    make_final_trench_book_relations_df
)
from opencontext_py.apps.imports.kobotoolbox.dbupdate import (
    update_contexts_subjects
)

"""
from opencontext_py.apps.imports.kobotoolbox.etl import (
    make_kobo_to_open_context_etl_files,
    update_open_context_db
)
# make_kobo_to_open_context_etl_files()
update_open_context_db()

"""

PROJECT_UUID = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
SOURCE_PATH = settings.STATIC_IMPORTS_ROOT +  'pc-2018/'
DESTINATION_PATH = settings.STATIC_IMPORTS_ROOT +  'pc-2018/2018-oc-etl/'
SOURCE_ID_PREFIX = 'kobo-pc-2018-'

FILENAME_ALL_CONTEXTS = 'all-contexts-subjects.csv'
FILENAME_LOADED_CONTEXTS = 'loaded-contexts-subjects.csv'
FILENAME_ATTRIBUTES_CATALOG = 'attributes--catalog.csv'
FILENAME_LINKS_MEDIA = 'links--media.csv'
FILENAME_LINKS_TRENCHBOOKS = 'links--trench-books.csv'
FILENAME_LINKS_STRATIGRAPHY = 'links--locus-stratigraphy.csv'
FILENAME_LINKS_CATALOG = 'links--catalog.csv'


def add_context_subjects_label_class_uri(df, all_contexts_df):
    """Adds label and class_uri to df from all_contexts_df based on uuid join"""
    join_df = all_contexts_df[['label', 'class_uri', 'uuid_source', 'context_uuid']].copy()
    join_df.rename(columns={'context_uuid': '_uuid'}, inplace=True)
    df_output = pd.merge(
        df,
        join_df,
        how='left',
        on=['_uuid']
    )
    df_output = reorder_first_columns(
        df_output,
        ['label', 'class_uri', 'uuid_source']
    )
    return df_output

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
    
    # Now prepare a media links dataframe.
    df_media_link = prepare_media_links_df(
        source_path,
        project_uuid,
        all_contexts_df
    )
    if df_media_link is not None:
        links_media_path = destination_path + FILENAME_LINKS_MEDIA
        df_media_link.to_csv(
            links_media_path,
            index=False,
            quoting=csv.QUOTE_NONNUMERIC
        )
    
    field_config_dfs = prep_field_tables(source_path, project_uuid, year)
    for act_sheet, act_dict_dfs in field_config_dfs.items():
        file_path =  destination_path + act_dict_dfs['file']
        df = act_dict_dfs['dfs'][act_sheet]
        df = add_context_subjects_label_class_uri(
            df,
            all_contexts_df
        )
        df.to_csv(file_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    
    # Now do the stratigraphy.
    locus_dfs = field_config_dfs['Locus Summary Entry']['dfs']
    df_strat = make_locus_stratigraphy_df(locus_dfs)
    strat_path = destination_path +  FILENAME_LINKS_STRATIGRAPHY
    df_strat.to_csv(strat_path, index=False, quoting=csv.QUOTE_NONNUMERIC)

    # Prepare Trench Book relations    
    tb_dfs = field_config_dfs['Trench Book Entry']['dfs']
    tb_all_rels_df = make_final_trench_book_relations_df(field_config_dfs)
    tb_all_rels_path = destination_path + FILENAME_LINKS_TRENCHBOOKS
    tb_all_rels_df.to_csv(tb_all_rels_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    
    # Prepare the catalog
    catalog_dfs = prepare_catalog(project_uuid, source_path)
    catalog_dfs[CATALOG_ATTRIBUTES_SHEET] = add_context_subjects_label_class_uri(
        catalog_dfs[CATALOG_ATTRIBUTES_SHEET],
        all_contexts_df
    )
    catalog_dfs[CATALOG_ATTRIBUTES_SHEET] = process_hiearchy_col_values(
        catalog_dfs[CATALOG_ATTRIBUTES_SHEET]
    )
    attribs_catalog_path = destination_path + FILENAME_ATTRIBUTES_CATALOG
    catalog_dfs[CATALOG_ATTRIBUTES_SHEET].to_csv(
        attribs_catalog_path,
        index=False,
        quoting=csv.QUOTE_NONNUMERIC
    )
    catalog_links_df = make_catalog_links_df(
        project_uuid,
        catalog_dfs,
        tb_dfs['Trench Book Entry'],
        all_contexts_df
    )
    links_catalog_path = destination_path + FILENAME_LINKS_CATALOG
    catalog_links_df.to_csv(
        links_catalog_path,
        index=False,
        quoting=csv.QUOTE_NONNUMERIC
    )
    
    


    
    
def update_open_context_db(project_uuid=PROJECT_UUID, source_prefix=SOURCE_ID_PREFIX, load_files=DESTINATION_PATH):
    """"Updates the Open Context database with ETL load files"""
    all_contexts_df = pd.read_csv((load_files + FILENAME_ALL_CONTEXTS))
    new_contexts_df = update_contexts_subjects(
        project_uuid,
        (source_prefix + FILENAME_ALL_CONTEXTS),
        all_contexts_df
    )
    loaded_contexts_path = (load_files + FILENAME_LOADED_CONTEXTS)
    new_contexts_df.to_csv(
        loaded_contexts_path,
        index=False,
        quoting=csv.QUOTE_NONNUMERIC
    )