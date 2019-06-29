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
from opencontext_py.apps.imports.kobotoolbox.kobofields import KoboFields


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
        'source-column': 'label',
        'sources': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Locus Label',
            
            'field_type': 'subjects',
            'field_value_cat': 'oc-gen:cat-locus'
        },
        'subject_col': True,
        'field_rels': {
            
        },
    },
    
    {
        'source-column': 'label',
        'sources': ['bulk-finds',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Bulk Find Label',
            
            'field_type': 'subjects',
            'field_value_cat': 'oc-gen:cat-sample-col'
        },
        'subject_col': True,
        'field_rels': {
            
        },
    },
    
    {
        'source-column': 'label',
        'sources': ['small-finds',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Small Find Label',
            
            'field_type': 'subjects',
            'field_value_cat': 'oc-gen:cat-sample'
        },
        'subject_col': True,
        'field_rels': {
            
        },
    },
    
    {
        'source-column': 'label',
        'sources': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Object Label',
            
            'field_type': 'subjects',
            'field_value_cat': 'oc-gen:cat-object'
        },
        'subject_col': True,
        'field_rels': {
            
        },
    },
    
    {
        'source-column': 'Trench Book Title',
        'sources': ['trench-book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Trench Book Title',
            
            'field_type': 'documents',
            'field_value_cat': ''
        },
        'subject_col': True,
        'field_rels': {
            
        },
    },
    
    
    {
        'source-column': 'Data Entry Person',
        'sources': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Data Entry Person',
            
            'field_type': 'persons',
            'field_data_type': 'id',
            'field_value_cat': ''
        },
        'field_rels': {
            
        },
    },
    
    {
        'source-column': 'Trench Supervisor',
        'sources': ['catalog', 'locus', 'bulk-finds', 'small-finds', 'trench-book',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Trench Supervisor',
            
            'field_type': 'persons',
            'field_data_type': 'id',
            'field_value_cat': ''
        },
        'field_rels': {
            
        },
    },

    {
        'source-column': 'Object Type, Title',
        'sources': ['catalog',],
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
        'sources': ['catalog',],
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
        'sources': ['catalog',],
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
        'sources': ['catalog',],
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
        'sources': ['catalog',],
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
        'sources': ['catalog',],
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
        'sources': ['catalog',],
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
        'sources': ['catalog',],
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
        'sources': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Supplemental Find Identification Note',
            
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Munsell Color',
        'sources': ['catalog',],
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
        'sources': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Fabric Category',
            'f_uuid': 'A70236CA-1599-42F5-4A12-ACEC8C423850',
            'field_type': 'description',
            'field_data_type': 'id',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Other Fabric Note',
        'sources': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Other Fabric Note',
            
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Object General Type',
        'sources': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Object Type',  # Note the difference from the source-column!
            'f_uuid': '7DB79382-7432-42A4-FBC5-EF760691905A',
            'field_type': 'description',
            'field_data_type': 'id',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Object Type',
        'sources': ['catalog', 'small-finds',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Object Type', 
            'f_uuid': '7DB79382-7432-42A4-FBC5-EF760691905A',
            'field_type': 'description',
            'field_data_type': 'id',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Decorative Techniques and Motifs/Decorative Technique',
        'sources': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Decorative Technique',
            'f_uuid': 'F07C30BC-6C71-4C97-7893-D61FF6D0B59B',
            'field_type': 'description',
            'field_data_type': 'id',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Decorative Techniques and Motifs/Other Decorative Technique Note',
        'sources': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Other Decorative Technique Note',
            
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Decorative Techniques and Motifs/Motif',
        'sources': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Motif',
            'f_uuid': '9B260671-CBBD-490E-48B0-CDC48F5DF62D',
            'field_type': 'description',
            'field_data_type': 'id',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Decorative Techniques and Motifs/Other Motif Note',
        'sources': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Other Motif Note',
            
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Vessel Form',
        'sources': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Vessel Form',
            'f_uuid': '6A890B60-3811-44AE-A554-CC8245C4D946',
            'field_type': 'description',
            'field_data_type': 'id',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Vessel Part Present',
        'sources': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Vessel Part Present',
            
            'field_type': 'description',
            'field_data_type': 'id',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Vessel Part Present',
        'sources': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Vessel Part Present',
            
            'field_type': 'description',
            'field_data_type': 'id',
        },
        'field_rels': {
                
        },
    },

    {
        'source-column': 'Find Spot/Grid X',
        'sources': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid (X)',
            'f_uuid': 'b428ff04-670b-4912-a237-ad8ff9635f5a',
            'field_type': 'description',
            'field_data_type': 'xsd:decimal',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Find Spot/Grid Y',
        'sources': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid (Y)',
            'f_uuid': '3e0c2eb3-266b-4fa4-ba59-c5c793a1e96d',
            'field_type': 'description',
            'field_data_type': 'xsd:decimal',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Find Spot/Elevation',
        'sources': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Elevation',
            'f_uuid': 'aaa910a0-51c1-472e-9bd6-67e333e63bbd',
            'field_type': 'description',
            'field_data_type': 'xsd:decimal',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Find Spot/Measurement Uncertainties/Grid X Uncertainty (+/- cm)',
        'sources': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid X Uncertainty (+/- cm)',
            
            'field_type': 'description',
            'field_data_type': 'xsd:decimal',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Find Spot/Measurement Uncertainties/Grid Y Uncertainty (+/- cm)',
        'sources': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid Y Uncertainty (+/- cm)',
            
            'field_type': 'description',
            'field_data_type': 'xsd:decimal',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Find Spot/Measurement Uncertainties/Elevation Uncertainty (+/- cm)',
        'sources': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Elevation Uncertainty (+/- cm)',
            
            'field_type': 'description',
            'field_data_type': 'xsd:decimal',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Find Spot/Measurement Uncertainties/Uncertainty Comment',
        'sources': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Measurement Uncertainties Comment',
            
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Find Type',
        'sources': ['bulk-finds',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Find Type',
            'f_uuid': '464b90e2-ce62-4570-bcea-58b7f9b5bb33',
            'field_type': 'description',
            'field_data_type': 'id',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Find Type (Other)',
        'sources': ['bulk-finds',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Find Type (Other)',
            
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Object Count',
        'sources': ['bulk-finds',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Object Count',
            'f_uuid': '84525f14-5e20-4765-a74e-303a5dbb4db8',
            'field_type': 'description',
            'field_data_type': 'xsd:decimal',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Count Type',
        'sources': ['bulk-finds',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Count Type',
            'f_uuid': 'fa2e0286-de17-45e6-959f-9dab8c8cc5f5',
            'field_type': 'description',
            'field_data_type': 'id',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Count Type (Other)',
        'sources': ['bulk-finds',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Count Type (Other)',
            
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'General Description',
        'sources': ['bulk-finds', 'locus'],
        'match_type': 'exact',
        'field_args': {
            'label': 'Description',
            'f_uuid': '7DBB5CB7-599F-42D5-61EE-1955CF898990',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Date Discovered',
        'sources': ['bulk-finds', 'small-finds'],
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Discovered',
            'f_uuid': '23ff0204-2b40-47b4-909a-66ec8d150528',
            'field_type': 'description',
            'field_data_type': 'xsd:date',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Preliminary Phasing',
        'sources': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Preliminary Phasing',
            'f_uuid': 'c2b40ac1-3b8d-4307-b217-c61732236d68',
            'field_type': 'description',
            'field_data_type': 'id',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Munsell Color',
        'sources': ['locus',],
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
        'source-column': 'Date Opened',
        'sources': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Opened',
            'f_uuid': '0ea21cdb-ffab-4b68-9d47-78b180f08162',
            'field_type': 'description',
            'field_data_type': 'xsd:date',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Date Closed',
        'sources': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Closed',
            'f_uuid': '99684fbb-55d5-447a-8159-7d54fea80b50',
            'field_type': 'description',
            'field_data_type': 'xsd:date',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Trench',
        'sources': ['locus',],
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
        'source-column': 'Field Season',
        'sources': ['small-finds',],
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
        'source-column': 'Date Documented',
        'sources': ['trench-book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Trench Book Entry Date',
            'f_uuid': '8b812e4f-edc4-44f1-a88d-4ad358aaf9aa',
            'field_type': 'description',
            'field_data_type': 'xsd:date',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'Start Page',
        'sources': ['trench-book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Start Page',
            'f_uuid': 'BECAD1AF-0245-44E0-CD2A-F2F7BD080443',
            'field_type': 'description',
            'field_data_type': 'xsd:integer',
        },
        'field_rels': {
                
        },
    },
    
    {
        'source-column': 'End Page',
        'sources': ['trench-book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'End Page',
            'f_uuid': '506924AA-B53D-41B5-9D02-9A7929EA6D6D',
            'field_type': 'description',
            'field_data_type': 'xsd:integer',
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

def load_attribute_df_configs(
    project_uuid,
    source_id,
    source_type,
    df,
    attribute_col_configs=DF_ATTRIBUTE_CONFIGS
):
    """Updates ImportFields with configurations"""
    defalut_field_args = {
        'field_type': 'ignore',
        'field_data_type': '',
    }
    kfs = KoboFields()
    cols = df.columns.tolist()
    for field_num, col in enumerate(cols, 1):
        if col in kfs.fields:
            # Skip fields configured in KoboFields.
            continue
        field_args = None
        for config in attribute_col_configs:
            # Default to ignore
            if (source_type in config['sources']
                and (col == config['source-column']
                    or (col.startswith(config['source-column'])
                        and config['match_type'] == 'startswith')
                    )
                ):
                print('Use config for {}'.format(col))
                field_args = config['field_args'].copy()
                break
        if field_args is None:
            field_args = defalut_field_args.copy()
            
        ImportField.objects.filter(
            project_uuid=project_uuid,
            source_id=source_id,
            ref_orig_name=col,
            field_num=field_num,
        ).update(**field_args)
            
    
def load_attribute_df_into_importer(
    project_uuid,
    source_id,
    source_type,
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
    # Now pre-configure the fields
    load_attribute_df_configs(
        project_uuid,
        source_id,
        source_type,
        df
    )
    
    