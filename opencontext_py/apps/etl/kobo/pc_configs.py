import copy
import os

from pathlib import Path

from opencontext_py.apps.all_items import configs

from opencontext_py.apps.etl.kobo import kobo_oc_configs


KOBO_API_URL = 'https://kform.opencontext.org'
PROJECT_UUID = 'df043419-f23b-41da-7e4d-ee52af22f92f'
DEFAULT_IMPORT_YEAR = 2025
IMPORT_SOURCE_ID_SUFFIX = '-v1'

HOME = str(Path.home())
ALL_IMPORTS_PATH = f'{HOME}/pc-data-{DEFAULT_IMPORT_YEAR}'
KOBO_EXCEL_FILES_PATH = f'{ALL_IMPORTS_PATH}/kobo-data'
KOBO_JSON_DATA_PATH = f'{ALL_IMPORTS_PATH}/kobo-json-data'
KOBO_CSV_FROM_JSON_DATA_PATH = f'{ALL_IMPORTS_PATH}/kobo-csv-from-json-data'
KOBO_TB_JSON_PATH = f'{KOBO_EXCEL_FILES_PATH}/trench_books.json'
KOBO_MEDIA_FILES_PATH = f'{ALL_IMPORTS_PATH}/kobo-media-files'

OC_MEDIA_FILES_PATH = f'{ALL_IMPORTS_PATH}/oc-media-files'
OC_IMPORT_FILES_PATH = f'{ALL_IMPORTS_PATH}/oc-import'

TRENCH_CSV_PATH = f'{ALL_IMPORTS_PATH}/trenches-{DEFAULT_IMPORT_YEAR}.csv'
PEOPLE_CSV_PATH = f'{ALL_IMPORTS_PATH}/people-{DEFAULT_IMPORT_YEAR}.csv'

SUBJECTS_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/subjects.csv'
SUBJECTS_VALIDATION_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/item-validation.csv'
SUBJECTS_ERRORS_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/item-duplicate-errors.csv'
MEDIA_ALL_KOBO_REFS_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/all-media-files.csv'
MEDIA_ALL_LINKS_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/all-media-links.csv'

CATALOG_ATTRIB_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/catalog-attribs.csv'
CATALOG_LINKS_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/catalog-links.csv'

SMALL_FINDS_ATTRIB_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/small-finds-attribs.csv'
SMALL_FINDS_LINKS_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/small-finds-links.csv'

BULK_FINDS_ATTRIB_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/bulk-finds-attribs.csv'
BULK_FINDS_LINKS_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/bulk-finds-links.csv'

LOCUS_ATTRIB_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/locus-attribs.csv'
LOCUS_LINKS_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/locus-links.csv'
LOCUS_GEO_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/locus-geo.csv'
LOCUS_GRID_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/locus-grid.csv'

TB_ATTRIB_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/tb-attribs.csv'
TB_LINKS_CSV_PATH = f'{OC_IMPORT_FILES_PATH}/tb-links.csv'

UNIT_GEO_QUALITY_REPORT = f'{ALL_IMPORTS_PATH}/geo-quality-{DEFAULT_IMPORT_YEAR}.csv'

# API config
API_FORM_ID_FORM_LABELS_2025 = [
    ('atmbiZ5FcsatazUPMnYJQ7', 'locus', 2025,),
    ('abLqjG2J8JgCTSKQXsC3WG', 'bulk-finds', 2025,),
    ('aAgCq4FrQVE8GokvcwQrWH', 'small-finds', 2025,),
    ('adcEaNGtnE3vzgckV3CM4S', 'trench', 2025,),
    ('awNWuRoffWTJkLeRn7igBg', 'catalog', 2025,),
    ('ao6bgn6vapsZ6e3PkgrqMC', 'media', 2025,),
]



API_FORM_ID_FORM_LABELS_2024 = [
    ('aRoYQKJ6M4SSewgJJ2GhAV', 'locus', 2024,),
    ('aTKQPZxVJzHfehk4XD6rL5', 'bulk-finds', 2024,),
    ('aTTy9G2EZobS4Yj5MLrh8b', 'small-finds', 2024,),
    ('aLMFzxvXmbSat8XMcjUcjq', 'trench', 2024,),
    ('a6aorrDfWR8TA8CMAsZmAP', 'catalog', 2024,),
    ('aQqfNMGNQTiZkcVZ8j5hyr', 'media', 2024,),
]


API_FORM_ID_FORM_LABELS_2023 = [
    ('aRoYQKJ6M4SSewgJJ2GhAV', 'locus', 2023,),
    ('aTKQPZxVJzHfehk4XD6rL5', 'bulk-finds', 2023,),
    ('aTTy9G2EZobS4Yj5MLrh8b', 'small-finds', 2023,),
    ('aLMFzxvXmbSat8XMcjUcjq', 'trench', 2023,),
    ('a6aorrDfWR8TA8CMAsZmAP', 'catalog', 2023,),
    ('aQqfNMGNQTiZkcVZ8j5hyr', 'media', 2023,),
]

API_FORM_ID_FORM_LABELS_2022 = [
    ('aGkVqvJPGWpgjDEDidmYiz', 'locus', 2022,),
    ('aKpnDAkEPtJfPYL4ekKfQH', 'trench', 2022,),
]

API_FORM_ID_FORM_LABELS_ALL = (
    API_FORM_ID_FORM_LABELS_2025
    # API_FORM_ID_FORM_LABELS_2023
    # + API_FORM_ID_FORM_LABELS_2022
)




# The column in the Kobo exports with the trench identifier
KOBO_TRENCH_COL = 'Trench ID'


