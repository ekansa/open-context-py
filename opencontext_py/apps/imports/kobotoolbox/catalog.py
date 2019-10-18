
from time import sleep
import uuid as GenUUID
import os, sys, shutil
import numpy as np
import pandas as pd
import xlrd

from django.conf import settings
from django.db.models import Q
from opencontext_py.apps.ocitems.assertions.models import Assertion
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.ocitems.subjects.models import Subject

from opencontext_py.apps.imports.kobotoolbox.contexts import (
    UNIT_LABEL_REPLACES,
    prepare_trench_contexts,
)
from opencontext_py.apps.imports.kobotoolbox.preprocess import (
    look_up_parent,
)
from opencontext_py.apps.imports.kobotoolbox.utilities import (
    UUID_SOURCE_KOBOTOOLBOX,
    UUID_SOURCE_OC_KOBO_ETL,
    UUID_SOURCE_OC_LOOKUP,
    LINK_RELATION_TYPE_COL,
    MULTI_VALUE_COL_PREFIXES,
    make_directory_files_df,
    list_excel_files,
    read_excel_to_dataframes,
    drop_empty_cols,
    reorder_first_columns,
    update_multivalue_col_vals,
    update_multivalue_columns,
    clean_up_multivalue_cols,
    parse_opencontext_uuid,
    parse_opencontext_type,
    lookup_manifest_uuid,
)


"""Uses Pandas to prepare Kobotoolbox exports for Open Context import


import csv
from django.conf import settings
from opencontext_py.apps.imports.kobotoolbox.catalog import (
    CATALOG_ATTRIBUTES_SHEET,
    prepare_catalog
)

project_uuid = 'DF043419-F23B-41DA-7E4D-EE52AF22F92F'
excels_filepath = settings.STATIC_IMPORTS_ROOT +  'pc-2018/'
catalog_dfs = prepare_catalog(project_uuid, excel_dirpath)


"""

CATALOG_ATTRIBUTES_SHEET = 'Catalog Entry'
CATALOG_RELS_SHEET = 'rel_ids_repeat'

ENTRY_DATE_PRED_UUID = '8b812e4f-edc4-44f1-a88d-4ad358aaf9aa'
START_PAGE_PRED_UUID = 'BECAD1AF-0245-44E0-CD2A-F2F7BD080443'
END_PAGE_PRED_UUID = '506924AA-B53D-41B5-9D02-9A7929EA6D6D'

FIRST_LINK_REL_COLS = [
    'label',
    'class_uri',
    'uuid_source',
    'subject_uuid',
    LINK_RELATION_TYPE_COL,
    'object_uuid',
    'object_uuid_source'
]

RELS_RENAME_COLS = {
    '_submission__uuid': 'subject_uuid',
    'Related Identifiers/Related Record Object/Type of Relationship': LINK_RELATION_TYPE_COL,
    'Related Identifiers/Related Record Object/Related ID': 'object__Related ID',
    'Related Identifiers/Related Record Object/Type of Related ID': 'object__Related Type',
    'Related Identifiers/Related Record Object/Note about Relationship': 'object__Relation Note',
}

REL_PREFIXES = {
    'Small Find': (
        ['SF '],
        ['oc-gen:cat-sample'],
    ),
    'Cataloged Object': (
        ['PC ', 'VdM '],
        ['oc-gen:cat-arch-element', 'oc-gen:cat-object', 'oc-gen:cat-pottery']
    ),
    'Supplemental Find': (
        [
            'Bulk Architecture-',
            'Bulk Bone-',
            'Bulk Ceramic-',
            'Bulk Metal-',
            'Bulk Other-',
            'Bulk Tile-',
        ],
        ['oc-gen:cat-sample-col'],
    ),
}

