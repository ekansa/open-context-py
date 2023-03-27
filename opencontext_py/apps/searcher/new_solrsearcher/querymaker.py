import re


from opencontext_py.libs.chronotiles import ChronoTile

from opencontext_py.apps.entities.uri.models import URImanagement

from opencontext_py.apps.indexer import solrdocument_new_schema as SolrDoc
from opencontext_py.apps.indexer.solr_utils import replace_slug_in_solr_field

from opencontext_py.apps.all_items.configs import (
    URI_ITEM_TYPES,
    DEFAULT_SUBJECTS_ROOTS
)
from opencontext_py.apps.all_items.models import AllManifest

from opencontext_py.apps.searcher.new_solrsearcher import configs
from opencontext_py.apps.searcher.new_solrsearcher import db_entities
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


# -------------------------------------------------------------
# SIMPLE, GENERAL METADATA RELATED FUNCTIONS
# -------------------------------------------------------------
def get_simple_metadata_query_dict(raw_value, solr_field):
    """Gets a query dict for simple, standard metadata solr fields"""
    if not raw_value:
        return None
    query_dict = {'fq': []}
    values_list = utilities.infer_multiple_or_hierarchy_paths(
        raw_value,
        or_delim=configs.REQUEST_OR_OPERATOR
    )
    terms = []
    for value in values_list:
        if not value:
            continue
        fq_term = '{}:{}'.format(solr_field, value)
        terms.append(fq_term)
    # Join the various path queries as OR terms.
    query_dict['fq'].append(
        utilities.join_solr_query_terms(
            terms, operator='OR'
        )
    )
    return query_dict


# -------------------------------------------------------------
# IDENTIFIER QUERY FUNCTIONS
# -------------------------------------------------------------
def get_identifier_query_dict(raw_identifier):
    """Make a query dict for identifiers"""
    if not raw_identifier:
        return None
    query_dict = {'fq': []}
    fq_terms = []

    values_list = utilities.infer_multiple_or_hierarchy_paths(
        raw_identifier,
        or_delim=configs.REQUEST_OR_OPERATOR,
        hierarchy_delim=None
    )
    id_list = []
    for value in values_list:
        if not value:
            continue
        id_list += utilities.make_uri_equivalence_list(value)

    for act_id in id_list:
        # The act_id maybe a persistent URI, escape it and
        # query the persistent_uri string.
        escape_id = utilities.escape_solr_arg(act_id)
        fq_terms.append('persistent_uri:{}'.format(escape_id))
        if ':' in act_id:
            # Skip below, because the act_id has a
            # character that's not in uuids or slugs.
            continue
        # The act_id maybe a UUID.
        fq_terms.append('uuid:{}'.format(act_id))
        # The act_id maybe a slug, so do a prefix query
        # for document slug_type_uri_label.
        fq_terms.append('slug_type_uri_label:{}'.format(
                utilities.fq_slug_value_format(act_id)
            )
        )

    # Now make URIs in case we have a naked identifier
    prefix_removes = [
        'doi:',
        'orcid:',
        'http://dx.doi.org/',
        'https://dx.doi.org/',
        'http://doi.org/',
        'https://doi.org/'
    ]
    for value in values_list:
        if not value:
            continue
        for prefix in prefix_removes:
            # strip ID prefixes, case insensitive
            re_gone = re.compile(re.escape(prefix), re.IGNORECASE)
            identifier = re_gone.sub('', value)
            if (identifier.startswith('http://')
                or identifier.startswith('https://')):
                continue

            # Only loop through URI templaces for N2T if
            # we have an ARK identifier.
            if identifier.startswith('ark:'):
                uri_templates = configs.N2T_URI_TEMPLATES
            else:
                uri_templates = configs.PERSISTENT_URI_TEMPLATES
            for uri_template in uri_templates:
                temp_uri = uri_template.format(id=identifier)
                temp_uri = AllManifest().clean_uri(temp_uri)
                escaped_uri = utilities.escape_solr_arg(temp_uri)
                fq_term = 'persistent_uri:{}'.format(escaped_uri)
                if fq_term in fq_terms:
                    # We already have this, so skip.
                    continue
                fq_terms.append(fq_term)
        # Now see if there's a UUID in the identifier.
        oc_check = URImanagement.get_uuid_from_oc_uri(value, True)
        if oc_check:
            # We have an identifier we can interperate as an
            # Open Context URI. So extract the uuid part.
            fq_term = 'uuid:{}'.format(oc_check['uuid'])
            if fq_term in fq_terms:
                # We already have this, so skip.
                continue
            fq_terms.append('uuid:{}'.format(oc_check['uuid']))

    # Join the various identifier queries as OR terms.
    query_dict['fq'].append(
        utilities.join_solr_query_terms(
            fq_terms, operator='OR'
        )
    )
    return query_dict


