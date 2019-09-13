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
    clean_up_multivalue_cols,
    reorder_first_columns,
    lookup_manifest_uuid,
)
from opencontext_py.apps.imports.kobotoolbox.attributes import (
    ATTRIBUTE_HIERARCHY_DELIM,
    GRID_GROUPBY_COLS,
    GRID_PROBLEM_COL,
    X_Y_GRID_COLS,
    create_grid_validation_columns,
    create_global_lat_lon_columns,
    process_hiearchy_col_values,
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
    prepare_media,
    prepare_media_links_df
)
from opencontext_py.apps.imports.kobotoolbox.preprocess import (
    FILENAME_ATTRIBUTES_LOCUS,
    FILENAME_ATTRIBUTES_BULK_FINDS,
    FILENAME_ATTRIBUTES_SMALL_FINDS,
    FILENAME_ATTRIBUTES_TRENCH_BOOKS,
    make_locus_stratigraphy_df,
    prep_field_tables,
    make_final_trench_book_relations_df
)
from opencontext_py.apps.imports.kobotoolbox.dbupdate import (
    update_contexts_subjects,
    load_attribute_df_into_importer,
    load_attribute_data_into_oc,
    load_link_relations_df_into_oc,
)

"""
from opencontext_py.apps.imports.kobotoolbox.etl import (
    make_kobo_to_open_context_etl_files,
    update_open_context_db,
    update_link_rel_open_context_db
)
make_kobo_to_open_context_etl_files()
update_open_context_db()
update_link_rel_open_context_db()

source_ids = {
    'kobo-pc-2018-all-contexts-subjects.csv',
    'kobo-pc-2018-all-media',
    'kobo-pc-2018-bulk-finds',
    'kobo-pc-2018-catalog',
    'kobo-pc-2018-links-catalog',
    'kobo-pc-2018-links-locus-strat',
    'kobo-pc-2018-links-media',
    'kobo-pc-2018-links-trench-book',
    'kobo-pc-2018-locus',
    'kobo-pc-2018-small-finds',
    'kobo-pc-2018-trench-book'
}
source_ids = {
    'kobo-pc-2019-all-contexts-subjects.csv',
    'kobo-pc-2019-all-media',
    'kobo-pc-2019-bulk-finds',
    'kobo-pc-2019-catalog',
    'kobo-pc-2019-links-catalog',
    'kobo-pc-2019-links-locus-strat',
    'kobo-pc-2019-links-media',
    'kobo-pc-2019-links-trench-book',
    'kobo-pc-2019-locus',
    'kobo-pc-2019-small-finds',
    'kobo-pc-2019-trench-book',
}


"""

ETL_YEAR = 2019
ETL_LABEL = 'PC-{}'.format(ETL_YEAR)
PROJECT_UUID = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
SOURCE_PATH = settings.STATIC_IMPORTS_ROOT +  'pc-{}/'.format(ETL_YEAR)
DESTINATION_PATH = settings.STATIC_IMPORTS_ROOT +  'pc-{}/{}-oc-etl/'.format(ETL_YEAR, ETL_YEAR)
SOURCE_ID_PREFIX = 'kobo-pc-{}-'.format(ETL_YEAR)
MEDIA_BASE_URL = 'https://artiraq.org/static/opencontext/poggio-civitate/{}-media/'.format(ETL_YEAR)
MEDIA_FILES_PATH = settings.STATIC_IMPORTS_ROOT + 'pc-{}/attachments'.format(ETL_YEAR)
OC_TRANSFORMED_FILES_PATH = settings.STATIC_IMPORTS_ROOT + 'pc-{}/{}-media'.format(ETL_YEAR, ETL_YEAR)

FILENAME_ALL_CONTEXTS = 'all-contexts-subjects.csv'
FILENAME_ALL_MEDIA = 'all-media-files.csv'
FILENAME_LOADED_CONTEXTS = 'loaded--contexts-subjects.csv'
FILENAME_ATTRIBUTES_CATALOG = 'attributes--catalog.csv'
FILENAME_LINKS_MEDIA = 'links--media.csv'
FILENAME_LINKS_TRENCHBOOKS = 'links--trench-books.csv'
FILENAME_LINKS_STRATIGRAPHY = 'links--locus-stratigraphy.csv'
FILENAME_LINKS_CATALOG = 'links--catalog.csv'

GRID_PROBLEM_EXP_COLS = [
    'label',
    'class_uri',
    '_uuid',
    GRID_PROBLEM_COL,
] + GRID_GROUPBY_COLS

