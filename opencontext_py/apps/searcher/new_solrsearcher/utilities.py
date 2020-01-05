import copy
import datetime
import itertools
import re

from opencontext_py.libs.general import LastUpdatedOrderedDict
from opencontext_py.apps.entities.uri.models import URImanagement

from opencontext_py.apps.indexer.solrdocumentnew import (
    get_solr_predicate_type_string,
    SolrDocumentNew as SolrDocument,
)

# ---------------------------------------------------------------------
# This module contains general utility functions for the solr search
# and query features.
#
# NOTE: The functions here must not access the database or solr. These
# functions will be independent of all DB interactions, so they can be
# tested with unit testing.
# ---------------------------------------------------------------------
def make_suffix_no_suffix_list(raw_term, suffix="/"):
    """Makes list where a string does and does not end with a suffix"""
    if not isinstance(raw_term, str):
        return None
    terms = [raw_term]
    if not suffix:
        return terms
    if raw_term.endswith(suffix):
        terms.append(raw_term[:-len(suffix)])
    else:
        terms.append((raw_term + suffix))
    return terms

def make_alternative_prefix_list(raw_term, alt_prefixes=('http://', 'https://',)):
    """Makes list where a string does and does not end with a suffix"""
    if not isinstance(raw_term, str):
        return None
    alt_term = None
    if raw_term.startswith(alt_prefixes[0]):
        alt_term = alt_prefixes[1] + raw_term[len(alt_prefixes[0]):]
    elif raw_term.startswith(alt_prefixes[1]):
        alt_term = alt_prefixes[0] + raw_term[len(alt_prefixes[1]):]
    if not alt_term:
        return None
    return [raw_term, alt_term]

def make_uri_equivalence_list(raw_term, alt_suffix="/"):
    """ Makes Prefixed, HTTP, HTTPS and '/' ending options list for URLs
    """
    # NOTE: Open Context often references Web URL/URIs to "linked data"
    # entities. Open Context considers http:// and https:// URLs to be
    # equivalent. This function takes a raw term and makes http://
    # https:// variants. It also makes a prefixed URL if a namespace
    # is recognized in URImanagement. Finally, it will by default, 
    # make variants that have and do not have a trailing "/".

    output_list = []
    if not isinstance(raw_term, str):
        return None
    output_list.append(raw_term)
    url_terms = []
    if raw_term.startswith('http://') or raw_term.startswith('https://'):
        # NOTE: The raw_term looks like a Web URL. We need to make
        # variants that start with http, https, and end in a slash, and
        # do not end in a slash.
        url_terms = make_suffix_no_suffix_list(raw_term, suffix=alt_suffix)
    elif raw_term.count(':') == 1:
        full_uri = URImanagement.convert_prefix_to_full_uri(raw_term)
        if full_uri:
            url_terms = make_suffix_no_suffix_list(full_uri, suffix=alt_suffix)
        url_terms.append(raw_term)

    for term in url_terms:
        http_alts = make_alternative_prefix_list(
            term, 
            alt_prefixes=('http://', 'https://',)
        )
        if not http_alts:
            continue
        for http_alt in http_alts:
            if http_alt not in output_list:
                output_list.append(http_alt)
            prefix_id = URImanagement.prefix_common_uri(http_alt)
            if alt_suffix and prefix_id.endswith(alt_suffix):
                # Remove any trailing slash with prefixed IDs.
                prefix_id = prefix_id[:-len(alt_suffix)]
            if prefix_id and prefix_id not in output_list:
                output_list.append(prefix_id)
    return output_list


