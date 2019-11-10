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
# GENERAL HIERARCHY FUNCTIONS
# ---------------------------------------------------------------------
def get_entity_item_parent_entity(item, add_original=False):
    """Gets the parent entity item dict for an item entity object
    
    :param entity item: See the apps/entity/models entity object for a
        definition. 
    """
    use_id = item.slug
    is_project = False
    if getattr(item, 'item_type', None) == 'projects':
        is_project = True
    if getattr(item, 'uuid', None):
        # Use the UUID for an item if we have it to look up parents.
        use_id = item.uuid
    item_parents = general_get_jsonldish_entity_parents(
        use_id,
        add_original=add_original,
        is_project=is_project,
    ) 
    if not item_parents or not len(item_parents):
        return None
    return item_parents[-1]


def compose_query_on_literal(raw_literal, attribute_item, facet_field):
    """Composes a solr query on literal values."""
    # TODO: Add this functionality.
    return None


def get_general_hierarchic_path_query_dict(
    path_list,
    root_field,
    field_suffix,
    obj_all_slug='',
    fq_solr_field_suffix='',
    value_slug_length_limit=120,
):
    """Gets a solr query dict for a general hierarchic list of
    path item identifiers (usually slugs).
    
    :param list path_list: List of string identifiers (usually slugs)
        for entities, and possibly literals that the client provides to
        search solr.
    :param str root_field: The root dynamic field for this solr query.
        It can be a root___project_id, a root___pred_id, etc.
    :param str field_suffix: They type of solr dynamic field being
        queried. (project_id, pred_id) etc.
    :param str obj_all_slug: An optional slug to identify a more
        specific solr "obj_all" field.
    """
    # NOTE: The goal for this function is to be as general and
    # reusable as possible for generating the solr query fq and
    # facet.fields arguments. It's intended for use with most of the
    # non-spatial-context hierarchies that we index. Because of that
    # it will be somewhat abstract and difficult to understand at
    # first.
    m_cache = MemoryCache()
    query_dict = {'fq': [], 'facet.field': []}

    if obj_all_slug:
        # This makes a more specific "obj_all" field that we use to
        # query all levels of the hierarchy in solr.
        obj_all_slug = (
            obj_all_slug.replace('-', '_')
            + SolrDocument.SOLR_VALUE_DELIM
        )

    if SolrDocument.DO_LEGACY_FQ:
        # Doing the legacy filter query method, so add a
        # suffix of _fq to the solr field.
        fq_solr_field_suffix = '_fq'

    # Make the obj_all_field_fq
    obj_all_field_fq = (
        'obj_all'
        + SolrDocument.SOLR_VALUE_DELIM
        + obj_all_slug
        + field_suffix
        + fq_solr_field_suffix
    )

    # Now start composing fq's for the parent item field with the
    # child as a value of the parent item field.
    facet_field = root_field
    
    # NOTE: The attribute_field_part is a part of a solr-field
    # for cases where the attribute is an entity in the database.
    # It starts with the default value of '' because we start
    # formulating solr queries on general/universal metadata
    # attributes, not the more specific, rarely used attributes that
    # are stored in the database.
    attribute_field_part = ''
    attribute_item = None
    
    for item_id in path_list:
        item = m_cache.get_entity(item_id)
        if not attribute_field_part and not item:
            # We don't recognize the first item, and it is not
            # a literal of an attribute field. So return None.
            return None
        elif not item:
            # We don't recognize the item, so skip the rest for now.
            # TODO: We need to also process literals in requests,
            # because some requests will filter according to
            # numeric, date, or string criteria. These literal
            # requests
            literal_output = compose_query_on_literal(
                raw_literal=item_id,
                attribute_item=attribute_item,
                facet_field=facet_field,
            )
            # Skip, because this doesn't do anything yet.
            continue
        item_parent = get_entity_item_parent_entity(item)
        if item_parent and item_parent.get('slug'):
            # The item has a parent item, and that parent item will
            # make a solr_field for the current item.
            facet_field = (
                # Use the most immediate parent item of the item entity
                # to identify the solr field we need to query. That
                # most immediate item is index -1 (because the item
                # item entity itself is not included in this list, as
                # specified by the add_original=False arg).
                item_parent['slug'].replace('-', '_')
                + SolrDocument.SOLR_VALUE_DELIM
                + attribute_field_part
                + field_suffix  
            )

        # NOTE: If SolrDocument.DO_LEGACY_FQ, we're doing the older
        # approach of legacy "_fq" filter query fields. If this is
        # False, the field_fq does NOT have a "_fq" suffix.
        # 
        # NOTE ON DO_LEGACY_FQ:  
        # Add the _fq suffix to make the field_fq which is what we use
        # to as the solr field to query for the current item. Note! The
        # field_fq is different from the facet_field because when we
        # query solr for slugs, we query solr-fields that end with "_fq".
        # The solr fields that don't have "_fq" are used exclusively for
        # making facets (counts of metadata values in different documents).
        field_fq = facet_field
        if not field_fq.endswith(fq_solr_field_suffix):
            field_fq += fq_solr_field_suffix
        
        # Make the query for the item and the solr field associated
        # with the item's immediate parent (or root, if it has no
        # parents). 
        query_dict['fq'].append('{field_fq}:{item_slug}'.format(
                field_fq=field_fq,
                item_slug=utilities.fq_slug_value_format(item.slug)
            )
        )
        # Now make the query for the item and the solr field
        # associated with all items in the whole hierarchy for this
        # type of solr dynamic field.
        query_dict['fq'].append('{field_fq}:{item_slug}'.format(
                field_fq=obj_all_field_fq,
                item_slug=utilities.fq_slug_value_format(item.slug)
            )
        )
        # Use the current item as the basis for the next solr_field
        # that will be used to query child items in the next iteration
        # of this loop.
        facet_field = (
            item.slug.replace('-', '_')
            + SolrDocument.SOLR_VALUE_DELIM
            + attribute_field_part
            + field_suffix  
        )
        
        if ((getattr(item, 'item_type', None) == 'predicates')
            or (getattr(item, 'entity_type', None) == 'property')):
            # The current item entity is a "predicates" or a "property"
            # type of item. That means the item is a kind of attribute
            # or a "predicate" in linked-data speak, (NOT the value of
            # an attribute). The slugs for such attribute entities are
            # used in solr fields. These will be used in all of the
            # queries of child items as we iterate through this
            # path_list.
            
            # The current item is an attribute item, so copy it for
            # use as we continue to iterate through this path_list.
            attribute_item = item
            
            # Compose the attribute field prefix, which is used to make
            # solr-field names for this particular attribute field.
            attribute_field_part = (
                item.slug.replace('-', '_')
                + SolrDocument.SOLR_VALUE_DELIM
            )
            # Now also update the obj_all_field_fq
            obj_all_field_fq = (
               'obj_all'
                + SolrDocument.SOLR_VALUE_DELIM
                + attribute_field_part
                + field_suffix
                + fq_solr_field_suffix 
            )

    # Make the facet field so solr will return any possible
    # facet values for chilren of the LAST item in this path_list.
    query_dict['facet.field'].append(facet_field)
    return query_dict 


