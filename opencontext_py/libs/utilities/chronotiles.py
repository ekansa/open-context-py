import re
import numbers



"""
Time ranges can be hard to present in hierarchic faceted search
since ranges do not usually fit into standard buckets.

To solve this problem, Open Context will start to organize time-spans using a hierarchy of 'tiles,'
similar to the map tiles in the globalmaptiles.py class

See unit tests that demonstrate round-trips of dates decoded from encoded
chronological tile path strings.

pytest opencontext_py/tests/unit/libs/utilities/test_chronotiles.py -v --log-cli-level info
"""

PREFIX_DELIM = '-'
DEFAULT_PATH_PREFIX = f'10M{PREFIX_DELIM}'
DEFAULT_MAXIMUM_BP = 10000000  # 10 million years ago
PRESENT = 2000 # Year 0 BP expressed in BCE/CE.
MAX_TILE_DEPTH = 38
MIN_INTERVAL_SPAN = .25


YEAR_POWER_DICT= {
    'k': 3,
    'm': 6,
    'g': 9
}


def raw_path_depth(raw_path):
    """
    gets the depth of a raw_path string
    """
    if PREFIX_DELIM in raw_path:
        path_ex = raw_path.split(PREFIX_DELIM)
        path = path_ex[1]
    else:
        path = raw_path
    
    return len(path)


def number_cast(test_string):
    """Cast a string as an integer or float number
    
    :param str test_string: An a string to be converted into an integer
        or float if valid.
    
    return integer, float or None (if string is non-numeric)
    """
    t_number = re.sub('[^0-9.]', '', test_string)
    if t_number is not None:
        try:
            return int(t_number)
        except ValueError:
            return float(t_number)
    else:
        return None


def get_maximum_bp_from_prefix(prefix):
    """Gets themaximum year BP from the path prefix.
   
    :param str prefix: A chrono-tile path prefix.
    :param dict year_power_dict: A mapping between characters and
       powers of ten (K for kilo, M for mega, etc.)
    """
    exp_char = prefix[-1].lower()
    if not YEAR_POWER_DICT.get(exp_char):
        raise ValueError(f'Unrecognized "year-power" character "{exp_char}"')
    
    # Extract the numeric part of the prefix
    numeric_prefix_part = number_cast(prefix)
    
    if not isinstance(numeric_prefix_part, (int, float, numbers.Number)):
        raise ValueError('Chrono-tile prefix invalid')
    
    return numeric_prefix_part * pow(10, YEAR_POWER_DICT.get(exp_char))


def get_path_interval_earliest_latest_bp(
    no_prefix_path, 
    path_max_bp=DEFAULT_MAXIMUM_BP,  
):
    """Gets a tuple of last interval size, earliest_bp, latest_bp dates from a path
    
    :param str no_prefix_path: A chrono-path string without a prefix.
    :param float path_max_bp: The maximum BP date encoded by this chrono-path.
    
    return Tuple (path_max_bp, level_interval, block_earliest_bp, block_latest_bp)
    """
    path_depth = len(no_prefix_path)
    level_interval = path_max_bp
    block_earliest_bp = path_max_bp
    block_latest_bp = 0
    for act_path_square in no_prefix_path:
        level_interval = level_interval / 2
        if act_path_square == '0':
            block_earliest_bp -= level_interval
        elif act_path_square == '1':
            # nothing happens
            # block_earliest_bp = block_earliest_bp
            continue
        elif act_path_square == '2' :
            block_earliest_bp -= level_interval
            block_latest_bp += level_interval
        elif act_path_square == '3':
            block_latest_bp += level_interval
        else:
            raise ValueError(
                f'Chrono-tile invalid character "{act_path_square}" in {no_prefix_path}'
            )
    return path_max_bp, level_interval, block_earliest_bp, block_latest_bp