def get_object_uri_query_dict(raw_object_uri):
    """Make a query dict for object uris"""
    if not raw_object_uri:
        return None
    query_dict = {'fq': []}
    fq_terms = []

    values_list = utilities.infer_multiple_or_hierarchy_paths(
        raw_object_uri,
        or_delim=configs.REQUEST_OR_OPERATOR
    )
    id_list = []
    for value in values_list:
        if not value:
            continue
        id_list += utilities.make_uri_equivalence_list(value)

    for act_id in id_list:
        # Allow any unique ID for the search, but solr only indexes
        # URIs. So we first hit the database to get the manifest object
        # for this ID so we can then use the manifest object's URI
        # in the search.
        man_obj = db_entities.get_cache_man_obj_by_any_id(act_id)
        if not man_obj:
            continue
        # The act_id maybe a persistent URI, escape it and
        # query the persistent_uri string.
        escape_id = utilities.escape_solr_arg(man_obj.uri)
        fq_term = f'((object_uri:{man_obj.uri}) OR (object_uri:{escape_id}))'
        if fq_term in fq_terms:
            # We already have this, so skip
            continue
        fq_terms.append(fq_term)

    # Join the various object_uri queries as OR terms.
    query_dict['fq'].append(
        utilities.join_solr_query_terms(
            fq_terms, operator='OR'
        )
    )
    return query_dict


def get_person_query_dict(raw_person_id):
    """Make a query dict for joined persons"""
    if not raw_person_id:
        return None
    query_dict = {'fq': [],}
    # query_dict = {'fq': [], 'facet.field': []}
    fq_terms = []

    values_list = utilities.infer_multiple_or_hierarchy_paths(
        raw_person_id,
        or_delim=configs.REQUEST_OR_OPERATOR
    )
    for value in values_list:
        # Allow any unique ID for the search, but solr only indexes
        # URIs. So we first hit the database to get the manifest object
        # for this ID so we can then use the manifest object's URI
        # in the search.
        man_obj = db_entities.get_cache_man_obj_by_any_id(value)
        if not man_obj:
            continue
        if man_obj.item_type != 'persons':
            continue
        solr_slug = man_obj.slug.replace('-', '_')
        fq_term = f'join_person_orgs___pred_id:{solr_slug}___*'
        if fq_term in fq_terms:
            # We already have this, so skip
            continue
        fq_terms.append(fq_term)
    # Join the various object_uri queries as OR terms.
    query_dict['fq'].append(
        utilities.join_solr_query_terms(
            fq_terms, operator='OR'
        )
    )
    # query_dict['facet.field'].append('join_person_orgs___pred_id')
    return query_dict



# -------------------------------------------------------------
# ITEM_TYPE FUNCTIONS
# -------------------------------------------------------------
def get_item_type_query_dict(raw_item_type):
    """Gets a query dict for item_types"""
    query_dict = {'fq': [], 'facet.field': []}
    paths_list = utilities.infer_multiple_or_hierarchy_paths(
        raw_item_type,
        or_delim=configs.REQUEST_OR_OPERATOR
    )
    path_terms = []
    for item_type in paths_list:
        item_type_slug =configs.ITEM_TYPE_SLUG_MAPPINGS.get(item_type)
        if not item_type_slug:
            # We can't map the item type to a slug so skip.
            continue
        path_term = 'item_type:{}'.format(item_type)
        path_terms.append(path_term)
        # Now add a field to the facet.field list so solr calculates
        # facets for class_uris for the current item type.
        query_dict['facet.field'].append(configs.ROOT_OC_CATEGORY_SOLR)
    # NOTE: Multiple item_type terms are the result of an "OR" (||) operator
    # in the client's request.
    query_dict['fq'].append(
        utilities.join_solr_query_terms(
            path_terms, operator='OR'
        )
    )
    return query_dict


# ---------------------------------------------------------------------
# GEOSPACE AND TIME FUNCTIONS
# ---------------------------------------------------------------------
def get_discovery_bbox_query_dict(raw_disc_bbox):
    """Makes a filter query for a discovery location bounding box"""
    query_dict = {'fq': []}
    terms = []
    bbox_list = utilities.infer_multiple_or_hierarchy_paths(
        raw_disc_bbox,
        or_delim=configs.REQUEST_OR_OPERATOR
    )
    for bbox_str in bbox_list:
        bbox_coors = utilities.return_validated_bbox_coords(bbox_str)
        if not bbox_coors:
            # Not valid so skip out of the function
            print(f'Invalid coordinates {bbox_str}')
            return None
        # Valid bounding box, now make a solr-query
        # not how solr expacts latitude / longitude order, which
        # is the revserse of geojson!
        q_bbox = f'[{bbox_coors[1]},{bbox_coors[0]} TO {bbox_coors[3]},{bbox_coors[2]}]'
        fq_term = f'{configs.ROOT_EVENT_CLASS}___geo_location_rpt:{q_bbox}'
        terms.append(fq_term)
    # Join the various bounding box query OR terms.
    query_dict['fq'].append(
        utilities.join_solr_query_terms(
            terms, operator='OR'
        )
    )
    return query_dict