def infer_multiple_or_hierarchy_paths(
    raw_path,
    hierarchy_delim='/',
    or_delim='||',
    get_paths_as_lists=False,
):
    '''Takes a raw path and returns a list of all combinations of paths
    infered from an OR operator.

    For example:

    >>> infer_multiple_or_hierarchy_paths('Turkey/Domuztepe/I||II||Stray')

    ['Turkey/Domuztepe/I', 'Turkey/Domuztepe/II', 'Turkey/Domuztepe/Stray']


    :param str raw_path: The raw path string as requested by the client
    :param str hierarchy_delim: The hierarchy delimiter.
    :param str or_delim: The OR operator / delimiter.
    '''
    # First, cleanup dangling delimeters at the start or end.
    for delim in [hierarchy_delim, or_delim]:
        raw_path = raw_path.lstrip(delim)
        raw_path = raw_path.rstrip(delim)
    # Split the raw_path by hiearchy delim (default to '/') and then by
    # the or_delim (default to '||').
    path_lists = [
        path_parts.split(or_delim)
        for path_parts in raw_path.split(hierarchy_delim)
    ]
    # Create a list of the various permutations
    path_tuple_list = list(itertools.product(*path_lists))
    
    # Make sure that we return unique paths. Make string
    # paths and paths-as-lists.
    paths_as_strs = []
    paths_as_lists = []
    for path_parts in path_tuple_list:
        if not len(path_parts):
            continue
        new_path = hierarchy_delim.join(path_parts)
        if not new_path or new_path in paths_as_strs:
            continue
        paths_as_strs.append(new_path)
        paths_as_lists.append(path_parts)
    
    # Return paths as either strings or as lists
    if get_paths_as_lists:
        return paths_as_lists
    # Default to returning the paths as strings.
    return paths_as_strs



def get_path_depth(self, path, delimiter='/'):
    """Gets the depth of a (number of items) if split by a delimiter
    
    :param str path: A hierachic path, with levels separated by a
        delimiter
    :param str delimiter: A string delimiter between different levels
        of a hiearchic path
    """
    # Remove a possible trailing delimiter before calculating
    # the depth
    return len(path.rstrip(delimiter).split(delimiter))


def rename_solr_field_for_data_type(data_type, solr_field):
    """Renames a solr field to match its data type.

    :param str data_type: The JSON-LD document data type
        for the solr field.
    :param str solr_field: The solr field that will changed
        appropriate to its datatype.
    """
    if not SolrDocument.SOLR_VALUE_DELIM in solr_field:
        # No change, this is not solr field formatted in a
        # way we'd expect data_type specific variants. 
        return solr_field
    parts = solr_field.split(SolrDocument.SOLR_VALUE_DELIM)
    general_part = parts[-1]
    first_part = SolrDocument.SOLR_VALUE_DELIM.join(parts[0:-1])
    if '_' in general_part:
        general_part = general_part.split('_')[0]
    new_ending = get_solr_predicate_type_string(
        data_type, 
        prefix=(general_part + '_')
    )
    return first_part + SolrDocument.SOLR_VALUE_DELIM + new_ending


def join_solr_query_terms(terms_list, operator='AND'):
    """Joins together a list of query terms into a string."""
    if not terms_list:
        return ''
    if not isinstance(terms_list, list):
        terms_list = [terms_list]
    if len(terms_list) == 1:
        # Nothing to process or wrap in parantheses.
        return terms_list[0]
    terms = ['({})'.format(term) for term in terms_list]
    terms_str = (' {} '.format(operator)).join(terms)
    if len(terms) > 1:
        # Multiple terms, so add
        return '({})'.format(terms_str)
    return terms_str


def fq_slug_value_format(slug, value_slug_length_limit=120):
    """Formats a slug for a Solr query value"""
    if SolrDocument.DO_LEGACY_FQ:
        return slug
    # NOTE: The '-' character is reserved in Solr, so we need to replace
    # it with a '_' character in order to do prefix queries on the slugs.
    slug = slug.replace('-', '_')
    slug += SolrDocument.SOLR_VALUE_DELIM
    slug = (
        slug[:value_slug_length_limit] + '*'
    )
    return slug


