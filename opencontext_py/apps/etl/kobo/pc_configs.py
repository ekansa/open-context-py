import copy
import os

from pathlib import Path

from opencontext_py.apps.all_items import configs

from opencontext_py.apps.etl.kobo import kobo_oc_configs


PROJECT_UUID = 'df043419-f23b-41da-7e4d-ee52af22f92f'
HOME = str(Path.home())
KOBO_EXCEL_FILES_PATH = f'{HOME}/data-dumps/pc-2022/kobo-data'
MEDIA_FILES_PATH = f'{HOME}/data-dumps/pc-2022/kobo-media-files'
TRENCH_CSV_PATH = f'{HOME}/data-dumps/pc-2022/trenches-2022.csv'
SUBJECTS_CSV_PATH = f'{HOME}/data-dumps/pc-2022/oc-import/subjects.csv'
MEDIA_ALL_KOBO_REFS_CSV_PATH = f'{HOME}/data-dumps/pc-2022/oc-import/all-media-kobo-files.csv'


CATALOG_ATTRIB_CSV_PATH = f'{HOME}/data-dumps/pc-2022/oc-import/catalog-attribs.csv'
CATALOG_LINKS_CSV_PATH = f'{HOME}/data-dumps/pc-2022/oc-import/catalog-links.csv'

SMALL_FINDS_ATTRIB_CSV_PATH = f'{HOME}/data-dumps/pc-2022/oc-import/small-finds-attribs.csv'
SMALL_FINDS_LINKS_CSV_PATH = f'{HOME}/data-dumps/pc-2022/oc-import/small-finds-links.csv'

BULK_FINDS_ATTRIB_CSV_PATH = f'{HOME}/data-dumps/pc-2022/oc-import/bulk-finds-attribs.csv'


LOCUS_ATTRIB_CSV_PATH = f'{HOME}/data-dumps/pc-2022/oc-import/locus-attribs.csv'
LOCUS_LINKS_CSV_PATH = f'{HOME}/data-dumps/pc-2022/oc-import/locus-links.csv'
LOCUS_GEO_CSV_PATH = f'{HOME}/data-dumps/pc-2022/oc-import/locus-geo.csv'
# The column in the Kobo exports with the trench identifier

KOBO_TRENCH_COL = 'Trench ID'

# Trench context mappings:
TRENCH_CONTEXT_MAPPINGS = {
    'CA': {
        'site':'Poggio Civitate',
        'area': 'Civitate A',
    },
    'CB': {
        'site':'Poggio Civitate',
        'area': 'Civitate B',
    },
    'T': {
        'site':'Poggio Civitate',
        'area': 'Tesoro',
    },
    'Agger': {
        'site':'Poggio Civitate',
        'area': 'Agger',
    },
    'VT': {
        'site':'Vescovado di Murlo',
        'area': 'Upper Vescovado',
        'prefix': 'Vescovado',
    },
}


LABEL_ALTERNATIVE_PARTS = {
    # Keyed by project_uuid
    PROJECT_UUID: {
        'PC': ['PC', 'PC '],
        'VDM': ['VDM', 'VdM', 'VdM ']
    },
}


LINK_RELATION_TYPE_COL = 'link_rel'


REL_SUBJECTS_PREFIXES = {
    'Small Find': (
        ['SF '],
        ['oc-gen-cat-sample',],
    ),
    'Cataloged Object': (
        ['PC ', 'VdM ',],
        [
            'oc-gen-cat-object',
            'oc-gen-cat-arch-element',
            'oc-gen-cat-coin',
            'oc-gen-cat-bio-subj-ecofact',
            'oc-gen-cat-pottery',
        ],
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
        ['oc-gen-cat-sample-col',],
    ),
    'Locus': (
        ['Locus ',],
        ['oc-gen-cat-locus',],
    ),
    'Trench': (
        [''],
        ['oc-gen-cat-exc-unit',],
    ),
}




REPROJECTED_LAT_COL = 'REPROJ_LAT'
REPROJECTED_LON_COL = 'REPROJ_LON'
X_Y_GRID_COLS = [
    ('Find Spot/Grid X', 'Find Spot/Grid Y', ),
    ('Grid X', 'Grid Y', ),
]

GRID_GROUPBY_COLS = ['Trench ID']
GRID_PROBLEM_COL = 'GRID_PROBLEM_FLAG'
ATTRIBUTE_HIERARCHY_DELIM = '::'