def decode_path(raw_path, path_max_bp=DEFAULT_MAXIMUM_BP):
    """Decodes a chrono-tile path into a tuple of path encoded interval values.

    :param str raw_path: A chrono-path string with or without a prefix.
    :param float path_max_bp: The default maximum BP value in the bounds of the path,
        if not otherwise provided by a prefix.

    return Tuple (path_max_bp, level_interval, earliest_bp, latest_bp)
    """
    if PREFIX_DELIM in raw_path:
        path_ex = raw_path.split(PREFIX_DELIM)
        prefix = path_ex[0].lower()
        path_max_bp = get_maximum_bp_from_prefix(prefix)
        path = path_ex[1]
    else:
        path = raw_path
    if len(path) == 0:
        # the path is empty, return the maximum BP value
        return path_max_bp, path_max_bp, path_max_bp, 0

    check_path = re.sub('[^0-3]', '', path)
    if path != check_path:
        raise ValueError(f'Chrono-tile invalid characters in "{path}"')
    
    return get_path_interval_earliest_latest_bp(
        no_prefix_path=path,
        path_max_bp=path_max_bp,
    )


def encode_path(earliest_bp, latest_bp, new_path=''):
    """Encodes a chrono tile path from earliest BP and lasted BP dates.

    :param float earliest_bp: An earliest BP date in the range
    :param float latest_bp: A latest BP date in the range
    :param str new_path: A prefix and or more general levels of the path being
        generated.

    return new_path (a chronotile path)
    """
    bp_list = [earliest_bp, latest_bp]
    bp_list.sort()
    latest_bp = bp_list[0]
    earliest_bp = bp_list[1]
    path_max_bp, level_interval, block_earliest_bp, block_latest_bp = decode_path(new_path)
    if level_interval < MIN_INTERVAL_SPAN:
        return new_path
    if raw_path_depth(new_path) >= MAX_TILE_DEPTH:
        return new_path
    if earliest_bp > path_max_bp:
        raise ValueError(f'{earliest_bp} is out of bounds, must be less than {path_max_bp}')

    half_interval = level_interval / 2
    if latest_bp < (block_latest_bp + half_interval):
        n_path = '0'
        if earliest_bp >= (block_earliest_bp - half_interval):
            n_path = '1'
    else:
        n_path = '2'
        if earliest_bp >= (block_earliest_bp - half_interval):
            n_path = '3'
    # Keep going recursively until we've reached the maximum tile depth
    # or smallest level_interval size.
    return encode_path(earliest_bp, latest_bp, (new_path + n_path))


def encode_path_from_bce_ce(earliest_bce_ce, latest_bce_ce, present_bce_ce=PRESENT, prefix=''):
    """Encodes a chrono tile path from earliest BCE/CE and lasted BCE/CE dates.
    
    :param float earliest_bce_ce: An earliest BCE/CE date in the range
    :param float latest_bce_ce: A latest BCE/CE date in the range
    :param float present_bce_ce: The BCE/CE date used as Year 0 BP.
    :param str new_path: A prefix of the path being generated.

    return new_path (a chronotile path)
    """
    if latest_bce_ce > present_bce_ce or earliest_bce_ce > present_bce_ce:
        return None  # no path created for dates later than the Present
    latest_bp = present_bce_ce- latest_bce_ce
    earliest_bp = present_bce_ce - earliest_bce_ce
    return encode_path(earliest_bp, latest_bp, prefix)


def decode_path_dates(raw_path, present_bce_ce=PRESENT):
    """ Decodes a chrono-tile path into a dictionary of BP, BCE/CE interval values.

    :param str raw_path: A chrono-path string with or without a prefix.
    :param float present_bce_ce: The BCE/CE date used as Year 0 BP.

    return dict
    """
    path_max_bp, _, earliest_bp, latest_bp = decode_path(raw_path)
    return {
        'earliest_bp': round(earliest_bp, 0),
        'latest_bp': round(latest_bp, 0),
        'earliest_bce_ce': round(present_bce_ce - earliest_bp, 0),
        'latest_bce_ce': round(present_bce_ce - latest_bp, 0),
        'path_max_bp': path_max_bp,
    }