def make_solr_term_via_slugs(
    field_slug,
    solr_dyn_field,
    value_slug,
    field_parent_slug=None,
    solr_field_suffix='',
):
    """Makes a solr query term from slugs
    
    :param str field_slug: Slug for the field name, which is sometimes
        the slug for the value_slug parent.
    :param str field_parent_slug: Slug for a parent entity that is the
        parent of the value_slug. This is used for hierarchic
        properties where the field_slug could be a slug for a predicate
        getting queried, while field_parent_slug could be a slug for a
        more general type that is a parent of the value_slug.
    :param str solr_dyn_field: A string for the kind of solr dymanic
        field that we want to query. 'project_id' is for projects,
        'pred_id' is for predicates.
    :param str solr_field_suffix: A string for the the sub-type of solr
        field that we want to query. "_fq" is for facet-query.
    :param str value_slug: A string for the slug value that we want
        to query.
    """
    if SolrDocument.DO_LEGACY_FQ:
        # Doing the legacy filter query method, so add a
        # suffix of _fq to the solr field.
        solr_field_suffix = '_fq'
    
    # Format the value slug for the filter query.
    value_slug = fq_slug_value_format(value_slug)

    solr_parent_prefix = field_slug.replace('-', '_')
    if field_parent_slug:
        # Add the immediate parent part of the solr
        # field, since it is set.
        solr_parent_prefix += (
            SolrDocument.SOLR_VALUE_DELIM
            + field_parent_slug.replace('-', '_')
        )
    
    return (
        solr_parent_prefix
        + SolrDocument.SOLR_VALUE_DELIM
        + solr_dyn_field
        + solr_field_suffix + ':'
        + value_slug
    )


def escaped_seq(term):
    """ Yield the next string based on the next character (either this char or escaped version)"""
    escaperules = {
        '+': r'\+',
        '-': r'\-',
        '&': r'\&',
        '|': r'\|',
        '!': r'\!',
        '(': r'\(',
        ')': r'\)',
        '{': r'\{',
        '}': r'\}',
        '[': r'\[',
        ']': r'\]',
        '^': r'\^',
        '~': r'\~',
        '*': r'\*',
        '?': r'\?',
        ':': r'\:',
        '"': r'\"',
        ';': r'\;',
        ' ': r'\ '
    }
    for char in term:
        if char in escaperules.keys():
            yield escaperules[char]
        else:
            yield char


def escape_solr_arg(arg):
    """ Apply escaping to the passed in query terms
        escaping special characters like : , etc"""
    arg = arg.replace('\\', r'\\')   # escape \ first
    return "".join([next_str for next_str in escaped_seq(arg)])


def string_to_float(str_val, invalid_output=None):
    """Convert a string value to a float, if valid
    
    :param str str_val: String value we want to convert to float
    """
    try:
        output = float(str_val)
    except:
        return invalid_output
    return output


def string_to_int(str_val, invalid_output=None):
    """Convert a string value to a integer, if valid
    
    :param str str_val: String value we want to convert to int
    """
    float_val = string_to_float(str_val, invalid_output)
    if float_val == invalid_output:
        return invalid_output
    try:
        output = int(float_val)
    except:
        return invalid_output
    return output
    

def get_request_param_value(
    request_dict,
    param,
    default,
    as_list=False,
    solr_escape=False,
    require_float=False,
    require_int=False,
):
    """ Return a list, str, float, or int (dependig on args) from a
        request dict:
    
    :param dict request_dict: The dictionary of keyed by client
        request parameters and their request parameter values.
    :param str param: The URL query parameter used as a key for to
        find client requested values in the request_dict
    :param * default: The default value to be returned if the param
        key does not exist in the request_dict
    :param bool as_list: Boolean to return a list or single value.
    :param solr_escape: Boolean for solr-escaping input values
    :param require_float: Boolean to require returned values to be
        of type float.
    :param require_int: Boolean to require returned values to be of
        type int.
    """
    if not isinstance(request_dict, dict):
        return None
    
    raw_vals = request_dict.get(param, default)
    if not isinstance(raw_vals, list):
        raw_vals = [raw_vals]
    outputs = []
    for raw_val in raw_vals:
        if solr_escape:
            if raw_val[0] == '"' and raw_val[-1] == '"':
                raw_val = '"{}"'.format(escape_solr_arg(raw_val[1:-1]))
            else:
                raw_val = escape_solr_arg(raw_val)
        elif require_float:
            raw_val = string_to_float(raw_val, invalid_output=default)
        elif require_int:
            raw_val = string_to_int(raw_val, invalid_output=default)
        outputs.append(raw_val)
    
    if not as_list:
        # We don't want the output returned as a list, so just return
        # the first element of the list as the output 
        return outputs[0]
    return outputs


