import copy

from django.contrib.auth.models import User, Group
from opencontext_py.apps.all_items import configs

from opencontext_py.apps.all_items.models import (
    AllManifest,
)

from opencontext_py.libs.models import (
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


# A commonly used attribute to add to meta_json. We also have automated
# ways of triggering this flag, but main way to remove the flag will be through
# a manual interface.
FLAG_HUMAN_REMAINS = {
    'key': 'flag_human_remains',
    'label': 'Flag Human Remains',
    'data_type': 'xsd:boolean',
    'note': 'Flag to warn users of human remains related content.',
    'options': [
        {'value': None, 'text': 'Not set',},
        {'value': True, 'text': 'Flag Human Remains',},
        {'value': False, 'text': 'Un-flag and remove Human Remains flag',},
    ],
}

# This flag, if True, will mean the solr indexer will NOT index an item
FLAG_DO_NOT_INDEX = {
    'key': 'flag_do_not_index',
    'label': 'Flag Do NOT Index',
    'data_type': 'xsd:boolean',
    'note': 'Flag to NOT include in the Solr Index.',
    'options': [
        {'value': None, 'text': 'Not set',},
        {'value': True, 'text': 'Do NOT Index with Solr',},
        {'value': False, 'text': 'Un-flag to permit indexing with Solr',},
    ],
}

# This flag, if True, will mean the solr indexer WILL index an item not normally indexed
FLAG_DO_INDEX = {
    'key': 'flag_do_index',
    'label': 'Flag DO Index',
    'data_type': 'xsd:boolean',
    'note': 'Flag to include in the Solr Index.',
    'options': [
        {'value': None, 'text': 'Not set',},
        {'value': True, 'text': 'DO index with Solr',},
        {'value': False, 'text': 'Un-flag for default, likely no indexing with Solr',},
    ],
}


# Item types allowed to be reindexed by members of an editing group (non-super users)
EDIT_GROUP_USER_ALLOWED_REINDEX_TYPES = [
    'subjects',
    'media',
    'documents',
    'projects',
    'tables',
]


GEO_ZOOM = {
    'key': 'geo_zoom',
    'label': 'Default zoom level for map views',
    'data_type': 'xsd:integer',
    'note': (
        'An integer value indicating the zoom level for map views. '
        'This is strictly a user interface control, '
        'and means nothing about data precision, accuracy or obfuscation. '
    ),
    'options': None,
}


EARLY_DATE = {
    'key': 'earliest_date',
    'label': 'Earliest date',
    'data_type': 'xsd:integer',
    'note': (
        'An integer value indicating this item should have a space-time '
        'record for a date range. Use negative (-) values for calendar years BCE '
        'and positive (+) values for calendar years CE. '
    ),
    'options': None,
}


LATE_DATE = {
    'key': 'latest_date',
    'label': 'Latest date',
    'data_type': 'xsd:integer',
    'note': (
        'An integer value indicating this item should have a space-time '
        'record for a date range. Use negative (-) values for calendar years BCE '
        'and positive (+) values for calendar years CE. '
    ),
    'options': None,
}

def make_login_to_view_config():
    view_groups = Group.objects.filter(name__icontains='can view')
    output = {
        'key': 'view_group_id',
        'label': 'Login view group',
        'data_type': 'xsd:integer',
        'note': 'Optional group membership required for logged in users to view items.',
        'options': [
            {'value': None, 'text': 'Not set',},
        ] + [
            {'value': g.id, 'text': g.name,} for g in view_groups
        ],
    }
    return output

def make_login_to_edit_config():
    edit_groups = Group.objects.filter(name__icontains='can edit')
    output = {
        'key': 'edit_group_id',
        'label': 'Login edit group',
        'data_type': 'xsd:integer',
        'note': 'Optional group membership required for logged in users to edit items.',
        'options': [
            {'value': None, 'text': 'Not set',},
        ] + [
            {'value': g.id, 'text': g.name,} for g in edit_groups
        ],
    }
    return output



# A commonly used attribute to add to meta_json. If this attribute is
# present and is True, then one will need a login to view items. This
# can be applied to single manifest items or whole projects.
LOGIN_TO_VIEW = make_login_to_view_config()

LOGIN_TO_EDIT = make_login_to_edit_config()

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
        {
            'key': 'omit_db_sampling_site',
            'label': 'No not look-up an iSamples sampling-site',
            'data_type': 'xsd:boolean',
            'note': (
                'Do not allow database queries to find sampling sites '
                'for iSamples harvests of this project. Will default to '
                'context.'
            ),
            'options': [
                {'value': None, 'text': 'Not set',},
                {'value': True, 'text': 'OMIT including sampling sites in API results for iSamples',},
                {'value': False, 'text': 'Un-flag for default, allow sampling sites for iSamples',},
            ],
        },
        {
            'key': 'query_context_path',
            'label': 'Context path for project page queries',
            'data_type': 'xsd:string',
            'note': (
                'Slash separated path for the spatial context to use as a filter for '
                'queries from the project page. For example, for the Murlo project, the '
                'context path is: "Europe/Italy".'
            ),
            'options': None,
        },
        GEO_ZOOM.copy(),
        FLAG_HUMAN_REMAINS.copy(),
        LOGIN_TO_VIEW.copy(),
        LOGIN_TO_EDIT.copy(),
        FLAG_DO_NOT_INDEX.copy(),
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
        {
            'key': 'geonames_id',
            'label': 'Geonames ID',
            'data_type': 'xsd:string',
            'note': (
                'A numeric (not a full Web URI) '
                'Geonames identifier.'
            ),
            'options': None,
        },
        {
            'key': 'pleiades_id',
            'label': 'Pleiades ID',
            'data_type': 'xsd:string',
            'note': (
                'A numeric (not a full Web URI) '
                'Pleiades gazetteer identifier.'
            ),
            'options': None,
        },
        {
            'key': 'wikidata_id',
            'label': 'Wikidata ID',
            'data_type': 'xsd:string',
            'note': (
                'An ID (not a full Web URI) '
                'Wikidata concept identifier.'
            ),
            'options': None,
        },
        GEO_ZOOM.copy(),
        FLAG_HUMAN_REMAINS.copy(),
        LOGIN_TO_VIEW.copy(),
        LOGIN_TO_EDIT.copy(),
        FLAG_DO_NOT_INDEX.copy(),
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
        FLAG_HUMAN_REMAINS.copy(),
        LOGIN_TO_VIEW.copy(),
        LOGIN_TO_EDIT.copy(),
        FLAG_DO_NOT_INDEX.copy(),
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
        FLAG_HUMAN_REMAINS.copy(),
        LOGIN_TO_VIEW.copy(),
        LOGIN_TO_EDIT.copy(),
        FLAG_DO_NOT_INDEX.copy(),
    ],
    'tables': [
        {
            'key': 'count_fields',
            'label': 'Count of fields',
            'data_type': 'xsd:integer',
            'note': (
                'An integer value indicating the number of fields (columns) contained '
                'in this data table.'
            ),
            'options':None,
        },
        {
            'key': 'count_rows',
            'label': 'Count of rows',
            'data_type': 'xsd:integer',
            'note': (
                'An integer value indicating the number of rows (records) contained '
                'in this data table.'
            ),
            'options':None,
        },
        {
            'key': 'full_csv_url',
            'label': 'URL to the full CSV file',
            'data_type': 'xsd:string',
            'note': (
                'An (optional) URL to the CSV file of ALL of the rows. '
                'Add this if the CSV file is not stored in a default location.'
            ),
            'options':None,
        },
        {
            'key': 'preview_csv_url',
            'label': 'URL to the preview CSV file',
            'data_type': 'xsd:string',
            'note': (
                'An (optional) URL to the CSV file of a sample of the rows. '
                'Add this if the sample CSV file is not stored in a default location.'
            ),
            'options':None,
        },
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
        FLAG_HUMAN_REMAINS.copy(),
        LOGIN_TO_VIEW.copy(),
        LOGIN_TO_EDIT.copy(),
        FLAG_DO_NOT_INDEX.copy(),
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
        FLAG_HUMAN_REMAINS.copy(),
        LOGIN_TO_VIEW.copy(),
        LOGIN_TO_EDIT.copy(),
        FLAG_DO_NOT_INDEX.copy(),
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
        FLAG_HUMAN_REMAINS.copy(),
        FLAG_DO_NOT_INDEX.copy(),
        FLAG_DO_INDEX.copy(),
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
    ],
    'class': [
        {
            'key': 'deprecated',
            'label': 'Deprecated',
            'data_type': 'xsd:boolean',
            'note': (
                'Is this item is deprecated, and while it is stored, it is not suitable for current use.'
            ),
            'options': [
                {'value': None, 'text': 'Not set',},
                {'value': True, 'text': 'Deprecated (stored but not current, retired)',},
                {'value': False, 'text': 'Not Deprecated (still current)',},
            ],
        },
        FLAG_HUMAN_REMAINS.copy(),
        EARLY_DATE.copy(),
        LATE_DATE.copy(),
    ],
    'types': [
        EARLY_DATE.copy(),
        LATE_DATE.copy(),
    ],
    'property': [
        {
            'key': 'deprecated',
            'label': 'Deprecated',
            'data_type': 'xsd:boolean',
            'note': (
                'Is this item is deprecated, and while it is stored, it is not suitable for current use.'
            ),
            'options': [
                {'value': None, 'text': 'Not set',},
                {'value': True, 'text': 'Deprecated (stored but not current, retired)',},
                {'value': False, 'text': 'Not Deprecated (still current)',},
            ],
        },
        FLAG_HUMAN_REMAINS.copy(),
    ],
    'uri': [
        {
            'key': 'deprecated',
            'label': 'Deprecated',
            'data_type': 'xsd:boolean',
            'note': (
                'Is this item is deprecated, and while it is stored, it is not suitable for current use.'
            ),
            'options': [
                {'value': None, 'text': 'Not set',},
                {'value': True, 'text': 'Deprecated (stored but not current, retired)',},
                {'value': False, 'text': 'Not Deprecated (still current)',},
            ],
        },
        FLAG_HUMAN_REMAINS.copy(),
    ],
    'vocabularies': [
        {
            'key': 'deprecated',
            'label': 'Deprecated',
            'data_type': 'xsd:boolean',
            'note': (
                'Items in this vocabulary are deprecated, and while it is stored, this is not suitable for current use.'
            ),
            'options': [
                {'value': None, 'text': 'Not set',},
                {'value': True, 'text': 'Deprecated (stored but not current, retired)',},
                {'value': False, 'text': 'Not Deprecated (still current)',},
            ],
        },
    ],
}


