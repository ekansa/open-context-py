import copy
from django.conf import settings

from opencontext_py.apps.all_items import configs

from opencontext_py.apps.all_items.models import (
    AllManifest,
    AllAssertion,
    AllHistory,
    AllResource,
    AllIdentifier,
    AllSpaceTime,
)

from opencontext_py.libs.models import (
    make_dict_json_safe, 
    make_model_object_json_safe_dict
)

#----------------------------------------------------------------------
# NOTE: These are configs for handling requests to manually create
# and edit new items.
# ---------------------------------------------------------------------
LITERAL_DATA_TYPE_OPTIONS = [
    {'value': 'xsd:double', 'text': 'Numeric (decimal)'},
    {'value': 'xsd:integer', 'text': 'Integer (whole numbers)'},
    {'value': 'xsd:boolean', 'text': 'Boolean (True/False)'},
    {'value': 'xsd:date', 'text': 'Calendar date, date-time'},
    {'value': 'xsd:string', 'text': 'Free alphanumeric text or HTML'},
]

DATA_TYPE_OPTIONS = [
    {'value': 'id', 'text': 'Named (identified) entity'},
] + LITERAL_DATA_TYPE_OPTIONS


ITEM_TYPE_META_JSON_CONFIGS = {
    'projects': [
        {
            'key': 'short_id', 
            'label': 'Short, Integer ID', 
            'data_type': 'xsd:integer',
            'note': 'An integer value to help identify this project.',
            'options': None,
        },
        {
            'key': 'edit_status', 
            'label': 'Editorial Status', 
            'data_type': 'xsd:integer',
            'note': 'An integer value indicating level of editorial review.',
            'options': [
                {'value': -1, 'text': 'Not set',},
                {'value': 0, 'text': 'In preparation, draft-stage',},
                {'value': 1, 'text': 'Demonstration, Minimal editorial acceptance',},
                {'value': 2, 'text': 'Minimal editorial acceptance',},
                {'value': 3, 'text': 'Managing editor reviewed',},
                {'value': 4, 'text': 'Editorial board reviewed',},
                {'value': 5, 'text': 'Peer-reviewed',},
            ],
        },
        {
            'key': 'geo_specificity', 
            'label': 'Level of Geospatial data specificity', 
            'data_type': 'xsd:integer',
            'note': (
                'An integer value indicating the zoom level of geospatial precision. '
                'Negative values indicate intentional obfuscation. '
                'For example, -11 indicates intentional obfuscation of coordinates '
                'to +/- 15km or so of their original values.'
            ),
            'options': None,
        },
        {
            'key': 'geo_note', 
            'label': 'Project geospatial data note', 
            'data_type': 'xsd:string',
            'note': (
                'A note visible to users that helps explain and document '
                'geospatial data in a project.'
            ),
            'options': None,
        },
    ],
    'subjects': [
        {
            'key': 'edit_status', 
            'label': 'Editorial Status', 
            'data_type': 'xsd:integer',
            'note': (
                'An integer value indicating level of editorial review. '
                'If given for this item, this supersedes a project-level editorial status.'
            ),
            'options': [
                {'value': -1, 'text': 'Not set',},
                {'value': 0, 'text': 'In preparation, draft-stage',},
                {'value': 1, 'text': 'Demonstration, Minimal editorial acceptance',},
                {'value': 2, 'text': 'Minimal editorial acceptance',},
                {'value': 3, 'text': 'Managing editor reviewed',},
                {'value': 4, 'text': 'Editorial board reviewed',},
                {'value': 5, 'text': 'Peer-reviewed',},
            ],
        },
        {
            'key': 'geo_specificity', 
            'label': 'Level of Geospatial data specificity', 
            'data_type': 'xsd:integer',
            'note': (
                'An integer value indicating the zoom level of geospatial precision. '
                'Negative values indicate intentional obfuscation. '
                'For example, -11 indicates intentional obfuscation of coordinates '
                'to +/- 15km or so of their original values.'
            ),
            'options': None,
        },
        {
            'key': 'geo_note', 
            'label': 'Item geospatial data note', 
            'data_type': 'xsd:string',
            'note': (
                'A note visible to users that helps explain and document '
                'geospatial data for this item.'
            ),
            'options': None,
        },
    ],
    'media': [
        {
            'key': 'edit_status', 
            'label': 'Editorial Status', 
            'data_type': 'xsd:integer',
            'note': (
                'An integer value indicating level of editorial review. '
                'If given for this item, this supersedes a project-level editorial status.'
            ),
            'options': [
                {'value': -1, 'text': 'Not set',},
                {'value': 0, 'text': 'In preparation, draft-stage',},
                {'value': 1, 'text': 'Demonstration, Minimal editorial acceptance',},
                {'value': 2, 'text': 'Minimal editorial acceptance',},
                {'value': 3, 'text': 'Managing editor reviewed',},
                {'value': 4, 'text': 'Editorial board reviewed',},
                {'value': 5, 'text': 'Peer-reviewed',},
            ],
        },
    ],
    'documents': [
        {
            'key': 'edit_status', 
            'label': 'Editorial Status', 
            'data_type': 'xsd:integer',
            'note': (
                'An integer value indicating level of editorial review. '
                'If given for this item, this supersedes a project-level editorial status.'
            ),
            'options': [
                {'value': -1, 'text': 'Not set',},
                {'value': 0, 'text': 'In preparation, draft-stage',},
                {'value': 1, 'text': 'Demonstration, Minimal editorial acceptance',},
                {'value': 2, 'text': 'Minimal editorial acceptance',},
                {'value': 3, 'text': 'Managing editor reviewed',},
                {'value': 4, 'text': 'Editorial board reviewed',},
                {'value': 5, 'text': 'Peer-reviewed',},
            ],
        },
    ],
    'tables': [
        {
            'key': 'edit_status', 
            'label': 'Editorial Status', 
            'data_type': 'xsd:integer',
            'note': (
                'An integer value indicating level of editorial review. '
                'If given for this item, this supersedes a project-level editorial status.'
            ),
            'options': [
                {'value': -1, 'text': 'Not set',},
                {'value': 0, 'text': 'In preparation, draft-stage',},
                {'value': 1, 'text': 'Demonstration, Minimal editorial acceptance',},
                {'value': 2, 'text': 'Minimal editorial acceptance',},
                {'value': 3, 'text': 'Managing editor reviewed',},
                {'value': 4, 'text': 'Editorial board reviewed',},
                {'value': 5, 'text': 'Peer-reviewed',},
            ],
        },
    ],
    'predicates': [
        {
            'key': 'sort', 
            'label': 'Sort Order', 
            'data_type': 'xsd:integer',
            'note': (
                'An integer value indicating suggested sort order for this predicate '
                'within a descriptive observation.'
            ),
            'options':None,
        },
    ],
    'observations': [
        {
            'key': 'sort', 
            'label': 'Sort Order', 
            'data_type': 'xsd:integer',
            'note': (
                'An integer value indicating suggested sort order for this observation.'
            ),
            'options':None,
        },
    ],
    'events': [
        {
            'key': 'sort', 
            'label': 'Sort Order', 
            'data_type': 'xsd:integer',
            'note': (
                'An integer value indicating suggested sort order for this event.'
            ),
            'options':None,
        },
    ],
    'attribute-groups': [
        {
            'key': 'sort', 
            'label': 'Sort Order', 
            'data_type': 'xsd:integer',
            'note': (
                'An integer value indicating suggested sort order for this attribute-group.'
            ),
            'options':None,
        },
    ],
    'persons': [
        {
            'key': 'combined_name', 
            'label': 'Full name (give with family)', 
            'data_type': 'xsd:string',
            'note': (
                'A full name for a person or organization.'
            ),
            'options':None,
        },
        {
            'key': 'given_name', 
            'label': 'Given name', 
            'data_type': 'xsd:string',
            'note': (
                'A given name ("first name" in European conventions).'
            ),
            'options':None,
        },
        {
            'key': 'mid_init', 
            'label': 'Middle Initials', 
            'data_type': 'xsd:string',
            'note': (
                'Initials for middle names if present.'
            ),
            'options':None,
        },
        {
            'key': 'surname', 
            'label': 'Family / surname', 
            'data_type': 'xsd:string',
            'note': (
                'A family or surname for a person.'
            ),
            'options':None,
        },
        {
            'key': 'initials', 
            'label': 'Initials', 
            'data_type': 'xsd:string',
            'note': (
                'Initials (or acronym) that are identifying (within the scope of a project).'
            ),
            'options':None,
        },
    ],
    'languages': [
        {
            'key': 'label_localized', 
            'label': 'Label Localized', 
            'data_type': 'xsd:string',
            'note': (
                'The preferred name / label for a language localized to that language and script.'
            ),
            'options':None,
        },
        {
            'key': 'iso_639_3_code', 
            'label': 'ISO 639-3 code', 
            'data_type': 'xsd:string',
            'note': (
                'Identifier for a language defined in ISO 639-3. '
                'See: https://www.wikidata.org/wiki/Property:P220'
            ),
            'options':None,
        },
        {
            'key': 'script_code', 
            'label': 'Script Code', 
            'data_type': 'xsd:string',
            'note': (
                'The 4-letter ISO 15924 code for the main script used to express the language. '
                'See: https://unicode.org/iso15924/iso15924-codes.html'
            ),
            'options':None,
        },
    ],
    'units': [
        {
            'key': 'data_type', 
            'label': 'Data Type', 
            'data_type': 'xsd:string',
            'note': (
                'The data-type allowed for a unit of measure.'
            ),
            'options': LITERAL_DATA_TYPE_OPTIONS,
        },
        {
            'key': 'symbol', 
            'label': 'Symbol', 
            'data_type': 'xsd:string',
            'note': (
                'A symbol or short abbreviation used to indicate this unit of measurement. '
                'For example "㎡", indicates a value is in square meters.'
            ),
            'options': None,
        },
    ]
}


