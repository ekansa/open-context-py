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
    MAX_TILE_DEPTH = 32
    MIN_INTERVAL_SPAN = .25
    PREFIX_DELIM = '-'
    SHOW_PROGRESS = False

    def __init__(self):
        self.block_latest = 0
        self.block_earliest = self.DEFAULT_MAXIMUM_BP
        self.path_max_bp = self.DEFAULT_MAXIMUM_BP

    def encode_path_from_bce_ce(self, latest_bce_ce, earliest_bce_ce, prefix=''):
        """
        encodes a path from latest and ealiest BCE or CE (AD) dates
        """
        if(latest_bce_ce > 1950 or earliest_bce_ce > 1950):
            return False  # no path created for dates later than 1950
        latest_bp = 1950 - latest_bce_ce
        earliest_bp = 1950 - earliest_bce_ce
        return self.encode_path(latest_bp, earliest_bp, prefix)

    def encode_path(self, latest_bp, earliest_bp, new_path=''):
        """
        encodes a path from latest and ealiest BP dates
        """
        bp_list = [latest_bp, earliest_bp]
        bp_list.sort()
        latest_bp = bp_list[0]
        earliest_bp = bp_list[1]
        level_interval = self.decode_path(new_path)
        if(level_interval >= self.MIN_INTERVAL_SPAN):
            half_interval = level_interval / 2
            if(earliest_bp > self.path_max_bp):
                # out of bound date, too early
                return False
            if(latest_bp < (self.block_latest + half_interval)):
                n_path = '0'
                if(earliest_bp >= (self.block_earliest - half_interval)):
                    n_path = '1'
            else:
                n_path = '2'
                if(earliest_bp >= (self.block_earliest - half_interval)):
                    n_path = '3'
            if(self.SHOW_PROGRESS):
                print('e:' + str(earliest_bp) + ', l:' + str(latest_bp) +
                      ' bl:' + str(self.block_latest) + ', be:' +
                      str(self.block_earliest) + ', nt:' + n_path + ', path:' + new_path + '\n')
            new_path += n_path
            new_path = self.encode_path(latest_bp, earliest_bp, new_path)
        return new_path

    def decode_path_dates(self, raw_path):
        """
        decodes a path to return a dictionary of start and end dates
        """
        output = False
        level_interval = self.decode_path(raw_path)
        if(level_interval is not False):
            output = {'earliest_bp': int(round(self.block_earliest, 0)),
                      'latest_bp': int(round(self.block_latest, 0)),
                      'earliest_bce': 1950 - int(round(self.block_earliest, 0)),
                      'latest_bce': 1950 - int(round(self.block_latest, 0))
                      }
        return output

    def decode_path(self, raw_path):
        """
        decodes a path to return start and end dates
        """
        if(self.PREFIX_DELIM in raw_path):
            path_ex = raw_path.split(self.PREFIX_DELIM)
            prefix = path_ex[0]
            self.get_prefix_maximum(prefix)
            path = path_ex[1]
        else:
            path = raw_path
        if(len(path) < 1):
            # the path is empty, return the maximum BP value
            self.block_latest = 0
            self.block_earliest = self.path_max_bp
            return self.path_max_bp
        else:
            t_path = re.sub('[^0-3]', '', path)
            if(t_path != path):
                # path contains invalid characters, return False
                return False
            else:
                return self.get_path_interval(path)

    def get_path_interval(self, path):
        """
        converts a path to a time interval
        """
        path_depth = len(path)
        self.block_latest = 0
        self.block_earliest = self.path_max_bp
        level_interval = self.path_max_bp
        i = 0
        while(i < path_depth):
            level_interval = level_interval / 2
            act_path_square = str(path[i])
            if(act_path_square == '0'):
                self.block_earliest -= level_interval
            elif(act_path_square == '1'):
                # nothing happens
                self.block_earliest = self.block_earliest
            elif(act_path_square == '2'):
                self.block_latest += level_interval
                self.block_earliest -= level_interval
            elif(act_path_square == '3'):
                self.block_latest += level_interval
            else:
                # wildy wrong character
                return False
            i += 1
        return level_interval

    def get_prefix_maximum(self, prefix):
        """
        gets the maximum BP from a path prefix
        """
        exp_dict = {'k': 3,
                    'm': 6,
                    'g': 9}
        exp_char = prefix[-1:]
        if(exp_char is not None):
            exp_char = exp_char.lower()
        numeric_prefix = self.number_cast(prefix)
        # print(str(exp_char) + " " + str(numeric_prefix))
        if(isinstance(numeric_prefix, (int, float, numbers.Number))):
            # print('\n oh yeah \n')
            if(exp_char in exp_dict):
                self.path_max_bp = numeric_prefix * pow(10, exp_dict[exp_char])
            else:
                self.path_max_bp = numeric_prefix
        return self.path_max_bp

    def raw_path_depth(self, raw_path):
        """
        gets the depth of a raw_path string
        """
        if(self.PREFIX_DELIM in raw_path):
            path_ex = raw_path.split(self.PREFIX_DELIM)
            prefix = path_ex[0]
            self.get_prefix_maximum(prefix)
            return len(path_ex[1])
        else:
            return len(raw_path)

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
