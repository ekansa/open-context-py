import copy
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
from opencontext_py.apps.ocitems.subjects.generation import SubjectGeneration

from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.records.create import ImportRecords
from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fields.create import ImportFields
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.sources.models import ImportSource
from opencontext_py.apps.imports.sources.create import ImportRefineSource
from opencontext_py.apps.imports.sources.unimport import UnImport

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
from opencontext_py.apps.imports.kobotoolbox.contexts import (
    PATH_CONTEXT_COLS
)


DB_ERROR_COL = 'OC_DB_LOAD_OK'
DEFAULT_OBS_NUM = 1

CLASS_CONTEXT_IMPORT_ORDER = [
    'oc-gen:cat-region',
    'oc-gen:cat-site',
    'oc-gen:cat-area',
    'oc-gen:cat-trench',
    'oc-gen:cat-exc-unit',
    'oc-gen:cat-locus',
    'oc-gen:cat-sample-col',
    'oc-gen:cat-sample',
    'oc-gen:cat-object',
    'oc-gen:cat-arch-element',
    'oc-gen:cat-pottery',
]

DF_ATTRIBUTE_CONFIGS = [
    {
        'source-column': 'Data Entry Person',
        'sources': ['catalog',]
        'match_type': 'exact',
        'field_args': {
            'label': 'Data Entry Person',
            'f_uuid': '',
            'field_type': 'persons',
            'field_data_type': 'id',
            'field_value_cat': ''
        },
        'field_rels': {
            
        },
    },

    {
        'source-column': 'Object Type, Title',
        'sources': ['catalog',]
        'match_type': 'exact',
        'field_args': {
            'label': 'Catalog ID Note',
            'f_uuid': '46c4ea6d-232f-45ec-97f8-3dd2762bcb56',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Size (Notes)',
        'sources': ['catalog',]
        'match_type': 'exact',
        'field_args': {
            'label': 'Size',
            'f_uuid': 'B6D48580-AF49-409C-1172-E27CBA31F235',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Condition (Notes)',
        'sources': ['catalog',]
        'match_type': 'exact',
        'field_args': {
            'label': 'Condition',
            'f_uuid': '4909306F-3102-47A2-66A3-561C296147BB',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Description',
        'sources': ['catalog',]
        'match_type': 'exact',
        'field_args': {
            'label': 'Description',
            'f_uuid': 'DBB5CB7-599F-42D5-61EE-1955CF898990',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Trench ID',
        'sources': ['catalog',]
        'match_type': 'exact',
        'field_args': {
            'label': 'Trench',
            'f_uuid': 'bd3aba0c-672a-4a1e-81ea-5408768ce407',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Date Cataloged',
        'sources': ['catalog',]
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Cataloged',
            'f_uuid': '2d60965b-5151-446c-99b7-402e94e44c25',
            'field_type': 'description',
            'field_data_type': 'xsd:date',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Year',
        'sources': ['catalog',]
        'match_type': 'exact',
        'field_args': {
            'label': 'Year',
            'f_uuid': '2C7FE888-C431-4FBD-39F4-38B7D969A811',
            'field_type': 'description',
            'field_data_type': 'xsd:integer',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Record Type',
        'sources': ['catalog',]
        'match_type': 'exact',
        'field_args': {
            'label': 'Record Type',
            'f_uuid': '609ff344-7304-48e3-8db4-64b47dd12215',
            'field_type': 'description',
            'field_data_type': 'id',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Supplemental Find Identification Note',
        'sources': ['catalog',]
        'match_type': 'exact',
        'field_args': {
            'label': 'Supplemental Find Identification Note',
            'f_uuid': None,
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Munsell Color',
        'sources': ['catalog',]
        'match_type': 'exact',
        'field_args': {
            'label': 'Munsell Color',
            'f_uuid': '9b99354c-55a2-45e0-9bfd-79bd7f2a801a',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Fabric Category',
        'sources': ['catalog',]
        'match_type': 'exact',
        'field_args': {
            'label': 'Fabric Category',
            'f_uuid': 'A70236CA-1599-42F5-4A12-ACEC8C423850',
            'field_type': 'description',
            'field_data_type': 'id',
        },
        'field_rels': {
                
        },
    },

]


# ---------------------------------------------------------------------
# CONTEXT (item_type: subjects) RELATED FUNCTIONS
# ---------------------------------------------------------------------

def load_context_row(project_uuid, source_id, row):
    """Loads a context record row into the database"""
    parent_man_obj = Manifest.objects.filter(
        uuid=row['parent_uuid']
    ).first()
    if parent_man_obj is None:
        print('Cannot find parent_uuid {} for uuid {}').format(
            row['parent_uuid'],
            row['context_uuid']
        )
        # Skip the rest.
        return False
    # OK to continue
    man_obj = Manifest.objects.filter(
        uuid=row['context_uuid']
    ).first()
    if man_obj is None:
        man_obj = Manifest()
    # Set up the new item in the Manifest
    man_obj.uuid = row['context_uuid']
    man_obj.source_id = source_id
    man_obj.label = row['label']
    man_obj.project_uuid = project_uuid
    man_obj.item_type = 'subjects'
    man_obj.class_uri = row['class_uri']
    man_obj.save()
    # Just to be sure, make sure this item does not
    # have any existing parent relations.
    Assertion.objects.filter(
        predicate_uuid=Assertion.PREDICATES_CONTAINS,
        object_uuid=man_obj.uuid,
    ).delete()
    # Now add a context relation to it.
    ass = Assertion()
    ass.uuid = parent_man_obj.uuid
    ass.subject_type = parent_man_obj.item_type
    ass.project_uuid = parent_man_obj.project_uuid
    ass.source_id = source_id
    ass.obs_node = '#contents-{}'.format(DEFAULT_OBS_NUM)
    ass.obs_num =  DEFAULT_OBS_NUM 
    ass.sort = 1
    ass.visibility = 1
    ass.predicate_uuid = Assertion.PREDICATES_CONTAINS
    ass.object_uuid = man_obj.uuid
    ass.object_type = man_obj.item_type
    ass.save()
    sg = SubjectGeneration()
    sg.generate_save_context_path_from_uuid(man_obj.uuid)
    return True

def load_context_dataframe(
    project_uuid,
    source_id,
    context_df,
    class_uri=None,
    parent_uuids=None
):
    """Loads the context dataframe"""
    if class_uri is not None:
        p_index = (
            (context_df['class_uri']==class_uri)
            & (context_df[DB_ERROR_COL] != True)
        )
    elif parent_uuids is not None:
        p_index = (
            (context_df['parent_uuid'].isin(parent_uuids))
            & (context_df[DB_ERROR_COL] != True)
        )
    context_df.sort_values(
        by=(PATH_CONTEXT_COLS + ['label']),
        na_position='first',
        inplace=True,
    )
    for i, row in context_df[p_index].iterrows():
        uuid = row['context_uuid']
        act_indx = (context_df['context_uuid'] == uuid)
        load_ok = load_context_row(project_uuid, source_id, row)
        context_df.loc[act_indx, DB_ERROR_COL] = load_ok
    return context_df

def update_contexts_subjects(project_uuid, source_id, all_contexts_df):
    """Updates the database to have subjects and contexts """
    print('Unimport project: {}, source: {}'.format(project_uuid, source_id))
    unimp = UnImport(source_id, project_uuid)
    unimp.delete_ok = True
    unimp.delete_all()
    # Now start the load.
    unimp = UnImport(source_id, project_uuid)
    unimp.delete_ok = True
    unimp.delete_all()
    update_indx = (
        all_contexts_df['uuid_source'].isin([UUID_SOURCE_KOBOTOOLBOX, UUID_SOURCE_OC_KOBO_ETL])
        & all_contexts_df['parent_uuid'].notnull()
    )
    new_contexts_df = all_contexts_df[update_indx].copy()
    ordered_classes = CLASS_CONTEXT_IMPORT_ORDER.copy()
    ordered_classes += [
        c for c in new_contexts_df['class_uri'].unique().tolist()
        if c not in CLASS_CONTEXT_IMPORT_ORDER
    ]
    new_contexts_df.sort_values(
        by=(PATH_CONTEXT_COLS + ['label']),
        inplace=True,
        na_position='first'
    )
    new_contexts_df[DB_ERROR_COL] = np.nan
    # First Create records for data with a parent in Open Context
    oc_par_index = (new_contexts_df['parent_uuid_source']==UUID_SOURCE_OC_LOOKUP)
    parent_uuids = new_contexts_df[oc_par_index]['parent_uuid'].unique().tolist()
    print('Loading contexts that are children of {} contexts in DB.'.format(
            len(parent_uuids)
        )
    )
    new_contexts_df = load_context_dataframe(
        project_uuid,
        source_id,
        new_contexts_df,
        parent_uuids=parent_uuids
    )
    for class_uri in ordered_classes:
        print('Loading contexts for class_uri: {}'.format(
                class_uri
            )
        )
        new_contexts_df = load_context_dataframe(
            project_uuid,
            source_id,
            new_contexts_df,
            class_uri=class_uri,
        )
    return new_contexts_df
    

# ---------------------------------------------------------------------
# ATTRIBUTES RELATED FUNCTIONS
# Attributes are loaded into the importer that normally gets data from
# an Open Refine source. The following functions load data from a
# dataframe with attributes, sets up the field types and relationships,
# assigns UUIDs where feasible, and imports the data into Open Context.
# The main expecation is that entities receiving attributes have been
# already created. 
# ---------------------------------------------------------------------

def purge_data_from_source(project_uuid, source_id):
    print('Unimport project: {}, source: {}'.format(project_uuid, source_id))
    unimp = UnImport(source_id, project_uuid)
    unimp.delete_ok = True
    unimp.delete_all()
    print('Unimport data from importer project: {}, source: {}'.format(project_uuid, source_id))
    ImportCell.objects.filter(
        project_uuid=project_uuid,
        source_id=source_id,
    ).delete()
    ImportField.objects.filter(
        project_uuid=project_uuid,
        source_id=source_id,
    ).delete()
    ImportFieldAnnotation.objects.filter(
        project_uuid=project_uuid,
        source_id=source_id,
    ).delete()
    ImportSource.objects.filter(
        project_uuid=project_uuid,
        source_id=source_id,
    ).delete()

def load_attribute_df_configs(project_uuid,
    source_id,
    df_configs,
    df
):
    cols = df.columns.tolist()
    
    
    
def load_attribute_df_into_importer(
    project_uuid,
    source_id,
    source_label,
    df
):
    """Loads a dataframe with attribute data into the importer"""
    # Purge any data from a prior import attempt from this source.
    purge_data_from_source(project_uuid, source_id)
    # 1st, make the source object
    impsrc = ImportRefineSource()
    impsrc.source_id = source_id
    impsrc.project_uuid = project_uuid
    impsrc.create_new_dataframe_source(source_label, df)
    # 2nd, add the fields.
    impfields = ImportFields()
    impfields.source_id = source_id
    impfields.project_uuid = project_uuid
    impfields.save_dataframe_fields(source_id, df)
    # 3rd, add the record cells
    imprecs = ImportRecords()
    imprecs.source_id = source_id
    imprecs.project_uuid = project_uuid
    imprecs.save_dataframe_records(source_id, df)
    
    