def get_general_hierarchic_paths_query_dict(
    raw_path,
    root_field,
    field_suffix,
    hierarchy_delim=configs.REQUEST_PROP_HIERARCHY_DELIM,
    or_delim=configs.REQUEST_OR_OPERATOR,
    obj_all_slug='',
):
    """Make a solr query for a hierarchic raw path string that may have OR operations."""
    if not raw_path:
        return None
    query_dict = {'fq': [], 'facet.field': []}
    paths_as_lists = utilities.infer_multiple_or_hierarchy_paths(
        raw_path,
        hierarchy_delim=hierarchy_delim,
        or_delim=or_delim,
        get_paths_as_lists=True,
    )
    path_terms = []
    for path_list in paths_as_lists:
        path_query_dict = get_general_hierarchic_path_query_dict(
            path_list,
            root_field=root_field,
            field_suffix=field_suffix,
            obj_all_slug=obj_all_slug,
        )
        if not path_query_dict:
            # This path had entities that could not be found in the
            # database. For now, just skip.
            continue
        # All the solr_query terms for a given hiearchic path need to
        # be satified to in a query. So join all the terms created from
        # a given hierarchic path with the "AND" operator into a single
        # string.
        path_term = utilities.join_solr_query_terms(
            path_query_dict['fq'], operator='AND'
        )
        # Add this path term to all the path terms.
        path_terms.append(path_term)
        query_dict['facet.field'] += path_query_dict['facet.field']
    
    if not path_terms:
        return None
    # The different paths iterated above are all "OR" options (union)
    # for the different paths. Join those together using the OR
    # operator.
    all_paths_term = utilities.join_solr_query_terms(
        path_terms, operator='OR'
    )
    query_dict['fq'] = [all_paths_term]
    return query_dict
   