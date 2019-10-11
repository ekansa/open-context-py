import copy
import itertools
import re

from opencontext_py.libs.general import LastUpdatedOrderedDict

from opencontext_py.apps.indexer.solrdocumentnew import (
    get_solr_predicate_type_string
)

# ---------------------------------------------------------------------
# This module contains general utility functions for the solr search
# and query features.
#
# NOTE: The functions here must not access the database or solr. These
# functions will be independent of all DB interactions, so they can be
# tested with unit testing.
# ---------------------------------------------------------------------


def infer_multiple_or_hierarchy_paths(raw_path, hierarchy_delim='/', or_delim='||'):
    '''Takes a raw path and returns a list of all combinations of paths
    infered from an OR operator.

    For example:

    >>> infer_multiple_or_hierarchy_paths('Turkey/Domuztepe/I||II||Stray')

    ['Turkey/Domuztepe/I', 'Turkey/Domuztepe/II', 'Turkey/Domuztepe/Stray']


    :param str raw_path: The raw path string as requested by the client
    :param str hierarchy_delim: The hierarchy delimiter.
    :param str or_delim: The OR operator / delimiter.
    '''
    # Split the raw_path by hiearchy delim (default to '/') and then by
    # the or_delim (default to '||').
    path_lists = [
        path_parts.split(or_delim)
        for path_parts in raw_path.split(hierarchy_delim)
    ]
    # Create a list of the various permutations
    path_tuple_list = list(itertools.product(*path_lists))
    # Turn the paths a list of unique strings
    paths = []
    for path_parts in path_tuple_list:
        new_path = hierarchy_delim.join(path_parts)
        if new_path in paths:
            continue
        paths.append(new_path)
    return paths


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


def join_solr_query_terms(terms_list, operator='AND'):
    """Joins together a list of query terms into a string."""
    if not isinstance(terms_list, list):
        terms_list = [terms_list]
    terms = ['({})'.format(term) for term in terms_list]
    terms_str = (' {} '.format(operator)).join(terms)
    return '({})'.format(terms_str)


def get_solr_field_type(predicate_type, prefix=''):
    '''Gets dynamic solr fields names for predicates of different
    datatypes, ending with ___pred_id, ___pred_numeric, etc.
    '''
    # Currently, this is just a wrapper for a function from
    # the solr document indexer.
    return get_solr_predicate_type_string(
        predicate_type=data_type,
        prefix=prefix,
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
    new_request = LastUpdatedOrderedDict()
    new_request['path'] = spatial_context
    if request:
        # "for key in request.GET" works too.
        for key, key_val in request.GET.items():
            new_request[key] = request.GET.getlist(key)
    return new_request