from opencontext_py.libs.general import LastUpdatedOrderedDict, DCterms

from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

# ---------------------------------------------------------------------
# This module contains general configuration global constants for use
# with solr search / query features.
# ---------------------------------------------------------------------

# If this is True, we're using a test solr instance, if False, we
# connect to the default solr server.
USE_TEST_SOLR_CONNECTION = True

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
    'document_count',
    'form_use_life_chrono_tile',
    'discovery_geotile',
    # 'disc_geosource',
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

# Set facet limits for different solr fields. -1 indicates
# no limit to the number of facets, which means the most
# expensive.
SOLR_FIELDS_FACET_LIMITS = [
    ('form_use_life_chrono_tile', -1,),
    ('discovery_geotile', -1,),
    ('disc_geosource', -1,),
]


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
    'oc_gen_predicates___pred_id',
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
RECORD_SNIPPET_HIGHLIGHT_TAG_PRE = '<em class="snippet">'
RECORD_SNIPPET_HIGHLIGHT_TAG_POST = '</em>'

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


# Prefix on identifiers to that it is being referenced as a
# related entity. The SOLR doc will have an underscore, but the public client
# request will have "-" character.
RELATED_ENTITY_ID_PREFIX = SolrDocument.RELATED_SOLR_DOC_PREFIX.replace('_', '-')



# ---------------------------------------------------------------------
# Configs for making solr result sorting
# ---------------------------------------------------------------------

SOLR_SORT_DEFAULT = 'interest_score desc'

SORT_NEW_URL_IGNORE_PARAMS = [
    'geodeep',
    'chronodeep',
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
ITEM_TYPE_MAPPINGS = {
    'subjects': {
        'rdfs:isDefinedBy': 'oc-gen:subjects',
        'label': 'Subjects',
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
        'label': 'Projects',
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
}

ITEM_TYPE_SLUG_MAPPINGS = {
    key: t_dict['slug'] 
    for key, t_dict in ITEM_TYPE_MAPPINGS.items()
}

ITEM_TYPE_URI_MAPPINGS = {
    key: t_dict['rdfs:isDefinedBy'] 
    for key, t_dict in ITEM_TYPE_MAPPINGS.items()
}


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
        'label-prop-template': 'Search Term(s): \'{act_val}\'',
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


# ---------------------------------------------------------------------
# Configs for the search/query response JSON
# ---------------------------------------------------------------------

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
]

# These response types get JSON-LD context objects
RESPONSE_TYPES_JSON_LD_CONTEXT = [
    'context',
    'chrono-facet',
    'geo-facet',
    'geo-feature',
    'geo-project',
    'geo-record',
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
            'label': 'Linked with media (non-image)',
            'facet_path': (FACETS_SOLR_ROOT_PATH_KEYS + ['other_binary_media_count']),
            'param_key': 'other-media',
        },
        {
            'label': 'Linked with documents',
            'facet_path': (FACETS_SOLR_ROOT_PATH_KEYS + ['document_count']),
            'param_key': 'documents',
        },
    ],
}


FACETS_CONTEXT_SUFFIX = (
    SolrDocument.SOLR_VALUE_DELIM + SolrDocument.FIELD_SUFFIX_CONTEXT
)
FACETS_PROP_SUFFIX = (
    SolrDocument.SOLR_VALUE_DELIM + SolrDocument.FIELD_SUFFIX_PREDICATE
)
FACETS_PROJ_SUFFIX = (
    SolrDocument.SOLR_VALUE_DELIM + SolrDocument.FIELD_SUFFIX_PROJECT
)

# Facet configuration for standard fields, identified as standard by
# their suffix. Each tuple means:
#
# (solr_field_suffix, request_param, hierarchy_delim, facet_type)
#
FACETS_STANDARD = [
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
        'Project',
    ),
]

# Facet metadata for standard root fields.
FACET_STANDARD_ROOT_FIELDS = {
    SolrDocument.ROOT_CONTEXT_SOLR: {
        "id": "#facet-context",
        "rdfs:isDefinedBy": "oc-api:facet-context",
        "label": "Context",
        "type": "oc-api:facet-context",
    },
    SolrDocument.ROOT_PREDICATE_SOLR: {
        "id": "#facet-prop-var",
        "rdfs:isDefinedBy": "oc-api:facet-prop-var",
        "label": "Descriptions (Project Defined)",
        "type": "oc-api:facet-prop",
    },
    SolrDocument.ROOT_LINK_DATA_SOLR: {
        "id": "#facet-prop-ld",
        "rdfs:isDefinedBy": "oc-api:facet-prop-ld",
        "label": "Descriptions (Common Standards)",
        "type": "oc-api:facet-prop",
    },
    SolrDocument.ROOT_PROJECT_SOLR: {
        "id": "#facet-project",
        "rdfs:isDefinedBy": "oc-api:facet-project",
        "label": "Project",
        "type": "oc-api:facet-project",
    },
    (
        SolrDocument.RELATED_SOLR_DOC_PREFIX 
        + SolrDocument.ROOT_PREDICATE_SOLR
    ): {
        "id": "#facet-rel-prop-var",
        "rdfs:isDefinedBy": "oc-api:facet-rel-prop-var",
        "label": "Related Descriptions (Project Defined)",
        "type": "oc-api:facet-prop",
        "oc-api:related-property": True,
    },
    (
        SolrDocument.RELATED_SOLR_DOC_PREFIX 
        + SolrDocument.ROOT_LINK_DATA_SOLR
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



# ---------------------------------------------------------------------
# Configs for front-end (HTML) organization of search facets
# ---------------------------------------------------------------------
FILTER_HIERARCHY_DEFAULT_DELIM = ' :: '

# Dictionary keyed by 'oc-api:filter' for delimiters of broader filters
# in a hierarchy.
FILTER_HIERARCHY_DELIMS = {
    'Context': ' / ',
}

FACET_OPT_SUB_HEADING_DEFAULT = ([], 'Other Attributes',)

FACET_OPT_ORDERED_SUB_HEADINGS = [
    (
        ['http://opencontext.org/vocabularies/dinaa/'], 
        'N. American Site (DINAA)',
    ),
    (
        ['http://purl.obolibrary.org/obo/FOODON_00001303'], 
        'Standard Biological',
    ),
    (
        ['http://opencontext.org/vocabularies/open-context-zooarch/'],
        'Standard Zooarchaeological',
    ),
    (
        ['http://erlangen-crm.org/'], 
        'Standard Cultural (CIDOC-CRM)',
    ),
    (
        [
            'http://purl.org/dc/terms/references',
            'http://purl.org/dc/terms/isReferencedBy',
        ],
        'Cross-References',
    ),
    (
        ['http://id.loc.gov/authorities/subjects/'],
        'Library of Congress (LoC)',
    ),
    (
        ['http://vocab.getty.edu/aat/'], 
        'Getty Art and Architecture Thesaurus',
    ),
    (   
        ['http://collection.britishmuseum.org'],
        'British Museum Terms',
    ),
    (   
        ['http://geonames.org/'], 
        'Geonames (Gazetteer)',
    ),
    (   
        ['http://pleiades.stoa.org/'], 
        'Pleiades (Ancient Places Gazetteer)',
    ),
    (
        ['http://levantineceramics.org/wares/'], 
        'Levantine Ceramics Wares',
    ),
    (
        ['http://wikipedia.org/'],
        'Wikipedia Topics',
    ),
    (   
        ['http://purl.org/NET/biol/ns#term_hasTaxonomy'],
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
FACETS_OPTIONS_LISTS_AND_DATA_TYPES = [
    {'data_type': k, 'list_key': v} 
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