def prep_string_search_term_list(raw_fulltext_search):
    """ Prepares a list of quoted, solr escaped search terms.
    
    :param str raw_term: The raw search term requested by the client.
    """
    # Make a temporary list of search terms.
    act_terms = []
    # Extract quoted parts of the raw search term
    act_terms += re.findall(r'"([^"]*)"', raw_fulltext_search)
    
    # Remove the quoted parts to get unquoted parts.
    not_quoted_part = raw_fulltext_search
    for quoted_part in act_terms:
        not_quoted_part = not_quoted_part.replace(
            '"{}"'.format(quoted_part), ''
        ).strip()
    
    # Use the space character to split the non-quoted parts into
    # different token/works
    act_terms += not_quoted_part.split(' ')
    
    # Now we can make the final list of quoted, escaped search
    # terms.
    terms = []
    for act_term in act_terms:
        act_term = act_term.strip()
        if not act_term:
            continue
        term = '"{}"'.format(escape_solr_arg(act_term))
        terms.append(term)
    return terms


def make_request_obj_dict(request, spatial_context=None):
    """Extracts GET parameters and values from a Django
    request object into a dictionary obj
    """
    request_dict = LastUpdatedOrderedDict()
    request_dict['path'] = spatial_context
    if request:
        # "for key in request.GET" works too.
        for key, key_val in request.GET.items():
            request_dict[key] = request.GET.getlist(key).copy()
    return request_dict


def safe_remove_item_from_list(item, item_list):
    """ Safely removes an item from a list, if it is actuall a list """
    if isinstance(item_list, list) and item in item_list:
        item_list.remove(item)
    return item_list


def combine_query_dict_lists(part_query_dict, main_query_dict, skip_keys=[]):
    """Combines lists from the part_query_dict into the 
    
    :param dict part_query_dict: The smaller query dict that will get
        merged into the main_query_dict.
    :param dict main_query_dict: The main query dict that we're adding
        to.
    :param list skip_keys: List of keys to skip and not include in
        adding to the main_query_dict.
    """
    if not part_query_dict:
        return main_query_dict
    for key, values in part_query_dict.items():
        if key in skip_keys or not values:
            continue
        if key not in main_query_dict:
            main_query_dict[key] = values
        elif (isinstance(main_query_dict[key], list)
            and isinstance(values, list)):
            main_query_dict[key] += values
    return main_query_dict

# ---------------------------------------------------------------------
# Date-Time Related Functions
# ---------------------------------------------------------------------
def date_convert(date_str):
    """Converts to a python datetime if not already so """
    if isinstance(date_str, str):
        date_str = date_str.replace('Z', '')
        if not 'T' in date_str:
            date_str += 'T00:00:00'
        dt = datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
        return dt
    return date_str


def convert_date_to_solr_date(date_str):
    """Converts a string for a date into a Solr formated datetime string """
    dt = date_convert(date_str)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def make_human_readable_date(date_str):
    """Converts a date value into something easier to read """
    dt = date_convert(date_str)
    check_date = dt.strftime('%Y-%m-%d')
    check_dt = date_convert(date_val)
    if check_dt == dt:
        return check_date
    return dt.strftime('%Y-%m-%d:%H:%M:%S')


