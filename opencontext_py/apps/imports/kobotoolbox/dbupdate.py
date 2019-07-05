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
from opencontext_py.apps.ocitems.assertions.sorting import AssertionSorting
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
from opencontext_py.apps.imports.sources.finalize import FinalizeImport

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
    REPROJECTED_LAT_COL,
    REPROJECTED_LON_COL,
)
from opencontext_py.apps.imports.kobotoolbox.contexts import (
    PATH_CONTEXT_COLS
)
from opencontext_py.apps.imports.kobotoolbox.kobofields import KoboFields
from  opencontext_py.apps.imports.kobotoolbox.media import (
    OPENCONTEXT_MEDIA_TYPES
)

DB_LOAD_RESULT_A_COL = 'OC_DB_LOAD_OK'
DB_LOAD_RESULT_B_COL = 'OC_DB_LOAD_B_OK'
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

MEDIA_FILETYPE_ATTRIBUTE_CONFIGS = [
    {
        'source-column': file_type['col'],
        'sources': ['all-media',],
        'match_type': 'exact',
        'field_args': {
            'label': file_type['col'],
            'field_type': 'media',
            'field_value_cat': file_type['file_type']
        },
        'field_rel': {
            'predicate': ImportFieldAnnotation.PRED_MEDIA_PART_OF,
        },
    }
    for file_type in OPENCONTEXT_MEDIA_TYPES
]

GEO_ATTRIBUTE_CONFIGS = [
    {
        'source-column': REPROJECTED_LAT_COL,
        'sources': ['catalog', 'locus', 'bulk-finds', 'small-finds', 'trench-book',],
        'match_type': 'exact',
        'field_args': {
            'label': REPROJECTED_LAT_COL,
            'field_type': 'lat',
            'field_value_cat': 'xsd:double',
        },
        'field_rel': {
            'predicate': ImportFieldAnnotation.PRED_GEO_LOCATION,
        },
    },
    {
        'source-column': REPROJECTED_LON_COL,
        'sources': ['catalog', 'locus', 'bulk-finds', 'small-finds', 'trench-book',],
        'match_type': 'exact',
        'field_args': {
            'label': REPROJECTED_LON_COL,
            'field_type': 'lon',
            'field_value_cat': 'xsd:double',
        },
        'field_rel': {
            'predicate': ImportFieldAnnotation.PRED_GEO_LOCATION,
        },
    },
]