LOCUS_GRID_COLS = [
    ('Elevations/Elevation', 'Elevation', ),
    ('Elevations/Grid X', 'Grid X',),
    ('Elevations/Grid Y', 'Grid Y',),
    ('Elevations/Measurement Uncertainties/Elevation Uncertainty (+/- cm)', 'Elevation Uncertainty (+/- cm)',),
    ('Elevations/Measurement Uncertainties/Grid X Uncertainty (+/- cm)', 'Grid X Uncertainty (+/- cm)',),
    ('Elevations/Measurement Uncertainties/Grid Y Uncertainty (+/- cm)', 'Grid Y Uncertainty (+/- cm)',),
    ('Elevations/Elevation Type', 'Elevation Type', ),
    ('Elevations/Elevation Location', 'Elevation Location',),
    ('Elevations/Elevation Other Location', 'Elevation Other Location',),
    ('Elevations/Elevation Note', 'Elevation Note',),
    ('_submission__uuid', '_uuid',),
]


MEDIA_FILETYPE_ATTRIBUTE_CONFIGS = [
    {
        'source_col': file_type['col'],
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': file_type['col'],
            'item_type': 'media',
            'item_class_id': file_type['resourcetype']
        },
        'field_rel': {
            'predicate_id': configs.PREDICATE_OC_ETL_MEDIA_HAS_FILES,
        },
    }
    for file_type in kobo_oc_configs.OPENCONTEXT_MEDIA_TYPES
]

GEO_ATTRIBUTE_CONFIGS = [
    {
        'source_col': REPROJECTED_LAT_COL,
        'form_type': ['catalog', 'locus', 'bulk find', 'small find', 'trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': REPROJECTED_LAT_COL,
            'item_type': 'longitude',
            'data_type': 'xsd:double',
        },
        'field_rel': {
            'predicate_id': configs.PREDICATE_OC_ETL_DESCRIBED_BY,
        },
    },
    {
        'source_col': REPROJECTED_LON_COL,
        'form_type': ['catalog', 'locus', 'bulk find', 'small find', 'trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': REPROJECTED_LON_COL,
            'item_type': 'longitude',
            'data_type': 'xsd:double',
        },
        'field_rel': {
            'predicate_id': configs.PREDICATE_OC_ETL_DESCRIBED_BY,
        },
    },
]