def make_tile_query_dict(raw_tile_path, solr_field, max_path_length):
    """Makes a filter query general tile path (geo or chrono)"""
    query_dict = {'fq': [], 'facet.field': [solr_field]}
    paths_list = utilities.infer_multiple_or_hierarchy_paths(
        raw_tile_path,
        or_delim=configs.REQUEST_OR_OPERATOR
    )
    terms = []
    for path in paths_list:
        if len(path) < max_path_length:
            path += '*'
        fq_term = '{}:{}'.format(solr_field, path)
        terms.append(fq_term)
    # Join the various path queries as OR terms.
    query_dict['fq'].append(
        utilities.join_solr_query_terms(
            terms, operator='OR'
        )
    )
    return query_dict


def get_discovery_geotile_query_dict(raw_disc_geo, low_res=True):
    """Makes a filter query for a discovery location geotile"""
    solr_field = f'{configs.ROOT_EVENT_CLASS}___lr_geo_tile'
    if not low_res:
        solr_field = f'{configs.ROOT_EVENT_CLASS}___geo_tile'
    return make_tile_query_dict(
        raw_tile_path=raw_disc_geo,
        solr_field=solr_field,
        max_path_length=SolrDoc.MAX_GEOTILE_ZOOM,
    )


def get_form_use_life_chronotile_query_dict(raw_chrono_tile, low_res=True):
    """Makes a filter query for formation-use-life chrono-tile string"""
    solr_field = f'{configs.ROOT_EVENT_CLASS}___lr_chrono_tile'
    if not low_res:
        solr_field = f'{configs.ROOT_EVENT_CLASS}___chrono_tile'
    return make_tile_query_dict(
        raw_tile_path=raw_chrono_tile,
        solr_field=solr_field,
        max_path_length=ChronoTile().MAX_TILE_DEPTH,
    )


def get_all_event_chrono_span_query_dict(all_start=None, all_stop=None):
    """Makes a filter query for formation-use-life chrono based on
    start and/or stop times
    """
    if all_start is None and all_stop is None:
        return None
    if all_start is None:
        # Set the start to be older than the entire Cosmos.
        all_start = -15*1000*1000*1000
    if all_stop is None:
        # Set the stop long after the Sun would have died.
        all_stop = 10*1000*1000*1000
    term =  f'{configs.ROOT_EVENT_CLASS}___chrono_point:[{all_start},{all_start} TO {all_stop},{all_stop}]'
    return {'fq': [term]}


# ---------------------------------------------------------------------
# SPATIAL CONTEXT RELATED FUNCTIONS
# ---------------------------------------------------------------------

def add_url_fixes_to_paths_list(paths_list):
    """Adds URL fixes to paths lists

    :param list paths_list: List of spatial context path
        strings.

    :return list
    """
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
    return paths_list