def db_lookup_trenchbooks_linked_to_trench_id(project_uuid, trench_id):
    """Gets a list of documents uuids that are linked to a given trench id."""
    # Get mappings for the trench_id and more canonical names
    parts = [trench_id]
    for f, r in UNIT_LABEL_REPLACES:
        parts.append((trench_id.lower().replace(f, r).strip()))
    # Get UUIDs for subject items that are in the trench_id and its path
    sub_uuids = []
    for part in parts:
        subs = Subject.objects.filter(
            project_uuid=project_uuid,
            context__contains=part
        )
        sub_uuids += [s.uuid for s in subs]
    # Now get the document items that are related to the trench_id and
    # its child items
    sub_linked_docs = Assertion.objects.filter(
        uuid__in=sub_uuids,
        object_type='documents'
    )
    # Make a list of the document uuids
    doc_uuids = [a.object_uuid for a in sub_linked_docs]
    return doc_uuids
    
def db_lookup_trenchbook(project_uuid, doc_uuids, trench_id, year, entry_date, start_page, end_page):
    """Look up trenchbook entries via database queries."""
    # Further filter the documents for the ones on the correct date.
    tbs = Manifest.objects.filter(
        project_uuid=project_uuid,
        uuid__in=doc_uuids,
        item_type='documents',
        label__contains=entry_date,
    )
    if len(tbs) == 0:
        print('No trench book for trench id: {}, year: {}'.format(trench_id, entry_date))
        # Sad case, not found at all.
        return None
    if len(tbs) == 1:
        # Happy case, no need to match pages.
        print('Match 1 on trench id: {}, year: {}'.format(trench_id, entry_date))
        return tbs[0].uuid
    # OK, now try to narrow down by pages
    tb_uuids = [m.uuid for m in tbs]
    ass_starts = Assertion.objects.filter(
        uuid__in=tb_uuids,
        predicate_uuid=START_PAGE_PRED_UUID,
        data_num__gte=start_page
    )
    st_uuids = [a.uuid for a in ass_starts]
    if len(st_uuids) == 1:
        # We found it by the only matched page start
        return st_uuids[0]
    ass_ends = Assertion.objects.filter(
        uuid__in=tb_uuids,
        predicate_uuid=START_PAGE_PRED_UUID,
        data_num__gte=start_page
    )
    end_uuids = [a.uuid for a in ass_ends]
    if len(end_uuid) == 1:
        # We found it by the only matched page end
        return end_uuids[0]
    both_uuids = [uuid for uuid in st_uuids if uuid in end_uuids]
    if len(both_uuids) > 0:
        # Return the first match
        return both_uuids[0]
    return None

def db_lookup_smallfind(project_uuid, trench_id, year, locus_id, find_number):
    """Looks up a small find record from the Manifest."""
    man_objs = Manifest.objects.filter(
        project_uuid=project_uuid,
        item_type='subjects',
        class_uri='oc-gen:cat-sample',
        label__contains=year
    ).filter(
        label__contains=trench_id
    ).filter(
        label__endswith='-{}-{}'.format(locus_id, find_number)
    )
    if len(man_objs) == 1:
        # We have an exact match.
        return man_objs[0].uuid
    return None