SOURCE_ID_PREFIX = f'pc{DEFAULT_IMPORT_YEAR}{IMPORT_SOURCE_ID_SUFFIX}'
SOURCE_ID_SUBJECTS = f'{SOURCE_ID_PREFIX}-subjects'
SOURCE_ID_TB_DEFAULT = f'{SOURCE_ID_PREFIX}-tb-default'
SOURCE_ID_MEDIA_FILES = f'{SOURCE_ID_PREFIX}-media-files'
SOURCE_ID_MEDIA_LINKS = f'{SOURCE_ID_PREFIX}-media-files-link'
SOURCE_ID_CATALOG_ATTRIB = f'{SOURCE_ID_PREFIX}-cat-attrib-2022-fix'
SOURCE_ID_CATALOG_LINKS = f'{SOURCE_ID_PREFIX}-cat-link-2022-fix'
SOURCE_ID_SMALL_FINDS_ATTRIB = f'{SOURCE_ID_PREFIX}-small-attrib'
SOURCE_ID_SMALL_FINDS_LINKS = f'{SOURCE_ID_PREFIX}-small-link'
SOURCE_ID_BULK_FINDS_ATTRIB = f'{SOURCE_ID_PREFIX}-bulk-attrib'
SOURCE_ID_BULK_FINDS_LINKS = f'{SOURCE_ID_PREFIX}-bulk-link'
SOURCE_ID_LOCUS_ATTRIB = f'{SOURCE_ID_PREFIX}-locus-attrib'
SOURCE_ID_LOCUS_LINKS = f'{SOURCE_ID_PREFIX}-locus-link'
SOURCE_ID_LOCUS_GEO = f'{SOURCE_ID_PREFIX}-locus-geo'
SOURCE_ID_LOCUS_GRID = f'{SOURCE_ID_PREFIX}-locus-grid'
SOURCE_ID_TB_ATTRIB = f'{SOURCE_ID_PREFIX}-tb-attrib'
SOURCE_ID_TB_LINKS = f'{SOURCE_ID_PREFIX}-tb-link'
SOURCE_ID_UNIT_AGG_GEO = f'{SOURCE_ID_PREFIX}-unit-agg-geo'
SOURCE_ID_PERSONS = f'{SOURCE_ID_PREFIX}-persons'

ALL_SOURCE_IDS = [
    SOURCE_ID_SUBJECTS,
    SOURCE_ID_TB_DEFAULT,
    SOURCE_ID_MEDIA_FILES,
    SOURCE_ID_MEDIA_LINKS,
    SOURCE_ID_CATALOG_ATTRIB,
    SOURCE_ID_CATALOG_LINKS,
    SOURCE_ID_SMALL_FINDS_ATTRIB,
    SOURCE_ID_SMALL_FINDS_LINKS,
    SOURCE_ID_BULK_FINDS_ATTRIB,
    SOURCE_ID_BULK_FINDS_LINKS,
    SOURCE_ID_LOCUS_ATTRIB,
    SOURCE_ID_LOCUS_LINKS,
    SOURCE_ID_LOCUS_GEO,
    SOURCE_ID_LOCUS_GRID,
    SOURCE_ID_TB_ATTRIB,
    SOURCE_ID_TB_LINKS,
    SOURCE_ID_UNIT_AGG_GEO,
]

ENTITY_CREATE_SOURCE_FILE_LIST = [
    # (form_type, source_id, attrib_csv_path,)
    ('trench book', SOURCE_ID_TB_ATTRIB, TB_ATTRIB_CSV_PATH,),
    ('media', SOURCE_ID_MEDIA_FILES, MEDIA_ALL_KOBO_REFS_CSV_PATH,),
]

GENERAL_ATTRIB_SOURCE_FILE_LIST = [
    # (form_type, source_id, attrib_csv_path,)
    ('catalog', SOURCE_ID_CATALOG_ATTRIB, CATALOG_ATTRIB_CSV_PATH,),
    ('small find', SOURCE_ID_SMALL_FINDS_ATTRIB, SMALL_FINDS_ATTRIB_CSV_PATH,),
    ('bulk find', SOURCE_ID_BULK_FINDS_ATTRIB, BULK_FINDS_ATTRIB_CSV_PATH,),
    ('locus', SOURCE_ID_LOCUS_ATTRIB, LOCUS_ATTRIB_CSV_PATH,),
    ('locus', SOURCE_ID_LOCUS_GEO, LOCUS_GEO_CSV_PATH,),
]

ALL_LINK_SOURCE_FILE_LIST = [
    # (source_id, attrib_csv_path,)
    (SOURCE_ID_CATALOG_LINKS, CATALOG_LINKS_CSV_PATH,),
    (SOURCE_ID_SMALL_FINDS_LINKS, SMALL_FINDS_LINKS_CSV_PATH,),
    (SOURCE_ID_BULK_FINDS_LINKS, BULK_FINDS_LINKS_CSV_PATH,),
    (SOURCE_ID_LOCUS_LINKS, LOCUS_LINKS_CSV_PATH,),
    (SOURCE_ID_TB_LINKS, TB_LINKS_CSV_PATH,),
    (SOURCE_ID_MEDIA_LINKS, MEDIA_ALL_LINKS_CSV_PATH,),
]

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
    'CD': {
        'site':'Poggio Civitate',
        'area': 'Civitate D',
    },
    'T': {
        'site':'Poggio Civitate',
        'area': 'Tesoro',
    },
    'Agger': {
        'site':'Poggio Civitate',
        'area': 'Agger',
    },
    'Rectangle': {
        'site':'Poggio Civitate',
        'area': 'Tesoro Rectangle',
    },
    'VT': {
        'site':'Vescovado di Murlo',
        'area': 'Upper Vescovado',
        'prefix': 'Vescovado',
    },
    'ca': {
        'site':'Poggio Civitate',
        'area': 'Civitate A',
    },
    'cb': {
        'site':'Poggio Civitate',
        'area': 'Civitate B',
    },
    'cd': {
        'site':'Poggio Civitate',
        'area': 'Civitate D',
    },
    't': {
        'site':'Poggio Civitate',
        'area': 'Tesoro',
    },
    'agger': {
        'site':'Poggio Civitate',
        'area': 'Agger',
    },
    'vt': {
        'site':'Vescovado di Murlo',
        'area': 'Upper Vescovado',
        'prefix': 'Vescovado',
    },
}

PC_LABEL_PREFIXES = ['PC', 'PC ', 'PC  ', 'pc', 'pc ']
VDM_LABEL_PREFIXES = ['VDM', 'VDM ', 'VdM', 'VdM ', 'vdm', 'vdm ']
ALL_CATALOG_PREFIXES = PC_LABEL_PREFIXES + VDM_LABEL_PREFIXES