ATTRIBUTE_SOURCES = [
    # (source_id, source_type, source_label, filename)
    (SOURCE_ID_PREFIX + 'catalog', 'catalog', '{} Catalog'.format(ETL_LABEL), FILENAME_ATTRIBUTES_CATALOG,),
    (SOURCE_ID_PREFIX + 'locus', 'locus', '{} Locus'.format(ETL_LABEL), FILENAME_ATTRIBUTES_LOCUS,),
    (SOURCE_ID_PREFIX + 'bulk-finds', 'bulk-finds', '{} Bulk Finds'.format(ETL_LABEL), FILENAME_ATTRIBUTES_BULK_FINDS,),
    (SOURCE_ID_PREFIX + 'small-finds',  'small-finds', '{} Small Finds'.format(ETL_LABEL), FILENAME_ATTRIBUTES_SMALL_FINDS,),
    (SOURCE_ID_PREFIX + 'trench-book', 'trench-book', '{} Trench Book'.format(ETL_LABEL), FILENAME_ATTRIBUTES_TRENCH_BOOKS,),
    (SOURCE_ID_PREFIX + 'all-media', 'all-media', '{} All Media'.format(ETL_LABEL), FILENAME_ALL_MEDIA,),
]

LINK_RELATIONS_SOURCES = [
     (SOURCE_ID_PREFIX + 'links-media', FILENAME_LINKS_MEDIA,),
     (SOURCE_ID_PREFIX + 'links-trench-book', FILENAME_LINKS_TRENCHBOOKS,),
     (SOURCE_ID_PREFIX + 'links-locus-strat', FILENAME_LINKS_STRATIGRAPHY,),
     (SOURCE_ID_PREFIX + 'links-catalog', FILENAME_LINKS_CATALOG,),
]