def make_catalog_small_finds_links_df(project_uuid, dfs, all_contexts_df):
    """Makes dataframe for a catalog links to trench book entries"""
    obj_prop_cols = [
        'Trench ID',
        'Year',
        'Locus ID',
        'Field Given Find ID',
    ]
    df_link = dfs[CATALOG_ATTRIBUTES_SHEET].copy().reset_index(drop=True)
    df_link['subject_uuid'] = df_link['_uuid']
    df_link[LINK_RELATION_TYPE_COL] = 'Initially documented as'
    for i, row in df_link[df_link['Field Given Find ID'].notnull()].iterrows():
        object_uuid = None
        object_source = None
        find_num = int(float(row['Field Given Find ID']))
        small_finds_indx = (
            (all_contexts_df['Trench ID'] == row['Trench ID'])
            & (all_contexts_df['Year'] == row['Year'])
            & (all_contexts_df['Locus ID'] == row['Locus ID'])
            & (all_contexts_df['Find Number'] == find_num)
        )
        if not all_contexts_df[small_finds_indx].empty:
            # Choose the first match, no need to get too fussy if
            # there are multiple matches.
            object_uuid = all_contexts_df[small_finds_indx]['context_uuid'].iloc[0]
            object_source = all_contexts_df[small_finds_indx]['uuid_source'].iloc[0]
        else:
            # Try looking in the database for a match
            object_uuid = db_lookup_smallfind(
                project_uuid,
                row['Trench ID'],
                row['Year'],
                row['Locus ID'],
                find_num
            )
            if object_uuid is not None:
                object_source = UUID_SOURCE_OC_LOOKUP
        print('Catalog small find lookup: {}-{}-{}-{} -> {}'.format(
                row['Year'],
                row['Trench ID'],
                row['Locus ID'],
                find_num,
                object_uuid,
            )
        )
        if object_uuid is None:
            # No match, just continue
            continue
        sub_indx = (df_link['subject_uuid'] == row['subject_uuid'])
        df_link.loc[sub_indx, 'object_uuid'] = object_uuid
        df_link.loc[sub_indx, 'object_uuid_source'] = object_source
    
    df_link = df_link[
        (
            ['label', 'class_uri', 'uuid_source', 'subject_uuid']
            + [LINK_RELATION_TYPE_COL]
            + ['object_uuid', 'object_uuid_source']
            + obj_prop_cols
        )
    ]
    return df_link

def make_catalog_tb_links_df(project_uuid, dfs, tb_df):
    """Makes dataframe for a catalog links to trench book entries"""
    obj_prop_cols = [
        'Trench ID',
        'Year',
        'Trench Book Entry Date',
        'Trench Book Start Page',
        'Trench Book End Page'
    ]
    df_link = dfs[CATALOG_ATTRIBUTES_SHEET].copy().reset_index(drop=True)
    df_link['subject_uuid'] = df_link['_uuid']
    df_link[LINK_RELATION_TYPE_COL] = 'Has Related Trench Book Entry'
    trench_doc_uuids = {}
    for i, row in df_link.iterrows():
        object_uuid = None
        object_source = None
        tb_indx = (
            (tb_df['Trench ID'] == row['Trench ID'])
            & (tb_df['Entry Year'] == row['Year'])
            # & (tb_df['Date Documented'] == row['Trench Book Entry Date'])
            & (tb_df['Start Page'] >= row['Trench Book Start Page'])
            & (tb_df['End Page'] <= row['Trench Book End Page'])
        )
        if not tb_df[tb_indx].empty:
            # Choose the first match, no need to get too fussy if
            # there are multiple matches.
            object_uuid = tb_df[tb_indx]['_uuid'].iloc[0]
            object_source = UUID_SOURCE_KOBOTOOLBOX
        else:
            # Try looking in the database for a match
            trench_id = row['Trench ID']
            if not trench_id in trench_doc_uuids:
                trench_doc_uuids[trench_id] = db_lookup_trenchbooks_linked_to_trench_id(
                    project_uuid,
                    trench_id
                )
            doc_uuids = trench_doc_uuids[trench_id]
            object_uuid = db_lookup_trenchbook(
                project_uuid,
                doc_uuids,
                row['Trench ID'],
                row['Year'],
                row['Trench Book Entry Date'],
                row['Trench Book Start Page'],
                row['Trench Book End Page']
            )
            if object_uuid is not None:
                object_source = UUID_SOURCE_OC_LOOKUP
        if object_uuid is None:
            # No match, just continue
            continue
        sub_indx = (df_link['subject_uuid'] == row['subject_uuid'])
        df_link.loc[sub_indx, 'object_uuid'] = object_uuid
        df_link.loc[sub_indx, 'object_uuid_source'] = object_source
    
    df_link = df_link[
        (
            ['label', 'class_uri', 'uuid_source', 'subject_uuid']
            + [LINK_RELATION_TYPE_COL]
            + ['object_uuid', 'object_uuid_source']
            + obj_prop_cols
        )
    ]
    return df_link

