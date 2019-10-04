
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
    
    val = request_dict.get(param, default)
    if not as_list:
        if isinstance(val, list):
            
        
    if as_list and not isinstance(val, list):
        if solr_escape:
            val = '"{}"'.format(val)
        output = [val]
    elif as_list and isinstance(val, list):
        output = val
    elif not as_list and isinstance(val, list):
        output = val[0]

    if as_list:
        if param in request_dict:
            param_obj = request_dict[param]
            if isinstance(param_obj, list):
                output = param_obj
            else:
                if solr_escape:
                    param_obj = '"' + param_obj + '"'
                output = [param_obj]
        else:
            output = default
    else:
        if param in request_dict:
            output = request_dict[param]
            if isinstance(output, list):
                output = output[0]
            if solr_escape:
                qm = QueryMaker()
                if output[0] == '"' and output[-1] == '"':
                    output = qm.escape_solr_arg(output[1:-1])
                    output = '"' + output + '"'
                else:
                    output = qm.escape_solr_arg(output)
        else:
            output = default

    return output