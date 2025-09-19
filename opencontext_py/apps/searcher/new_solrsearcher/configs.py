from opencontext_py.libs.utilities.chronotiles import MAX_TILE_DEPTH
from opencontext_py.apps.all_items import configs as gen_configs
from opencontext_py.apps.indexer import solrdocument_new_schema as SolrDoc

# ---------------------------------------------------------------------
# This module contains general configuration global constants for use
# with solr search / query features.
# ---------------------------------------------------------------------

# If this is True, we're using a test solr instance, if False, we
# connect to the default solr server.
USE_TEST_SOLR_CONNECTION = True

REQUEST_CONTEXT_HIERARCHY_DELIM = '/'
REQUEST_PROP_HIERARCHY_DELIM = SolrDoc.SOLR_VALUE_DELIM.replace('_', '-')
REQUEST_OR_OPERATOR = '||'
REQUEST_SORT_DIR_DELIM = '--'


REQUEST_URL_FORMAT_EXTENTIONS = [
    ('html', None),
    ('json', '.json'),
    # '.atom', skip for now
]


# These are used to add additional request parameters and values to the request_dict.
# For example if 'linked' and 'dinaa' are in the request dict, we need to make sure
# we also have type=subjects, proj=52-digital-index.., and prop=dc-terms-is-ref..
PARAM_KEY_VAL_EXPANSIONS = [
    ('linked', 'dinaa', 'type', 'subjects',),
    ('linked', 'dinaa', 'proj', '52-digital-index-of-north-american-archaeology-dinaa',),
    ('linked', 'dinaa', 'prop', 'dc-terms-is-referenced-by',),
]



# Geospace and chronology related facets are in a hierarchy of
# event classes. For now, we'll only use the root of the hierarchy, but
# in the future we may want to implement features to allow queries and
# visualizations of different types of geospatial and chronological
# events.
ROOT_EVENT_CLASS = SolrDoc.ALL_EVENTS_SOLR


# ---------------------------------------------------------------------
# Solr Search Configs
# ---------------------------------------------------------------------
SOLR_DEFAULT_ROW_COUNT = 50
SOLR_MAX_RESULT_ROW_COUNT = 10000
# This is the threshold for shifting to a cursor to iterate through result
# sets. At this number and above, a cursor should be used for paging.
SOLR_RESULT_COUNT_CURSOR_THRESHOLD = 200000


DEFAULT_FACET_FIELDS = [
    SolrDoc.ROOT_CONTEXT_SOLR,
    # Remove some clutter
    # SolrDoc.ROOT_PROJECT_SOLR,
    SolrDoc.ROOT_LINK_DATA_SOLR,
    'image_media_count',
    'three_d_media_count',
    'gis_media_count',
    'other_binary_media_count',
    'documents_count',
    'all_events___geo_precision_factor',
    'event_class_slugs',
    f'{ROOT_EVENT_CLASS}___geo_count',
    f'{ROOT_EVENT_CLASS}___chrono_count',
    'human_remains',
]

SITEMAP_FACET_FIELD = 'obj_all___project_id'

PROJECT_FACET_FIELDS = [
    # SolrDoc.ROOT_LINK_DATA_SOLR
    'dc_terms_subject___pred_id',
    'dc_terms_coverage___pred_id',
    'dc_terms_temporal___pred_id',
]

# The number of rows to display by default for different item types
ITEM_TYPE_ROWS = {'projects': 100}

# The minimum number of facets to display for different item types
ITEM_TYPE_FACET_MIN = {'projects': 2}

# We exclude collections from project specific summaries.
PROJECT_COLLECTIONS_DATA_PUB_SOLR_SLUG = 'oc_gen_cat_data_publication'
PROJECT_COLLECTIONS_SOLR_SLUG = 'oc_gen_cat_collection'

# Facet fields for different item_types
ITEM_TYPE_FACETFIELDS = {
    'projects': [
        'dc_terms_subject___pred_id',
        # 'dc_terms_temporal___pred_id',
        'dc_terms_spatial___pred_id',
        'dc_terms_coverage___pred_id',

    ],
    """
    'subjects': [
        'oc_gen_subjects___pred_id'
    ],
    'media': [
        'oc_gen_media___pred_id'
    ],
    """
    'subjects': [
        'oc_gen_category___pred_id'
    ],
    'media': [
        'oc_gen_category___pred_id'
    ],
}

# What is the minimum context depth for defaulting to high resolution geo
# spatial tiles? For example "Europe" will have a context depth of 1,
# so will not trigger high resolution tiles, but "Europe/Italy" will.
MIN_CONTEXT_DEPTH_FOR_HIGH_RES_GEOTILES = 2


SOLR_FIELDS_FACET_LIMITS = [
    (f'{ROOT_EVENT_CLASS}___lr_geo_tile', -1,),
    (f'{ROOT_EVENT_CLASS}___geo_tile', -1,),
    (f'{ROOT_EVENT_CLASS}___geo_source', -1,),

    (f'{ROOT_EVENT_CLASS}___lr_chrono_tile', -1,),
    (f'{ROOT_EVENT_CLASS}___chrono_tile', -1,),
    (f'{ROOT_EVENT_CLASS}___chrono_source', -1,),
]