DF_ATTRIBUTE_CONFIGS = MEDIA_FILETYPE_ATTRIBUTE_CONFIGS + GEO_ATTRIBUTE_CONFIGS + [
    
    {
        'source_col': 'label',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Locus Label',
            'item_type': 'subjects',
            'item_class_id': '00000000-6e24-600d-a274-f02367a32c33',
        },
        'subject_pk': True,
    },
    
    {
        'source_col': 'label',
        'form_type': ['bulk find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Bulk Find Label',
            'item_type': 'subjects',
            'item_class_id': '00000000-6e24-1147-b189-ad24b8a86f76',
        },
        'subject_pk': True,
    },
    
    {
        'source_col': 'label',
        'form_type': ['small find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Small Find Label',
            'item_type': 'subjects',
            'item_class_id': '00000000-6e24-0b70-0230-0cc0398d6184',
        },
        'subject_pk': True,
    },
    
    {
        'source_col': 'label',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Catalog Label',
            'item_type': 'subjects',
            'item_class_id': '00000000-6e24-2339-9f63-582218c3f76a',
        },
        'subject_pk': True,
    },
    
    {
        'source_col': 'Trench Book Title',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Trench Book Title',
            'item_type': 'documents',
        },
        'subject_pk': True,
    },
    
    {
        'source_col': 'Entry Text',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Entry Text',
            'item_type': 'property',
            'data_type': 'xsd:string',
            # schema:text (The schema.org text property)
            'context_id': '00000000-4ad5-1d91-3710-6f501a79e9f3',
        },
    },
    
    {
        'source_col': 'File Title',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'File Title',
            'item_type': 'media',
        },
        'subject_pk': True,
    },
    
    {
        'source_col': 'Data Entry Person',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Data Entry Person',
            'item_type': 'persons',
            'data_type': 'id',
            'item_class_id': configs.CLASS_FOAF_PERSON_UUID,
        },
        'field_rel': {
            'predicate_id': '0487907f-59a4-ae5d-7e18-5716e8f16baf',  # Catalogued by
        },
    },
    
    {
        'source_col': 'Data Entry Person',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'File Creator',
            'item_type': 'persons',
            'data_type': 'id',
            'item_class_id': configs.CLASS_FOAF_PERSON_UUID,
        },
        'field_rel': {
            'predicate_id': 'd2fe0142-e4c7-9601-5011-08f47580dae1',  # Photographed by
        },
    },
    
    {
        'source_col': 'File Creator',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'File Creator',
            'item_type': 'persons',
            'data_type': 'id',
            'item_class_id': configs.CLASS_FOAF_PERSON_UUID,
        },
        'field_rel': {
            'predicate_id': 'd2fe0142-e4c7-9601-5011-08f47580dae1',  # Photographed by
        },
    },
    
    {
        'source_col': 'Trench Supervisor',
        'form_type': ['catalog', 'locus', 'bulk find', 'small find', 'trench book',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Trench Supervisor',
            'item_type': 'persons',
            'data_type': 'id',
            'item_class_id': configs.CLASS_FOAF_PERSON_UUID,
        },
        'field_rel': {
            'predicate_id': 'b4f7df9b-47a8-5cd4-d2e1-021087f03815',  # Principal Author / Analyst
        },
    },
    
    {
        'source_col': 'Size (Notes)',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Size',
            'context_id': 'b6d48580-af49-409c-1172-e27cba31f235',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Condition (Notes)',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Condition',
            'context_id': '4909306f-3102-47a2-66a3-561c296147bb',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Description',
        'form_type': ['catalog', 'media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Description',
            'context_id': '7dbb5cb7-599f-42d5-61ee-1955cf898990',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Trench ID',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Trench',
            'context_id': 'bd3aba0c-672a-4a1e-81ea-5408768ce407',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Date Cataloged',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Cataloged',
            'context_id': '2d60965b-5151-446c-99b7-402e94e44c25',
            'item_type': 'description',
            'data_type': 'xsd:date',
        },
    },
    
    {
        'source_col': 'Year',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Year',
            'context_id': '2c7fe888-c431-4fbd-39f4-38b7d969a811',
            'item_type': 'description',
            'data_type': 'xsd:integer',
        },
    },
    
    {
        'source_col': 'Record Type',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Record Type',
            'context_id': '609ff344-7304-48e3-8db4-64b47dd12215',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Supplemental Find Identification Note',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Supplemental Find Identification Note',
            'context_id': 'b065bd99-859c-4ac2-ae54-9b1721e25c33',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Munsell Color',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Munsell Color',
            'context_id': '9b99354c-55a2-45e0-9bfd-79bd7f2a801a',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Fabric Category',
        'form_type': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Fabric Category',
            'context_id': 'a70236ca-1599-42f5-4a12-acec8c423850',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Other Fabric Note',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Other Fabric Note',
            'context_id': 'cfb6e3c6-a51f-4da9-a794-dca7b92e56fd',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Object General Type',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Object Type',  # Note the difference from the source-column!
            'context_id': '7db79382-7432-42a4-fbc5-ef760691905a',
            'item_type': 'description',
            'data_type': 'id',
        },
    },

    {
        'source_col': 'Alternative Object General Type',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            # NOTE: This is also mapped to the 'Object Type' predicate.
            'label': 'Object Type',  # Note the difference from the source-column!
            'context_id': '7db79382-7432-42a4-fbc5-ef760691905a',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Object Type',
        'form_type': ['catalog', 'small find',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Object Type', 
            'context_id': '7db79382-7432-42a4-fbc5-ef760691905a',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Object Type, Title',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Catalog ID Note',
            'context_id': '46c4ea6d-232f-45ec-97f8-3dd2762bcb56',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Decorative Techniques and Motifs/Decorative Technique',
        'form_type': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Decorative Technique',
            'context_id': 'f07c30bc-6c71-4c97-7893-d61ff6d0b59b',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Decorative Techniques and Motifs/Other Decorative Technique Note',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Other Decorative Technique Note',
            'context_id': '8cbd3c5a-b3ec-4e3a-b1eb-bf2d53b01781',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Decorative Techniques and Motifs/Motif',
        'form_type': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Motif',
            'context_id': '9b260671-cbbd-490e-48b0-cdc48f5df62d',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Decorative Techniques and Motifs/Other Motif Note',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Other Motif Note',
            'context_id': '5dd0bdb8-782f-42fb-93c4-60018860fb24',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Vessel Form',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Vessel Form',
            'context_id': '6a890b60-3811-44ae-a554-cc8245c4d946',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Vessel Part Present',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Vessel Part Present',
            'context_id': 'c16a0682-5956-4180-af94-9981f937651a',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Vessel Part Present',
        'form_type': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Vessel Part Present',
            'context_id': 'c16a0682-5956-4180-af94-9981f937651a',
            'item_type': 'description',
            'data_type': 'id',
        },
    },

    {
        'source_col': 'Find Spot/Grid X',
        'form_type': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid (X)',
            'context_id': 'b428ff04-670b-4912-a237-ad8ff9635f5a',
            'item_type': 'description',
            'data_type': 'xsd:double',
        },
    },
    
    {
        'source_col': 'Find Spot/Grid Y',
        'form_type': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid (Y)',
            'context_id': '3e0c2eb3-266b-4fa4-ba59-c5c793a1e96d',
            'item_type': 'description',
            'data_type': 'xsd:double',
        },
    },
    
    {
        'source_col': 'Find Spot/Elevation',
        'form_type': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Elevation',
            'context_id': 'aaa910a0-51c1-472e-9bd6-67e333e63bbd',
            'item_type': 'description',
            'data_type': 'xsd:double',
        },
    },
    
    {
        'source_col': 'Find Spot/Measurement Uncertainties/Grid X Uncertainty (+/- cm)',
        'form_type': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid X Uncertainty (+/- cm)',
            'context_id': '074574a6-43bd-4bc4-9bd2-001d44512cc3',
            'item_type': 'description',
            'data_type': 'xsd:double',
        },
    },
    
    {
        'source_col': 'Find Spot/Measurement Uncertainties/Grid Y Uncertainty (+/- cm)',
        'form_type': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid Y Uncertainty (+/- cm)',
            'context_id': '1bb7b997-c572-4fe5-ac89-c372c322ed78',
            'item_type': 'description',
            'data_type': 'xsd:double',
        },
    },
    
    {
        'source_col': 'Find Spot/Measurement Uncertainties/Elevation Uncertainty (+/- cm)',
        'form_type': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Elevation Uncertainty (+/- cm)',
            'context_id': '529e931c-51ed-4d85-9759-5c9d4069dbb6',
            'item_type': 'description',
            'data_type': 'xsd:double',
        },
    },
    
    {
        'source_col': 'Find Spot/Measurement Uncertainties/Uncertainty Comment',
        'form_type': ['catalog', 'small-find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Measurement Uncertainties Comment',
            'context_id': None,
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Find Type',
        'form_type': ['bulk find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Find Type',
            'context_id': '464b90e2-ce62-4570-bcea-58b7f9b5bb33',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Find Type (Other)',
        'form_type': ['bulk find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Find Type (Other)',
            'context_id': '36027b0c-3c4b-49df-9ab0-d110cdb5d9b4',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Object Count',
        'form_type': ['bulk find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Object Count',
            'context_id': '84525f14-5e20-4765-a74e-303a5dbb4db8',
            'item_type': 'description',
            'data_type': 'xsd:double',
        },
    },
    
    {
        'source_col': 'Count Type',
        'form_type': ['bulk find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Count Type',
            'context_id': 'fa2e0286-de17-45e6-959f-9dab8c8cc5f5',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Count Type (Other)',
        'form_type': ['bulk find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Count Type (Other)',
            'context_id': '630e3548-7050-4891-9971-94e91593b74d',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'General Description',
        'form_type': ['bulk find', 'locus'],
        'match_type': 'exact',
        'field_args': {
            'label': 'Description',
            'context_id': '7dbb5cb7-599f-42d5-61ee-1955cf898990',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Date Discovered',
        'form_type': ['bulk find', 'small find'],
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Discovered',
            'context_id': '23ff0204-2b40-47b4-909a-66ec8d150528',
            'item_type': 'description',
            'data_type': 'xsd:date',
        },
    },
    
    {
        'source_col': 'Deposit Compaction',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Deposit Compaction',
            'context_id': '3eb4639d-a67e-47e6-9435-a87723486a82',
            'item_type': 'description',
            'data_type': 'id',
        },
    },

    {
        'source_col': 'Stratigraphic Reliability',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Stratigraphic Reliability',
            'context_id': '1ed85342-864a-4ae9-81ed-3a484233ec43',
            'item_type': 'description',
            'data_type': 'id',
        },
    },

    {
        'source_col': 'Preliminary Phasing',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Preliminary Phasing',
            'context_id': 'c2b40ac1-3b8d-4307-b217-c61732236d68',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Munsell Color',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Munsell Color',
            'context_id': '9b99354c-55a2-45e0-9bfd-79bd7f2a801a',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },

    {
        'source_col': 'Deposit Compaction',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Deposit Compaction',
            'context_id': '3eb4639d-a67e-47e6-9435-a87723486a82',
            'item_type': 'description',
            'data_type': 'id',
        },
    },

    {
        'source_col': 'Stratigraphic Reliability',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Stratigraphic Reliability',
            'context_id': '1ed85342-864a-4ae9-81ed-3a484233ec43',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Date Opened',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Opened',
            'context_id': '0ea21cdb-ffab-4b68-9d47-78b180f08162',
            'item_type': 'description',
            'data_type': 'xsd:date',
        },
    },
    
    {
        'source_col': 'Date Closed',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Closed',
            'context_id': '99684fbb-55d5-447a-8159-7d54fea80b50',
            'item_type': 'description',
            'data_type': 'xsd:date',
        },
    },
    
    {
        'source_col': 'Trench',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Trench',
            'context_id': 'bd3aba0c-672a-4a1e-81ea-5408768ce407',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Field Season',
        'form_type': ['small find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Year',
            'context_id': '2c7fe888-c431-4fbd-39f4-38b7d969a811',
            'item_type': 'description',
            'data_type': 'xsd:integer',
        },
    },
    
    {
        'source_col': 'Entry Type',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Entry Type',
            'context_id': 'eea8648f-7df4-48f6-a58e-2971f001d245',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Document Type',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Document Type',
            'context_id': '565672fe-eee1-4e85-3c66-538137e6d332',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Date Documented',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Trench Book Entry Date',
            'context_id': '8b812e4f-edc4-44f1-a88d-4ad358aaf9aa',
            'item_type': 'description',
            'data_type': 'xsd:date',
        },
    },
    
    {
        'source_col': 'Entry Year',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Entry Year',
            'context_id': '37e30449-43fa-45e0-8142-8e3f6a70441b',
            'item_type': 'description',
            'data_type': 'xsd:integer',
        },
    },
    
    {
        'source_col': 'Book Year',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Book Year',
            'context_id': '8fb4a650-ef81-4238-a75b-603e07dd4455',
            'item_type': 'description',
            'data_type': 'xsd:integer',
        },
    },
    
    {
        'source_col': 'Start Page',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Start Page',
            'context_id': 'becad1af-0245-44e0-cd2a-f2f7bd080443',
            'item_type': 'description',
            'data_type': 'xsd:integer',
        },
    },
    
    {
        'source_col': 'End Page',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'End Page',
            'context_id': '506924aa-b53d-41b5-9d02-9a7929ea6d6d',
            'item_type': 'description',
            'data_type': 'xsd:integer',
        },
    },
    
    {
        'source_col': 'Date Created',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Created',
            'context_id': 'e4671bb6-094d-4001-bb10-32685a168bc1',
            'item_type': 'description',
            'data_type': 'xsd:date',
        },
    },
    
    {
        'source_col': 'Direction or Orientation Notes/Direction Faced in Field',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Direction Faced in Field',
            'context_id': None,
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Direction or Orientation Notes/Object Orientation Note',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Object Orientation Note',
            'context_id': '804bf2fe-043c-4405-bd4a-558a5ffd7d50',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Image Type',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Image Type',
            'context_id': 'b8556eaa-cf52-446b-39fa-ae4798c13a6b',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
    {
        'source_col': 'Images/Note about Primary Image',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Description',
            'context_id': '7dbb5cb7-599f-42d5-61ee-1955cf898990',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Images/Supplemental Files/Note about Supplemental Image',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Description',
            'context_id': '7dbb5cb7-599f-42d5-61ee-1955cf898990',
            'item_type': 'description',
            'data_type': 'xsd:string',
        },
    },
    
    {
        'source_col': 'Media Type',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Media Type',
            'context_id': 'eced82b8-8f45-4ca3-b9f9-b94ddcd3d2ab',
            'item_type': 'description',
            'data_type': 'id',
        },
    },
    
]