LABEL_ALTERNATIVE_PARTS = {
    # Keyed by project_uuid
    PROJECT_UUID: {
        'PC': PC_LABEL_PREFIXES,
        'VDM': VDM_LABEL_PREFIXES,
        'pc': PC_LABEL_PREFIXES,
        'vdm': VDM_LABEL_PREFIXES,
    },
}


LINK_RELATION_TYPE_COL = 'link_rel'


REL_SUBJECTS_PREFIXES = {
    'Small Find': (
        ['SF ', 'sf', 'sf ',],
        ['oc-gen-cat-sample',],
    ),
    'Cataloged Object': (
        ALL_CATALOG_PREFIXES,
        [
            'oc-gen-cat-object',
            'oc-gen-cat-arch-element',
            'oc-gen-cat-coin',
            'oc-gen-cat-bio-subj-ecofact',
            'oc-gen-cat-pottery',
        ],
    ),
    'Object': (
        ALL_CATALOG_PREFIXES,
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
            'bf Architectural ',
            'bf Bone ',
            'bf Ceramic ',
            'bf Metal ',
            'bf Other ',
            'bf Tile ',
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
REPROJECTED_GEOJSON_COL = 'REPROJ_GEOJSON'
EVENT_GEOJSON_COL = 'EVENT_GEOJSON'
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

    # Added for 2024
    ('Elevation', 'Elevation', ),
    ('Grid X', 'Grid X',),
    ('Grid Y', 'Grid Y',),
    ('Elevation Uncertainty', 'Elevation Uncertainty (+/- cm)',),
    ('Grid X Uncertainty', 'Grid X Uncertainty (+/- cm)',),
    ('Grid Y Uncertainty', 'Grid Y Uncertainty (+/- cm)',),
    ('Elevation Type', 'Elevation Type', ),
    ('Elevation Location', 'Elevation Location',),
    ('Elevation Other Location', 'Elevation Other Location',),
    ('Elevation Note', 'Elevation Note',),

    ('_submission__uuid', '_uuid',),
]


MEDIA_FILETYPE_ATTRIBUTE_CONFIGS = [
    {
        'source_col': file_type['col'],
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': file_type['col'],
            'item_type': 'resources',
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
            'item_type': 'latitude',
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
    {
        'source_col': REPROJECTED_GEOJSON_COL,
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': REPROJECTED_GEOJSON_COL,
            'item_type': 'geometry',
            'data_type': 'xsd:string',
        },
        'field_rel': {
            'predicate_id': configs.PREDICATE_OC_ETL_DESCRIBED_BY,
        },
    },
    {
        'source_col': EVENT_GEOJSON_COL,
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': EVENT_GEOJSON_COL,
            'item_type': 'events',
            'data_type': 'id',
        },
    },
]


LOCUS_GRID_ATTRIBUTE_CONFIGS = [
    {
        'source_col': 'subject_label',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'subject_label',
            'item_type': 'subjects',
            'data_type': 'id',
            'item_class_id': '00000000-6e24-600d-a274-f02367a32c33',
        },
        'subject_pk': True,
    },
    {
        'source_col': 'Observation',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Observation',
            'item_type': 'observations',
            'data_type': 'id',
        },
    },
    {
        'source_col': 'Elevation Type',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Elevation Type',
            'item_type': 'events',
            'data_type': 'id',
        },
    },
    {
        'source_col': 'Elevation Location',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Elevation Location',
            'item_type': 'attribute-groups',
            'data_type': 'id',
        },
    },
    {
        'source_col': 'Elevation',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Elevation',
            'context_id': 'aaa910a0-51c1-472e-9bd6-67e333e63bbd',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Grid X',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid (X)',
            'context_id': 'b428ff04-670b-4912-a237-ad8ff9635f5a',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Grid Y',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid (Y)',
            'context_id': '3e0c2eb3-266b-4fa4-ba59-c5c793a1e96d',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Elevation Uncertainty (+/- cm)',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Elevation Uncertainty (+/- cm)',
            'context_id': '529e931c-51ed-4d85-9759-5c9d4069dbb6',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Grid X Uncertainty (+/- cm)',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid X Uncertainty (+/- cm)',
            'context_id': '074574a6-43bd-4bc4-9bd2-001d44512cc3',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Grid Y Uncertainty (+/- cm)',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Grid Y Uncertainty (+/- cm)',
            'context_id': '1bb7b997-c572-4fe5-ac89-c372c322ed78',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Elevation Note',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Elevation (Note)',
            'context_id': '03ec1dcf-e0d6-44fc-a7aa-498e7b3f04a6',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
]


MEDIA_IMAGE_FIELD_ARGS = {
    'label': 'subject_label',
    'item_type': 'media',
    'data_type': 'id',
    'item_class_id': configs.CLASS_OC_IMAGE_MEDIA,
}