def write_grid_problem_csv(df,  destination_path, filename):
    """Export the grid problem dataframe if needed """
    if not GRID_PROBLEM_COL in df.columns:
        # No grid problems in this DF
        return None
    bad_indx = (df[GRID_PROBLEM_COL].notnull())
    if df[bad_indx].empty:
        # No problem grid coordinates found
        return None
    df_report = df[bad_indx].copy()
    all_tuple_cols = [(c[0] + ' ' + c[1]) for c in df_report.columns if isinstance(c, tuple)]
    x_tuple_cols = [c for c in all_tuple_cols if 'Grid X' in c]
    y_tuple_cols = [c for c in all_tuple_cols if 'Grid Y' in c]
    tuple_renames = {
        c:(c[0] + ' ' + c[1]) for c in df_report.columns if isinstance(c, tuple)
    }
    x_cols = [x for x, _ in X_Y_GRID_COLS if x in df_report.columns]
    y_cols = [y for _, y in X_Y_GRID_COLS if y in df_report.columns]
    df_report.rename(columns=tuple_renames, inplace=True)
    df_report = df_report[(GRID_PROBLEM_EXP_COLS + x_cols + y_cols +  x_tuple_cols + y_tuple_cols)]
    df_report.sort_values(by=GRID_GROUPBY_COLS, inplace=True)
    report_path = destination_path + 'bad-grid--' + filename
    df_report.to_csv(
        report_path,
        index=False,
        quoting=csv.QUOTE_NONNUMERIC
    )
    

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
    year=ETL_YEAR,
    source_path=SOURCE_PATH,
    destination_path=DESTINATION_PATH,
    base_url=MEDIA_BASE_URL,
    files_path=MEDIA_FILES_PATH,
    oc_media_root_dir=OC_TRANSFORMED_FILES_PATH,
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
    
    # Now prepare a consolidated, all media dataframe for all the media
    # files referenced in all of the source datasets.
    df_media_all = prepare_media(
        source_path,
        files_path,
        oc_media_root_dir,
        project_uuid,
        base_url
    )
    all_media_csv_path = destination_path + FILENAME_ALL_MEDIA
    df_media_all.to_csv(all_media_csv_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    
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
        # Add global coordinates if applicable.
        df = create_grid_validation_columns(df)
        write_grid_problem_csv(df,  destination_path, act_dict_dfs['file'])
        df = create_global_lat_lon_columns(df)
        df.to_csv(file_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
    
    # Now do the stratigraphy.
    locus_dfs = field_config_dfs['Locus Summary Entry']['dfs']
    df_strat = make_locus_stratigraphy_df(locus_dfs)
    strat_path = destination_path +  FILENAME_LINKS_STRATIGRAPHY
    df_strat.to_csv(strat_path, index=False, quoting=csv.QUOTE_NONNUMERIC)

    # Prepare Trench Book relations    
    tb_dfs = field_config_dfs['Trench Book Entry']['dfs']
    tb_all_rels_df = make_final_trench_book_relations_df(field_config_dfs, all_contexts_df)
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
    # Clean up redundent data from the hierarchies
    catalog_dfs[CATALOG_ATTRIBUTES_SHEET] = clean_up_multivalue_cols(
        catalog_dfs[CATALOG_ATTRIBUTES_SHEET],
        delim=ATTRIBUTE_HIERARCHY_DELIM
    )
    # Add global coordinates to the catalog data.
    catalog_dfs[CATALOG_ATTRIBUTES_SHEET] = create_grid_validation_columns(
        catalog_dfs[CATALOG_ATTRIBUTES_SHEET]
    )
    write_grid_problem_csv(
        catalog_dfs[CATALOG_ATTRIBUTES_SHEET],
        destination_path,
        FILENAME_ATTRIBUTES_CATALOG
    )
    catalog_dfs[CATALOG_ATTRIBUTES_SHEET] = create_global_lat_lon_columns(
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


def update_subjects_context_open_context_db(
    project_uuid=PROJECT_UUID,
    source_prefix=SOURCE_ID_PREFIX,
    load_files=DESTINATION_PATH,
    all_contexts_file=FILENAME_ALL_CONTEXTS,
    loaded_contexts_file=FILENAME_LOADED_CONTEXTS,
):
    """Loads subjects, contexts items and containment relations"""
    all_contexts_df = pd.read_csv((load_files + all_contexts_file))
    new_contexts_df = update_contexts_subjects(
        project_uuid,
        (source_prefix + all_contexts_file),
        all_contexts_df
    )
    loaded_contexts_path = (load_files + loaded_contexts_file)
    new_contexts_df.to_csv(
        loaded_contexts_path,
        index=False,
        quoting=csv.QUOTE_NONNUMERIC
    )

def update_attributes_open_context_db(
    project_uuid=PROJECT_UUID,
    source_prefix=SOURCE_ID_PREFIX,
    load_files=DESTINATION_PATH,
    attribute_sources=ATTRIBUTE_SOURCES,
):
    # Load attribute data into the importer
    for source_id, source_type, source_label, filename in attribute_sources:
        df = pd.read_csv((load_files + filename))
        load_attribute_df_into_importer(
            project_uuid,
            source_id,
            source_type,
            source_label,
            df
        )
    # Now actually import the data into Open Context
    for source_id, _, _, _ in attribute_sources:
        load_attribute_data_into_oc(project_uuid, source_id)
    
def update_link_rel_open_context_db(
    project_uuid=PROJECT_UUID,
    source_prefix=SOURCE_ID_PREFIX,
    load_files=DESTINATION_PATH,
    link_sources=LINK_RELATIONS_SOURCES,
    loaded_link_file_prefix='loaded--',
):
    """Loads linking relationships into the database"""
    for source_id, filename in link_sources:
        df = pd.read_csv((load_files + filename))
        df = load_link_relations_df_into_oc(
            project_uuid,
            source_id,
            df
        )
        df.to_csv(
            (load_files + loaded_link_file_prefix + filename),
            index=False,
            quoting=csv.QUOTE_NONNUMERIC
        )


def update_open_context_db(
    project_uuid=PROJECT_UUID,
    source_prefix=SOURCE_ID_PREFIX,
    load_files=DESTINATION_PATH,
    all_contexts_file=FILENAME_ALL_CONTEXTS,
    loaded_contexts_file=FILENAME_LOADED_CONTEXTS,
    attribute_sources=ATTRIBUTE_SOURCES,
    link_sources=LINK_RELATIONS_SOURCES
):
    """"Updates the Open Context database with ETL load files"""
    # First add subjects / contexts and their containment relations
    update_subjects_context_open_context_db(
        project_uuid=project_uuid,
        source_prefix=source_prefix,
        load_files=load_files,
        all_contexts_file=all_contexts_file,
        loaded_contexts_file=loaded_contexts_file,
    )

    # Load attribute data into the importer, then import them into
    # Open Context.
    update_attributes_open_context_db(
        project_uuid=project_uuid,
        source_prefix=source_prefix,
        load_files=load_files,
        attribute_sources=attribute_sources
    )
    
    # Load link relationships into the Open Context database.
    update_link_rel_open_context_db(
        project_uuid=project_uuid,
        source_prefix=source_prefix,
        load_files=load_files,
        link_sources=link_sources
    )
    