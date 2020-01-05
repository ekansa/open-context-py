from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

# ---------------------------------------------------------------------
# This module contains general configuration global constants for use
# with solr search / query features.
# ---------------------------------------------------------------------


REQUEST_CONTEXT_HIERARCHY_DELIM = '/'
REQUEST_PROP_HIERARCHY_DELIM = '---'
REQUEST_OR_OPERATOR = '||'
REQUEST_SORT_DIR_DELIM = '--'


REQUEST_URL_FORMAT_EXTENTIONS = [
    ('html', None),
    ('json', '.json'),
    # '.atom', skip for now 
]


# ---------------------------------------------------------------------
# Solr Search Configs
# ---------------------------------------------------------------------
SOLR_DEFAULT_ROW_COUNT = 20
SOLR_MAX_RESULT_ROW_COUNT = 10000

DEFAULT_FACET_FIELDS = [
    SolrDocument.ROOT_LINK_DATA_SOLR,
    SolrDocument.ROOT_PROJECT_SOLR,
    'image_media_count',
    'other_binary_media_count',
    'document_count'
]

PROJECT_FACET_FIELDS = [
    # SolrDocument.ROOT_LINK_DATA_SOLR
    'dc_terms_subject___pred_id',
    'dc_terms_coverage___pred_id',
    'dc_terms_temporal___pred_id',
]

# The number of rows to display by default for different item types
ITEM_TYPE_ROWS = {'projects': 100}

# The minimum number of facets to display for different item types
ITEM_TYPE_FACET_MIN = {'projects': 2}

# Facet fields for different item_types
ITEM_TYPE_FACETFIELDS = {
    'projects': [
        'dc_terms_subject___pred_id',
        # 'dc_terms_temporal___pred_id',
        'dc_terms_spatial___pred_id',
        'dc_terms_coverage___pred_id',
    ],
    'subjects': [
        'oc_gen_subjects___pred_id'
    ],
}