DF_ATTRIBUTE_CONFIGS = MEDIA_FILETYPE_ATTRIBUTE_CONFIGS + GEO_ATTRIBUTE_CONFIGS + [
    
    {
        'source-column': 'label',
        'sources': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Locus Label',
            'is_keycell': True,
            'field_type': 'subjects',
            'field_value_cat': 'oc-gen:cat-locus'
        },
        'subject_pk': True,
    },
    
    {
        'source-column': 'label',
        'sources': ['bulk-finds',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Bulk Find Label',
            'is_keycell': True,
            'field_type': 'subjects',
            'field_value_cat': 'oc-gen:cat-sample-col'
        },
        'subject_pk': True,
    },
    
    {
        'source-column': 'label',
        'sources': ['small-finds',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Small Find Label',
            'is_keycell': True,
            'field_type': 'subjects',
            'field_value_cat': 'oc-gen:cat-sample'
        },
        'subject_pk': True,
    },
    
    {
        'source-column': 'label',
        'sources': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Object Label',
            'is_keycell': True,
            'field_type': 'subjects',
            'field_value_cat': 'oc-gen:cat-object'
        },
        'subject_pk': True,
    },
    
    {
        'source-column': 'Trench Book Title',
        'sources': ['trench-book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Trench Book Title',
            'is_keycell': True,
            'field_type': 'documents',
            'field_value_cat': ''
        },
        'subject_pk': True,
    },
    
    {
        'source-column': 'Entry Text',
        'sources': ['trench-book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Entry Text',
            
            'field_type': 'documents',
            'field_value_cat': 'oc-gen:document-text'
        },
        'field_rel': {
            'predicate': 'oc-gen:document-text',
        },
    },
    
    {
        'source-column': 'File Title',
        'sources': ['all-media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'File Title',
            'is_keycell': True,
            'field_type': 'media',
            'field_value_cat': ''
        },
        'subject_pk': True,
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
        'field_rel': {
            'predicate': 'oc-9',  # Catalogued by
        },
    },
    
    {
        'source-column': 'Data Entry Person',
        'sources': ['all-media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'File Creator',
            'field_type': 'persons',
            'field_data_type': 'id',
            'field_value_cat': ''
        },
        'field_rel': {
            'predicate': 'oc-14',  # Photographed by
        },
    },
    
    {
        'source-column': 'File Creator',
        'sources': ['all-media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'File Creator',
            'field_type': 'persons',
            'field_data_type': 'id',
            'field_value_cat': ''
        },
        'field_rel': {
            'predicate': 'oc-14',  # Photographed by
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
        'field_rel': {
            'predicate': 'oc-28',  # Principal Author / Analyst
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
    },
    
    {
        'source-column': 'Description',
        'sources': ['catalog', 'all-media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Description',
            'f_uuid': '7DBB5CB7-599F-42D5-61EE-1955CF898990',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
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
    },

    {
        'source-column': 'Find Spot/Grid X',
        'sources': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid (X)',
            'f_uuid': 'b428ff04-670b-4912-a237-ad8ff9635f5a',
            'field_type': 'description',
            'field_data_type': 'xsd:double',
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
            'field_data_type': 'xsd:double',
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
            'field_data_type': 'xsd:double',
        },
    },
    
    {
        'source-column': 'Find Spot/Measurement Uncertainties/Grid X Uncertainty (+/- cm)',
        'sources': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid X Uncertainty (+/- cm)',
            
            'field_type': 'description',
            'field_data_type': 'xsd:double',
        },
    },
    
    {
        'source-column': 'Find Spot/Measurement Uncertainties/Grid Y Uncertainty (+/- cm)',
        'sources': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid Y Uncertainty (+/- cm)',
            
            'field_type': 'description',
            'field_data_type': 'xsd:double',
        },
    },
    
    {
        'source-column': 'Find Spot/Measurement Uncertainties/Elevation Uncertainty (+/- cm)',
        'sources': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Elevation Uncertainty (+/- cm)',
            
            'field_type': 'description',
            'field_data_type': 'xsd:double',
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
    },
    
    {
        'source-column': 'Object Count',
        'sources': ['bulk-finds',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Object Count',
            'f_uuid': '84525f14-5e20-4765-a74e-303a5dbb4db8',
            'field_type': 'description',
            'field_data_type': 'xsd:double',
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
    },
    
    {
        'source-column': 'Entry Type',
        'sources': ['trench-book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Entry Type',
            
            'field_type': 'description',
            'field_data_type': 'id',
        },
    },
    
    {
        'source-column': 'Document Type',
        'sources': ['trench-book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Document Type',
            
            'field_type': 'description',
            'field_data_type': 'id',
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
    },
    
    {
        'source-column': 'Entry Year',
        'sources': ['trench-book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Entry Year',
            'field_type': 'description',
            'field_data_type': 'xsd:integer',
        },
    },
    
    {
        'source-column': 'Book Year',
        'sources': ['trench-book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Book Year',
            'field_type': 'description',
            'field_data_type': 'xsd:integer',
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
    },
    
    {
        'source-column': 'Date Created',
        'sources': ['all-media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Created',
            'f_uuid': 'e4671bb6-094d-4001-bb10-32685a168bc1',
            'field_type': 'description',
            'field_data_type': 'xsd:date',
        },
    },
    
    {
        'source-column': 'Direction or Orientation Notes/Direction Faced in Field',
        'sources': ['all-media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Direction Faced in Field',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
    },
    
    {
        'source-column': 'Direction or Orientation Notes/Object Orientation Note',
        'sources': ['all-media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Object Orientation Note',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
    },
    
    {
        'source-column': 'Direction or Orientation Notes/Object Orientation Note',
        'sources': ['all-media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Object Orientation Note',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
    },
    
    {
        'source-column': 'Image Type',
        'sources': ['all-media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Image Type',
            'f_uuid': 'B8556EAA-CF52-446B-39FA-AE4798C13A6B',
            'field_type': 'description',
            'field_data_type': 'id',
        },
    },
    
    {
        'source-column': 'Images/Note about Primary Image',
        'sources': ['all-media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Description',
            'f_uuid': '7DBB5CB7-599F-42D5-61EE-1955CF898990',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
    },
    
    {
        'source-column': 'Images/Supplemental Files/Note about Supplemental Image',
        'sources': ['all-media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Description',
            'f_uuid': '7DBB5CB7-599F-42D5-61EE-1955CF898990',
            'field_type': 'description',
            'field_data_type': 'xsd:string',
        },
    },
    
    {
        'source-column': 'Media Type',
        'sources': ['all-media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Media Type',
            'field_type': 'description',
            'field_data_type': 'id',
        },
    },
    
]

LINK_REL_PRED_MAPPINGS = {
    # This describes mappings between link/relation types extrated and derived from the
    # source data from Kobo and predicate_uuid identifiers for use in the Open Context
    # Assertions table. This dictionary is keyed by a text string of link/relation types.
    # The tuple value for each key expresses the predicate_uuid for the
    # subject -> pred[0] -> object relation, as well as the inverse assertion for a relationship
    # between an object -> pred[1] -> subject relationship.
    'link': (Assertion.PREDICATES_LINK, Assertion.PREDICATES_LINK),
    'Is Part of': ('0BB889F9-54DD-4F70-5B63-F5D82425F0DB', 'BD384F1F-FB29-4A9D-7ACA-D8F6B4AF0AF9'),
    'Has Part': ('BD384F1F-FB29-4A9D-7ACA-D8F6B4AF0AF9', '0BB889F9-54DD-4F70-5B63-F5D82425F0DB'),
    'Previous Entry': ('fd94db54-c6f8-484b-9aa6-e0aacc9d132d', None, ),
    'Next Entry': ('50472e1c-2825-47cf-a69c-803b78f8891a', None, ),
    'Stratigraphy: Same/Same as Locus': ('254ea71a-ca2b-4568-bced-f82bf12cb2f9', '254ea71a-ca2b-4568-bced-f82bf12cb2f9'),
    'Same as': ('254ea71a-ca2b-4568-bced-f82bf12cb2f9', '254ea71a-ca2b-4568-bced-f82bf12cb2f9'),
    'Stratigraphy: Contemporary/Contemporary with Locus': ('eee95a2a-c3f8-4637-b67a-f4ff6ea4ee53', 'eee95a2a-c3f8-4637-b67a-f4ff6ea4ee53'),
    'Stratigraphy: Above/Above Locus': ('7895f4a8-d7e0-4219-bb47-9eef76c4acc0', '04a9d0b0-0ff8-412e-b134-23f705e666ca'),
    'Stratigraphy: Below/Below Locus': ('04a9d0b0-0ff8-412e-b134-23f705e666ca', '7895f4a8-d7e0-4219-bb47-9eef76c4acc0'),
    'Stratigraphy: Overlies/Overlies Locus': ('f2fd2edb-4505-447a-9403-13c18150d1d2', None),
    'Stratigraphic Relations: Cuts/Cuts Locus': ('0d5daed7-873d-4415-a0eb-3e7ddf7f25f7', None),
    'Objects join, refit together': ('5E41E490-0618-4D15-0826-38E3B4681C58', '5E41E490-0618-4D15-0826-38E3B4681C58'),
    'Additional ID': ('d58724ee-ecb9-4c2c-87a1-02f853edc2f2', '17012df0-ef2f-41a8-b8d6-ddf5b6687a7e'),
    'Associated in Context': ('3d4a7baa-8b52-4363-9a10-3f3a70cf919c', '3d4a7baa-8b52-4363-9a10-3f3a70cf919c'),
    'Has Related Trench Book Entry': ('f20e9e2e-246f-4421-b1dd-e31e8b58805c', Assertion.PREDICATES_LINK),
    'Related Open Locus': ('b0149b7c-88c8-4913-b6c8-81375239e71f', 'f20e9e2e-246f-4421-b1dd-e31e8b58805c'),
    'Related Small Find': (Assertion.PREDICATES_LINK, 'f20e9e2e-246f-4421-b1dd-e31e8b58805c'),
    'Initially documented as': ('d58724ee-ecb9-4c2c-87a1-02f853edc2f2', '17012df0-ef2f-41a8-b8d6-ddf5b6687a7e'),
}


# ---------------------------------------------------------------------
# CONTEXT (item_type: subjects) RELATED FUNCTIONS
# ---------------------------------------------------------------------

def load_context_row(project_uuid, source_id, row):
    """Loads a context record row into the database"""
    parent_man_obj = Manifest.objects.filter(
        uuid=row['parent_uuid']
    ).first()
    if parent_man_obj is None:
        print('Cannot find parent_uuid {} for uuid {}'.format(
                row['parent_uuid'],
                row['context_uuid']
            )
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
            & (context_df[DB_LOAD_RESULT_A_COL] != True)
        )
    elif parent_uuids is not None:
        p_index = (
            (context_df['parent_uuid'].isin(parent_uuids))
            & (context_df[DB_LOAD_RESULT_A_COL] != True)
        )
    context_df.sort_values(
        by=(PATH_CONTEXT_COLS + ['label']),
        na_position='first',
        inplace=True,
    )
    existing_man_objs = Manifest.objects.filter(
        uuid__in=context_df[p_index]['context_uuid'].unique().tolist()
    )
    existing_uuids = [m.uuid for m in existing_man_objs]
    for i, row in context_df[p_index].iterrows():
        uuid = row['context_uuid']
        if uuid in existing_uuids:
            # This uuid already exists, so do NOT import it.
            continue
        act_indx = (context_df['context_uuid'] == uuid)
        load_ok = load_context_row(project_uuid, source_id, row)
        context_df.loc[act_indx, DB_LOAD_RESULT_A_COL] = load_ok
    return context_df

def update_contexts_subjects(project_uuid, source_id, all_contexts_df):
    """Updates the database to have subjects and contexts """
    print('Unimport project: {}, source: {}'.format(project_uuid, source_id))
    unimp = UnImport(source_id, project_uuid)
    unimp.delete_ok = True
    unimp.delete_all()
    update_indx = (
        all_contexts_df['parent_uuid'].notnull()
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
    new_contexts_df[DB_LOAD_RESULT_A_COL] = np.nan
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
    
    # Now sort the assertions we just created.
    # Now sort the assertions for the items just impacted.
    asor = AssertionSorting()
    asor.re_rank_assertions_by_source(project_uuid, source_id)
    
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
    # NOTE: This has the assumption that a column has a "primary key",
    # of the main entity that gets description. Descriptions and other
    # relationships between columns by default use the "primary key"
    # column as subject of a relationship.
    defalut_field_args = {
        'field_type': 'ignore',
        'field_data_type': '',
    }
    
    kfs = KoboFields()
    cols = df.columns.tolist()
    pk_field_num = None
    field_rels = []
    for field_num, col in enumerate(cols, 1):
        if col in kfs.fields:
            # This is a kobo metadata field, to be 
            field_rels.append(
                {
                    'predicate': ImportFieldAnnotation.PRED_METADATA,
                    'subject_field_num': field_num,
                }
            )
            # Skip fields configured in KoboFields.
            continue
        field_args = None
        field_rel = None
        for config in attribute_col_configs:
            # Default to ignore
            if (source_type in config['sources']
                and (col == config['source-column']
                    or (col.startswith(config['source-column'])
                        and config['match_type'] == 'startswith')
                    )
                ):
                field_args = config['field_args'].copy()
                if config.get('subject_pk'):
                    pk_field_num = field_num
                if config.get('field_rel'):
                    field_rel = config['field_rel']
                    if field_rel.get('predicate') == ImportFieldAnnotation.PRED_MEDIA_PART_OF:
                        # A media file type column is the subject, the primary key field is obj.
                        field_rel['subject_field_num'] = field_num
                    elif field_rel.get('predicate') == ImportFieldAnnotation.PRED_GEO_LOCATION:
                        # A geospatial type column is the subject, the primary key field is obj.
                        field_rel['subject_field_num'] = field_num
                    else:
                        field_rel['object_field_num'] = field_num
                elif field_args.get('field_type') == 'description':
                    field_rel = {
                        'predicate': ImportFieldAnnotation.PRED_DESCRIBES,
                        'subject_field_num': field_num,
                    }
                # Don't break, incase a more specific config
                # is waiting.
        # Now update the field.
        if field_args is None:
            # We didn't find any specific config, so we will ignore
            # the column.
            field_args = defalut_field_args.copy()
        else:
            print('Found {} config for {}'.format(source_type, col))
        
        # Update the column with configutations 
        ImportField.objects.filter(
            project_uuid=project_uuid,
            source_id=source_id,
            ref_orig_name=col,
            field_num=field_num,
        ).update(**field_args)
        
        if field_rel is not None:
            field_rels.append(field_rel)
    
    # Now add configured relationship annotations between fields
    if pk_field_num is None or not len(field_rels):
        return None
    for field_rel in field_rels:
        # Use the specified subject field num, or default to the
        # source table's pk_field_num.
        subject_field_num = field_rel.get('subject_field_num', pk_field_num)
        object_field_num = field_rel.get('object_field_num', pk_field_num)
        # Just to be sure, delete prior links between these fields for
        # this source.
        ImportFieldAnnotation.objects.filter(
            source_id=source_id,
            project_uuid=project_uuid,
            field_num=subject_field_num,
            object_field_num=object_field_num,
        ).delete()
        # Now create the linkage
        imp_fa = ImportFieldAnnotation()
        imp_fa.source_id = source_id
        imp_fa.project_uuid = project_uuid
        # Use the specified subject field num, or default to the
        # source table's pk_field_num.
        imp_fa.field_num = subject_field_num
        imp_fa.predicate = field_rel['predicate']
        imp_fa.predicate_field_num = field_rel.get('predicate_field_num', 0)
        imp_fa.object_field_num = object_field_num
        imp_fa.save()
            
    
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

def load_attribute_data_into_oc(
    project_uuid,
    source_id,
):
    fi = FinalizeImport(source_id)
    if not fi.project_uuid:
        raise RuntimeError('Problem with import source: {}'.format(source_id))
    fi.reset_state()
    import_done = False
    print('Start import into Open Context: {}'.format(source_id))
    while not import_done:
        fi = FinalizeImport(source_id)
        fi.batch_size = (settings.IMPORT_BATCH_SIZE * 10)
        output = fi.process_current_batch()
        import_done = fi.done
    print('Completed import into Open Context: {}'.format(source_id))


def purge_prior_link_rel_import(project_uuid, source_id):
    """Deletes a prior import of linking relation data from a source"""
    Assertion.objects.filter(
        project_uuid=project_uuid,
        source_id=source_id
    ).delete()


def validate_pred_uuid(predicate_uuid):
    """Validates a predicate_uuid to make sure it is actually usable"""
    if predicate_uuid is None:
        # We're OK with None, we just skip import.
        return True
    pred_man = Manifest.objects.filter(uuid=predicate_uuid, item_type='predicates').first()
    if pred_man:
        return True
    pred_ok = Assertion.objects.filter(predicate_uuid=predicate_uuid).first()
    if pred_ok:
        return True
    # We could not validate the use of this predicate uuid.
    return False


def add_link_assertion(
    project_uuid,
    source_id,
    subj_man_obj,
    predicate_uuid,
    obj_man_obj,
    obs_num=1,
    sort=0,
):

    if not subj_man_obj or not obj_man_obj or not predicate_uuid:
        # Skip out, we have some None objects, so no assertion
        return None
    ass = Assertion()
    ass.uuid = subj_man_obj.uuid
    ass.subject_type = subj_man_obj.item_type
    ass.project_uuid = project_uuid
    ass.source_id = source_id
    ass.obs_node = '#obs-' + str(obs_num)
    ass.obs_num =  obs_num
    ass.sort = sort
    ass.visibility = 1
    ass.predicate_uuid = predicate_uuid
    ass.object_uuid = obj_man_obj.uuid
    ass.object_type = obj_man_obj.item_type
    try:
        ass.save()
        return True
    except:
        return False
    
        

def load_link_relations_df_into_oc(
    project_uuid,
    source_id,
    df,
    subject_uuid_col='subject_uuid',
    link_rel_col=LINK_RELATION_TYPE_COL,
    object_uuid_col='object_uuid',
    link_rel_pred_mappings=LINK_REL_PRED_MAPPINGS,
):
    """Loads a link relations dataframe into Open Context."""
    df[DB_LOAD_RESULT_A_COL] = np.nan
    df[DB_LOAD_RESULT_B_COL] = np.nan
    # First, purge any prior import of this source
    print('Purge any prior import of {} to project_uuid: {}'.format(
            source_id,
            project_uuid
        )
    )
    purge_prior_link_rel_import(project_uuid, source_id)
    
    # Make a list of all uuids, and associate manifest objects to them, if found
    # in a dictionary, uuid_manifest_objs
    uuid_manifest_objs = {}
    all_uuids = df[df[subject_uuid_col].notnull()][subject_uuid_col].unique().tolist()
    all_uuids += df[df[object_uuid_col].notnull()][object_uuid_col].unique().tolist()
    for man_obj in Manifest.objects.filter(uuid__in=all_uuids):
        uuid_manifest_objs[man_obj.uuid] = man_obj

    # Now process the import.
    valid_predicte_uuids = {}  # validation results for predicate_uuids
    link_types = df[df[link_rel_col].notnull()][link_rel_col].unique().tolist()
    for link_type in link_types:
        if not link_type in link_rel_pred_mappings:
            raise RuntimeError('Need to configure predicate(s) for {}: {}'.format(
                    link_rel_col,
                    link_type
                )
            )
        # Get a tuple of predicate_uuids from the link_rel_pred_mappings configuration.
        # How these get used for assertions (essentially, pred_b is for inverse
        # relations):
        #
        # (1) pred_a is used for: subject_uuid_col -> pred_a -> object_uuid_col
        # (2) pred_b is used for: object_uuid_col -> pred_b -> subject_uuid_col
        #
        pred_a, pred_b = link_rel_pred_mappings[link_type]
        if not validate_pred_uuid(pred_a) or not validate_pred_uuid(pred_b):
            raise RuntimeError('Unrecognized config uuids for {}:{} -> {}, is ok {}; {}, is ok {}'.format(
                    link_rel_col,
                    link_type,
                    pred_a,
                    validate_pred_uuid(pred_a),
                    pred_b,
                    validate_pred_uuid(pred_b)
                )
            )
        
        # Filter the dataframe for subj, links, and objects that are not blank.
        poss_ass_indx = (
            (df[link_rel_col] == link_type)
            & (df[subject_uuid_col].notnull())
            & (df[object_uuid_col].notnull())
        )
        if df[poss_ass_indx].empty:
            # Skip, we've got some blanks.
            continue
        # Now proceed with loading.
        print('Load {} records for link_type: {}'.format(
                len(df[poss_ass_indx].index),
                link_type
            )
        )
        for i, row in df[poss_ass_indx].iterrows():
            s_man_obj = uuid_manifest_objs.get(row[subject_uuid_col])
            o_man_obj = uuid_manifest_objs.get(row[object_uuid_col])
            # Add the main link assertion, if applicable 
            ok_a = add_link_assertion(
                project_uuid,
                source_id,
                s_man_obj,
                pred_a,
                o_man_obj,
            )
            # Now add the inverse link relation, if applicable
            ok_b = add_link_assertion(
                project_uuid,
                source_id,
                o_man_obj,
                pred_b,
                s_man_obj,
                sort= (i * 0.01)
            )
            up_indx = (
                (df[link_rel_col] == link_type)
                & (df[subject_uuid_col] ==row [subject_uuid_col])
                & (df[object_uuid_col] == row[object_uuid_col])
            )
            df.loc[up_indx, DB_LOAD_RESULT_A_COL] = ok_a
            df.loc[up_indx, DB_LOAD_RESULT_B_COL] = ok_b
       
    # Now sort the assertions for the items just impacted.
    asor = AssertionSorting()
    asor.re_rank_assertions_by_source(project_uuid, source_id)
    return df