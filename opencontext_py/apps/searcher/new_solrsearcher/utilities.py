import copy

from opencontext_py.libs.general import LastUpdatedOrderedDict


# This module contains general utility functions for the solr search and query
# features.


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


def get_request_param_value(
    request_dict,
    param,
    default,
    as_list=False,
    solr_escape=False
):
    """ get a string or list to use in queries from either
        the request object or the internal_request object
        so we have flexibility in doing searches without
        having to go through HTTP
    """
    if not isinstance(request_dict, dict):
        return None
    
    raw_val = request_dict.get(param, default)
    if not as_list:
        if isinstance(raw_val, list):
            output = raw_val[0]
        else:
            output = raw_val
        if solr_escape:
            if output[0] == '"' and output[-1] == '"':
                output = '"{}"'.format(escape_solr_arg(output[1:-1]))
            else:
                output = escape_solr_arg(output)
        # Return the non-list output and skip the rest of the
        # function.
        return output
    # The rest is for outputs requested as a list.
    if not isinstance(raw_val, list):
        if solr_escape:
            raw_val = '"{}"'.format(escape_solr_arg(raw_val))
        # 
        return [raw_val]
    else:
        return raw_val


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