# NOTE: Adding tables is handled a bit differently, since the added tables
# first need to be generated by the export table process rather than by a
# a normal manifest add process.
TABLES_ADD_EDIT_CONFIG = {
    'item_type': 'tables',
    'item_type_note': 'A tabular data export of a subset of records from one or more projects',
    'edit_uuid': True,
    'edit_slug': True,
    'edit_item_key': False,
    'edit_uri': False,
    'expected_assert_pred_ids': [],
    'expected_resource_types_ids': [
        configs.OC_RESOURCE_FULLFILE_UUID,
        configs.OC_RESOURCE_PREVIEW_UUID,
    ],
    'data_type': 'id',
    'data_type_options': None,
    'item_class_id': configs.DEFAULT_CLASS_UUID,
    'item_class_lookup': None,
    'context_id': None,
    'context_lookup': None,
    'pref_editing_project_id': False,
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
    ],
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
                'edit_published': True,
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
                'pref_editing_project_id': False,
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
                ],
            },
            {
                'item_type': 'subjects',
                'item_type_note': 'A location or object. The main subject of description and observational data in Open Context',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'edit_published': True,
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
                'pref_editing_project_id': True,
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
                ],
            },
            {
                'item_type': 'media',
                'item_type_note': 'A media item of binary files (images, 3D)',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'edit_published': True,
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
                'pref_editing_project_id': True,
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
                ],
            },
            {
                'item_type': 'documents',
                'item_type_note': 'An HTML or plain text document',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'edit_published': True,
                'expected_assert_pred_ids': [
                    configs.PREDICATE_SCHEMA_ORG_TEXT_UUID,
                ],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': None,
                'context_lookup': None,
                'pref_editing_project_id': True,
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
                ],
            },
            {
                'item_type': 'persons',
                'item_type_note': 'A person or organization',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'edit_published': True,
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
                'pref_editing_project_id': True,
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
                ],
            },
            {
                'item_type': 'predicates',
                'item_type_note': 'A project-defined descriptive attribute or relationship',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'edit_published': True,
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
                'pref_editing_project_id': True,
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
                'edit_published': True,
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
                'pref_editing_project_id': True,
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
                'edit_published': True,
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
                'pref_editing_project_id': True,
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
                ],
            },
            {
                'item_type': 'events',
                'item_type_note': 'A distinct spatial and/or chronological description',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'edit_published': True,
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
                'pref_editing_project_id': True,
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
                ],
            },
            {
                'item_type': 'attribute-groups',
                'item_type_note': 'A meaningful sub-group of descriptive attributes',
                'edit_uuid': True,
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': False,
                'edit_published': True,
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
                'pref_editing_project_id': True,
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
                'edit_published': True,
                'expected_assert_pred_ids': [],
                'expected_resource_types_ids': [],
                'data_type': 'id',
                'data_type_options': None,
                'item_class_id': configs.DEFAULT_CLASS_UUID,
                'item_class_lookup': None,
                'context_id': configs.WIKIDATA_VOCAB_UUID, # Must be in Wikidata
                'context_lookup': None,
                'pref_editing_project_id': False,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'uri',
                    'project_id',
                    'context_id',
                ],
            },
            {
                'item_type': 'class',
                'item_type_note': 'A Linked Data concept used in classification',
                'edit_uuid': False, # Deterministic from vocabulary and URI
                'edit_slug': True,
                'edit_item_key': True,
                'edit_uri': True,
                'edit_published': True,
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
                'pref_editing_project_id': False,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'uri',
                    'project_id',
                    'context_id',
                ],
            },
            {
                'item_type': 'property',
                'item_type_note': 'A Linked Data defined descriptive attribute or relationship',
                'edit_uuid': False, # Deterministic from vocabulary and URI
                'edit_slug': True,
                'edit_item_key': True,
                'edit_uri': True,
                'edit_published': True,
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
                'pref_editing_project_id': False,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'uri',
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
                'edit_published': True,
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
                'pref_editing_project_id': False,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'uri',
                    'project_id',
                    'context_id',
                ],
            },
            {
                'item_type': 'units',
                'item_type_note': 'A Linked Data identified unit of measure',
                'edit_uuid': False, # Deterministic from vocabulary and URI
                'edit_slug': True,
                'edit_item_key': True,
                'edit_uri': True,
                'edit_published': True,
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
                'pref_editing_project_id': False,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'uri',
                    'project_id',
                    'context_id',
                ],
            },
            {
                'item_type': 'media-types',
                'item_type_note': 'A Linked Data identified digital media type',
                'edit_uuid': False, # Deterministic from vocabulary and URI
                'edit_slug': True,
                'edit_item_key': True,
                'edit_uri': True,
                'edit_published': True,
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
                'pref_editing_project_id': False,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'uri',
                    'project_id',
                    'context_id',
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
                'edit_published': True,
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
                'pref_editing_project_id': False,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'uri',
                    'project_id',
                ],
            },
            {
                'item_type': 'publishers',
                'item_type_note': 'A person or organization publishing vocabularies or other Linked Data',
                'edit_uuid': False, # Deterministic from vocabulary and URI
                'edit_slug': True,
                'edit_item_key': False,
                'edit_uri': True,
                'edit_published': True,
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
                'pref_editing_project_id': False,
                'project_id': configs.OPEN_CONTEXT_PROJ_UUID,
                'project_lookup': None,
                'add_required_attributes': [
                    'label',
                    'uri',
                    'project_id',
                ],
            },
        ],
    },
]


def api_single_item_type_config_response(item_type_config):
    """Makes a configuration dict for the API response

    :param dict item_type_config: A dict that configures adding of a
        single item-type
    """
    expected_mappings = [
        ('expected_assert_pred_ids', 'expected_assert_predicates',),
        ('expected_resource_types_ids', 'expected_resource_types',),
    ]
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
    return item_type_config


def api_all_item_types_config_response():
    """Makes a configuration dict for the API response"""
    all_configs = copy.deepcopy(MANIFEST_ADD_EDIT_CONFIGS)
    for config_group in all_configs:
        for item_type_config in config_group['item_types']:
            item_type_config = api_single_item_type_config_response(
                item_type_config
            )
    return all_configs