#!/usr/bin/env python
import re
import numbers


class ChronoTile():
    """
    Time ranges can be hard to present in hierarchic faceted search
    since ranges do not usually fit into standard buckets.

    To solve this problem, Open Context will start to organize time-spans using a hierarchy of 'tiles,'
    similar to the map tiles in the globalmaptiles.py class

    """

    DEFAULT_MAXIMUM_BP = 10000000  # 10 million years ago
    MAX_TILE_DEPTH = 30
    MIN_INTERVAL_SPAN = 1
    PREFIX_DELIM = '-'
    block_start = False
    block_end = False
    path_max_bp = False

    def __init__(self):
        DEFAULT_MAXIMUM_BP = 10000000  # 10 million years ago
        MAX_TILE_DEPTH = 30
        MIN_INTERVAL_SPAN = 1
        PREFIX_DELIM = '-'
        block_start = False
        block_end = False
        path_max_bp = False

    def get_path_maximum(self, raw_path):
        """
        Reads a path and checks for a prefix to indicate what the maximum value can be
        """

        self.path_max_bp = self.DEFAULT_MAXIMUM_BP
        exp_dict = {'k': 3,
                    'm': 6,
                    'g': 9}
        if(len(raw_path) > 3):
            if(self.PREFIX_DELIM in raw_path):
                path_ex = raw_path.split(self.PREFIX_DELIM)
                prefix = path_ex[0]
                exp_char = prefix[-1:]
                if(exp_char is not None):
                    exp_char = exp_char.lower()
                numeric_prefix = self.number_cast(prefix)
                print(str(exp_char) + " " + str(numeric_prefix))
                if(isinstance(numeric_prefix, (int, float, numbers.Number))):
                    print('\n oh yeah \n')
                    if(exp_char in exp_dict):
                        self.path_max_bp = numeric_prefix * pow(10, exp_dict[exp_char])
                    else:
                        self.path_max_bp = numeric_prefix
        return self.path_max_bp

    def number_cast(self, test_string):
        """
        Spits out a number from a string if numeric characters returned
        """
        t_number = re.sub('[^0-9.]', '', test_string)
        if(t_number is not None):
            try:
                return int(t_number)
            except ValueError:
                return float(t_number)
        else:
            return None