def get_links_from_rel_ids(project_uuid, dfs, all_contexts_df):
    """Gets links from the related links sheet"""
    df_rel = dfs[CATALOG_RELS_SHEET]
    df_rel.rename(
        columns=RELS_RENAME_COLS,
        inplace=True
    )
    # Join in metadata about the subjects (the catalog object entities)
    subject_uuids = df_rel['subject_uuid'].unique().tolist()
    df_all_parents = dfs[CATALOG_ATTRIBUTES_SHEET].copy().reset_index(drop=True)
    df_all_parents['subject_uuid'] = df_all_parents['_uuid']
    df_all_parents = df_all_parents[df_all_parents['subject_uuid'].isin(subject_uuids)]
    df_all_parents = df_all_parents[['label', 'class_uri', 'uuid_source', 'subject_uuid']]
    df_rel = pd.merge(
        df_rel,
        df_all_parents,
        how='left',
        on=['subject_uuid']
    )
    # Now look up the UUIDs for the objects.
    for i, row in df_rel.iterrows():
        object_uuid = None
        object_uuid_source = None
        raw_object_id = row['object__Related ID']
        object_type = row['object__Related Type']
        act_labels = [str(raw_object_id)]
        act_prefixes, act_classes = REL_PREFIXES.get(object_type, ([], []))
        if len(act_classes) == 0:
            # Didn't find any classes in our object type lookup, so continue
            continue
        act_labels += [p + str(raw_object_id) for p in act_prefixes]
        context_indx = (
            all_contexts_df['label'].isin(act_labels)
            & all_contexts_df['class_uri'].isin(act_classes)
        )
        if not all_contexts_df[context_indx].empty:
            object_uuid = all_contexts_df[context_indx]['context_uuid'].iloc[0]
            object_uuid_source = all_contexts_df[context_indx]['uuid_source'].iloc[0]
        if object_uuid is None:
            man_obj = Manifest.objects.filter(
                project_uuid=project_uuid,
                label__in=act_labels,
                class_uri__in=act_classes
            ).first()
            if man_obj is not None:
                object_uuid = man_obj.uuid
                object_uuid_source = UUID_SOURCE_OC_LOOKUP
        # Now update the df_rel values.
        if object_uuid is None:
            object_uuid = np.nan
            object_uuid_source = np.nan
        update_indx = (
            (df_rel['object__Related ID'] == raw_object_id)
            & (df_rel['object__Related Type'] == object_type)
        )
        df_rel.loc[update_indx, 'object_uuid'] = object_uuid
        df_rel.loc[update_indx, 'object_uuid_source'] = object_uuid_source
    return df_rel

def make_catalog_links_df(project_uuid, dfs, tb_df, all_contexts_df):
    """Makes a dataframe for catalog object linking relations"""
    df_small_finds_link = make_catalog_small_finds_links_df(
        project_uuid,
        dfs,
        all_contexts_df
    )
    df_tb_link = make_catalog_tb_links_df(
        project_uuid,
        dfs,
        tb_df
    )
    df_rel = get_links_from_rel_ids(
        project_uuid,
        dfs,
        all_contexts_df
    )
    df_all_links = pd.concat([df_small_finds_link, df_tb_link, df_rel])
    df_all_links = reorder_first_columns(
        df_all_links,
        FIRST_LINK_REL_COLS
    )
    return df_all_links

def prepare_catalog(project_uuid, excel_dirpath):
    """Prepares catalog dataframes."""
    dfs = None
    for excel_filepath in list_excel_files(excel_dirpath):
        if not 'Catalog' in excel_filepath:
            continue
        dfs = read_excel_to_dataframes(excel_filepath)
        df_f = dfs[CATALOG_ATTRIBUTES_SHEET]
        df_f = drop_empty_cols(df_f)
        df_f = update_multivalue_columns(df_f)
        df_f = clean_up_multivalue_cols(df_f)
        dfs[CATALOG_ATTRIBUTES_SHEET] = df_f
    return dfs
        

    