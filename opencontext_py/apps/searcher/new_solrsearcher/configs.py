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

# The miniumum number of facets to display for different item types
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
    {'type': 'oc-api:sort-interest',
     'value': None,
     'label': 'Interest score',
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