def get_date_difference_for_solr(min_date, max_date, groups):
    """ Gets a solr date difference from two values """
    min_dt = date_convert(min_date)
    max_dt = date_convert(max_date)
    dif_dt = (max_dt - min_dt) / groups
    if dif_dt.days >= 366:
        solr_val = int(round((dif_dt.days / 365.25), 0))
        solr_dif = '+' + str(solr_val) + 'YEAR'
    elif dif_dt.days >= 31:
        solr_val = int(round((dif_dt.days / 30), 0))
        solr_dif = '+' + str(solr_val) + 'MONTH'
    elif dif_dt.days >= 1:
        solr_val = int(round(dif_dt.days, 0))
        solr_dif = '+' + str(solr_val) + 'DAY'
    elif (dif_dt.seconds // 3600) >= 1:
        solr_val = int(round((dif_dt.seconds // 3600), 0))
        solr_dif = '+' + str(solr_val) + 'HOUR'
    elif ((dif_dt.seconds % 3600) // 60) >= 1:
        solr_val = int(round(((dif_dt.seconds % 3600) // 60), 0))
        solr_dif = '+' + str(solr_val) + 'MINUTE'
    elif dif_dt.seconds >= 1:
        solr_val = int(round(dif_dt.seconds, 0))
        solr_dif = '+' + str(solr_val) + 'SECOND'
    else:
        solr_dif = '+1YEAR'
    return solr_dif


def add_solr_gap_to_date(date_val, solr_gap):
    """ Adds a solr gap to a date_val """
    solr_val = re.sub(r'[^\d.]', r'', solr_gap)
    solr_val = int(float(solr_val))
    dt = date_convert(date_val)
    if 'YEAR' in solr_gap:
        dt = dt + datetime.timedelta(days=int(round((solr_val * 365.25), 0)))
    elif 'MONTH' in solr_gap:
        dt = dt + datetime.timedelta(days=(solr_val * 30))
    elif 'DAY' in solr_gap:
        dt = dt + datetime.timedelta(days=solr_val)
    elif 'HOUR' in solr_gap:
        dt = dt + datetime.timedelta(hours=solr_val)
    elif 'MINUTE' in solr_gap:
        dt = dt + datetime.timedelta(minutes=solr_val)
    elif 'SECOND' in solr_gap:
        dt = dt + datetime.timedelta(seconds=solr_val)
    else:
        dt = dt
    return dt


# ---------------------------------------------------------------------
# GEOSPATIAL AND TIME FUNCTIONS
# ---------------------------------------------------------------------
def validate_geo_coordinate(coordinate, coord_type):
    """Validates a geo-spatial coordinate """
    try:
        fl_coord = float(coordinate)
    except ValueError:
        return False
    if 'lat' in coord_type:
        if (fl_coord <= 90 
            and fl_coord >= -90):
            return True
    elif 'lon' in coord_type:
        if (fl_coord <= 180 
            and fl_coord >= -180):
            return True
    return False

def validate_geo_lon_lat(lon, lat):
    """ checks to see if a lon, lat pair
        are valid. Note the GeoJSON ordering
        of the coordinates
    """
    lon_valid = validate_geo_coordinate(lon, 'lon')
    lat_valid = validate_geo_coordinate(lat, 'lat')
    if lon_valid and lat_valid:
        return True
    return False

def validate_bbox_coordinates(bbox_coors):
    """Validates a set of bounding box coordinates """
    if len(bbox_coors) != 4:
        # Need four coordinates (2 points) for a box
        return False

    lower_left_valid = validate_geo_lon_lat(
        bbox_coors[0], bbox_coors[1]
    )
    top_right_valid = validate_geo_lon_lat(
        bbox_coors[2], bbox_coors[3])
    if not lower_left_valid or not top_right_valid:
        return False

    if (float(bbox_coors[0]) < float(bbox_coors[2]) 
        and float(bbox_coors[1]) < float(bbox_coors[3])):
        return True
    else:
        return False

def return_validated_bbox_coords(bbox_str):
    """Returns a valid bounding box coordinate list of floats"""
    if not isinstance(bbox_str, str):
        return False
    if not ',' in bbox_str:
        return False
    bbox_coors = [c.strip() for c in bbox_str.split(',')]
    valid = validate_bbox_coordinates(bbox_coors)
    if not valid:
        return False
    valid_bbox_coors = [float(c) for c in bbox_coors]
    return valid_bbox_coors