# Lists of tuples to configure filter queries that limit
# for 1 or more linked media resources of different types.
REL_MEDIA_EXISTS = [
    # Tuple means: (url-parameter, solr filter query)
    ('images', 'image_media_count:[1 TO *]',),
    ('3d', 'three_d_media_count:[1 TO *]',),
    ('gis', 'gis_media_count:[1 TO *]',),
    ('other-media', 'other_binary_media_count:[1 TO *]',),
    ('documents', 'document_count:[1 TO *]',),
]

# Lists of tuples to configure simple filter queries
# standard, required metadata fields.
SIMPLE_METADATA = [
    # Tuple means: (url-parameter, solr field)
    ('uuid', 'uuid'),
    ('updated', 'updated'),
    ('published', 'published'),
]

N2T_URI_TEMPLATES = [
    'http://n2t.net/{id}', # ARK (CDL / Merritt)
    'https://n2t.net/{id}', # ARK (CDL / Merritt)
]

PERSISTENT_URI_TEMPLATES = [
    'http://dx.doi.org/{id}', # DOI (old)
    'http://doi.org/{id}', # DOI (new)
    'https://dx.doi.org/{id}', # DOI (old)
    'https://doi.org/{id}', # DOI (new)
    'http://orcid.org/{id}', # Orcid (people)
    'https://orcid.org/{id}', # Orcid (people)
]


ROOT_OC_CATEGORY_SOLR = SolrDoc.ROOT_OC_CATEGORY_SOLR
ITEM_CAT_FIELDS = [
    ROOT_OC_CATEGORY_SOLR,
]

REL_CAT_FACET_FIELDS = [
    f'{SolrDoc.RELATED_SOLR_DOC_PREFIX}{ROOT_OC_CATEGORY_SOLR}'
]

ZOOARCH_FACET_FIELDS_PATH_SOLR_TUPS = [
    ('cidoc-crm-p2-has-type', 'cidoc_crm_p2_has_type___pred_id'),
    ('cidoc-crm-e54-dimension---oc-zoo-anatomical-meas', 'oc_zoo_anatomical_meas___cidoc_crm_e54_dimension___pred_id'),
    ('oc-zoo-has-fusion-char---obo-pato-0000051', 'obo_pato_0000051___oc_zoo_has_fusion_char___cidoc_crm_p2_has_type___pred_id'),
]

# This configures what solr facet fields get grouped into a zooarch preconfig'd set
# of facets. The dict is keyed by the solr_facet_field_key. If all options from
# that solr_facet_field_key need to be added to the preconfiged facet, then
# the value for the key will be "ALL" to include all the options. If only certain
# slug identified options are to be included, those will be expressed in a list.
ZOOARCH_SOLR_FACET_FIELD_KEYS_AND_OPTIONS_SLUGS = {
    'cidoc_crm_p2_has_type___pred_id': [
        'oc-zoo-has-anat-id',
        #'oc-zoo-has-fusion-char',
        'oc-zoo-has-phys-sex-det',
    ],
    'oc_zoo_anatomical_meas___cidoc_crm_e54_dimension___pred_id': 'ALL',
    'obo_pato_0000051___oc_zoo_has_fusion_char___cidoc_crm_p2_has_type___pred_id': 'ALL',
    'ld___pred_id': ['obo-foodon-00001303'],
}


PRECONFIG_FACET_FIELDS_BACKEND = [
    (
        'oc-gen-cat-bio-subj-ecofact',
        {
            'id': '#facet-fgoup-oc-gen-cat-bio-subj-ecofact',
            'rdfs:isDefinedBy': None,
            'label': 'Ecofact (Standards)',
            'slug': 'fgoup-oc-gen-cat-bio-subj-ecofact',
            'type': 'oc-api:facet-prop',
            'solr_facet_field_keys_opts_slugs': ZOOARCH_SOLR_FACET_FIELD_KEYS_AND_OPTIONS_SLUGS,
        },
    ),
    (
        'oc-gen-cat-animal-bone',
        {
            'id': '#facet-fgoup-oc-gen-cat-animal-bone',
            'rdfs:isDefinedBy': None,
            'label': 'Zooarchaelogy (Standards)',
            'slug': 'fgoup-oc-gen-cat-animal-bone',
            'type': 'oc-api:facet-prop',
            'solr_facet_field_keys_opts_slugs': ZOOARCH_SOLR_FACET_FIELD_KEYS_AND_OPTIONS_SLUGS,
        },
    ),
]


ITEM_CAT_FACET_FIELDS_SOLR = {
    'oc-gen-cat-bio-subj-ecofact': ZOOARCH_FACET_FIELDS_PATH_SOLR_TUPS.copy(),
    'oc-gen-cat-animal-bone': ZOOARCH_FACET_FIELDS_PATH_SOLR_TUPS.copy(),
}


GENERAL_STATS_FIELDS = [
    'updated',
    'published',
    'interest_score',
]

CHRONO_STATS_FIELDS =  [
    f'{ROOT_EVENT_CLASS}___chrono_point_0___pdouble',
    f'{ROOT_EVENT_CLASS}___chrono_point_1___pdouble'
]

MEDIA_STATS_FIELDS = [
    SolrDoc.FILE_SIZE_SOLR
]

ALL_TYPES_STATS_FIELDS = (
    GENERAL_STATS_FIELDS
    + CHRONO_STATS_FIELDS
    + MEDIA_STATS_FIELDS
)