LINK_REL_PRED_MAPPINGS = {
    # This describes mappings between link/relation types extracted and derived from the
    # source data from Kobo and predicate_uuid identifiers for use in the Open Context
    # Assertions table. This dictionary is keyed by a text string of link/relation types.
    # The tuple value for each key expresses the predicate_uuid for the
    # subject -> pred[0] -> object relation, as well as the inverse assertion for a relationship
    # between an object -> pred[1] -> subject relationship.
    'link': (configs.PREDICATE_LINK_UUID, configs.PREDICATE_LINK_UUID),
    'Is Part of': ('0bb889f9-54dd-4f70-5b63-f5d82425f0db','bd384f1f-fb29-4a9d-7aca-d8f6b4af0af9'),
    'Has Part': ('bd384f1f-fb29-4a9d-7aca-d8f6b4af0af9', '0bb889f9-54dd-4f70-5b63-f5d82425f0db'),
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
    'Has Related Trench Book Entry': ('f20e9e2e-246f-4421-b1dd-e31e8b58805c', configs.PREDICATE_LINK_UUID),
    'Related Open Locus': ('b0149b7c-88c8-4913-b6c8-81375239e71f', 'f20e9e2e-246f-4421-b1dd-e31e8b58805c'),
    'Related Small Find': (configs.PREDICATE_LINK_UUID, 'f20e9e2e-246f-4421-b1dd-e31e8b58805c'),
    'Initially documented as': ('d58724ee-ecb9-4c2c-87a1-02f853edc2f2', '17012df0-ef2f-41a8-b8d6-ddf5b6687a7e'),
    'Cataloged as': ('17012df0-ef2f-41a8-b8d6-ddf5b6687a7e', 'd58724ee-ecb9-4c2c-87a1-02f853edc2f2'),
    
    # Added for PC 2019
    'Other relation': (configs.PREDICATE_LINK_UUID, configs.PREDICATE_LINK_UUID),
    'Comparanda, based on form': ('46037eb4-c4b7-432b-bebb-500aff0e4fe6', '46037eb4-c4b7-432b-bebb-500aff0e4fe6'),
    'Comparanda, based on motif': ('1c5a1fca-0853-4612-9663-f908d9c081b2', '1c5a1fca-0853-4612-9663-f908d9c081b2'),
}