MANIFEST_ADD_EDIT_CONFIGS = [
    {
        'group': 'Open Context Items',
        'item_types': [
            {
                'item_type': 'projects', 
                'item_type_note': 'A publication project (collection) or sub-project',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'expected_assert_pred_ids': [
                    configs.PREDICATE_DCTERMS_DESCRIPTION_UUID,
                    configs.PREDICATE_DCTERMS_ABSTRACT_UUID,
                ],
                'expected_resource_types_ids': [
                    configs.OC_RESOURCE_HERO_UUID,
                ],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': None,
                'context_lookup': None,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': {
                    'root_item_id': None,
                    'item_type': ['projects'],
                    'show_project': False,
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                },
                'add_required_attributes': [
                    'label',
                    'data_type',
                ],
            },
            {
                'item_type': 'subjects', 
                'item_type_note': 'A location or object. The main subject of description and observational data in Open Context.',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'expected_assert_pred_ids': [],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': {
                    'root_item_id': 'subjects',
                },
                'context_id': None,
                'context_lookup': {
                    'root_item_id': None,
                    'item_type': ['subjects'],
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                    'show_path_search_box': True,
                    'show_total_results': True,
                    'show_item_class': True,
                    'show_project': True,
                },
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': {
                    'root_item_id': None,
                    'item_type': ['projects'],
                    'show_project': False,
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                },
                'add_required_attributes': [
                    'label',
                    'item_class_id',
                    'context_id',
                    'project_id',
                    'data_type',
                ],
            },
            {
                'item_type': 'media', 
                'item_type_note': 'A media item of binary files (images, 3D)',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'expected_assert_pred_ids': [],
                'expected_resource_types_ids': [
                    configs.OC_RESOURCE_FULLFILE_UUID,
                    configs.OC_RESOURCE_PREVIEW_UUID,
                    configs.OC_RESOURCE_THUMBNAIL_UUID,
                ],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': {
                    'root_item_id': 'media',
                },
                'context_id': None,
                'context_lookup': None,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': {
                    'root_item_id': None,
                    'item_type': ['projects'],
                    'show_project': False,
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                },
                'add_required_attributes': [
                    'label',
                    'item_class_id',
                    'project_id',
                    'data_type',
                ],
            },
            {
                'item_type': 'documents', 
                'item_type_note': 'An HTML or plain text document',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'expected_assert_pred_ids': [
                    configs.PREDICATE_BIBO_CONTENT_UUID,
                ],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': None,
                'context_lookup': None,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': {
                    'root_item_id': None,
                    'item_type': ['projects'],
                    'show_project': False,
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                },
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'data_type',
                ],
            },
            {
                'item_type': 'persons', 
                'item_type_note': 'A person or organization',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'expected_assert_pred_ids': [],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': {
                    'root_item_id': 'persons',
                },
                'context_id': None,
                'context_lookup': None,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': {
                    'root_item_id': None,
                    'item_type': ['projects'],
                    'show_project': False,
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                },
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'data_type',
                ],
            },
            {
                'item_type': 'predicates', 
                'item_type_note': 'A project-defined descriptive attribute or relationship',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'expected_assert_pred_ids': [
                    configs.PREDICATE_SKOS_NOTE_UUID,
                ],
                'expected_resource_types_ids': [],
                'data_type': None,
                'data_type_options': DATA_TYPE_OPTIONS,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': {
                    'uuid': configs.CLASS_LIST_OC_PREDICATES,
                },
                'context_id': None,
                'context_lookup': None,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': {
                    'root_item_id': None,
                    'item_type': ['projects'],
                    'show_project': False,
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                },
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'data_type',
                ],
            },
            {
                'item_type': 'types', 
                'item_type_note': 'A project-defined controlled vocabulary term used with a descriptive attribute',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'expected_assert_pred_ids': [
                    configs.PREDICATE_SKOS_NOTE_UUID,
                ],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': None,
                'context_lookup': {
                    'root_item_id': None,
                    'item_type': ['predicates'],
                    'data_type': ['id'],
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                    'show_project': True,
                },
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': {
                    'root_item_id': None,
                    'item_type': ['projects'],
                    'show_project': False,
                },
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'context_id',
                    'data_type',
                ],
            },
        ],
    },
    # Node item types. These are for grouping different
    # attributes, including geospatial / chronological descriptions
    # together
    {
        'group': 'Descriptive Groupings',
        'item_types': [
            {
                'item_type': 'observations', 
                'item_type_note': 'An episode of description',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'expected_assert_pred_ids': [
                    configs.PREDICATE_SKOS_NOTE_UUID,
                ],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': None,
                'context_lookup': None,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': {
                    'root_item_id': None,
                    'item_type': ['projects'],
                    'show_project': False,
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                },
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'data_type',
                ],
            },
            {
                'item_type': 'events', 
                'item_type_note': 'A distinct spatial and/or chronological description',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'expected_assert_pred_ids': [
                    configs.PREDICATE_SKOS_NOTE_UUID,
                ],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': None,
                'context_lookup': None,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': {
                    'root_item_id': None,
                    'item_type': ['projects'],
                    'show_project': False,
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                },
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'data_type',
                ],
            },
            {
                'item_type': 'attribute-groups', 
                'item_type_note': 'A meaningful sub-group of descriptive attributes',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'expected_assert_pred_ids': [
                    configs.PREDICATE_SKOS_NOTE_UUID,
                ],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': None,
                'context_id': None,
                'context_lookup': None,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': {
                    'root_item_id': None,
                    'item_type': ['projects'],
                    'show_project': False,
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                },
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'data_type',
                ],
            },
        ],
    },
    # Individual concepts / entities
    {
        'group': 'Linked Data Concepts / Items',
        'item_types': [
            {
                'item_type': 'languages', 
                'item_type_note': 'A human language',
                'edit_uuid': False, # Deterministic from vocabulary and URI
                'edit_slug': True,
                'edit_item_key': True,
                'edit_uri': True,
                'expected_assert_pred_ids': [],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': configs.WIKIDATA_VOCAB_UUID, # Must be in Wikidata
                'context_lookup': None,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'context_id',
                    'data_type',
                ],
            },
            {
                'item_type': 'class', 
                'item_type_note': 'A Linked Data concept used in classification',
                'edit_uuid': False, # Deterministic from vocabulary and URI
                'edit_slug': True,
                'edit_item_key': True,
                'edit_uri': True,
                'expected_assert_pred_ids': [],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': None,
                'context_lookup': {
                    'root_item_id': None,
                    'item_type': ['vocabularies'],
                    'show_total_results': True,
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                    'show_project': False,
                },
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'context_id',
                    'data_type',
                ],
            },
            {
                'item_type': 'property', 
                'item_type_note': 'A Linked Data defined descriptive attribute or relationship',
                'edit_uuid': False, # Deterministic from vocabulary and URI
                'edit_slug': True,
                'edit_item_key': True,
                'edit_uri': True,
                'expected_assert_pred_ids': [],
                'expected_resource_types_ids': [],
                'data_type': None,
                'data_type_options': DATA_TYPE_OPTIONS,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': None,
                'context_lookup': {
                    'root_item_id': None,
                    'item_type': ['vocabularies'],
                    'show_total_results': True,
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                    'show_project': False,
                },
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'context_id',
                    'data_type',
                ],
            },
            {
                'item_type': 'uri', 
                'item_type_note': (
                    'A specific Linked Data identified item or instance, '
                    'such as a specific place in a gazetteer, an article in a '
                    'journal repository, or an object in a museum.'
                ),
                'edit_uuid': False, # Deterministic from vocabulary and URI
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': True,
                'expected_assert_pred_ids': [],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': None,
                'context_lookup': {
                    'root_item_id': None,
                    'item_type': ['vocabularies'],
                    'show_total_results': True,
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                    'show_project': False,
                },
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'context_id',
                    'data_type',
                ],
            },
            {
                'item_type': 'units', 
                'item_type_note': 'A Linked Data identified unit of measure',
                'edit_uuid': False, # Deterministic from vocabulary and URI
                'edit_slug': True,
                'edit_item_key': True,
                'edit_uri': True,
                'expected_assert_pred_ids': [],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': configs.WIKIDATA_VOCAB_UUID, # Preference is in Wikidata
                'context_lookup': {
                    'root_item_id': None,
                    'item_type': ['vocabularies'],
                    'show_total_results': True,
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                    'show_project': False,
                },
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'context_id',
                    'data_type',
                ],
            },
            {
                'item_type': 'media-types', 
                'item_type_note': 'A Linked Data identified digital media type',
                'edit_uuid': False, # Deterministic from vocabulary and URI
                'edit_slug': True,
                'edit_item_key': True,
                'edit_uri': True,
                'expected_assert_pred_ids': [],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': configs.IANA_MEDIA_TYPE_VOCAB_UUID, # Preference is in IANA
                'context_lookup': {
                    'root_item_id': None,
                    'item_type': ['vocabularies'],
                    'show_total_results': True,
                    'show_label_search_box': False,
                    'show_q_search_box': True,
                    'show_project': False,
                },
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'context_id',
                    'data_type',
                ],
            },
        ],
    },
    # Linked data vocabularies and publishers
    {
        'group': 'Linked Data Vocabularies, Ontologies, and Publishers',
        'item_types': [
            {
                'item_type': 'vocabularies', 
                'item_type_note': (
                    'An ontology, controlled vocabulary, or data source '
                    'that is NOT part of an Open Context project. Examples include: '
                    'GBIF, UBERON, and the Wikipedia.'
                ),
                'edit_uuid': False, # Deterministic from vocabulary and URI
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': True,
                'expected_assert_pred_ids': [
                    configs.PREDICATE_SKOS_NOTE_UUID,
                ],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': configs.OPEN_CONTEXT_PROJ_UUID,  # Always in the OC project
                'context_lookup': None,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'data_type',
                ],
            },
            {
                'item_type': 'publishers', 
                'item_type_note': 'A person or organization publishing vocabularies or other Linked Data',
                'edit_uuid': False, # Deterministic from vocabulary and URI
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': True,
                'expected_assert_pred_ids': [
                    configs.PREDICATE_SKOS_NOTE_UUID,
                ],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': configs.OPEN_CONTEXT_PROJ_UUID,  # Always in the OC project
                'context_lookup': None,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'project_id',
                    'data_type',
                ],
            },
        ],
    },
]


def api_config_response():
    """Makes a configuration dict for the API response"""
    expected_mappings = [
        ('expected_assert_pred_ids', 'expected_assert_predicates',),
        ('expected_resource_types_ids', 'expected_resource_types',),
    ]
    all_configs = copy.deepcopy(MANIFEST_ADD_EDIT_CONFIGS)
    for config_group in all_configs:
        for item_type_config in config_group['item_types']:
            item_type = item_type_config.get('item_type')
            item_type_config['meta_json_edit'] = ITEM_TYPE_META_JSON_CONFIGS.get(item_type, [])
            for expected_id_list, expected_obj_list in expected_mappings:
                # Iterate through the expected IDs to look up their
                # manifest object to include in the output.
                item_type_config.setdefault(expected_obj_list, [])
                expected_ids = item_type_config.get(expected_id_list, [])
                if not expected_ids:
                    continue
                man_obj_qs = AllManifest.objects.filter(uuid__in=expected_ids)
                for man_obj in man_obj_qs:
                    # NOTE: this works because of the splendor that is 
                    # mutable lists and dicts.
                    item_type_config[expected_obj_list].append(
                        make_model_object_json_safe_dict(
                            man_obj
                        )
                    )
    return all_configs