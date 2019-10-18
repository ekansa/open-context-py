from django.conf import settings

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.libs.memorycache import MemoryCache

from opencontext_py.apps.indexer.solrdocumentnew import (
    get_solr_predicate_type_string,
    general_get_jsonldish_entity_parents,
    SolrDocumentNew as SolrDocument,
)

from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion
from opencontext_py.apps.ldata.linkannotations.equivalence import LinkEquivalence
from opencontext_py.apps.ocitems.assertions.containment import Containment

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import utilities


# ---------------------------------------------------------------------
# This module contains functions translating requests from clients into
# queries to Solr.
#
# NOTE: The functions will typically require database access to get
# required information about entities involved in the search requests.
# Therefore, these functions will require regression testing.
#
# Functions that do not require database access should probably get
# added to the utilities module.
# ---------------------------------------------------------------------



# ---------------------------------------------------------------------
# SPATIAL CONTEXT RELATED FUNCTIONS
# ---------------------------------------------------------------------
def get_containment_parent_slug(slug):
    '''Takes a slug and returns the slug of its parent. Returns 'root'
    if a slug has no parent.
        
    :param str slug: Slug identifying a subjects item.
    '''
    m_cache = MemoryCache()
    cache_key = m_cache.make_cache_key('contain-par-slug', slug)
    parent_slug = m_cache.get_cache_object(cache_key)
    if parent_slug is None:
        contain_obj = Containment()
        # Because it seems to introduce memory errors, turn off
        # caching for this class instance.
        contain_obj.use_cache = False
        parent_slug = contain_obj.get_parent_slug_by_slug(slug)
        m_cache.save_cache_object(cache_key, parent_slug)
    if parent_slug:
        return parent_slug
    return 'root'

def get_valid_context_slugs(paths_list):
    '''Takes a list of context paths and returns a list of
    slugs for valid paths, ignoring invalid paths.
    
    :param list paths_list: List of spatial context path
        strings.
    '''
    m_cache = MemoryCache()
    paths_list = list(paths_list)
    url_fixes = []
    for context in paths_list:
        for url_issue, rep in {'+':' ', '%20':' '}.items():
            if not url_issue in context:
                continue
            url_fix_context = context.replace(url_issue, rep)
            if url_fix_context in paths_list:
                # skip, we already have this context in the paths_list
                continue
            url_fixes.append(url_fix_context)
    # Add a list of url_fixes that have substitutions that maybe
    # needed for replace problematic URL encoding to successfully
    # lookup items.
    paths_list += url_fixes
    valid_context_slugs = []
    for context in list(paths_list):
        # Verify that the contexts are valid
        # find and save the enity to memory
        entity = m_cache.get_entity_by_context(context)
        if not entity:
            # Skip, we couldn't find an entity for
            # this context path
            continue
        if entity.slug in valid_context_slugs:
            # Skip, we already have this entity slug in our valid list.
            continue
        valid_context_slugs.append(entity.slug)
    return valid_context_slugs

def get_spatial_context_query_dict(spatial_context=None):
    '''Returns a query_dict object for a spatial_context path.
    
    :param str spatial_context: Raw spatial context path requested by
        the client.
    '''
    query_dict = {'fq': [], 'facet.field': []}
    if not spatial_context:
        query_dict['fq'] = []
        query_dict['facet.field'] = [SolrDocument.ROOT_CONTEXT_SOLR]
        return query_dict

    # Get a list of spatial context paths in the client request.
    # Multiple paths indicate an "OR" query, where the client is
    # requesting the union of different context paths.
    paths_list = utilities.infer_multiple_or_hierarchy_paths(
        spatial_context,
        hierarchy_delim=configs.REQUEST_CONTEXT_HIERARCHY_DELIM,
        or_delim=configs.REQUEST_OR_OPERATOR
    )
    # Look up slugs for the subjects entities identified by each of the
    # spatial context paths in the paths_list. The valid_context_slugs
    # is a list of slugs for entities successfully identified in a
    # database lookup of the spatial context paths.
    valid_context_slugs = get_valid_context_slugs(paths_list)
    path_terms = []
    for slug in valid_context_slugs:
        parent_slug = get_containment_parent_slug(slug)
        if not parent_slug:
            # An odd case where we don't have a parent slug.
            # Just continue so we don't trigger an error or have
            # weird behavior.
            continue
        path_term = utilities.make_solr_term_via_slugs(
            field_slug=parent_slug,
            solr_dyn_field=SolrDocument.FIELD_SUFFIX_CONTEXT,
            value_slug=slug,
        )
        path_terms.append(path_term)
        # Now add a field to the facet.field list so solr calculates
        # facets for any child contexts that may be contained inside
        # the context identified by the slug "slug".
        query_dict['facet.field'].append(
            slug.replace('-', '_')
            + SolrDocument.SOLR_VALUE_DELIM
            + SolrDocument.FIELD_SUFFIX_CONTEXT
        )
    # NOTE: Multiple path terms are the result of an "OR" (||) operator
    # in the client's request. 
    query_dict['fq'].append(
        utilities.join_solr_query_terms(
            path_terms, operator='OR'
        )
    )
    return query_dict


# ---------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------


# ---------------------------------------------------------------------
# NOTES, NOT USED
# ---------------------------------------------------------------------

def process_hiearchic_query_path(
    path,
    hierarchy_delim=configs.REQUEST_PROP_HIERARCHY_DELIM
):
    path_term = None
    return path_term 


def process_hiearchic_query(
    raw_path,
    hierarchy_delim=configs.REQUEST_PROP_HIERARCHY_DELIM,
    or_delim=configs.REQUEST_OR_OPERATOR,
):
    """Process a raw_path request to formulate a solr query"""
    paths_list = utilities.infer_multiple_or_hierarchy_paths(
        raw_path,
        hierarchy_delim=hierarchy_delim,
        or_delim=or_delim,
    )
    path_terms = []
    for path in paths_list:
        path_term = process_hiearchic_query_path(
            path,
            hierarchy_delim=hierarchy_delim
        )
        path_terms.append(path_term)
    return utilities.join_solr_query_terms(path_terms, operator='OR')
    
    