# Trench book related predicates
TB_ENTRY_DATE_PRED_UUID = '8b812e4f-edc4-44f1-a88d-4ad358aaf9aa'
TB_START_PAGE_PRED_UUID = 'becad1af-0245-44e0-cd2a-f2f7bd080443'
TB_END_PAGE_PRED_UUID = '506924aa-b53d-41b5-9d02-9a7929ea6d6d'

# UUID lookup sources
UUID_SOURCE_OC_LOOKUP = 'oc-db-lookup'
UUID_SOURCE_KOBOTOOLBOX = 'kobo-data-lookup'


# First link columns for related entities dataframes
FIRST_LINK_REL_COLS = [
    'subject_label',
    'subject_uuid',
    LINK_RELATION_TYPE_COL,
    'object_label',
    'object_uuid',
    'object_uuid_source'
]


# Column renames for Related ID sheets
RELS_RENAME_COLS = {
    '_submission__uuid': 'subject_uuid',
    'Type of Relationship': LINK_RELATION_TYPE_COL,
    'Related ID': 'object_related_id',
    'Type of Related ID': 'object_related_type',
    'Note about Relationship': 'object_related_note',
}


# The subjects.csv (subjects_df) will sometimes update UUIDs
# for entities submitted on Kobo forms with existing UUIDs from
# the database. This config maps between different form types
# and the best entity label and entity uuids as stored on the
# subjects_df (subjects.csv) dataset.
# See: utilites.get_general_form_type_from_sheet_name to get
# the keys for this config.
SUBJECTS_SHEET_PRIMARY_IDs = {
    'locus': ('locus_name', 'locus_uuid',),
    'small find': ('find_name', 'find_uuid',),
    'bulk find': ('bulk_name', 'bulk_uuid',),
    'catalog': ('catalog_name', 'catalog_uuid',),
}




# Configuration to import the subjects (locations/objects) items
# in their proper hierarchy
SUBJECTS_IMPORT_TREE_COL_TUPS = [
    # (parent_context_col, child_label_col, child_uuid_col, child_class_slug_col)
    ('p_trench_uuid', 'unit_name', 'unit_uuid', 'unit_item_class_slug', ),
    ('unit_uuid', 'locus_name', 'locus_uuid', 'locus_item_class_slug',),
    ('locus_uuid', 'catalog_name', 'catalog_uuid', 'catalog_item_class_slug',),
    ('locus_uuid', 'find_name', 'find_uuid', 'find_item_class_slug',),
    ('locus_uuid', 'bulk_name', 'bulk_uuid', 'bulk_item_class_slug',),
]