DF_ATTRIBUTE_CONFIGS = MEDIA_FILETYPE_ATTRIBUTE_CONFIGS + GEO_ATTRIBUTE_CONFIGS + [

    {
        'source_col': 'subject_label',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'subject_label',
            'item_type': 'subjects',
            'data_type': 'id',
            'item_class_id': '00000000-6e24-600d-a274-f02367a32c33',
        },
        'subject_pk': True,
    },

    {
        'source_col': 'subject_label',
        'form_type': ['bulk find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'subject_label',
            'item_type': 'subjects',
            'data_type': 'id',
            'item_class_id': '00000000-6e24-1147-b189-ad24b8a86f76',
        },
        'subject_pk': True,
    },

    {
        'source_col': 'subject_label',
        'form_type': ['small find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'subject_label',
            'item_type': 'subjects',
            'data_type': 'id',
            'item_class_id': '00000000-6e24-0b70-0230-0cc0398d6184',
        },
        'subject_pk': True,
    },

    {
        'source_col': 'subject_label',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'subject_label',
            'item_type': 'subjects',
            'data_type': 'id',
            'item_class_id': '00000000-6e24-2339-9f63-582218c3f76a',
        },
        'subject_pk': True,
    },

    {
        'source_col': 'subject_label',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'subject_label',
            'data_type': 'id',
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
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'subject_label',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': MEDIA_IMAGE_FIELD_ARGS,
        'subject_pk': True,
    },

    {
        'source_col': 'Size (Notes)',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Size',
            'context_id': 'b6d48580-af49-409c-1172-e27cba31f235',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Size',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Size',
            'context_id': 'b6d48580-af49-409c-1172-e27cba31f235',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Condition (Notes)',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Condition',
            'context_id': '4909306f-3102-47a2-66a3-561c296147bb',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Description',
        'form_type': ['catalog', 'media', 'bulk find', 'small find', 'locus'],
        'match_type': 'exact',
        'field_args': {
            'label': 'Description',
            'context_id': '7dbb5cb7-599f-42d5-61ee-1955cf898990',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Trench ID',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Trench',
            'context_id': 'bd3aba0c-672a-4a1e-81ea-5408768ce407',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Date Cataloged',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Cataloged',
            'context_id': '2d60965b-5151-446c-99b7-402e94e44c25',
            'item_type': 'predicates',
            'data_type': 'xsd:date',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Year',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Year',
            'context_id': '2c7fe888-c431-4fbd-39f4-38b7d969a811',
            'item_type': 'predicates',
            'data_type': 'xsd:integer',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Record Type',
        'form_type': ['catalog', 'small find'],
        'match_type': 'exact',
        'field_args': {
            'label': 'Record Type',
            'context_id': '609ff344-7304-48e3-8db4-64b47dd12215',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Supplemental Find Identification Note',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Supplemental Find Identification Note',
            'context_id': 'b065bd99-859c-4ac2-ae54-9b1721e25c33',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Munsell Color',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Munsell Color',
            'context_id': '9b99354c-55a2-45e0-9bfd-79bd7f2a801a',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Fabric Category',
        'form_type': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Fabric Category',
            'context_id': 'a70236ca-1599-42f5-4a12-acec8c423850',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Other Fabric Note',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Other Fabric Note',
            'context_id': 'cfb6e3c6-a51f-4da9-a794-dca7b92e56fd',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Object General Type',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Object Type',  # Note the difference from the source-column!
            'context_id': '7db79382-7432-42a4-fbc5-ef760691905a',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Alternative Object General Type',
        'form_type': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            # NOTE: This is also mapped to the 'Object Type' predicate.
            'label': 'Object Type',  # Note the difference from the source-column!
            'context_id': '7db79382-7432-42a4-fbc5-ef760691905a',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Object General Type Alternatives',
        'form_type': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            # NOTE: This is also mapped to the 'Object Type' predicate.
            'label': 'Object Type',  # Note the difference from the source-column!
            'context_id': '7db79382-7432-42a4-fbc5-ef760691905a',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Object Type (General)',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Object Type',  # Note the difference from the source-column!
            'context_id': '7db79382-7432-42a4-fbc5-ef760691905a',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Alternative Object Type (General)',
        'form_type': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            # NOTE: This is also mapped to the 'Object Type' predicate.
            'label': 'Object Type',  # Note the difference from the source-column!
            'context_id': '7db79382-7432-42a4-fbc5-ef760691905a',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Object Type Notes',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Catalog ID Note',
            'context_id': '46c4ea6d-232f-45ec-97f8-3dd2762bcb56',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Object Type',
        'form_type': ['catalog', 'small find',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Object Type',
            'context_id': '7db79382-7432-42a4-fbc5-ef760691905a',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Object Type Notes',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Catalog ID Note',
            'context_id': '46c4ea6d-232f-45ec-97f8-3dd2762bcb56',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Object Type, Title',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Catalog ID Note',
            'context_id': '46c4ea6d-232f-45ec-97f8-3dd2762bcb56',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Decorative Technique',
        'form_type': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Decorative Technique',
            'context_id': 'f07c30bc-6c71-4c97-7893-d61ff6d0b59b',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Other Decorative Technique Note',
        'form_type': ['catalog',],
        'match_type': 'endswith',
        'field_args': {
            'label': 'Other Decorative Technique Note',
            'context_id': '8cbd3c5a-b3ec-4e3a-b1eb-bf2d53b01781',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Motif',
        'form_type': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Motif',
            'context_id': '9b260671-cbbd-490e-48b0-cdc48f5df62d',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Other Motif Note',
        'form_type': ['catalog',],
        'match_type': 'endswith',
        'field_args': {
            'label': 'Other Motif Note',
            'context_id': '5dd0bdb8-782f-42fb-93c4-60018860fb24',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Vessel Form',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Vessel Form',
            'context_id': '6a890b60-3811-44ae-a554-cc8245c4d946',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Vessel Part Present',
        'form_type': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Vessel Part Present',
            'context_id': 'c16a0682-5956-4180-af94-9981f937651a',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Modification',
        'form_type': ['catalog',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Modification',
            'context_id': 'fb59a2ed-e2f5-4a88-a651-0aa5f779eb54',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Other Modification Note',
        'form_type': ['catalog',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Modification Description',
            'context_id': '26fe0b22-e88b-4777-8457-a61e6cc0ed8b',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Grid X',
        'form_type': ['catalog', 'small find',],
        'match_type': 'endswith',
        'field_args': {
            'label': 'Grid (X)',
            'context_id': 'b428ff04-670b-4912-a237-ad8ff9635f5a',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Grid Y',
        'form_type': ['catalog', 'small find',],
        'match_type': 'endswith',
        'field_args': {
            'label': 'Grid (Y)',
            'context_id': '3e0c2eb3-266b-4fa4-ba59-c5c793a1e96d',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Elevation',
        'form_type': ['catalog', 'small find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Elevation',
            'context_id': 'aaa910a0-51c1-472e-9bd6-67e333e63bbd',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Grid X Uncertainty (+/- cm)',
        'form_type': ['catalog', 'small find',],
        'match_type': 'endswith',
        'field_args': {
            'label': 'Grid X Uncertainty (+/- cm)',
            'context_id': '074574a6-43bd-4bc4-9bd2-001d44512cc3',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Grid Y Uncertainty (+/- cm)',
        'form_type': ['catalog', 'small find',],
        'match_type': 'endswith',
        'field_args': {
            'label': 'Grid Y Uncertainty (+/- cm)',
            'context_id': '1bb7b997-c572-4fe5-ac89-c372c322ed78',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Elevation Uncertainty (+/- cm)',
        'form_type': ['catalog', 'small find',],
        'match_type': 'endswith',
        'field_args': {
            'label': 'Elevation Uncertainty (+/- cm)',
            'context_id': '529e931c-51ed-4d85-9759-5c9d4069dbb6',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Uncertainty Comment',
        'form_type': ['catalog', 'small find',],
        'match_type': 'endswith',
        'field_args': {
            'label': 'Measurement Uncertainties Comment',
            'context_id': None,
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Find Type',
        'form_type': ['bulk find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Find Type',
            'context_id': '464b90e2-ce62-4570-bcea-58b7f9b5bb33',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Find Type (Other)',
        'form_type': ['bulk find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Find Type (Other)',
            'context_id': '36027b0c-3c4b-49df-9ab0-d110cdb5d9b4',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Object Count',
        'form_type': ['bulk find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Object Count',
            'context_id': '056a3e7c-3d5d-4004-a9ed-7b0f88b74648',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Count Type',
        'form_type': ['bulk find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Count Type',
            'context_id': 'fa2e0286-de17-45e6-959f-9dab8c8cc5f5',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Count Type (Other)',
        'form_type': ['bulk find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Count Type (Other)',
            'context_id': '630e3548-7050-4891-9971-94e91593b74d',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'General Description',
        'form_type': ['small find', 'bulk find', 'locus'],
        'match_type': 'exact',
        'field_args': {
            'label': 'Description',
            'context_id': '7dbb5cb7-599f-42d5-61ee-1955cf898990',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Date Discovered',
        'form_type': ['bulk find', 'small find'],
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Discovered',
            'context_id': '23ff0204-2b40-47b4-909a-66ec8d150528',
            'item_type': 'predicates',
            'data_type': 'xsd:date',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Deposit Compaction',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Deposit Compaction',
            'context_id': '3eb4639d-a67e-47e6-9435-a87723486a82',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Stratigraphic Reliability',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Stratigraphic Reliability',
            'context_id': '1ed85342-864a-4ae9-81ed-3a484233ec43',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Locus Type',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Locus Type',
            'context_id': '12eb02f4-d1a6-48cd-8bde-93162c12ca01',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

     {
        'source_col': 'Locus Type Note',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Locus Type Note',
            'context_id': '98e374e8-7da8-4b21-a95c-ec8f40aeec6e',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Preliminary Phasing',
        'form_type': ['locus',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Preliminary Phasing',
            'context_id': 'c2b40ac1-3b8d-4307-b217-c61732236d68',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Munsell Color',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Munsell Color',
            'context_id': '9b99354c-55a2-45e0-9bfd-79bd7f2a801a',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Deposit Compaction',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Deposit Compaction',
            'context_id': '3eb4639d-a67e-47e6-9435-a87723486a82',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Stratigraphic Reliability',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Stratigraphic Reliability',
            'context_id': '1ed85342-864a-4ae9-81ed-3a484233ec43',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Date Opened',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Opened',
            'context_id': '0ea21cdb-ffab-4b68-9d47-78b180f08162',
            'item_type': 'predicates',
            'data_type': 'xsd:date',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Date Closed',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Closed',
            'context_id': '99684fbb-55d5-447a-8159-7d54fea80b50',
            'item_type': 'predicates',
            'data_type': 'xsd:date',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Trench',
        'form_type': ['locus', 'bulk find', 'small find',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Trench',
            'context_id': 'bd3aba0c-672a-4a1e-81ea-5408768ce407',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Field Season',
        'form_type': ['small find', 'bulk find', 'locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Year',
            'context_id': '2c7fe888-c431-4fbd-39f4-38b7d969a811',
            'item_type': 'predicates',
            'data_type': 'xsd:integer',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Season',
        'form_type': ['small find', 'bulk find', 'locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Year',
            'context_id': '2c7fe888-c431-4fbd-39f4-38b7d969a811',
            'item_type': 'predicates',
            'data_type': 'xsd:integer',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Entry Type',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Entry Type',
            'context_id': 'eea8648f-7df4-48f6-a58e-2971f001d245',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Entry Title',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Title',
            'context_id': '08bc76a7-5240-48cc-1998-8f861eeb08bf',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Document Type',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Document Type',
            'context_id': '565672fe-eee1-4e85-3c66-538137e6d332',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Date Documented',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Trench Book Entry Date',
            'context_id': '8b812e4f-edc4-44f1-a88d-4ad358aaf9aa',
            'item_type': 'predicates',
            'data_type': 'xsd:date',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Entry Year',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Entry Year',
            'context_id': '37e30449-43fa-45e0-8142-8e3f6a70441b',
            'item_type': 'predicates',
            'data_type': 'xsd:integer',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Book Year',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Book Year',
            'context_id': '8fb4a650-ef81-4238-a75b-603e07dd4455',
            'item_type': 'predicates',
            'data_type': 'xsd:integer',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Start Page',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Start Page',
            'context_id': 'becad1af-0245-44e0-cd2a-f2f7bd080443',
            'item_type': 'predicates',
            'data_type': 'xsd:integer',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'End Page',
        'form_type': ['trench book',],
        'match_type': 'exact',
        'field_args': {
            'label': 'End Page',
            'context_id': '506924aa-b53d-41b5-9d02-9a7929ea6d6d',
            'item_type': 'predicates',
            'data_type': 'xsd:integer',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Date Created',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Date Created',
            'context_id': 'e4671bb6-094d-4001-bb10-32685a168bc1',
            'item_type': 'predicates',
            'data_type': 'xsd:date',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Type of Composition Subject',
        'form_type': ['media',],
        'match_type': 'startswith',
        'field_args': {
            'label': 'Composition Subject Type',
            'context_id': '7bf4999e-264d-4515-a468-c041848a6259',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Note about Supplemental Image',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Image Note',
            'context_id': '12cc9a67-f902-4319-91b0-ef22f8dca380',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Image Sup Note',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Image Note',
            'context_id': '12cc9a67-f902-4319-91b0-ef22f8dca380',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Image Note',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Image Note',
            'context_id': '12cc9a67-f902-4319-91b0-ef22f8dca380',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'File Title',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Title',
            'context_id': '08bc76a7-5240-48cc-1998-8f861eeb08bf',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Note about Primary Image',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Image Note',
            'context_id': '12cc9a67-f902-4319-91b0-ef22f8dca380',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Direction or Orientation Notes/Direction Faced in Field',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Direction Faced in Field',
            'context_id': None,
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Direction or Orientation Notes/Object Orientation Note',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Object Orientation Note',
            'context_id': '804bf2fe-043c-4405-bd4a-558a5ffd7d50',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Image Type',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Image Type',
            'context_id': 'b8556eaa-cf52-446b-39fa-ae4798c13a6b',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Images/Note about Primary Image',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Description',
            'context_id': '7dbb5cb7-599f-42d5-61ee-1955cf898990',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Images/Supplemental Files/Note about Supplemental Image',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Description',
            'context_id': '7dbb5cb7-599f-42d5-61ee-1955cf898990',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Media Type',
        'form_type': ['media',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Media Type',
            'context_id': 'eced82b8-8f45-4ca3-b9f9-b94ddcd3d2ab',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },


    # Added for additonal locus descriptions starting in 2024
    {
        'source_col': 'Recovery Techniques Other',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Interpretation',
            'context_id': 'e16c3104-cc6b-4db3-9813-61d1f15d6423',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Mode of Formation',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Mode of Formation',
            'context_id': '590c3369-8888-4f3d-92c5-d4ef42e05b55',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Inorganic Components',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Inorganic Components',
            'context_id': '7dbd0dac-8fcc-4122-82fb-72d02d9fa6bf',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Organic Components',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Organic Components',
            'context_id': '0057c76d-eda4-43fc-964b-0d5e1f24e3a2',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Definition and Position',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Definition and Position',
            'context_id': '2e3c8948-cfbd-42a5-84de-87387d13b0fa',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'State of Conservation',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'State of Conservation',
            'context_id': '3ff9ed87-8f6f-4375-9d9f-7a510e00f3c2',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Observations',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Observations',
            'context_id': '3764b728-950a-4206-8951-cb535d423702',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Interpretation',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Interpretation',
            'context_id': 'bb4730f5-9c0f-4501-a4e1-dc418fece57c',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Length m',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Length (m)',
            'context_id': '40898a63-6ebd-4c08-bece-863e87bf90d4',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Width m',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Width (m)',
            'context_id': '5a7225be-a815-49f9-9ac1-223fa708d33c',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Depth cm',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Depth (cm)',
            'context_id': '6562bf69-21e0-4db2-ad1e-d3dd621bbd5c',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },
    {
        'source_col': 'Area m sq',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Area (m sq)',
            'context_id': '30c3d741-f10d-40a4-a3da-25b7269b197b',
            'item_type': 'predicates',
            'data_type': 'xsd:double',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Locus Periods',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Locus Period',
            'context_id': '13399317-94d9-49e7-ab3a-b2114c2e1972',
            'item_type': 'types',
            'data_type': 'id',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
        },
    },

    {
        'source_col': 'Locus Periods (Other)',
        'form_type': ['locus',],
        'match_type': 'exact',
        'field_args': {
            'label': 'Locus Period (Notes)',
            'context_id': '5ceee060-319b-4cf5-85ab-aae9231131ab',
            'item_type': 'predicates',
            'data_type': 'xsd:string',
            'item_class_id': configs.CLASS_OC_VARIABLES_UUID,
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
    'Contemporary with': ('eee95a2a-c3f8-4637-b67a-f4ff6ea4ee53', 'eee95a2a-c3f8-4637-b67a-f4ff6ea4ee53'),
    'Stratigraphy: Above/Above Locus': ('7895f4a8-d7e0-4219-bb47-9eef76c4acc0', '04a9d0b0-0ff8-412e-b134-23f705e666ca'),
    'Above': ('7895f4a8-d7e0-4219-bb47-9eef76c4acc0', '04a9d0b0-0ff8-412e-b134-23f705e666ca'),
    'Stratigraphy: Below/Below Locus': ('04a9d0b0-0ff8-412e-b134-23f705e666ca', '7895f4a8-d7e0-4219-bb47-9eef76c4acc0'),
    'Below': ('04a9d0b0-0ff8-412e-b134-23f705e666ca', '7895f4a8-d7e0-4219-bb47-9eef76c4acc0'),
    'Stratigraphy: Overlies/Overlies Locus': ('f2fd2edb-4505-447a-9403-13c18150d1d2', None),
    'Overlies': ('f2fd2edb-4505-447a-9403-13c18150d1d2', None),
    'Stratigraphic Relations: Cuts/Cuts Locus': ('0d5daed7-873d-4415-a0eb-3e7ddf7f25f7', None),
    'Cuts': ('0d5daed7-873d-4415-a0eb-3e7ddf7f25f7', None),
    'Objects join, refit together': ('5E41E490-0618-4D15-0826-38E3B4681C58', '5E41E490-0618-4D15-0826-38E3B4681C58'),
    'Additional ID': ('d58724ee-ecb9-4c2c-87a1-02f853edc2f2', '17012df0-ef2f-41a8-b8d6-ddf5b6687a7e'),
    'Associated in Context': ('3d4a7baa-8b52-4363-9a10-3f3a70cf919c', '3d4a7baa-8b52-4363-9a10-3f3a70cf919c'),
    'Has Related Trench': (configs.PREDICATE_LINK_UUID, 'f20e9e2e-246f-4421-b1dd-e31e8b58805c'),
    'Has Related Trench Book Entry': ('f20e9e2e-246f-4421-b1dd-e31e8b58805c', configs.PREDICATE_LINK_UUID),
    'Related Open Locus': ('b0149b7c-88c8-4913-b6c8-81375239e71f', 'f20e9e2e-246f-4421-b1dd-e31e8b58805c'),
    'Related Small Find': (configs.PREDICATE_LINK_UUID, 'f20e9e2e-246f-4421-b1dd-e31e8b58805c'),
    'Initially documented as': ('d58724ee-ecb9-4c2c-87a1-02f853edc2f2', '17012df0-ef2f-41a8-b8d6-ddf5b6687a7e'),
    'Cataloged as': ('17012df0-ef2f-41a8-b8d6-ddf5b6687a7e', 'd58724ee-ecb9-4c2c-87a1-02f853edc2f2'),
    'Supervised by': ('4c15bbbf-4c0d-4262-8bcc-f6d9236813af', None),
    'Creator': ('00000000-ed50-3cf1-c266-683c89afdac4', None),
    'Photographed by': ('d2fe0142-e4c7-9601-5011-08f47580dae1', None),

    # Added for PC 2019
    'Other relation': (configs.PREDICATE_LINK_UUID, configs.PREDICATE_LINK_UUID),
    'Comparanda, based on form': ('46037eb4-c4b7-432b-bebb-500aff0e4fe6', '46037eb4-c4b7-432b-bebb-500aff0e4fe6'),
    'Comparanda, based on motif': ('1c5a1fca-0853-4612-9663-f908d9c081b2', '1c5a1fca-0853-4612-9663-f908d9c081b2'),

    # Added for PC 2024, new stratigraphy relations
    'Overlies Locus': (
        '316b8a61-a439-4f6b-abbb-138f103296e0', 
        '7bd95ff4-eab2-41c8-a8ce-779bd83f3f20', # Underlies Locus
    ),
    'Anterior To Locus': (
        '72e24968-90bd-48fd-a242-d25073bc35ce', 
        '5a97fda9-2dd9-45b3-b113-881b68077d0c', # Posterior To Locus
    ),
    'Underlies Locus': (
        '7bd95ff4-eab2-41c8-a8ce-779bd83f3f20', 
        '316b8a61-a439-4f6b-abbb-138f103296e0', # Overlies Locus
    ),
    'Posterior To Locus': (
        '5a97fda9-2dd9-45b3-b113-881b68077d0c', 
        '72e24968-90bd-48fd-a242-d25073bc35ce', # Anterior To Locus
    ),
    'Is Bound To Locus': (
        '8211f9ef-3def-4e2c-8bf3-eee3f2345be0', 
        None,
    ),
    'Above Locus': (
        '321d7448-91b9-4e1d-88bc-120ef916a118', 
        'ebc93594-a9c9-4e36-b720-1da3d644be25',  # Below Locus
    ),
    'Below Locus': (
        'ebc93594-a9c9-4e36-b720-1da3d644be25', 
        '321d7448-91b9-4e1d-88bc-120ef916a118', # Above Locus
    ),
    'Is Cut By Locus': (
        '53ecfa29-c58e-4227-bc2c-c64d858aaa70', 
        '974de24e-a454-4fb1-9422-eaaeee103ba1', # Cuts Locus
    ),
    'Cuts Locus': (
        '974de24e-a454-4fb1-9422-eaaeee103ba1', 
        '53ecfa29-c58e-4227-bc2c-c64d858aaa70', # Is Cut By Locus
    ),

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
    'Related_ID': 'object_related_id',
    'Type of Related ID': 'object_related_type',
    'Rel_ID_Type': 'object_related_type',
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
    ('area_uuid', 'ptrench_name', 'ptrench_uuid', 'ptrench_item_class_slug', ),
    ('ptrench_uuid', 'unit_name', 'unit_uuid', 'unit_item_class_slug', ),
    ('unit_uuid', 'locus_name', 'locus_uuid', 'locus_item_class_slug',),
    ('locus_uuid', 'catalog_name', 'catalog_uuid', 'catalog_item_class_slug',),
    ('locus_uuid', 'find_name', 'find_uuid', 'find_item_class_slug',),
    ('locus_uuid', 'bulk_name', 'bulk_uuid', 'bulk_item_class_slug',),
]


MEDIA_BASE_URL = f'https://storage.googleapis.com/opencontext-media/poggio-civitate/{DEFAULT_IMPORT_YEAR}-media'


MAIN_TRENCH_BOOKS = {
    2022: {
        'T26_2022': ('Trench Book T26 2022', '028af835-57dc-4952-af76-1772295442bd',),
        'T90_2022': ('Trench Book T90 2022', 'b01c144b-5fdc-44ff-b00f-5bcd36e91b56',),
        'T100_2022': ('Trench Book T100 2022', '7227c029-e202-42ed-a786-844bc0e42edb',),
        'T101_2022': ('Trench Book T101 2022', 'd6a6080c-625d-4263-8bea-d20c19a0ee8a',),
        'T102_2022': ('Trench Book T102 2022', '763b203b-c37c-4076-a12e-845cc9fb02ad',),
        'CA90_2022': ('Trench Book CA90 2022', 'e911d2b1-898b-413b-8e8e-d45271bca34d',),
        'CA91_2022': ('Trench Book CA91 2022', 'b4ed4510-f6cf-4b38-aaea-4d2c136c4c57',),
        'CA92_2022': ('Trench Book CA92 2022', '1d4d7311-9dc0-4667-bdb0-93bda1f8bd65',),
    },
    2023: {
        't26_2023': ('Trench Book T26 2023', '8618682d-387b-4ac6-8e82-710d184ab5a4',),
        't90_2023': ('Trench Book T90 2023', '1d58fb05-7de4-42fd-aada-c79c725a960a',),
        't101_2023': ('Trench Book T101 2023', '6e5c196b-1fe9-4c76-aedd-32a30620eb70',),
        't102_2023': ('Trench Book T102 2023', '0ec10cf6-7dc4-4509-a99f-2debe29edd34',),
        't103_2023': ('Trench Book T103 2023', 'd9a9eb89-72b2-460a-8dd7-e61eed362399',),
        't104_2023': ('Trench Book T104 2023', 'd1a2ea5e-c0a5-4787-9df2-3f8dce513e4f',),
        't105_2023': ('Trench Book T105 2023', '0adb7aaa-63d9-4a60-b43f-92bd18011830',),
        't106_2023': ('Trench Book T106 2023', '7379e0f5-218e-4619-a96c-d7dcb6046f16',),
        't107_2023': ('Trench Book T107 2023', '0e7b71d7-5cf2-4767-addd-9377cd9e0903',),
        't108_2023': ('Trench Book T108 2023', '8c26efa2-a065-4161-98a9-0fbe60a9ed71',),
        't109_2023': ('Trench Book T109 2023', 'cf3a78a0-45bc-4407-8df2-f48df45e6f4e',),
        't110_2023': ('Trench Book T110 2023', '62e7377a-6082-40cb-b88b-78bbe6a649f7',),
        'ca93_2023': ('Trench Book CA93 2023', 'a2bd5827-2f22-481b-9e71-c9fdda48c83f',),
        'ca96_2023': ('Trench Book CA96 2023', 'd33c6f6b-947e-44c4-b9a7-605e7d542341',),
        'ca94_2023': ('Trench Book CA94 2023', '3d0d17b3-61af-47e1-844b-41a04cabfd26',),
        'ca95_2023': ('Trench Book CA95 2023', '5b98f49d-e514-4933-bcdf-31213339a445',),
        'ca97_2023': ('Trench Book CA97 2023', 'a4a23477-e74b-43e8-afae-973ac511d59e',),
        'ca98_2023': ('Trench Book CA98 2023', 'bdd75b3a-740b-40df-9edd-4b4919188fc1',),
        'ca99_2023': ('Trench Book CA99 2023', '743dd0df-3842-4a81-985f-1a6f5c7a2342',),
        'ca100_2023': ('Trench Book CA100 2023', 'df6fc670-750c-4267-86dc-924cb745b922',),
    },
    2024:{
        'T26_2024': ('Trench Book T26 2024', '78bde3fd-44ec-4325-8a41-7ec11cfb0768',),
        'T104_2024': ('Trench Book T104 2024', 'e7daa25d-e255-4839-a6e6-90db71fbdbdd',),
        'T105_2024': ('Trench Book T105 2024', '28b8c221-071b-497d-a367-f1c9a7dac892',),
        'T106_2024': ('Trench Book T106 2024', '22bc4a8a-cb1d-4e4b-a77c-38f1c2a67d3f',),
        'T107_2024': ('Trench Book T107 2024', '6bf6e6e9-60c8-4176-bbb5-55cd7d6fb61b',),
        'T108_2024': ('Trench Book T108 2024', '0dad4b9f-034b-4ee8-8563-8581d06f9b05',),
        'T109_2024': ('Trench Book T109 2024', '5ce30dd6-7f1a-4aff-b701-100880b0615d',),
        'T110_2024': ('Trench Book T110 2024', '27b76eed-e05f-4deb-8597-95546b160cbf',),
    },
    2025:{
        'T104_2025': ('Trench Book T104 2025', 'fa3dcc46-01b2-446c-bf4e-dd29ded731c7',),
        'T111_2025': ('Trench Book T111 2025', '08e598ca-2ca1-412f-afcb-b5b6b64b73c5',),
        'T112_2025': ('Trench Book T112 2025', '4d5f1a31-8a51-4a53-b6b7-322cccb67cb4',),
        'T113_2025': ('Trench Book T113 2025', '0770af35-8af0-401e-b567-f18801cbf44b',),
        'T114_2025': ('Trench Book T114 2025', 'e9c847ee-6d7c-4904-982f-133195bfd443',),
        'T115_2025': ('Trench Book T115 2025', '06060946-cab3-4676-9fb4-840e97c56ead',),
        'T116_2025': ('Trench Book T116 2025', 'd522668e-5630-441e-bd11-f5f5ddd2a67e',),
        'T117_2025': ('Trench Book T117 2025', 'eb228acc-39e9-4a47-ac69-e6b97511e849',),
        'T118_2025': ('Trench Book T118 2025', 'ff0acd52-030f-4481-b179-4bccd617be23',),
        'T119_2025': ('Trench Book T119 2025', 'e4e7be02-05fc-43c8-bb19-60b5da1adcc9',),
        'T120_2025': ('Trench Book T120 2025', '6a26960e-d0c4-48a5-88b3-dd33f9250aff',),
        'T121_2025': ('Trench Book T121 2025', '147c75e2-c8e3-48c6-af5e-f0726b8e083c',),
        'T122_2025': ('Trench Book T122 2025', '164fa7ef-c11f-457e-886f-05cb58acfa0c',),
        'T123_2025': ('Trench Book T123 2025', '99b13297-ce14-470d-a851-b9b6aa7f717f',),
        'T124_2025': ('Trench Book T124 2025', 'b53501d9-53e5-4c2b-a613-0356a435613c',),
        'T125_2025': ('Trench Book T125 2025', '77740e68-aead-49c4-9894-163883943613',),
        'T126_2025': ('Trench Book T126 2025', 'ebd82b8a-8455-4954-96d9-0d39f1b20174',),
        'T127_2025': ('Trench Book T127 2025', '661721e9-df52-4ad1-8b23-5ce3ea47119b',),
    },
}


FORM_COLS_DELIM_SPLIT_TO_MULTIPLE_COLS = [
    ('catalog', 'Fabric Category', ' '),
    ('catalog', 'Alternative Object General Type', ' '),
    ('catalog', 'Modification', ' '),
    ('catalog', 'Vessel Part Present', ' '),
    ('catalog', 'Motif', ' '),
    ('catalog', 'Decorative Technique', ' '),
    ('catalog', 'Object General Type Alternatives', ' '),
    ('catalog', 'Alternative Object Type (General)', ' '),
]


# SKIP fields
SKIP_FIELDS = [
    "_id",
    "start",
    "end",
    "_status",
    "_geolocation",
    "_submission_time",
    "_tags",
    "_notes",
    "_validation_status",
    "_submitted_by",
    "meta/instanceID",
    "meta/rootUuid",
    "meta/deprecatedID",
    "formhub/uuid",
    "__version__",
    "download_url",
    "download_large_url",
    "download_medium_url",
    "download_small_url",
    "instance",
    "xform",
    "id",
]

# Naming fields
NAMING_FIELDS = [
    "_uuid",
    "Trench",
    "Trench_ID",
    "Locus_ID",
    "Season",
    "Find_ID",
    "OC_Locus_ID",
    "OC_Find_ID",
    "Catalog_ID_PC",
    "Tag_ID",
    "OC_Bulk_ID",
    "Media_Title",
]