def get_spatial_context_query_dict(spatial_context=None):
    '''Returns a query_dict object for a spatial_context path.

    :param str spatial_context: Raw spatial context path requested by
        the client.
    '''
    query_dict = {'fq': [], 'facet.field': []}
    if not spatial_context:
        query_dict['fq'] = []
        query_dict['facet.field'] = [SolrDoc.ROOT_CONTEXT_SOLR]
        return query_dict

    # Get a list of spatial context paths in the client request.
    # Multiple paths indicate an "OR" query, where the client is
    # requesting the union of different context paths.
    paths_list = utilities.infer_multiple_or_hierarchy_paths(
        spatial_context,
        hierarchy_delim=configs.REQUEST_CONTEXT_HIERARCHY_DELIM,
        or_delim=configs.REQUEST_OR_OPERATOR
    )

    # Now add path items with URL escape fixes if needed.
    paths_list = add_url_fixes_to_paths_list(paths_list)

    # Get manifest objects from the paths list. This uses the cache,
    # or the DB if the cache doesn't have what we want.
    path_terms = []
    for man_obj in db_entities.get_cache_manifest_items_by_path(
        paths_list
    ):
        parent_slug = man_obj.context.slug
        if str(man_obj.context.uuid) in DEFAULT_SUBJECTS_ROOTS:
            # We're at the root of spatial containment.
            parent_slug = 'root'
        # Make the query term for the path
        path_term = utilities.make_solr_term_via_slugs(
            field_slug=parent_slug,
            solr_dyn_field=SolrDoc.FIELD_SUFFIX_CONTEXT,
            value_slug=man_obj.slug,
        )
        path_terms.append(path_term)
        # Now add a field to the facet.field list so solr calculates
        # facets for any child contexts that may be contained inside
        # the context identified by the slug "slug".
        query_dict['facet.field'].append(
            man_obj.slug.replace('-', '_')
            + SolrDoc.SOLR_VALUE_DELIM
            + SolrDoc.FIELD_SUFFIX_CONTEXT
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

def get_range_stats_fields(attribute_item_obj, field_fq, attribute_group_obj_slug=None):
    """Prepares facet request for value range (numeric, date) fields"""
    # Strip the '_id' end of the field_fq (for the filter query).
    # The field_fq needs to be updated to have the suffix of the
    # right type of literal that we're going t query.

    # NOTE: 'xsd:boolean' is excluded from range facets
    # print(f'attribute_item_obj {attribute_item_obj.slug} has data_type {attribute_item_obj.data_type}')
    if not attribute_item_obj.data_type in [
        'xsd:integer',
        'xsd:double',
        'xsd:date'
    ]:
        # Not an attribute that has value ranges to facet.
        return None
    field_fq = utilities.rename_solr_field_for_data_type(
        attribute_item_obj.data_type,
        field_fq
    )
    if attribute_group_obj_slug:
        # We're working in the context of an attribute group, so make sure the range
        # query is about that attribute group.
        field_fq = replace_slug_in_solr_field(
            solr_field=field_fq,
            old_slug=configs.ALL_ATTRIBUTE_GROUPS_SLUG,
            new_slug=attribute_group_obj_slug,
        )
    query_dict = {'prequery-stats': []}
    query_dict['prequery-stats'].append(
        field_fq
    )
    return query_dict


def compose_filter_query_on_literal(raw_literal, attribute_item_obj, field_fq):
    """Composes a solr filter query on literal values."""

    # The field_fq needs to be updated to have the suffix of the
    # right type of literal that we're going to query.
    field_fq = utilities.rename_solr_field_for_data_type(
        attribute_item_obj.data_type,
        field_fq
    )

    query_dict = {'fq': []}
    if attribute_item_obj.data_type == 'xsd:string':
        # Case for querying string literals. This is the most
        # complicated type of literal to query.
        query_dict['hl-queries'] = []
        string_terms = utilities.prep_string_search_term_list(
            raw_literal
        )
        for qterm in string_terms:
            query_dict['fq'].append('{field_fq}:{field_val}'.format(
                    field_fq=field_fq,
                    field_val=qterm
                )
            )
            query_dict['hl-queries'].append(
                '{field_label}: {field_val}'.format(
                    field_label=attribute_item_obj.label,
                    field_val=qterm,
                )
            )
    elif attribute_item_obj.data_type in ['xsd:integer', 'xsd:double', 'xsd:boolean']:
        # Case for querying numeric or boolean literals. This is a
        # simple type of literal to query. We pass the literal on without
        # modification as the filter field query value.
        query_dict['fq'].append('{field_fq}:{field_val}'.format(
                field_fq=field_fq,
                field_val=raw_literal
            )
        )
    elif attribute_item_obj.data_type == 'xsd:date':
        # Case for querying date literals. This is a simple
        # type of literal to query. We pass the literal on without
        # modification as the filter field query value.
        query_dict['fq'].append('{field_fq}:{field_val}'.format(
                field_fq=field_fq,
                field_val=raw_literal
            )
        )
    else:
        # we shouldn't be here. Return nothing.
        return None
    return query_dict


def add_rel_prefix_if_needed(str_value, prefix=""):
    """Adds a related prefix if not present"""
    if not isinstance(str_value, str) or not len(prefix):
        return str_value
    if str_value.startswith(prefix):
        return str_value
    return prefix + str_value


def get_general_hierarchic_path_query_dict(
    path_list,
    root_field,
    field_suffix,
    obj_all_slug='',
    fq_solr_field_suffix='',
    attribute_field_part='',
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

    query_dict = {'fq': [], 'facet.field': []}

    if obj_all_slug:
        # This makes a more specific "obj_all" field that we use to
        # query all levels of the hierarchy in solr.
        obj_all_slug = (
            obj_all_slug.replace('-', '_')
            + SolrDoc.SOLR_VALUE_DELIM
        )

    if field_suffix != 'pred_id':
        obj_all_field_fq = (
            'obj_all'
            + SolrDoc.SOLR_VALUE_DELIM
            + obj_all_slug
            + field_suffix
            + fq_solr_field_suffix
        )
    else:
        # Don't make an obj_all_field_fq for root predicates.
        obj_all_field_fq = None

    # Now start composing fq's for the parent item field with the
    # child as a value of the parent item field.
    facet_field = root_field

    # NOTE: The attribute_field_part is a part of a solr-field
    # for cases where the attribute is an entity in the database.
    # It starts with the default value of '' because we start
    # formulating solr queries on general/universal metadata
    # attributes, not the more specific, rarely used attributes that
    # are stored in the database.
    attribute_item_obj = None

    # NOTE: An attribute group acts as the root parent of all the
    # entities that maybe indexes within a given attribute group
    attribute_group_obj = None
    attribute_group_obj_slug = None

    # Default to no solr related prefix
    use_solr_rel_prefix = ''

    last_path_index = len(path_list) -1
    for path_index, item_id in enumerate(path_list):

        if (attribute_item_obj is not None
            and attribute_item_obj.data_type in configs.LITERAL_DATA_TYPES):
            # Process literals in requests, because some requests will filter according to
            # numeric, date, or string criteria.
            literal_query_dict = compose_filter_query_on_literal(
                raw_literal=item_id,
                attribute_item_obj=attribute_item_obj,
                field_fq=field_fq,
            )

            # Now combine the query dict for the literals with
            # the main query dict for this function
            query_dict = utilities.combine_query_dict_lists(
                part_query_dict=literal_query_dict,
                main_query_dict=query_dict,
            )
            # Skip out, because a literal query will never involve
            # children in a hierarchy path (because these are literals,
            # not entities in the database)
            return query_dict

        if not item_id:
            # It is empty or not a string, so skip out.
            return None

        use_solr_rel_prefix = ''
        if item_id.startswith(configs.RELATED_ENTITY_ID_PREFIX):
            # Strip off the prefix.
            item_id = item_id[len(configs.RELATED_ENTITY_ID_PREFIX):]
            use_solr_rel_prefix = SolrDoc.RELATED_SOLR_DOC_PREFIX

        # Add the solr-rel prefix if needed.
        obj_all_field_fq = add_rel_prefix_if_needed(
            obj_all_field_fq,
            prefix=use_solr_rel_prefix
        )

        item_obj = db_entities.get_cache_man_obj_by_any_id(item_id)
        if not item_obj:
            # We don't recognize the first item, and it is not
            # a literal of an attribute field. So return None.
            return None

        if not attribute_group_obj and item_obj.item_type == 'attribute-groups':
            attribute_group_obj = item_obj
            attribute_group_obj_slug = attribute_group_obj.slug

        # Default to prefer the facet_field information stored in meta_json
        pref_meta_json_facet_field = True
        item_parent_obj = db_entities.get_man_obj_parent(item_obj)
        if (
            item_parent_obj
            and field_suffix == configs.ROOT_OC_CATEGORY_SOLR
            and item_parent_obj.slug in configs.ITEM_TYPE_SLUGS
        ):
            # We don't want to use item_type item parents as parents
            # for category filters. This is redundant and makes search
            # filtering more complicated.
            pref_meta_json_facet_field = False
            item_parent_obj = None

        if False:
            if item_parent_obj is None:
                print(f'NO parent {item_obj.slug} pref_meta_json_facet_field: {pref_meta_json_facet_field}')
            else:
                print(f'{item_parent_obj.slug} parent of {item_obj.slug} pref_meta_json_facet_field: {pref_meta_json_facet_field}')
            print(f'NO parent {item_obj.slug} pref_meta_json_facet_field: {pref_meta_json_facet_field}')

        if item_parent_obj:
            # The item has a parent item, and that parent item will
            # make a solr_field for the current item.
            parent_slug_part = item_parent_obj.slug.replace('-', '_')
            if pref_meta_json_facet_field and item_parent_obj.meta_json.get('solr_field'):
                facet_field = item_parent_obj.meta_json.get('solr_field')
                print(f'Use parent {item_parent_obj.slug} meta_json facet_field {facet_field}')
            elif not attribute_field_part.startswith(parent_slug_part):
                facet_field = (
                    # Use the most immediate parent item of the item entity
                    # to identify the solr field we need to query. That
                    # most immediate item is index -1 (because the item
                    # item entity itself is not included in this list, as
                    # specified by the add_original=False arg).
                    parent_slug_part
                    + SolrDoc.SOLR_VALUE_DELIM
                    + attribute_field_part
                    + field_suffix
                )
                print(f'Facet field {facet_field}, from parent_slug_part {parent_slug_part}, and attribute_field_part {attribute_field_part}')

        # If the item is a linked data entity, and we have a
        # root field field defined for project specific predicates.
        # So, change the root solr field to be the linked data root.
        if (item_obj.item_type in URI_ITEM_TYPES
           and facet_field == SolrDoc.ROOT_PREDICATE_SOLR):
            facet_field = SolrDoc.ROOT_LINK_DATA_SOLR


        # Add the solr related prefix for related entity searches
        # and it not already used as a prefix.
        # Add the solr-rel prefix if needed.
        facet_field = add_rel_prefix_if_needed(
            facet_field,
            prefix=use_solr_rel_prefix
        )

        # Make the filter query field.
        if pref_meta_json_facet_field and item_obj.meta_json.get('obj_all_solr_field'):
            # Use the obj_all_solr_field associated with this item, because
            # it is more forgiving about where in a hierarchy we are.
            field_fq = add_rel_prefix_if_needed(
                item_obj.meta_json.get('obj_all_solr_field'),
                prefix=use_solr_rel_prefix
            )
            print(f'field_fq: {field_fq}, from {item_obj.slug} meta json obj_all_solr_field')
        else:
            # This is the default behavior without the DB specifying
            # an object all field.
            field_fq = facet_field
            print(f'field_fq: {field_fq}, from facet_field')

        # NOTE: If SolrDoc.DO_LEGACY_FQ, we're doing the older
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
        if not field_fq.endswith(fq_solr_field_suffix):
            field_fq += fq_solr_field_suffix

        if attribute_group_obj_slug:
            # Make sure we replace the general all-attribute slug
            # that make in the pref-meta-json facet field to use the
            # specific attribute group slug
            field_fq = replace_slug_in_solr_field(
                solr_field=field_fq,
                old_slug=configs.ALL_ATTRIBUTE_GROUPS_SLUG,
                new_slug=attribute_group_obj_slug,
            )

        # Make the query for the item and the solr field associated
        # with the item's immediate parent (or root, if it has no
        # parents).
        fq_item_slug = add_rel_prefix_if_needed(
            utilities.fq_slug_value_format(item_obj.slug),
            prefix=use_solr_rel_prefix
        )

        query_dict['fq'].append(f'{field_fq}:{fq_item_slug}')
        # Now make the query for the item and the solr field
        # associated with all items in the whole hierarchy for this
        # type of solr dynamic field.
        if obj_all_field_fq:
            if attribute_group_obj_slug:
                # Make sure we replace the general all-attribute slug
                # that make in the pref-meta-json facet field to use the
                # specific attribute group slug
                obj_all_field_fq = replace_slug_in_solr_field(
                    solr_field=obj_all_field_fq,
                    old_slug=configs.ALL_ATTRIBUTE_GROUPS_SLUG,
                    new_slug=attribute_group_obj_slug,
                )
            query_dict['fq'].append(f'{obj_all_field_fq}:{fq_item_slug}')

        if pref_meta_json_facet_field and item_obj.meta_json.get('solr_field'):
            # We're preferencing the solr_field_name stored in the meta_json.
            facet_field = item_obj.meta_json.get('solr_field')
            # print(f'Use preferred {item_obj.slug} facet_field {facet_field}')
        else:
            # Use the current item as the basis for the next solr_field
            # that will be used to query child items in the next iteration
            # of this loop.
            facet_field = (
                item_obj.slug.replace('-', '_')
                + SolrDoc.SOLR_VALUE_DELIM
                + attribute_field_part
                + field_suffix
            )

        facet_field = add_rel_prefix_if_needed(
            facet_field,
            prefix=use_solr_rel_prefix
        )

        # print(f'Now {item_obj.slug} facet_field {facet_field}')

        if attribute_group_obj_slug:
            # Make sure we replace the general all-attribute slug
            # that make in the pref-meta-json facet field to use the
            # specific attribute group slug
            facet_field = replace_slug_in_solr_field(
                solr_field=facet_field,
                old_slug=configs.ALL_ATTRIBUTE_GROUPS_SLUG,
                new_slug=attribute_group_obj_slug,
            )

        field_fq = facet_field
        if not field_fq.endswith(fq_solr_field_suffix):
            field_fq += fq_solr_field_suffix


        if (item_obj.item_type in ['predicates', 'property']
            or item_obj.data_type in configs.LITERAL_DATA_TYPES):
            # The current item entity is a "predicates" or a "property"
            # type of item. That means the item is a kind of attribute
            # or a "predicate" in linked-data speak, (NOT the value of
            # an attribute). The slugs for such attribute entities are
            # used in solr fields. These will be used in all of the
            # queries of child items as we iterate through this
            # path_list.

            # The current item is an attribute item, so copy it for
            # use as we continue to iterate through this path_list.
            attribute_item_obj = item_obj
            if False:
                # Keep for debugging but turn it off
                print('attribute item {} is a {}, {}'.format(
                        attribute_item_obj.label,
                        attribute_item_obj.item_type,
                        attribute_item_obj.data_type
                    )
                )

            if attribute_item_obj.data_type in configs.LITERAL_DATA_TYPES:
                # This attribute_item_obj has a data type for literal
                # values.

                children = db_entities.get_man_obj_children_list(attribute_item_obj)
                if len(children):
                    # The (supposedly) literal attribute item
                    # has children so force it to have a data_type of
                    # 'id'.
                    attribute_item_obj.data_type = 'id'

                # NOTE: Generally, we don't make facets on literal
                # attributes. However, some literal attributes are
                # actually parents of other literal atttributes, so
                # we should make facets for them.
                if path_index != last_path_index:
                    # The current item_id is not the last item in the
                    # in the path_list, so we do not need to check
                    # for child items.
                    facet_field = None
                elif attribute_item_obj.data_type == 'xsd:boolean':
                    # Make sure we get the facet field, identified
                    # with the correct data type, for boolean values.
                    facet_field = utilities.rename_solr_field_for_data_type(
                        attribute_item_obj.data_type,
                        (
                            use_solr_rel_prefix
                            + attribute_item_obj.slug.replace('-', '_')
                            + SolrDoc.SOLR_VALUE_DELIM
                            + field_suffix
                        )
                    )
                elif attribute_item_obj.data_type != 'id':
                    # The attribute item data type has not been reset
                    # to be 'id', b/c there are no children items to
                    # this literal attribute item. Thus, there is no
                    # need to make a facet field for it.
                    facet_field = None

                if pref_meta_json_facet_field and item_obj.meta_json.get('solr_field'):
                    facet_field = item_obj.meta_json.get('solr_field')
                    if attribute_group_obj_slug:
                        # Make sure we replace the general all-attribute slug
                        # that make in the pref-meta-json facet field to use the
                        # specific attribute group slug
                        facet_field = replace_slug_in_solr_field(
                            solr_field=facet_field,
                            old_slug=configs.ALL_ATTRIBUTE_GROUPS_SLUG,
                            new_slug=attribute_group_obj_slug,
                        )
                    field_fq = item_obj.meta_json.get('solr_field')
                else:
                    # Format the field_fq appropriately for this specific
                    # data type.
                    field_fq = utilities.rename_solr_field_for_data_type(
                        attribute_item_obj.data_type,
                        (
                            use_solr_rel_prefix
                            + item_obj.slug.replace('-', '_')
                            + SolrDoc.SOLR_VALUE_DELIM
                            + field_suffix
                        )
                    )
                    facet_field = field_fq

                # The attribute item is for a literal type field.
                # Gather numeric and date fields that need a
                range_query_dict = get_range_stats_fields(
                    attribute_item_obj,
                    field_fq,
                    attribute_group_obj_slug=attribute_group_obj_slug,
                )
                # Now combine the query dict for the range fields with
                # the main query dict for this function
                query_dict = utilities.combine_query_dict_lists(
                    part_query_dict=range_query_dict,
                    main_query_dict=query_dict,
                )
            elif (
                    not attribute_field_part
                    or attribute_item_obj.item_type in ['predicates', 'property']
                ):
                # This attribute is for making descriptions with
                # non-literal values (meaning entities in the DB).
                if False:
                    # Keep for debugging, but turn it off.
                    print(
                        f'Pred attribute: {attribute_item_obj.item_type}'
                    )
                if not attribute_item_obj.meta_json.get('solr_field'):
                    attribute_field_part = (
                        attribute_item_obj.slug.replace('-', '_')
                        + SolrDoc.SOLR_VALUE_DELIM
                    )
                else:
                    # the attribute item has a preferred solr_field configured, so use that as a basis
                    # for the attribute field part. This is all kinda insane, but it seems to work
                    # for now until we can figure out a simplified approach that is less insane, maybe by
                    # doing a better job of storing solr fields that we want to query in the database.
                    solr_parts = attribute_item_obj.meta_json.get('solr_field').split(SolrDoc.SOLR_VALUE_DELIM)
                    use_parts = SolrDoc.SOLR_VALUE_DELIM.join(solr_parts[:-1])
                    attribute_field_part = (
                        use_parts
                        + SolrDoc.SOLR_VALUE_DELIM
                    )

                attribute_field_part = add_rel_prefix_if_needed(
                    attribute_field_part,
                    prefix=use_solr_rel_prefix
                )

                if pref_meta_json_facet_field and item_obj.meta_json.get('solr_field'):
                    # This is the preferred way to get the obj_all field fq, because
                    # the solr_field_name is explicitly in the DB for us to use.
                    obj_all_field_fq = (
                        'obj_all'
                        + SolrDoc.SOLR_VALUE_DELIM
                        + item_obj.meta_json.get('solr_field')
                    )
                    print(f'{item_obj.slug} meta_json solr_field is source of obj_all_field_fq {obj_all_field_fq}')
                else:
                    # Fall back to complex logic to guess the obj_all_field_fq
                    obj_all_field_fq = (
                        'obj_all'
                        + SolrDoc.SOLR_VALUE_DELIM
                        + attribute_field_part
                        + field_suffix
                        + fq_solr_field_suffix
                    )
                    print(f'{obj_all_field_fq} derived from {attribute_field_part}')
                if attribute_group_obj_slug:
                    # Make sure we replace the general all-attribute slug
                    # that make in the pref-meta-json facet field to use the
                    # specific attribute group slug
                    obj_all_field_fq = replace_slug_in_solr_field(
                        solr_field=obj_all_field_fq,
                        old_slug=configs.ALL_ATTRIBUTE_GROUPS_SLUG,
                        new_slug=attribute_group_obj_slug,
                    )
                obj_all_field_fq = add_rel_prefix_if_needed(
                    obj_all_field_fq,
                    prefix=use_solr_rel_prefix
                )



    # Make the facet field so solr will return any possible
    # facet values for children of the LAST item in this path_list.
    if facet_field:
        query_dict['facet.field'].append(facet_field)
    return query_dict


def get_general_hierarchic_paths_query_dict(
    raw_path,
    root_field,
    field_suffix,
    hierarchy_delim=configs.REQUEST_PROP_HIERARCHY_DELIM,
    or_delim=configs.REQUEST_OR_OPERATOR,
    obj_all_slug='',
    attribute_field_part='',
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
            attribute_field_part=attribute_field_part,
        )
        if not path_query_dict:
            # This path had no entities that could not be found in the
            # database. For now, just skip.
            continue
        # All the solr_query terms for a given hiearchic path need to
        # be satisfied to in a query. So join all the terms created from
        # a given hierarchic path with the "AND" operator into a single
        # string.
        path_term = utilities.join_solr_query_terms(
            path_query_dict['fq'], operator='AND'
        )
        # Add this path term to all the path terms.
        path_terms.append(path_term)
        # Add all of the path_query_dict keys, values to the main
        # query dict, except for values from the fq key, which we
        # further processed into a path_term.
        query_dict = utilities.combine_query_dict_lists(
            part_query_dict=path_query_dict,
            main_query_dict=query_dict,
            skip_keys=['fq'],
        )

    if not path_terms:
        return None
    # The different paths iterated above are all "OR" options (union)
    # for the different paths. Join those together using the OR
    # operator.
    all_paths_term = utilities.join_solr_query_terms(
        path_terms, operator='OR'
    )
    query_dict['fq'] = [all_paths_term]
    # print(f'query_dict: {query_dict}')
    return query_dict


# ---------------------------------------------------------------------
# SPECIALIZED DINAA FUNCTIONS
# ---------------------------------------------------------------------

def get_linked_dinaa_query_dict():
    """Get a query dict for records that in some way cross reference with DINAA records"""
    query_dict = {'fq': [], 'facet.field': []}
    # Find all reference to tDAR related resources
    dc_terms = [f'({pred}:tdar*)' for pred in configs.PROJECT_FACET_FIELDS]
    # Find all records that have an isreferencedby predicate
    dc_terms.append('(ld___pred_id:dc_terms_is_referenced_by___*)')
    or_dc_terms = ' OR '.join(dc_terms)
    query_dict['fq'].append(f'({or_dc_terms})')
    query_dict['fq'].append(f'{SolrDoc.ROOT_PROJECT_SOLR}:52_digital_index_of_north_american_archaeology_dinaa___*')
    query_dict['fq'].append('item_type:subjects')
    # Now add a field to the facet.field list so solr calculates
    # facets for class_uris for the current item type.
    query_dict['facet.field'].append(configs.ROOT_OC_CATEGORY_SOLR)
    query_dict['facet.field'].append('dc_terms_is_referenced_by___pred_id')
    return query_dict


def get_trinomial_query_dict(raw_trinomial):
    """Make a query dict for trinomial identifiers"""
    if not raw_trinomial:
        return None
    query_dict = {'fq': []}
    values_list = utilities.infer_multiple_or_hierarchy_paths(
        raw_trinomial,
        or_delim=configs.REQUEST_OR_OPERATOR,
        hierarchy_delim=None
    )
    tri_list = []
    for value in values_list:
        if not value:
            continue
        tri_list += utilities.make_uri_equivalence_list(value)

    act_terms = []
    tri_pred_solr_slugs = [
        '52_smithsonian_trinomial_identifier',
        '52_sortable_trinomial',
        '52_variant_trinomial_expressions',
        '145_smithsonian_trinomial_identifier',
        '145_sortable_trinomial',
        '145_variant_trinomial_expressions',
    ]
    for act_tri in tri_list:
        # The act_id maybe a persistent URI, escape it and
        # query the persistent_uri string.
        escape_tri = utilities.escape_solr_arg(act_tri)
        for tri_pred_solr_slug in tri_pred_solr_slugs:
            act_terms.append(
                f'({tri_pred_solr_slug}___pred_string:{escape_tri})'
            )
        act_terms.append(
            f'(slug_type_uri_label:*{escape_tri})'
        )
        query_dict['fq'].append(
            utilities.join_solr_query_terms(
                act_terms, operator='OR'
            )
        )
    return query_dict