ITEM_TYPE_STATS_FIELDS = {
    'projects': GENERAL_STATS_FIELDS,
    'subjects': (
        GENERAL_STATS_FIELDS + CHRONO_STATS_FIELDS
    ),
    'documents': (
        GENERAL_STATS_FIELDS + CHRONO_STATS_FIELDS
    ),
    'media': (
        GENERAL_STATS_FIELDS
        + CHRONO_STATS_FIELDS
        + MEDIA_STATS_FIELDS
    ),
}

LITERAL_DATA_TYPES = [
    'xsd:integer',
    'xsd:double',
    'xsd:date',
    'xsd:boolean',
    'xsd:string',
]




# Tags to use before and after the highlighted term to clearly set the
# term off from surrounding text. These are for the internal solr query
# and solr response
QUERY_SNIPPET_HIGHLIGHT_TAG_PRE = '<h_l>'
QUERY_SNIPPET_HIGHLIGHT_TAG_POST = '</h_l>'

# Tags to use before and after the highlighted term to clearly set the
# term off from surrounding text. These are for the highlighted text
# for result records returned to the client.
# RECORD_SNIPPET_HIGHLIGHT_TAG_PRE = '<em class="snippet">'
# RECORD_SNIPPET_HIGHLIGHT_TAG_POST = '</em>'
RECORD_SNIPPET_HIGHLIGHT_TAG_PRE = '<mark>'
RECORD_SNIPPET_HIGHLIGHT_TAG_POST = '</mark>'