# Lists of tuples to configure filter queries that limit
# for 1 or more linked media resources of different types.
REL_MEDIA_EXISTS = [
    # Tuple means: (url-parameter, solr filter query)
    ('images', 'image_media_count:[1 TO *]',),
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

ITEM_CAT_FIELDS = [
    'oc_gen_subjects___pred_id',
    'oc_gen_media___pred_id',
    'oc_gen_persons___pred_id',
]

REL_CAT_FACET_FIELDS = ['rel__oc_gen_subjects___pred_id']
GENERAL_STATS_FIELDS = [
    'updated',
    'published',
]

CHRONO_STATS_FIELDS =  [
    'form_use_life_chrono_earliest',
    'form_use_life_chrono_latest'
]

MEDIA_STATS_FIELDS = [SolrDocument.FILE_SIZE_SOLR]

LITERAL_DATA_TYPES = [
    'xsd:integer', 
    'xsd:double', 
    'xsd:date', 
    'xsd:boolean', 
    'xsd:string',
]

# ---------------------------------------------------------------------
# Hierarchic parameters configs:
#
# NOTE: There are several parameters that clients can use to make GET
# requests over the Web that need to be processed with hierarchically
# fields and values in solr. The following list of tuples configures
# how different URL parameters from Web GET requsests get translated
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
        'proj', SolrDocument.ROOT_PROJECT_SOLR,
        {
            'root_field': SolrDocument.ROOT_PROJECT_SOLR,
            'field_suffix': SolrDocument.FIELD_SUFFIX_PROJECT,
        },
    ),
    (
        'prop', None,
        {
            'root_field': SolrDocument.ROOT_PREDICATE_SOLR,
            'field_suffix': SolrDocument.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'dc-subject', None,
        {
            'root_field': 'dc_terms_subject___pred_id',
            'obj_all_slug': "dc-terms-subject",
            'field_suffix': SolrDocument.FIELD_SUFFIX_PREDICATE,
            'attribute_field_part': 'dc_terms_subject___',
        },
    ),
    (
        'dc-spatial', None,
        {
            'root_field': 'dc_terms_spatial___pred_id',
            'obj_all_slug': 'dc-terms-spatial',
            'field_suffix': SolrDocument.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'dc-coverage', None,
        {
            'root_field': 'dc_terms_coverage___pred_id',
            'obj_all_slug': 'dc-terms-coverage',
            'field_suffix': SolrDocument.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'dc-temporal', None,
        {
            'root_field': 'dc_terms_temporal___pred_id',
            'obj_all_slug': 'dc-terms-temporal',
            'field_suffix': SolrDocument.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'dc-isReferencedBy', None,
        {
            'root_field': 'dc_terms_isreferencedby___pred_id',
            'obj_all_slug': 'dc-terms-isreferencedby',
            'field_suffix': SolrDocument.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'dc-creator', None, {
            'root_field': 'dc_terms_creator___pred_id',
            'obj_all_slug': 'dc-terms-creator',
            'field_suffix': SolrDocument.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'dc-contributor', None,
        {
            'root_field': 'dc_terms_contributor___pred_id',
            'obj_all_slug': 'dc-terms-contributor',
            'field_suffix': SolrDocument.FIELD_SUFFIX_PREDICATE,
        },
    ),
    (
        'bibo-status', None,
        {
            'root_field': 'bibo_status___pred_id',
            'obj_all_slug': 'bibo-status',
            'field_suffix': SolrDocument.FIELD_SUFFIX_PREDICATE,
        },
    ),
]




# ---------------------------------------------------------------------
# Configs for making solr result sorting
# ---------------------------------------------------------------------

SOLR_SORT_DEFAULT = 'interest_score desc'

SORT_NEW_URL_IGNORE_PARAMS = [
    'geodeep',
    'chronodeep',
    'rows',
    'start'
]

SORT_DEFAULT_TYPE = 'oc-api:sort-interest'
SORT_DEFAULT_LABEL = 'Interest score'
SORT_DEFAULT_ORDER = 'descending'

SORT_OPTIONS = [
    {'type': 'oc-api:sort-item',
     'value': 'item',
     'label': 'Item (type, provenance, label)',
     'opt': True},
    {'type': 'oc-api:sort-updated',
     'value': 'updated',
     'label': 'Updated',
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
    # 'item': 'sort_score',
    'updated': 'updated',
    'published': 'published',
    'interest': 'interest_score'
}


# ---------------------------------------------------------------------
# Configs for making solr queries
# ---------------------------------------------------------------------
# Main item-types mapped to their slugs to get solr-facet field prefix
ITEM_TYPE_SLUG_MAPPINGS = {
    'subjects': 'oc-gen-subjects',
    'media': 'oc-gen-media',
    'documents': 'oc-gen-documents',
    'persons': 'oc-gen-persons',
    'projects': 'oc-gen-projects',
    'types': 'oc-gen-types',
    'predicates': 'oc-gen-predicates',
    'tables': 'oc-gen-tables',
}

ITEM_TYPE_URI_MAPPINGS = {
    'subjects': 'oc-gen:subjects',
    'media': 'oc-gen:media',
    'documents': 'oc-gen:documents',
    'persons': 'oc-gen:persons',
    'projects': 'oc-gen:projects',
    'types': 'oc-gen:types',
    'predicates': 'oc-gen:predicates',
    'tables': 'oc-gen:tables',
}


# ---------------------------------------------------------------------
# Configs for current search/query filters
# ---------------------------------------------------------------------




# Label for full-text search.
FILTER_TEXT_SEARCH_TITLE = 'Current Text Search Filter'

# Request parameters that do not describe filters,
# so ignore them.
FILTER_IGNORE_PARAMS = [
    'geodeep',
    'chronodeep',
    'sort',
    'rows',
    'start'
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
        'oc-api:filter': 'Project',
        'hierarchy_delim': REQUEST_PROP_HIERARCHY_DELIM,
        'is_spatial_context': False,
    },
    'prop': {
        'oc-api:filter': 'Description',
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
        'hierarchy_delim': False,
        'is_spatial_context': False,
    },
    'linked': {
        'oc-api:filter': 'Has cross references',
        # False to not split on hierarchy but do check
        # for entities
        'hierarchy_delim': False,
        'is_spatial_context': False,
    },
    'type': {
        'oc-api:filter': 'Open Context Type',
        'hierarchy_delim': False,
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
    'form-chronotile': {
        'oc-api:filter': 'Time of formation, use, or life',
    },
    'form-start': {
        'oc-api:filter': 'Earliest formation, use, or life date',
    },
    'form-stop': {
        'oc-api:filter': 'Latest formation, use, or life date',
    },
    'disc-geotile': {
        'oc-api:filter': 'Location of discovery or observation',
    },
    'disc-bbox': {
        'oc-api:filter': 'Location of discovery or observation',
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
}