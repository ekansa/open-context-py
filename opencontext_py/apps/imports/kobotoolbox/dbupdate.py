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

from opencontext_py.apps.imports.fields.models import ImportField
from opencontext_py.apps.imports.fieldannotations.models import ImportFieldAnnotation
from opencontext_py.apps.imports.records.models import ImportCell
from opencontext_py.apps.imports.sources.models import ImportSource
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
    
    
    
    


    