# ---------------------------------------------------------------------
# Hierarchic parameters configs:
#
# NOTE: There are several parameters that clients can use to make GET
# requests over the Web that need to be processed with hierarchically
# fields and values in solr. The following list of tuples configures
# how different URL parameters from Web GET requests get translated
# to solr via the querymaker.get_general_hierarchic_paths_query_dict
# function. The tuple is organized as so:
#
# 1st element: request GET parameter
# 2nd element: field to remove from the Solr facet.field list
#              (usually None).
# 3rd element: dictionary of key-word arguments to supply to
#              querymaker.get_general_hierarchic_paths_query_dict
# ---------------------------------------------------------------------
HIERARCHY_PARAM_TO_SOLR = [
    (
        'path', SolrDoc.ROOT_CONTEXT_SOLR,
        {
            'root_field':SolrDoc.ROOT_CONTEXT_SOLR,
            'field_suffix': SolrDoc.FIELD_SUFFIX_CONTEXT,
        },
    ),
    (
        'proj', SolrDoc.ROOT_PROJECT_SOLR,
        {
            'root_field': SolrDoc.ROOT_PROJECT_SOLR,
            'field_suffix': SolrDoc.FIELD_SUFFIX_PROJECT,
        },
    ),
    (
        'cat', SolrDoc.ROOT_OC_CATEGORY_SOLR,
        {
            'root_field': SolrDoc.ROOT_OC_CATEGORY_SOLR,
            'field_suffix': SolrDoc.ROOT_OC_CATEGORY_SOLR,
        },
    ),
    (
        'prop', None,
        {
            'root_field': SolrDoc.ROOT_PREDICATE_SOLR,
            'field_suffix': SolrDoc.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'dc-subject', None,
        {
            'root_field': 'dc_terms_subject___pred_id',
            'obj_all_slug': "dc-terms-subject",
            'field_suffix': SolrDoc.FIELD_SUFFIX_PREDICATE,
            'attribute_field_part': 'dc_terms_subject___',
        },
    ),
    (
        'dc-spatial', None,
        {
            'root_field': 'dc_terms_spatial___pred_id',
            'obj_all_slug': 'dc-terms-spatial',
            'field_suffix': SolrDoc.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'dc-coverage', None,
        {
            'root_field': 'dc_terms_coverage___pred_id',
            'obj_all_slug': 'dc-terms-coverage',
            'field_suffix': SolrDoc.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'dc-temporal', None,
        {
            'root_field': 'dc_terms_temporal___pred_id',
            'obj_all_slug': 'dc-terms-temporal',
            'field_suffix': SolrDoc.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'dc-isReferencedBy', None,
        {
            'root_field': 'dc_terms_is_referenced_by___pred_id',
            'obj_all_slug': 'dc-terms-is-referenced-by',
            'field_suffix': SolrDoc.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'dc-creator', None, {
            'root_field': 'dc_terms_creator___pred_id',
            'obj_all_slug': 'dc-terms-creator',
            'field_suffix': SolrDoc.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'dc-contributor', None,
        {
            'root_field': 'dc_terms_contributor___pred_id',
            'obj_all_slug': 'dc-terms-contributor',
            'field_suffix': SolrDoc.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'dc-license', None,
        {
            'root_field': 'dc_terms_license___pred_id',
            'obj_all_slug': 'dc-terms-license',
            'field_suffix': SolrDoc.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'bibo-status', None,
        {
            'root_field': 'bibo_status___pred_id',
            'obj_all_slug': 'bibo-status',
            'field_suffix': SolrDoc.FIELD_SUFFIX_PREDICATE,
        },
    ),
]


# Prefix on identifiers to that it is being referenced as a
# related entity. The SOLR doc will have an underscore, but the public client
# request will have "-" character.
RELATED_ENTITY_ID_PREFIX = SolrDoc.RELATED_SOLR_DOC_PREFIX.replace('_', '-')



# ---------------------------------------------------------------------
# Configs for making solr result sorting
# ---------------------------------------------------------------------

SOLR_SORT_DEFAULT = 'interest_score desc, uuid asc'

SORT_NEW_URL_IGNORE_PARAMS = [
    'geodeep',
    'chronodeep',
    'start',
    'fsort',
]

SORT_DEFAULT_TYPE = 'oc-api:sort-interest'
SORT_DEFAULT_LABEL = 'Interest score'
SORT_DEFAULT_ORDER = 'descending'

SORT_OPTIONS = [
    {'type': 'oc-api:sort-item',
     'value': 'item',
     'label': 'Item (type, provenance, label)',
     'opt': True},
    {'type': 'oc-api:sort-item-type',
     'value': 'item-type',
     'label': 'Item type',
     'opt': False},
    {'type': 'oc-api:sort-item-class',
     'value': 'item-class',
     'label': 'General category',
     'opt': True},
    {'type': 'oc-api:sort-project',
     'value': 'project',
     'label': 'Project',
     'opt': True},
    {'type': 'oc-api:sort-updated',
     'value': 'updated',
     'label': 'Updated',
     'opt': True},
    {'type': 'oc-api:sort-context',
     'value': 'context',
     'label': 'Item Context',
     'opt': True},
    {'type': 'oc-api:sort-published',
     'value': 'published',
     'label': 'Published',
     'opt': False},  # don't make a sorting option available in the interface (hide this)
    {'type': SORT_DEFAULT_TYPE,
     'value': None,
     'label': SORT_DEFAULT_LABEL,
     'opt': True}
]

REQUEST_SOLR_SORT_MAPPINGS = {
    'item': 'slug_type_uri_label',
    'updated': 'updated',
    'published': 'published',
    'interest': 'interest_score',
    'item-type': 'item_type',
    'item-class': 'item_class',
    'project': 'project_label',
    'context': 'context_path',
}

# Frontend sort configurations, keyed by
# the frontend table fields.
SORT_OPTIONS_FRONTEND = {
    'descriptiveness': 'interest',
    'label': 'item',
    'updated': 'updated',
    'item_class': 'item-class',
    'context': 'context',
    'project': 'project',
}


# ---------------------------------------------------------------------
# Configs for making solr facet sorting
# ---------------------------------------------------------------------
FACET_SORT_DEFAULT = 'count'



ALL_ATTRIBUTE_GROUPS_SLUG = SolrDoc.ALL_ATTRIBUTE_GROUPS_SLUG

# ---------------------------------------------------------------------
# Configs for making solr queries
# ---------------------------------------------------------------------
# Main item-types mapped to their slugs to get solr-facet field prefix
ITEM_TYPE_MAPPINGS = {
    'subjects': {
        'rdfs:isDefinedBy': 'oc-gen:subjects',
        'label': 'Subjects of Observation',
        'slug': 'oc-gen-subjects',
    },
    'media': {
        'rdfs:isDefinedBy': 'oc-gen:media',
        'label': 'Media',
        'slug': 'oc-gen-media',
    },
    'documents': {
        'rdfs:isDefinedBy': 'oc-gen:documents',
        'label': 'Documents',
        'slug':'oc-gen-documents',
    },
    'persons': {
        'rdfs:isDefinedBy': 'oc-gen:persons',
        'label': 'Persons or organizations',
        'slug': 'oc-gen-persons',
    },
    'projects': {
        'rdfs:isDefinedBy': 'oc-gen:projects',
        'label': 'Projects or collections',
        'slug': 'oc-gen-projects',
    },
    'types': {
        'rdfs:isDefinedBy': 'oc-gen:types',
        'label': 'Descriptive Types',
        'slug': 'oc-gen-types',
    },
    'predicates': {
        'rdfs:isDefinedBy': 'oc-gen:predicates',
        'label': 'Predicates or properties',
        'slug': 'oc-gen-predicates',
    },
    'tables': {
        'rdfs:isDefinedBy': 'oc-gen:tables',
        'label': 'Data tables',
        'slug': 'oc-gen-tables',
    },
    'attribute-groups': {
        'rdfs:isDefinedBy': 'oc-gen:attribute-groups',
        'label': 'Attribute groups',
        'slug': ALL_ATTRIBUTE_GROUPS_SLUG,
    },
}

ITEM_TYPE_SLUG_MAPPINGS = {
    key: t_dict['slug']
    for key, t_dict in ITEM_TYPE_MAPPINGS.items()
}

ITEM_TYPE_URI_MAPPINGS = {
    key: t_dict['rdfs:isDefinedBy']
    for key, t_dict in ITEM_TYPE_MAPPINGS.items()
}

ITEM_TYPE_SLUGS = [
    t_dict['slug']
    for _, t_dict in ITEM_TYPE_MAPPINGS.items()
]

# ---------------------------------------------------------------------
# Configs for current search/query filters
# ---------------------------------------------------------------------

# Label for full-text search.
FILTER_TEXT_SEARCH_TITLE = 'Current Text Search Filter'
URL_TEXT_QUERY_TEMPLATE = '{search_term}'

# Request parameters that do not describe filters,
# so ignore them.
FILTER_IGNORE_PARAMS = [
    'geodeep',
    'chronodeep',
    'sort',
    'rows',
    'start',
    'proj-summary',
    'download',
    'fsort',
]

# Request parameters that describe different search or
# query filters.
FILTER_PARAM_CONFIGS = {
    'path': {
        'oc-api:filter': 'Context',
        'hierarchy_delim': REQUEST_CONTEXT_HIERARCHY_DELIM,
        'is_spatial_context': True,
        'split_hierarchy': None,
    },
    'proj': {
        'oc-api:filter': 'Project or Collection',
        'hierarchy_delim': REQUEST_PROP_HIERARCHY_DELIM,
        'is_spatial_context': False,
    },
    'cat': {
        'oc-api:filter': 'Category',
        'hierarchy_delim': REQUEST_PROP_HIERARCHY_DELIM,
        'is_spatial_context': False,
    },
    'prop': {
        'oc-api:filter': 'Description',
        'hierarchy_delim': REQUEST_PROP_HIERARCHY_DELIM,
        'is_spatial_context': False,
        'label-prop-template': 'Search Term(s): \'{act_val}\'',
    },
    'pers': {
        'oc-api:filter': 'Associated with Person or Organization',
        'hierarchy_delim': REQUEST_PROP_HIERARCHY_DELIM,
        'is_spatial_context': False,
    },
    'dc-subject': {
        'oc-api:filter': 'Has subject metadata',
        'hierarchy_delim': REQUEST_PROP_HIERARCHY_DELIM,
        'is_spatial_context': False,
    },
    'dc-spatial': {
        'oc-api:filter': 'Has spatial metadata',
        'hierarchy_delim': REQUEST_PROP_HIERARCHY_DELIM,
        'is_spatial_context': False,
    },
    'dc-coverage': {
        'oc-api:filter': 'Has coverage / period metadata',
        'hierarchy_delim': REQUEST_PROP_HIERARCHY_DELIM,
        'is_spatial_context': False,
    },
    'dc-temporal': {
        'oc-api:filter': 'Has temporal coverage metadata',
        'hierarchy_delim': REQUEST_PROP_HIERARCHY_DELIM,
        'is_spatial_context': False,
    },
    'dc-isReferencedBy': {
        'oc-api:filter': 'Is referenced by',
        'hierarchy_delim': REQUEST_PROP_HIERARCHY_DELIM,
        'is_spatial_context': False,
    },
    'obj': {
        'oc-api:filter': 'Links (in some manner) to object',
        # False to not split on hierarchy but do check
        # for entities
        'hierarchy_delim': '',
        'is_spatial_context': False,
    },
    'linked': {
        'oc-api:filter': 'Has cross references',
        # False to not split on hierarchy but do check
        # for entities
        'hierarchy_delim': None,
        'is_spatial_context': False,
        'key_in_val_labels': {
            'dinaa': 'Links to, or with, DINAA curated site records'
        },
    },
    'type': {
        'oc-api:filter': 'Open Context Type',
        'hierarchy_delim': '',
        'is_spatial_context': False,
        'look_up_mapping_dict': ITEM_TYPE_SLUG_MAPPINGS,
    },
    'q': {
        'oc-api:filter': FILTER_TEXT_SEARCH_TITLE,
        'label-template': 'Search Term(s): \'{act_val}\'',
    },
    'id': {
        'oc-api:filter': 'Identifier Lookup',
        'label-template': 'Identifier: \'{act_val}\'',
    },
    'allevent-chronotile': {
        'oc-api:filter': 'Time of any event',
    },
    'allevent-start': {
        'oc-api:filter': 'Earliest event date',
    },
    'allevent-stop': {
        'oc-api:filter': 'Latest event date',
    },
    'allevent-geotile': {
        'oc-api:filter': 'Any observed location',
    },
    'bbox': {
        'oc-api:filter': 'Any observed location',
    },
    'images': {
        'oc-api:filter': 'Has related media',
        'label': 'Linked to images',
    },
    'other-media': {
        'oc-api:filter': 'Has related media',
        'label': 'Linked to media (other than images)',
    },
    'documents': {
        'oc-api:filter': 'Has related media',
        'label': 'Linked to documents',
    },
    'gis-media': {
        'oc-api:filter': 'Has related GIS media',
        'label': 'Linked to GIS media',
    },
    '3d-media': {
        'oc-api:filter': 'Has related 3D media',
        'label': 'Linked to 3D media',
    },
}


# ---------------------------------------------------------------------
# Configs for the search/query response JSON
# ---------------------------------------------------------------------

# Below are response types that require facet queries
RESPONSE_TYPES_WITH_FACET_QUERIES = [
    'chrono-facet',
    'prop-range',
    'prop-facet',
    'geo-facet',
    'geo-project',
]

# The response to a search can include different types of search
# results. Below lists the default types included unless otherwise
# specified.
RESPONSE_DEFAULT_TYPES = [
    'context',
    'metadata',
    'chrono-facet',
    'prop-range',
    'prop-facet',
    'geo-facet',
    'geo-feature',
    'geo-record',
    'no-geo-record',
]

# These response types get JSON-LD context objects
RESPONSE_TYPES_JSON_LD_CONTEXT = [
    'context',
    'chrono-facet',
    'geo-facet',
    'geo-feature',
    'geo-project',
    'geo-record',
    'no-geo-record',
]

# Parameters to ignore / remove for generating new search
# query urls. This is for URLS to remove or broaden existing filters,
# more making templates for text searches, and for making facet
# query URLS.
QUERY_NEW_URL_IGNORE_PARAMS = SORT_NEW_URL_IGNORE_PARAMS + ['sort']


# ---------------------------------------------------------------------
# Configs to process facets from the solr-response JSON
# ---------------------------------------------------------------------
STATS_FIELDS_PATH_KEYS = ['stats', 'stats_fields',]

# This lists the keys for finding facets in the JSON solr response
# dict.
FACETS_SOLR_ROOT_PATH_KEYS = [
    'facet_counts',
    'facet_fields',
]

# This lists the keys for finding range facets in the JSON solr
# response.
FACETS_RANGE_SOLR_ROOT_PATH_KEYS = [
    'facet_counts',
    'facet_ranges',
]

# Facets for item_type
FACETS_ITEM_TYPE = {
    'id': '#facet-item-type',
    'rdfs:isDefinedBy': 'oc-api:facet-item-type',
    'label': 'Open Context Type',
    'data-type': 'id',
    'type': 'oc-api:facet-item-type',
    'oc-api:has-id-options': [],
}


# Configs for faceting on links to related media of different types.
FACETS_RELATED_MEDIA = {
    'id': '#related-media',
    'label': 'Has Related Media',
    'oc-api:has-rel-media-options': [
        {
            'label': 'Linked with images',
            'facet_path': (FACETS_SOLR_ROOT_PATH_KEYS + ['image_media_count']),
            'param_key': 'images',
        },
        {
            'label': 'Linked with 3D media',
            'facet_path': (FACETS_SOLR_ROOT_PATH_KEYS + ['three_d_media_count']),
            'param_key': '3d-media',
        },
        {
            'label': 'Linked with GIS media',
            'facet_path': (FACETS_SOLR_ROOT_PATH_KEYS + ['gis_media_count']),
            'param_key': 'gis-media',
        },
        {
            'label': 'Linked with media (non-image)',
            'facet_path': (FACETS_SOLR_ROOT_PATH_KEYS + ['other_binary_media_count']),
            'param_key': 'other-media',
        },
        {
            'label': 'Linked with documents',
            'facet_path': (FACETS_SOLR_ROOT_PATH_KEYS + ['documents_count']),
            'param_key': 'documents',
        },
    ],
}


FACETS_CAT_SUFFIX = (
    SolrDoc.ROOT_OC_CATEGORY_SOLR
)
FACETS_CONTEXT_SUFFIX = (
    SolrDoc.SOLR_VALUE_DELIM + SolrDoc.FIELD_SUFFIX_CONTEXT
)
FACETS_PROP_SUFFIX = (
    SolrDoc.SOLR_VALUE_DELIM + SolrDoc.FIELD_SUFFIX_PREDICATE
)
FACETS_PROJ_SUFFIX = (
    SolrDoc.SOLR_VALUE_DELIM + SolrDoc.FIELD_SUFFIX_PROJECT
)

# Facet configuration for standard fields, identified as standard by
# their suffix. Each tuple means:
#
# (solr_field_suffix, request_param, hierarchy_delim, facet_type)
#
FACETS_STANDARD = [
    (
        FACETS_CAT_SUFFIX,
        'cat',
        REQUEST_PROP_HIERARCHY_DELIM,
        'oc-api:facet-category',
        'Category',
    ),
    (
        FACETS_CONTEXT_SUFFIX,
        'path',
        REQUEST_CONTEXT_HIERARCHY_DELIM,
        'oc-api:facet-context',
        'Context',
    ),
    (
        FACETS_PROP_SUFFIX,
        'prop',
        REQUEST_PROP_HIERARCHY_DELIM,
        'oc-api:facet-prop',
        'Description',
    ),
    (
        FACETS_PROJ_SUFFIX,
        'proj',
        REQUEST_PROP_HIERARCHY_DELIM,
        'oc-api:facet-project',
        'Project or Collection',
    ),
]

SITE_MAP_FACETS_DICT = {
    SITEMAP_FACET_FIELD: {
        'type': 'oc-api:sitemap-facet-project',
        'label': 'Sitemap Project Facets',
        'rdfs:isDefinedBy': 'oc-api:sitemap-facet-project',
        'slug': 'oc-api-sitemap-facet-project',
    }
}

# Facet metadata for standard root fields.
FACET_STANDARD_ROOT_FIELDS = {
    SolrDoc.ROOT_CONTEXT_SOLR: {
        "id": "#facet-context",
        "rdfs:isDefinedBy": "oc-api:facet-context",
        "label": "Context",
        "type": "oc-api:facet-context",
    },
    SolrDoc.ROOT_OC_CATEGORY_SOLR: {
        "id": "#facet-category",
        "rdfs:isDefinedBy": "oc-api:facet-category",
        "label": "Category",
        "type": "oc-api:facet-category",
    },
    SolrDoc.ROOT_PREDICATE_SOLR: {
        "id": "#facet-prop-var",
        "rdfs:isDefinedBy": "oc-api:facet-prop-var",
        "label": "Descriptions (Project Defined)",
        "type": "oc-api:facet-prop",
    },
    SolrDoc.ROOT_LINK_DATA_SOLR: {
        "id": "#facet-prop-ld",
        "rdfs:isDefinedBy": "oc-api:facet-prop-ld",
        "label": "Descriptions (Common Standards)",
        "type": "oc-api:facet-prop",
    },
    SolrDoc.ROOT_PROJECT_SOLR: {
        "id": "#facet-project",
        "rdfs:isDefinedBy": "oc-api:facet-project",
        "label": "Project or Collection",
        "type": "oc-api:facet-project",
    },
    (
        SolrDoc.RELATED_SOLR_DOC_PREFIX
        + SolrDoc.ROOT_PREDICATE_SOLR
    ): {
        "id": "#facet-rel-prop-var",
        "rdfs:isDefinedBy": "oc-api:facet-rel-prop-var",
        "label": "Related Descriptions (Project Defined)",
        "type": "oc-api:facet-prop",
        "oc-api:related-property": True,
    },
    (
        SolrDoc.RELATED_SOLR_DOC_PREFIX
        + SolrDoc.ROOT_LINK_DATA_SOLR
    ): {
        "id": "#facet-rel-prop-ld",
        "rdfs:isDefinedBy": "oc-api:facet-rel-prop-ld",
        "label": "Related Descriptions (Common Standards)",
        "type": "oc-api:facet-prop",
        "oc-api:related-property": True,
    },
}


# Mappings between Solr field data types and facet options lists
FACETS_DATA_TYPE_OPTIONS_LISTS = {
    'id': 'oc-api:has-id-options',
    'bool': 'oc-api:has-boolean-options',
    'int': 'oc-api:has-integer-options',
    'double': 'oc-api:has-float-options',
    'date': 'oc-api:has-date-options',
    'string': 'oc-api:has-text-options',
    # This is not a data-type, but is convenient to include
    # here to assist in HTML templating.
    'media': 'oc-api:has-rel-media-options',
}


# Slugs to identify facet options to ignore / skip
# in the facet results
NOT_INCLUDE_FACET_OPTION_SLUGS = [
    'oc-world-root',
    'open-context',
]

# Default time-space event category for API
DEFAULT_API_EVENT_ID = 'oc-gen:general-time-space'



# ---------------------------------------------------------------------
# Configs to process records from the solr-response JSON
# ---------------------------------------------------------------------
RECORD_PATH_KEYS = ['response', 'docs',]

# Delimiter for listing multiple attribute slugs in the client request
MULTIVALUE_ATTRIB_CLIENT_DELIM = ','

# Delimiter for multiple values of a given attribute in response to
# the client.
MULTIVALUE_ATTRIB_RESP_DELIM = '; '

# Client request values for all attributes found on each record
REQUEST_ALL_ATTRIBUTES = 'ALL-ATTRIBUTES'

# Client request values for all linked-data (standards) attributes
# on each record
REQUEST_ALL_LD_ATTRIBUTES = 'ALL-STANDARD-LD'

# Client request values for all project specific attributes
# on each record
REQUEST_ALL_PROJ_ATTRIBUTES ='ALL-PROJECT'

# Client request for iSamples specific attributes and nested presentation of results
REQUEST_ISAMPLES_ATTRIBUTES = 'iSamples'

# Attribute shape, for Nested JSON objects
REQUEST_NESTED_JSON_ATTRIBUTES = 'JSON-NESTED'


ISAMPLES_DEFAULT_CLASS_SLUGS = [
    'oc-gen-cat-sample-col',
    'oc-gen-cat-bio-subj-ecofact',
    'oc-gen-cat-object',
    'oc-gen-cat-c14-sample',
]

ISAMPLES_DEFAULT_CLASS_SLUG_RAW_PATH = REQUEST_OR_OPERATOR.join(ISAMPLES_DEFAULT_CLASS_SLUGS)

# Sampling site OK item_classes for a given specimen's context
ISAMPLES_SAMPLING_SITE_ITEM_CLASS_SLUGS = [
    'oc-gen-cat-site',
    'oc-gen-cat-sampling-site',
]

# ---------------------------------------------------------------------
# Configs for front-end (HTML) organization of search facets
# ---------------------------------------------------------------------
FILTER_HIERARCHY_DEFAULT_DELIM = ' :: '

# Dictionary keyed by 'oc-api:filter' for delimiters of broader filters
# in a hierarchy.
FILTER_HIERARCHY_DELIMS = {
    'Context': ' / ',
}

FACET_OPT_SUB_HEADING_DEFAULT_LABEL = 'Other Attributes'
FACET_OPT_SUB_HEADING_DEFAULT = ([], FACET_OPT_SUB_HEADING_DEFAULT_LABEL,)

FACET_OPT_ORDERED_SUB_HEADINGS = [
    (
        [
            'opencontext.org/vocabularies/dinaa/',
            'staging.opencontext.org/vocabularies/dinaa/',
            'http://127.0.0.1:8000/vocabularies/dinaa/',
        ],
        'N. American Site (DINAA)',
    ),
    (
        ['purl.obolibrary.org/obo/FOODON_00001303',],
        'Standard Biological',
    ),
    (
        [
            'opencontext.org/vocabularies/open-context-zooarch/',
            'staging.opencontext.org/vocabularies/open-context-zooarch/',
            'http://127.0.0.1:8000/vocabularies/open-context-zooarch/',
        ],
        'Standard Zooarchaeological',
    ),
    (
        ['erlangen-crm.org/'],
        'Standard Cultural (CIDOC-CRM)',
    ),
    (
        [
            'purl.org/dc/terms/references',
            'purl.org/dc/terms/isReferencedBy',
        ],
        'Cross-References',
    ),
    (
        ['id.loc.gov/authorities/subjects/'],
        'Library of Congress (LoC)',
    ),
    (
        ['vocab.getty.edu/aat/'],
        'Getty Art and Architecture Thesaurus',
    ),
    (
        ['collection.britishmuseum.org'],
        '(Deprecated) British Museum Terms',
    ),
    (
        ['geonames.org/'],
        'Geonames (Gazetteer)',
    ),
    (
        ['pleiades.stoa.org/'],
        'Pleiades (Ancient Places Gazetteer)',
    ),
    (
        ['levantineceramics.org/wares/', 'www.levantineceramics.org/wares/',],
        'Levantine Ceramics Wares',
    ),
    (
        ['purl.org/dc/terms/'],
        'Publication Metadata (Dublin Core)',
    ),
    (
        ['n2t.net/ark:/99152/p0', 'https://n2t.net/ark:/99152/p0', ],
        'Time Periods (PeriodO)',
    ),
    (
        ['wikipedia.org/', 'en.wikipedia.org/wiki/',],
        'Wikipedia Topics',
    ),
    (
        ['purl.org/NET/biol/ns#term_hasTaxonomy'],
        '(Deprecated) Biological',
    ),
    FACET_OPT_SUB_HEADING_DEFAULT,
]

# This is the above list, but as dicts not tuples for easier use
# in javascript.
FACET_OPT_ORDERED_SUB_HEADINGS_DICTS = [
    {'uris':uri_list, 'label': label}
    for uri_list, label in FACET_OPT_ORDERED_SUB_HEADINGS
]

FACET_DATA_TYPE_FRONT_END_LABEL_PREFIXES = {
    'id': '',
    'bool': 'True/False ',
    'int': 'Integer ',
    'double': 'Decimal ',
    'date': 'Calendar ',
    'string': 'Text ',
    'media': '',
}

FACETS_OPTIONS_LISTS_AND_DATA_TYPES = [
    {'data_type': k, 'list_key': v, 'label_prefix': FACET_DATA_TYPE_FRONT_END_LABEL_PREFIXES.get(k)}
    for k,v in FACETS_DATA_TYPE_OPTIONS_LISTS.items()
]


FACET_OPT_SUB_HEADING_URI_MAPS = {
    'http://purl.obolibrary.org/obo/FOODON_00001303': 'Standard Biological',
    'http://purl.org/NET/biol/ns#term_hasTaxonomy': '(Deprecated) Biological',
    'http://purl.org/dc/terms/references': 'Cross-References',
    'http://purl.org/dc/terms/isReferencedBy': 'Cross-References',
}

FACET_OPT_HIDE_URI_MAPS = [
    'http://purl.org/NET/biol/ns#term_hasTaxonomy',
    'http://www.w3.org/2004/02/skos/core#closeMatch',
    'http://purl.org/dc/terms/subject',
    'http://www.wikidata.org/wiki/Q247204',
    'http://www.w3.org/2004/02/skos/core#related',
    'http://purl.org/dc/terms/isPartOf',
    'http://purl.org/dc/terms/hasPart'
]

FACET_OPT_HIDE_URI_PREFIX_MAPS = [

]


# Levels of tile aggregation supported for geospatial
MIN_GEOTILE_ZOOM = SolrDoc.MIN_GEOTILE_ZOOM
MAX_GEOTILE_ZOOM = SolrDoc.MAX_GEOTILE_ZOOM

# Levels of tile aggregation supported for chronology
MIN_CHRONOTILE_ZOOM = 12
DEFAULT_CHRONOTILE_ZOOM = 16
MAX_CHRONOTILE_ZOOM = MAX_TILE_DEPTH

# Maximum number of project facets to allow for
# querying for image overlays
MAX_PROJECTS_FOR_OVERLAYS = 5
GEO_OVERLAY_OPACITY_DEFAULT = 0.9

# URL parts that ONLY support the http protocol, not https
HTTP_ONLY_URL_PARTS = [
    'purl.obolibrary.org'
]

# Site documentation pages need some special handling on the front end
# view options
CLASS_OC_SITE_DOCUMENTATION_LABEL = gen_configs.CLASS_OC_SITE_DOCUMENTATION_LABEL


# ---------------------------------------------------------------------
# Keywords configs
# Facet congifurations for keywords, which are strings that are
# used in named enities that describe Open Context records and power
# the search suggestions. Exposing key words in factes can help
# users understand the main themes of the data in Open Context.
# ---------------------------------------------------------------------
KEYWORDS_FACET_LIMIT = 1000
KEYWORDS_FACET_MINCOUNT = 100

KEYWORDS_TO_SKIP = [
    "license",
    "context",
    "open",
    "items",
    "creator",
    "4.0",
    "attribution",
    "cc",
    "international",
    "commons",
    "creative",
    "licenses",
    "subjects",
    "bce",
    "ce",
]

# Facets for item_type
FACETS_KEYWORDS = {
    'id': '#facet-keywords',
    'rdfs:isDefinedBy': 'oc-api:keywords',
    'label': 'Keywords',
    'data-type': 'xsd:string',
    'type': 'oc-api:facet-keywords',
    'oc-api:has-id-options': [],
}
